"""
Animation Intent Detection Module

This module detects whether a user wants an animation and what type.
Updated to use the new chart_inference module for smarter detection
when data is available.

Intended usage:
    from agents.tools.intent_detection import detect_animation_intent, is_animation_intent

    result = detect_animation_intent(user_message, csv_path="/path/to/data.csv")
    if result.animation_requested:
        print(f"Chart type: {result.chart_type}")
        print(f"Confidence: {result.confidence}")
    else:
        # Text-only or non-animation path
        pass

Design notes:
- Pure regex/heuristic for quick checks (no LLM calls).
- Integrates with chart_inference for data-driven recommendations.
- Supports all 5 chart types: bubble, distribution, bar_race, line_evolution, bento_grid.
- Multilingual keywords (ID/EN) for common phrasing.
"""

from __future__ import annotations

import re
import logging
import time
from dataclasses import dataclass, field
from typing import List, Optional

# Setup logging
_logger = logging.getLogger("intent_detection")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))
    _logger.addHandler(handler)


def _log(level: str, message: str, context: dict = None):
    """Internal logging helper."""
    context = context or {}
    log_msg = f"[intent_detection] {message}"
    if context:
        log_msg += f" | {context}"

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    _logger.log(level_map.get(level.upper(), logging.INFO), log_msg)


# =============================================================================
# ANIMATION INTENT PATTERNS
# =============================================================================

# Strong animation keywords (ID + EN)
_STRONG_ANIM_PATTERNS = [
    r"\banimasi\b",            # ID: animasi
    r"\banimasikan\b",         # ID: animasikan data
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

# Medium-strength context tokens
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

# Code cue (explicit user-provided Manim code)
_CODE_CUES = [
    r"\bclass\s+GenScene\b",
    r"\bfrom\s+manim\s+import\b",
    r"\bScene\):",  # class ... (Scene):
]


# =============================================================================
# CHART TYPE PATTERNS (All 5 chart types)
# =============================================================================

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

_BAR_RACE_PATTERNS = [
    r"\bbar\s*(chart\s*)?race\b",
    r"\bracing\s*bar\b",
    r"\branking\b",
    r"\bperingkat\b",
    r"\btop\s*\d+\b",
    r"\bleaderboard\b",
    r"\blomba\s*bar\b",
]

_LINE_EVOLUTION_PATTERNS = [
    r"\bline\s*(chart|evolution|graph)?\b",
    r"\bgrafik\s*garis\b",
    r"\btrend\b",
    r"\btren\b",
    r"\btime\s*series\b",
    r"\bevolution\b",
    r"\bevolusi\b",
    r"\btrajectory\b",
]

_BENTO_GRID_PATTERNS = [
    r"\bbento\s*(grid|box)?\b",
    r"\bdashboard\b",
    r"\bkpi\b",
    r"\bmetric(s)?\b",
    r"\bkey\s*indicator\b",
    r"\boverview\b",
    r"\bsummary\b",
    r"\bringkasan\b",
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class IntentResult:
    """Result of intent detection"""
    animation_requested: bool
    chart_type: str = "unknown"  # "bubble" | "distribution" | "bar_race" | "line_evolution" | "bento_grid" | "unknown"
    confidence: float = 0.0       # 0.0 - 1.0
    reasons: List[str] = field(default_factory=list)

    # Additional info from data analysis
    data_analyzed: bool = False
    recommended_charts: List[str] = field(default_factory=list)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _compile_any(patterns: List[str]) -> re.Pattern:
    """Compile a list of patterns into a single regex"""
    joined = "|".join(f"(?:{p})" for p in patterns)
    return re.compile(joined, flags=re.IGNORECASE | re.MULTILINE)


# Pre-compile all regex patterns
_RE_STRONG = _compile_any(_STRONG_ANIM_PATTERNS)
_RE_MEDIUM = _compile_any(_MEDIUM_ANIM_PATTERNS)
_RE_CODE = _compile_any(_CODE_CUES)
_RE_BUBBLE = _compile_any(_BUBBLE_PATTERNS)
_RE_DIST = _compile_any(_DISTRIBUTION_PATTERNS)
_RE_BAR_RACE = _compile_any(_BAR_RACE_PATTERNS)
_RE_LINE_EVOLUTION = _compile_any(_LINE_EVOLUTION_PATTERNS)
_RE_BENTO_GRID = _compile_any(_BENTO_GRID_PATTERNS)


def _collect_matches(text: str, pattern: re.Pattern, label: str) -> List[str]:
    """Collect all matches for a pattern with a label prefix"""
    return [f"{label}:{m.group(0)}" for m in pattern.finditer(text or "")]


def _score_animation_intent(
    strong_hits: int,
    medium_hits: int,
    has_code: bool,
    chart_hint: bool,
) -> float:
    """
    Calculate confidence score for animation intent.

    Scoring:
      - Code present: 1.0 (definite animation request)
      - Strong tokens: 0.45 each
      - Medium tokens: 0.20 each
      - Chart hint: +0.10
    """
    if has_code:
        return 1.0

    score = 0.0
    score += strong_hits * 0.45
    score += medium_hits * 0.20
    if chart_hint:
        score += 0.10

    return min(score, 1.0)


def _infer_chart_type_from_keywords(text: str) -> str:
    """
    Infer chart type from keywords in text.
    Supports all 5 chart types.
    """
    scores = {
        "bubble": len(_RE_BUBBLE.findall(text)),
        "distribution": len(_RE_DIST.findall(text)),
        "bar_race": len(_RE_BAR_RACE.findall(text)),
        "line_evolution": len(_RE_LINE_EVOLUTION.findall(text)),
        "bento_grid": len(_RE_BENTO_GRID.findall(text)),
    }

    # Find the chart type with the most keyword matches
    best_type = max(scores.items(), key=lambda x: x[1])

    if best_type[1] > 0:
        return best_type[0]

    return "unknown"


# =============================================================================
# MAIN DETECTION FUNCTIONS
# =============================================================================

def quick_intent_check(message: Optional[str]) -> IntentResult:
    """
    Quick heuristic-only detection (no data analysis).
    Use this when you don't have a CSV path.

    Threshold logic:
      - If code cues detected: animation_requested=True with confidence=1.0
      - Else compute score from tokens; requested=True if score >= 0.45
    """
    start_time = time.time()
    _log("DEBUG", "Starting quick intent check", {
        "message_length": len(message) if message else 0,
    })

    text = message or ""
    reasons: List[str] = []

    code_hits = _collect_matches(text, _RE_CODE, "code")
    strong_hits = _collect_matches(text, _RE_STRONG, "strong")
    medium_hits = _collect_matches(text, _RE_MEDIUM, "medium")

    _log("DEBUG", "Pattern matching results", {
        "code_hits": len(code_hits),
        "strong_hits": len(strong_hits),
        "medium_hits": len(medium_hits),
    })

    reasons.extend(code_hits[:5])
    reasons.extend(strong_hits[:5])
    reasons.extend(medium_hits[:5])

    has_code = len(code_hits) > 0
    strong_count = len(strong_hits)
    medium_count = len(medium_hits)

    # Use the expanded chart type detection
    chart_type = _infer_chart_type_from_keywords(text)
    chart_hint = chart_type != "unknown"

    confidence = _score_animation_intent(strong_count, medium_count, has_code, chart_hint)
    animation_requested = has_code or (confidence >= 0.45)

    elapsed_ms = (time.time() - start_time) * 1000
    _log("INFO", "Quick intent check completed", {
        "animation_requested": animation_requested,
        "chart_type": chart_type,
        "confidence": round(confidence, 3),
        "has_code": has_code,
        "elapsed_ms": round(elapsed_ms, 2),
    })

    return IntentResult(
        animation_requested=animation_requested,
        chart_type=chart_type,
        confidence=confidence,
        reasons=reasons,
        data_analyzed=False,
    )


def detect_animation_intent(
    message: Optional[str],
    csv_path: Optional[str] = None,
) -> IntentResult:
    """
    Full intent detection with optional data analysis.

    If csv_path is provided, uses the smart chart_inference module
    to recommend the best chart type based on data structure.

    Args:
        message: User's message/prompt
        csv_path: Optional path to CSV file for data-driven inference

    Returns:
        IntentResult with animation_requested, chart_type, confidence, etc.
    """
    start_time = time.time()
    _log("INFO", "Starting full intent detection", {
        "message_length": len(message) if message else 0,
        "has_csv_path": bool(csv_path),
        "csv_path": csv_path,
    })

    # Start with keyword-based detection
    result = quick_intent_check(message)

    # If we have a CSV path, enhance with data analysis
    if csv_path and result.animation_requested:
        _log("INFO", "Enhancing with data-driven analysis", {
            "csv_path": csv_path,
            "initial_chart_type": result.chart_type,
            "initial_confidence": result.confidence,
        })

        try:
            from agents.tools.chart_inference import recommend_chart

            # Get data-driven recommendations
            _log("DEBUG", "Calling chart inference module", {"csv_path": csv_path})
            recommendations = recommend_chart(csv_path, message)

            if recommendations:
                best = recommendations[0]

                # Update result with data-driven chart type
                result.data_analyzed = True
                result.recommended_charts = [r.chart_type for r in recommendations[:3]]

                # If keyword detection was "unknown", use data-driven result
                if result.chart_type == "unknown":
                    result.chart_type = best.chart_type
                    result.reasons.append(f"Data analysis suggests: {best.chart_type} (score={best.score})")
                    result.confidence = max(result.confidence, best.score)

                # If keyword detection found a type, but data suggests different
                elif result.chart_type != best.chart_type:
                    # Check if data strongly suggests something else
                    if best.score >= 0.8 and best.confidence == "high":
                        result.reasons.append(
                            f"Note: Data structure better fits '{best.chart_type}' "
                            f"(score={best.score}) than '{result.chart_type}'"
                        )

                # Add data analysis reasons
                for reason in best.reasons[:3]:
                    result.reasons.append(f"[Data] {reason}")

        except ImportError as e:
            # chart_inference module not available
            _log("WARNING", "chart_inference module not available", {"error": str(e)})
            result.reasons.append("Data analysis skipped: chart_inference module not available")
        except FileNotFoundError as e:
            # CSV file not found
            _log("WARNING", "CSV file not found for data analysis", {
                "csv_path": csv_path,
                "error": str(e),
            })
            result.reasons.append(f"Data analysis skipped: CSV file not found at {csv_path}")
        except Exception as e:
            # Other errors - continue with keyword-only result
            _log("ERROR", f"Data analysis failed: {e}", {
                "csv_path": csv_path,
                "error_type": type(e).__name__,
                "error": str(e),
            })
            result.reasons.append(f"Data analysis skipped: {e}")

    elapsed_ms = (time.time() - start_time) * 1000
    _log("INFO", "Intent detection completed", {
        "animation_requested": result.animation_requested,
        "chart_type": result.chart_type,
        "confidence": round(result.confidence, 3),
        "data_analyzed": result.data_analyzed,
        "recommended_charts": result.recommended_charts,
        "elapsed_ms": round(elapsed_ms, 2),
    })

    return result


def is_animation_intent(message: Optional[str]) -> bool:
    """Convenience boolean helper"""
    return detect_animation_intent(message).animation_requested


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    "IntentResult",
    "quick_intent_check",
    "detect_animation_intent",
    "is_animation_intent",
]
