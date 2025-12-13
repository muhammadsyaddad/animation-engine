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
import time
import logging
from typing import Optional, List

# Import pipeline logger
try:
    from api.pipeline_logger import (
        PipelineLogger, PipelineStep, get_pipeline_logger, log_pipeline_event
    )
    PIPELINE_LOGGING_AVAILABLE = True
except ImportError:
    PIPELINE_LOGGING_AVAILABLE = False

# Fallback standard logger
_logger = logging.getLogger("code_generation")
_logger.setLevel(logging.DEBUG)
if not _logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))
    _logger.addHandler(handler)


def _log(level: str, message: str, run_id: str = None, step: str = None, context: dict = None):
    """Internal logging helper that uses pipeline logger if available."""
    context = context or {}

    # Always log to standard logger
    log_msg = f"[{step or 'code_gen'}] {message}"
    if run_id:
        log_msg = f"[run={run_id}] {log_msg}"
    if context:
        log_msg += f" | {context}"

    level_map = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
    _logger.log(level_map.get(level.upper(), logging.INFO), log_msg)

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
    run_id: Optional[str] = None,
) -> str:
    """Call Anthropic API with comprehensive logging."""

    _log("INFO", f"Starting Anthropic API call", run_id, "llm_api_call_start", {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "prompt_length": len(prompt),
        "has_api_key": bool(api_key),
    })

    try:
        import anthropic
    except Exception as e:
        _log("ERROR", f"Anthropic SDK not available: {e}", run_id, "llm_api_call_error", {
            "error_type": "sdk_import_error",
            "error": str(e),
        })
        raise CodeGenerationError(f"Anthropic SDK not available: {e}")

    # Check API key
    if not api_key:
        _log("ERROR", "ANTHROPIC_API_KEY not set or empty", run_id, "llm_api_call_error", {
            "error_type": "missing_api_key",
        })
        raise CodeGenerationError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)

    start_time = time.time()
    _log("DEBUG", "Sending request to Anthropic API...", run_id, "llm_api_call_start", {
        "model": model,
    })

    try:
        resp = client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )

        elapsed_ms = (time.time() - start_time) * 1000
        _log("INFO", f"Anthropic API call successful", run_id, "llm_api_call_complete", {
            "model": model,
            "elapsed_ms": round(elapsed_ms, 2),
            "stop_reason": getattr(resp, "stop_reason", None),
            "usage_input_tokens": getattr(getattr(resp, "usage", None), "input_tokens", None),
            "usage_output_tokens": getattr(getattr(resp, "usage", None), "output_tokens", None),
        })

    except anthropic.AuthenticationError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        _log("ERROR", f"Anthropic authentication failed - invalid API key", run_id, "llm_api_call_error", {
            "error_type": "authentication_error",
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(e),
        })
        raise CodeGenerationError(f"Anthropic authentication failed: Invalid API key. Check ANTHROPIC_API_KEY environment variable.")

    except anthropic.RateLimitError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        _log("ERROR", f"Anthropic rate limit exceeded", run_id, "llm_api_call_error", {
            "error_type": "rate_limit_error",
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(e),
        })
        raise CodeGenerationError(f"Anthropic rate limit exceeded: {e}")

    except anthropic.APIConnectionError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        _log("ERROR", f"Anthropic connection error", run_id, "llm_api_call_error", {
            "error_type": "connection_error",
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(e),
        })
        raise CodeGenerationError(f"Failed to connect to Anthropic API: {e}")

    except anthropic.APIStatusError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        _log("ERROR", f"Anthropic API status error", run_id, "llm_api_call_error", {
            "error_type": "api_status_error",
            "status_code": getattr(e, "status_code", None),
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(e),
        })
        raise CodeGenerationError(f"Anthropic API error: {e}")

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        _log("ERROR", f"Anthropic call failed with unexpected error", run_id, "llm_api_call_error", {
            "error_type": type(e).__name__,
            "elapsed_ms": round(elapsed_ms, 2),
            "error": str(e),
        })
        raise CodeGenerationError(f"Anthropic call failed: {e}")

    # Parse response
    _log("DEBUG", "Parsing Anthropic response...", run_id, "code_generation_parse")

    try:
        blocks: List = resp.content or []
        text = "".join(
            getattr(block, "text", "") for block in blocks if getattr(block, "type", "") == "text"
        )

        _log("DEBUG", f"Response parsed successfully", run_id, "code_generation_parse", {
            "response_length": len(text),
            "num_blocks": len(blocks),
        })

    except Exception as e:
        _log("ERROR", f"Failed to parse Anthropic response", run_id, "code_generation_error", {
            "error_type": "response_parse_error",
            "error": str(e),
        })
        raise CodeGenerationError(f"Unexpected Anthropic response format: {e}")

    code = _extract_code_from_text(text)
    code = _clean_output(code)

    _log("DEBUG", f"Code extracted and cleaned", run_id, "code_generation_complete", {
        "code_length": len(code),
        "has_genscene": "class GenScene" in code,
    })

    if "class GenScene" not in code:
        _log("ERROR", "Generated code missing 'class GenScene'", run_id, "code_generation_error", {
            "error_type": "invalid_code_structure",
            "code_preview": code[:200] if code else "(empty)",
        })
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
    run_id: Optional[str] = None,
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
        run_id: Optional run ID for pipeline logging.

    Returns:
        Manim Python code as a string. Must contain class GenScene(Scene).

    Raises:
        CodeGenerationError: If the model call fails or code is invalid.
    """
    start_time = time.time()

    _log("INFO", "Starting Manim code generation", run_id, "code_generation_start", {
        "engine": engine,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "prompt_length": len(prompt) if prompt else 0,
        "has_extra_rules": bool(extra_rules),
    })

    engine = (engine or "anthropic").lower().strip()
    if engine not in DEFAULT_MODELS:
        _log("ERROR", f"Invalid engine specified", run_id, "code_generation_error", {
            "engine": engine,
            "valid_engines": list(DEFAULT_MODELS.keys()),
        })
        raise CodeGenerationError(f"Invalid engine '{engine}'. Use one of: {list(DEFAULT_MODELS.keys())}")

    if model is None:
        model = DEFAULT_MODELS[engine]
        _log("DEBUG", f"Using default model for engine", run_id, "code_generation_config", {
            "engine": engine,
            "model": model,
        })
    else:
        model = model.strip()
        # If we have a validation set for this engine, enforce it (best-effort).
        valid = VALID_MODELS.get(engine)
        if valid and model not in valid:
            _log("ERROR", f"Invalid model specified", run_id, "code_generation_error", {
                "model": model,
                "engine": engine,
                "valid_models": sorted(valid),
            })
            raise CodeGenerationError(
                f"Invalid model '{model}' for engine '{engine}'. Valid: {sorted(valid)}"
            )

    system_prompt = _build_system_prompt(extra_rules=extra_rules)
    _log("DEBUG", "System prompt built", run_id, "code_generation_config", {
        "system_prompt_length": len(system_prompt),
    })

    # OpenAI branch removed; only Anthropic is supported.

    if engine == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")

        _log("DEBUG", "Checking ANTHROPIC_API_KEY environment variable", run_id, "code_generation_config", {
            "api_key_present": bool(api_key),
            "api_key_length": len(api_key) if api_key else 0,
            "api_key_prefix": api_key[:10] + "..." if api_key and len(api_key) > 10 else "(not set)",
        })

        try:
            code = _call_anthropic(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=system_prompt,
                api_key=api_key,
                run_id=run_id,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            _log("INFO", "Manim code generation completed successfully", run_id, "code_generation_complete", {
                "engine": engine,
                "model": model,
                "elapsed_ms": round(elapsed_ms, 2),
                "code_length": len(code),
            })

            return code

        except CodeGenerationError as e:
            elapsed_ms = (time.time() - start_time) * 1000
            _log("ERROR", f"Code generation failed", run_id, "code_generation_error", {
                "engine": engine,
                "model": model,
                "elapsed_ms": round(elapsed_ms, 2),
                "error": str(e),
            })
            raise

    # Should never reach here
    _log("ERROR", f"Unhandled engine", run_id, "code_generation_error", {"engine": engine})
    raise CodeGenerationError(f"Unhandled engine '{engine}'")
