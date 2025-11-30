"""
Auto-fix utilities for Manim code.

Provides:
  - Static syntax validation (AST parse + required class check).
  - Classification of common Python / Manim generation errors.
  - Iterative LLM-driven repair attempts using the existing `generate_manim_code` tool.
  - Helpers to integrate into the streaming pipeline (return structured events).

Typical usage inside a run pipeline (pseudocode in `agents/routes/agents.py`):
    from agents.tools.auto_fix import quick_validate, fix_code_with_iterations

    validation = quick_validate(code)
    if not validation.ok:
        # Attempt syntax auto-fix (max 2 tries)
        code, attempts, last_error = fix_code_with_iterations(
            initial_code=code,
            initial_error=validation.error,
            max_attempts=2,
            engine="anthropic",
            model=None,
        )
        if code is None:
            # Emit RunError and abort
            ...

Runtime traceback handling:
    If preview tool returns a traceback (e.g., NameError, AttributeError), call
    `fix_code_with_iterations` again with the original code + error message.

NOTE: We intentionally keep execution sandbox-free (no exec) for safety. Only AST parsing
and regex scanning is done. Downstream Manim runtime does deeper validation.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

from agents.tools.code_generation import generate_manim_code, CodeGenerationError


# -------------------------------------------------------------------------------------------------
# Data Structures
# -------------------------------------------------------------------------------------------------

@dataclass
class ValidationResult:
    ok: bool
    error: str = ""


@dataclass
class FixResult:
    """
    Result of a multi-attempt fix procedure.

    Attributes:
        code: The successfully fixed code (None if not fixed).
        attempts: Number of fix attempts performed.
        last_error: Final error encountered if code is None.
        history: List of (attempt_index, error_message) for traceability.
    """
    code: Optional[str]
    attempts: int
    last_error: Optional[str]
    history: List[Tuple[int, str]]


# -------------------------------------------------------------------------------------------------
# Syntax Validation
# -------------------------------------------------------------------------------------------------

_GENSCENE_CLASS_RE = re.compile(r"class\s+GenScene\s*\(\s*Scene\s*\)\s*:", re.MULTILINE)


def quick_validate(code: str) -> ValidationResult:
    """
    Perform quick static validation:
      - Non-empty
      - Contains 'class GenScene(Scene):'
      - AST parses without SyntaxError
      - Basic parentheses/brackets/braces balance check

    Returns:
        ValidationResult(ok=True) if passes, else ok=False with error detail.
    """
    if not code or not code.strip():
        return ValidationResult(False, "Empty code.")

    if "class GenScene" not in code:
        return ValidationResult(False, "Missing 'class GenScene' definition.")

    if not _GENSCENE_CLASS_RE.search(code):
        return ValidationResult(False, "GenScene class must be exactly 'class GenScene(Scene):'.")

    try:
        ast.parse(code)
    except SyntaxError as e:
        # Include line + snippet if available
        snippet = (e.text or "").strip()
        msg = f"SyntaxError: {e.msg} at line {e.lineno}: {snippet}"
        return ValidationResult(False, msg)

    # Balance check for (), {}, []
    if not _balanced_delimiters(code):
        return ValidationResult(False, "Unbalanced parentheses/brackets/braces detected.")

    return ValidationResult(True, "")


def _balanced_delimiters(code: str) -> bool:
    """
    Rough delimiter balance checker. Does not handle strings intricately but is
    sufficient to catch most truncated generations.
    """
    stack = []
    opening = "([{"
    closing = ")]}"
    mapping = {")": "(", "]": "[", "}": "{"}
    for ch in code:
        if ch in opening:
            stack.append(ch)
        elif ch in closing:
            if not stack or stack[-1] != mapping[ch]:
                return False
            stack.pop()
    return not stack


# -------------------------------------------------------------------------------------------------
# Error Classification
# -------------------------------------------------------------------------------------------------

_FIXABLE_ERROR_PATTERNS = [
    re.compile(r"SyntaxError", re.IGNORECASE),
    re.compile(r"NameError", re.IGNORECASE),
    re.compile(r"AttributeError", re.IGNORECASE),
    re.compile(r"IndentationError", re.IGNORECASE),
    re.compile(r"unbalanced parenthesis", re.IGNORECASE),
    re.compile(r"was never closed", re.IGNORECASE),
    re.compile(r"invalid syntax", re.IGNORECASE),
]


def is_fixable_error(error_text: str) -> bool:
    """
    Heuristic: return True if the error appears to be automatically fixable by regeneration.
    """
    if not error_text:
        return False
    for pat in _FIXABLE_ERROR_PATTERNS:
        if pat.search(error_text):
            return True
    return False


def extract_primary_error_line(error_text: str) -> str:
    """
    Try to isolate the most meaningful line from a traceback or error blob.
    """
    if not error_text:
        return ""

    lines = [l for l in error_text.splitlines() if l.strip()]
    # From bottom up, look for common Python error patterns
    for line in reversed(lines):
        if any(k in line for k in ["Error", "Exception", "SyntaxError", "Traceback"]):
            return line.strip()
    # Fallback: first non-empty line
    return lines[0].strip() if lines else ""


# -------------------------------------------------------------------------------------------------
# Auto-Fix Prompt Construction
# -------------------------------------------------------------------------------------------------

def _build_fix_prompt(bad_code: str, error: str) -> str:
    """
    Construct a targeted prompt to repair code while preserving intent.
    """
    primary = extract_primary_error_line(error)
    return f"""
The following Manim Python code has an error that prevents execution or preview.

Error Summary:
{primary or error}

Full Error (for context):
{error}

Task:
- Correct ONLY the code.
- Preserve all intended animations and objects where possible.
- Keep the scene named GenScene(Scene) with a construct method.
- Ensure balanced parentheses, brackets, and braces.
- Do not add textual explanations, comments, or markdown.
- Return ONLY valid Python code (no backticks).

Original code:
{bad_code}
""".strip()


# -------------------------------------------------------------------------------------------------
# Single Attempt Fix
# -------------------------------------------------------------------------------------------------

def attempt_auto_fix(
    bad_code: str,
    error: str,
    engine: str = "anthropic",
    model: Optional[str] = None,
    temperature: float = 0.15,
    max_tokens: int = 1200,
) -> str:
    """
    Invoke LLM to repair given code using existing code generation tool.

    Raises:
        CodeGenerationError if underlying generation fails.
    """
    fix_prompt = _build_fix_prompt(bad_code=bad_code, error=error)
    # We reuse generate_manim_code. `extra_rules` can reinforce constraints.
    extra_rules = (
        "Repair the code. Keep the original scene logic. "
        "Avoid introducing unrelated imports or global config beyond necessity."
    )
    return generate_manim_code(
        prompt=fix_prompt,
        engine=engine,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_rules=extra_rules,
    )


# -------------------------------------------------------------------------------------------------
# Multi-Attempt Orchestrator
# -------------------------------------------------------------------------------------------------

def fix_code_with_iterations(
    initial_code: str,
    initial_error: Optional[str],
    max_attempts: int = 2,
    engine: str = "anthropic",
    model: Optional[str] = None,
    include_runtime_errors: bool = True,
) -> Tuple[Optional[str], int, Optional[str]]:
    """
    High-level fix loop:
      - Validate syntax first.
      - If syntax invalid OR initial_error is fixable, attempt iterative repair.
      - Optionally consider runtime errors (tracebacks) for fix triggers.

    Returns:
        (final_code_or_None, attempts_used, last_error_or_None)

    NOTE:
        For richer telemetry, integrate with `FixResult` builder below.
    """
    result = fix_code_with_iterations_verbose(
        initial_code=initial_code,
        initial_error=initial_error,
        max_attempts=max_attempts,
        engine=engine,
        model=model,
        include_runtime_errors=include_runtime_errors,
    )
    return result.code, result.attempts, result.last_error


def fix_code_with_iterations_verbose(
    initial_code: str,
    initial_error: Optional[str],
    max_attempts: int = 4,
    engine: str = "anthropic",
    model: Optional[str] = None,
    include_runtime_errors: bool = True,
) -> FixResult:
    """
    Verbose variant returning a FixResult object with history.

    Strategy:
      1. Run quick_validate on initial_code.
      2. If ok and no fixable error -> return immediately.
      3. Else loop up to max_attempts:
           - attempt_auto_fix with current code + error
           - validate new code
           - break early on success
      4. Return FixResult with final status.

    `initial_error`:
        - Syntax or runtime error message captured earlier (e.g., from preview stderr).
        - If None but validation fails, we synthesize a syntax message.

    Runtime errors:
        If `include_runtime_errors` = True and `initial_error` is a fixable runtime error (NameError etc.),
        we treat it like a syntax error and try to fix.

    """
    history: List[Tuple[int, str]] = []

    # Step 1: Baseline validation
    validation = quick_validate(initial_code)
    need_fix = not validation.ok

    # Step 2: If there's an initial error that is fixable (even if syntax validated),
    # mark that we need to attempt a repair.
    if not need_fix and initial_error and include_runtime_errors and is_fixable_error(initial_error):
        need_fix = True
        # If syntax is fine but runtime error present, treat runtime error as current "error"
        if validation.ok:
            validation = ValidationResult(False, initial_error)

    if not need_fix:
        return FixResult(code=initial_code, attempts=0, last_error=None, history=history)

    current_code = initial_code
    current_error = validation.error if validation.error else (initial_error or "Unknown error")

    # Step 3: Iterative repair
    attempts = 0
    while attempts < max_attempts:
        history.append((attempts, current_error))
        try:
            fixed = attempt_auto_fix(
                bad_code=current_code,
                error=current_error,
                engine=engine,
                model=model,
            )
        except CodeGenerationError as e:
            # Generation failure counts as an attempt
            attempts += 1
            current_error = f"Auto-fix generation failed: {e}"
            continue

        # Validate fixed code
        v = quick_validate(fixed)
        if v.ok:
            return FixResult(code=fixed, attempts=attempts + 1, last_error=None, history=history)
        else:
            # Prepare next iteration
            attempts += 1
            current_code = fixed
            current_error = v.error

    # Exhausted attempts
    history.append((attempts, current_error))
    return FixResult(code=None, attempts=attempts, last_error=current_error, history=history)


# -------------------------------------------------------------------------------------------------
# Event Helper
# -------------------------------------------------------------------------------------------------

def build_fix_events(
    fix_result: FixResult,
    run_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[dict]:
    """
    Convert a FixResult into a list of SSE-friendly payload dicts
    (without the 'data:' prefix – caller handles formatting).

    Each history entry produces a 'RunContent' message. Final status produces either
    a success message or a 'RunError'.
    """
    events: List[dict] = []
    for idx, err in fix_result.history:
        events.append(
            {
                "event": "RunContent",
                "content": f"Auto-fix attempt {idx + 1}: {err}",
                "run_id": run_id,
                "session_id": session_id,
            }
        )

    if fix_result.code is not None:
        events.append(
            {
                "event": "RunContent",
                "content": f"Code fixed after {fix_result.attempts} attempt(s).",
                "run_id": run_id,
                "session_id": session_id,
            }
        )
    else:
        events.append(
            {
                "event": "RunError",
                "content": f"Auto-fix failed after {fix_result.attempts} attempt(s). Final error: {fix_result.last_error}",
                "run_id": run_id,
                "session_id": session_id,
            }
        )
    return events


# -------------------------------------------------------------------------------------------------
# Convenience API for Integration
# -------------------------------------------------------------------------------------------------

def auto_fix_if_needed(
    code: str,
    error: Optional[str],
    max_attempts: int = 2,
    engine: str = "anthropic",
    model: Optional[str] = None,
    include_runtime_errors: bool = True,
) -> Tuple[Optional[str], List[dict]]:
    """
    One-call convenience:
      - Decide if fix needed (syntax fail or fixable runtime error).
      - Run fix loop if needed.
      - Return (final_code_or_None, list_of_events).

    The list_of_events are already SSE-ready payload dicts (to be JSON-dumped).
    """
    validation = quick_validate(code)
    fix_required = not validation.ok

    if not fix_required and error and include_runtime_errors and is_fixable_error(error):
        fix_required = True
        # Overwrite validation error message with runtime error for context
        validation = ValidationResult(False, error)

    if not fix_required:
        # Nothing to do
        return code, []

    fix_result = fix_code_with_iterations_verbose(
        initial_code=code,
        initial_error=validation.error,
        max_attempts=max_attempts,
        engine=engine,
        model=model,
        include_runtime_errors=include_runtime_errors,
    )
    events = build_fix_events(fix_result)
    return fix_result.code, events
