"""
Lightweight validation and auto-fix helpers for Manim code.

This module provides:
- quick_validate(code): fast syntax checks (AST + simple patterns)
- parse_runtime_error(stderr): extract a concise error message from Manim/Python tracebacks
- attempt_auto_fix(bad_code, error, engine, model): LLM-based code correction using existing code generation logic

Intended usage:
- Before invoking Manim for preview/render, call quick_validate(code).
- If validation fails, emit an SSE message and invoke attempt_auto_fix(...) once or twice, then re-validate.
- For runtime errors from Manim (traceback), pass the relevant error text into attempt_auto_fix to request a targeted fix.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Optional, Tuple


# --- Results -----------------------------------------------------------------


@dataclass
class ValidationResult:
    ok: bool
    error: str = ""
    details: Optional[str] = None


# --- Simple validators --------------------------------------------------------


_CLASS_RE = re.compile(r"^\s*class\s+GenScene\s*\(\s*Scene\s*\)\s*:", re.MULTILINE)
_CONSTRUCT_RE = re.compile(r"^\s*def\s+construct\s*\(\s*self\s*\)\s*:", re.MULTILINE)


def _check_balanced_brackets(code: str) -> Tuple[bool, Optional[str]]:
    """
    Naive balanced bracket check for (), {}, [].
    This is not a full parser and may be confused by brackets inside strings,
    but it can still catch many simple mistakes before AST parsing is attempted.
    """
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[Tuple[str, int]] = []  # (char, index)

    for i, ch in enumerate(code):
        if ch in "([{":
            stack.append((ch, i))
        elif ch in ")]}":
            if not stack:
                return False, f"Unmatched closing bracket '{ch}' at index {i}"
            top, idx = stack.pop()
            if pairs[ch] != top:
                return False, f"Mismatched brackets: '{top}' at index {idx} vs '{ch}' at index {i}"
    if stack:
        top, idx = stack[-1]
        return False, f"Unclosed opening bracket '{top}' at index {idx}"
    return True, None


def quick_validate(code: str) -> ValidationResult:
    """
    Perform fast validation on Manim code.

    Checks:
    - Non-empty content
    - Required class and method signatures (GenScene(Scene), construct(self))
    - Naive bracket balance
    - Python AST parsing (syntax errors with line/column)

    Returns:
        ValidationResult(ok=True) if code seems valid enough to attempt running Manim.
        Otherwise, ok=False with an error message.
    """
    if not code or not code.strip():
        return ValidationResult(False, "Empty code.")

    # Required structure (best-effort checks)
    if "class GenScene" not in code:
        return ValidationResult(False, "Missing 'class GenScene' definition.")
    if not _CLASS_RE.search(code):
        return ValidationResult(
            False,
            "Expected 'class GenScene(Scene):' with proper parentheses."
        )
    if "def construct" not in code or not _CONSTRUCT_RE.search(code):
        return ValidationResult(False, "Missing 'def construct(self):' method in GenScene.")

    # Naive bracket balance
    ok, msg = _check_balanced_brackets(code)
    if not ok:
        return ValidationResult(False, f"Bracket balance error: {msg}")

    # AST parse (definitive syntax check)
    try:
        ast.parse(code)
    except SyntaxError as e:
        # Build a concise error message with line context if available
        line = e.text.strip() if e.text else ""
        where = f"line {getattr(e, 'lineno', '?')}, col {getattr(e, 'offset', '?')}"
        msg = f"SyntaxError: {e.msg} at {where}"
        details = f"{line}" if line else None
        return ValidationResult(False, msg, details)

    return ValidationResult(True)


# --- Runtime error parsing ----------------------------------------------------


_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE)


def parse_runtime_error(stderr: str, tail_chars: int = 2000) -> str:
    """
    Extract a concise error summary from Manim/Python stderr output.

    Strategy:
    - If a Python traceback exists, return the last non-empty line after the traceback block.
    - Else, if 'SyntaxError:' appears, return the line containing it.
    - Else, return the tail of stderr.

    Args:
        stderr: Full stderr text captured from a failed Manim run.
        tail_chars: Fallback to the last N chars for compactness.

    Returns:
        A short, human/LLM-friendly error message string.
    """
    stderr = stderr or ""
    lines = [ln.rstrip("\n") for ln in stderr.splitlines()]

    # If there's a traceback, grab the last meaningful line (typically "ErrorType: message")
    if _TRACEBACK_RE.search(stderr):
        for ln in reversed(lines):
            if ln.strip():
                return ln.strip()

    # If a SyntaxError line appears without a full traceback
    for ln in lines:
        if "SyntaxError:" in ln:
            return ln.strip()

    # Fallback: return tail
    return stderr[-tail_chars:].strip()


# --- Auto-fix (LLM-driven) ---------------------------------------------------


def _build_fix_prompt(bad_code: str, error: str) -> str:
    """
    Construct a targeted prompt to repair Manim code while preserving intent.
    """
    return (
        "The following Manim Python code fails to run. Fix it.\n\n"
        "Constraints:\n"
        "- Return ONLY valid Python code (no backticks, no explanations).\n"
        "- Must contain exactly one class: GenScene(Scene) with def construct(self).\n"
        "- Use stable Manim primitives (Text, Circle, Square, Create, Write, FadeIn, etc.).\n"
        "- Ensure all parentheses/brackets/braces are balanced.\n"
        "- Avoid extraneous imports or config changes unless required.\n"
        "- Preserve the original animation intent.\n\n"
        f"Error observed:\n{error}\n\n"
        "Original code:\n"
        f"{bad_code}\n"
    )


class AutoFixError(Exception):
    """Raised when auto-fix fails or cannot produce valid code."""
    pass


def attempt_auto_fix(
    bad_code: str,
    error: str,
    *,
    engine: str = "anthropic",
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 1200,
) -> str:
    """
    Attempt to auto-fix Manim code using the existing LLM code generation tool.

    Args:
        bad_code: The original (invalid) Manim code.
        error: A short error description (e.g., from quick_validate or parse_runtime_error).
        engine: "openai" | "anthropic" (passed through to the code generator).
        model: Optional model ID override for the selected engine.
        temperature: Sampling temperature (defaults low for deterministic fixes).
        max_tokens: Max tokens for the completion.

    Returns:
        The corrected Manim code as a string.

    Raises:
        AutoFixError: If the LLM call fails or produces invalid output.
    """
    try:
        # Lazy import to avoid heavy deps at module import time
        from agents.tools.code_generation import generate_manim_code, CodeGenerationError
    except Exception as e:
        raise AutoFixError(f"Code generation tools unavailable: {e}")

    prompt = _build_fix_prompt(bad_code=bad_code, error=error)

    try:
        fixed = generate_manim_code(
            prompt=prompt,
            engine=engine,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            extra_rules="Ensure the output is syntactically valid Python and runnable by Manim.",
        )
    except Exception as e:
        # Normalize underlying error type
        if "CodeGenerationError" in type(e).__name__:
            raise AutoFixError(str(e))
        raise AutoFixError(f"Auto-fix call failed: {e}")

    # Validate the fixed code quickly to fail fast if still broken
    v = quick_validate(fixed)
    if not v.ok:
        raise AutoFixError(f"Auto-fix produced invalid code: {v.error}")

    return fixed


__all__ = [
    "ValidationResult",
    "quick_validate",
    "parse_runtime_error",
    "attempt_auto_fix",
    "AutoFixError",
]
