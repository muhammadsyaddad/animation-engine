"""
Regex-based animation intent detection utilities.

This module provides lightweight, dependency-free helpers to detect whether a user
is asking for animated data visualization (e.g., Manim video), and to infer an
intended chart type (bubble/distribution) directly from the text.

Intended usage (gate your pipeline):
    from agents.tools.intent_detection import detect_animation_intent, is_animation_intent

    result = detect_animation_intent(user_message)
    if result.animation_requested:
        # Turn on "Danim Mode" / animation pipeline
        ...
    else:
        # Text-only or non-animation path
        ...

Design notes:
- Pure regex/heuristic (no LLM calls).
- Conservative scoring + threshold to prevent false positives.
- Multilingual keywords (ID/EN) for common phrasing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# Strong animation keywords (ID + EN)
# Rationale: These terms strongly imply "animated output" rather than static chart.
_STRONG_ANIM_PATTERNS = [
    r"\banimasi\b",            # ID: animasi
    r"\banimasikan\b",         # ID: anmasikan data
    r"\banimate\b",
    r"\banimation\b",
    r"\banimating\b",
    r"\banimated\b",
    r"\bgerakkan\b",           # ID: gerakkan data
    r"\bbergerak\b",           # ID: objek bergerak
    r"\bmanim\b",              # explicit Manim mention
    r"\bvideo\b",
    r"\bmp4\b",
    r"\bgif\b",
    r"\brender\b",
    r"\bpreview\b",
]

# Medium-strength context tokens that often co-occur with animation requests
_MEDIUM_ANIM_PATTERNS = [
    r"\bframe\b",
    r"\bframes\b",
    r"\btimeline\b",
    r"\btime[\s-]?series\b",
    r"\btime[\s-]?lapse\b",
    r"\bper\s*tahun\b",        # ID: per tahun (per-year progression)
    r"\bper\s*waktu\b",        # ID: over time
    r"\bper\s*year\b",
    r"\bover\s*time\b",
]

# Chart-type hints
_BUBBLE_PATTERNS = [
    r"\bbubble\s*chart\b",
    r"\bbubblechart\b",
    r"\bbubble\b",
    r"\bgelembung\b",          # ID: bubble
    r"\bsebar\b",              # ID: sebar (scatter-like)
    r"\bscatter\b",
]

_DISTRIBUTION_PATTERNS = [
    r"\bdistribution\b",
    r"\bdistribusi\b",
    r"\bhistogram\b",
    r"\bkde\b",
    r"\bdensity\b",
    r"\bstacked\s*distribution\b",
]

# Code cue (explicit user-provided Manim code)
_CODE_CUES = [
    r"\bclass\s+GenScene\b",
    r"\bfrom\s+manim\s+import\b",
    r"\bScene\):",  # class ... (Scene):
]


@dataclass
class IntentResult:
    animation_requested: bool
    chart_type: str = "unknown"  # "bubble" | "distribution" | "unknown"
    confidence: float = 0.0       # 0.0 - 1.0
    reasons: List[str] = field(default_factory=list)


def _compile_any(patterns: List[str]) -> re.Pattern:
    joined = "|".join(f"(?:{p})" for p in patterns)
    return re.compile(joined, flags=re.IGNORECASE | re.MULTILINE)


# Pre-compile regex
_RE_STRONG = _compile_any(_STRONG_ANIM_PATTERNS)
_RE_MEDIUM = _compile_any(_MEDIUM_ANIM_PATTERNS)
_RE_BUBBLE = _compile_any(_BUBBLE_PATTERNS)
_RE_DIST = _compile_any(_DISTRIBUTION_PATTERNS)
_RE_CODE = _compile_any(_CODE_CUES)


def _collect_matches(text: str, pattern: re.Pattern, label: str) -> List[str]:
    return [f"{label}:{m.group(0)}" for m in pattern.finditer(text or "")]


def _score_intent(strong_hits: int, medium_hits: int, has_code: bool, chart_hint: bool) -> float:
    """
    Weighted scoring to estimate confidence that user wants an animation:
      - Code present (class GenScene / from manim import): 1.0
      - Strong tokens: 0.45 each (cap later)
      - Medium tokens: 0.20 each (cap later)
      - Chart hint: +0.10 (bubble/distribution present)
    Score is clamped to [0, 1].
    """
    if has_code:
        return 1.0

    score = 0.0
    score += strong_hits * 0.45
    score += medium_hits * 0.20
    if chart_hint:
        score += 0.10

    # Cap to 1.0
    if score > 1.0:
        score = 1.0
    return score


def _infer_chart_type(text: str) -> str:
    bubble = bool(_RE_BUBBLE.search(text))
    dist = bool(_RE_DIST.search(text))
    if bubble and not dist:
        return "bubble"
    if dist and not bubble:
        return "distribution"
    # Both present or neither → unknown (we'll let downstream spec resolver decide)
    return "unknown"


def quick_intent_check(message: Optional[str]) -> IntentResult:
    """
    Heuristic-only detection. Returns IntentResult without calling external services.

    Threshold logic:
      - If code cues detected: animation_requested=True with confidence=1.0
      - Else compute score from tokens; requested=True if score >= 0.45
    """
    text = message or ""
    reasons: List[str] = []

    code_hits = _collect_matches(text, _RE_CODE, "code")
    strong_hits = _collect_matches(text, _RE_STRONG, "strong")
    medium_hits = _collect_matches(text, _RE_MEDIUM, "medium")

    reasons.extend(code_hits[:5])   # limit reasons length to keep it small
    reasons.extend(strong_hits[:5])
    reasons.extend(medium_hits[:5])

    has_code = len(code_hits) > 0
    strong_count = len(strong_hits)
    medium_count = len(medium_hits)

    chart_type = _infer_chart_type(text)
    chart_hint = chart_type in ("bubble", "distribution")

    confidence = _score_intent(strong_count, medium_count, has_code, chart_hint)
    animation_requested = has_code or (confidence >= 0.45)

    return IntentResult(
        animation_requested=animation_requested,
        chart_type=chart_type,
        confidence=confidence,
        reasons=reasons,
    )


def detect_animation_intent(message: Optional[str]) -> IntentResult:
    """
    Public API for intent detection. Currently just a wrapper over quick_intent_check
    to allow future extension (e.g., LLM refinement) without changing call sites.
    """
    return quick_intent_check(message)


def is_animation_intent(message: Optional[str]) -> bool:
    """
    Convenience boolean helper.
    """
    return detect_animation_intent(message).animation_requested


__all__ = [
    "IntentResult",
    "quick_intent_check",
    "detect_animation_intent",
    "is_animation_intent",
]
