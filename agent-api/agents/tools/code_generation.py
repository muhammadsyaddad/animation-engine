"""
Code generation tool for producing Manim code from natural language prompts.

This module calls Anthropic Claude models to generate Manim code that follows
specific constraints (e.g., GenScene class). OpenAI support has been removed.

Usage:
    from agents.tools.code_generation import generate_manim_code, CodeGenerationError

    code = generate_manim_code(
        prompt="Buat animasi lingkaran biru yang muncul dan membesar.",
        model=None,                   # optional; defaults to Claude Sonnet
        temperature=0.2,
        max_tokens=1200,
    )
"""

from __future__ import annotations

import os
import re
from typing import Optional, List

# Lazy imports inside functions to avoid import errors when an engine is unused.


class CodeGenerationError(Exception):
    """Raised when code generation fails or returns invalid output."""
    pass


# Default models per engine. Adjust if your environment has different availability.
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
}

VALID_MODELS = {
    "anthropic": {"claude-sonnet-4-20250514"},
}


def _build_system_prompt(extra_rules: Optional[str] = None) -> str:
    """
    Returns a system prompt that guides the model to output only Manim code,
    following constraints compatible with downstream rendering.
    """
    base_rules = """
You are an assistant that knows about Manim. Manim is a mathematical animation engine used to create videos programmatically.

Return ONLY valid Python code for Manim. Do NOT include explanations or backticks in your final output.

Example minimal structure:
from manim import *
from math import *

class GenScene(Scene):
    def construct(self):
        c = Circle(color=BLUE)
        self.play(Create(c))

Rules:
1) Always define the class exactly as: GenScene(Scene).
2) Always place animation logic inside GenScene.construct(self).
3) Always use self.play(...) to run animations.
4) Do NOT include any non-code commentary, markdown, or backticks.
5) Prefer primitives available in stable Manim APIs (e.g., Text, Circle, Square, Create, Write, FadeIn, etc.).
6) If the user does not specify aspect ratio or resolution, do not add config changes; just provide scene code.
"""
    if extra_rules:
        base_rules += "\nAdditional rules:\n" + extra_rules.strip() + "\n"
    return base_rules.strip()


_CODE_FENCE_RE = re.compile(
    r"```(?:python|py)?\s*(?P<code>[\s\S]*?)```", re.IGNORECASE
)


def _extract_code_from_text(text: str) -> str:
    """
    Extract code from a response. If code fences exist, prefer their contents.
    Otherwise return the full text (after trimming).
    """
    if not text:
        return ""
    m = _CODE_FENCE_RE.search(text)
    if m:
        return m.group("code").strip()
    # No fences; return as-is (trimmed)
    return text.strip()


def _clean_output(code: str) -> str:
    """
    Post-process the model output to ensure it's pure code:
    - Strip surrounding backticks if any remain.
    - Ensure it contains 'class GenScene' (best-effort).
    """
    if not code:
        return code

    # Remove stray triple backticks if any slipped through
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3].strip()

    # The contract strongly suggests GenScene must be present.
    # We don't try to rewrite user code; just pass it along.
    return code


# OpenAI path removed (OpenAI support deprecated for this project).


def _call_anthropic(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str,
    api_key: Optional[str],
) -> str:
    try:
        import anthropic
    except Exception as e:
        raise CodeGenerationError(f"Anthropic SDK not available: {e}")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        resp = client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        raise CodeGenerationError(f"Anthropic call failed: {e}")

    # Anthropics returns a list of content blocks; collect text parts.
    try:
        blocks: List = resp.content or []
        text = "".join(
            getattr(block, "text", "") for block in blocks if getattr(block, "type", "") == "text"
        )
    except Exception as e:
        raise CodeGenerationError(f"Unexpected Anthropic response format: {e}")

    code = _extract_code_from_text(text)
    code = _clean_output(code)

    if "class GenScene" not in code:
        raise CodeGenerationError("Generated code does not define 'class GenScene'.")

    return code


def generate_manim_code(
    prompt: str,
    *,
    engine: str = "anthropic",
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    extra_rules: Optional[str] = None,
) -> str:
    """
    Generate Manim code from a natural-language prompt using the selected engine.

    Args:
        prompt: Natural-language instruction describing the desired animation.
        engine: "openai" or "anthropic".
        model: Optional model ID. If omitted, a default for the engine is used.
        temperature: Sampling temperature for the model.
        max_tokens: Maximum tokens for the completion.
        extra_rules: Additional constraints appended to the system prompt.

    Returns:
        Manim Python code as a string. Must contain class GenScene(Scene).

    Raises:
        CodeGenerationError: If the model call fails or code is invalid.
    """
    engine = (engine or "anthropic").lower().strip()
    if engine not in DEFAULT_MODELS:
        raise CodeGenerationError(f"Invalid engine '{engine}'. Use one of: {list(DEFAULT_MODELS.keys())}")

    if model is None:
        model = DEFAULT_MODELS[engine]
    else:
        model = model.strip()
        # If we have a validation set for this engine, enforce it (best-effort).
        valid = VALID_MODELS.get(engine)
        if valid and model not in valid:
            raise CodeGenerationError(
                f"Invalid model '{model}' for engine '{engine}'. Valid: {sorted(valid)}"
            )

    system_prompt = _build_system_prompt(extra_rules=extra_rules)

    # OpenAI branch removed; only Anthropic is supported.

    if engine == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        return _call_anthropic(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            api_key=api_key,
        )

    # Should never reach here
    raise CodeGenerationError(f"Unhandled engine '{engine}'")
