"""
Summarization tool for generating concise text summaries using Anthropic Claude.

This module exposes a single entry-point function:

    from agents.tools.summarization import summarize_text, SummarizationError

    summary = summarize_text(
        text="Long content here...",
        model=None,              # optional; defaults to Claude Sonnet
        temperature=0.3,
        max_tokens=512,
        instructions="Focus on key takeaways and action items.",
        bullet=True,             # produce bullet-point summary if True
    )

Environment:
- Reads ANTHROPIC_API_KEY for Anthropic.

Notes:
- The function returns plain text (Markdown-friendly).
- If the SDK call fails, a SummarizationError is raised.
"""

from __future__ import annotations

import os
from typing import Optional, List


class SummarizationError(Exception):
    """Raised when summarization fails or a provider is unavailable."""
    pass


# Defaults and (optional) validation sets to encourage consistent usage.
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-20250514",
}

VALID_MODELS = {
    "anthropic": {"claude-sonnet-4-20250514"},
}


def _build_system_prompt(instructions: Optional[str], bullet: bool) -> str:
    """
    Build a focused system prompt for summarization.
    """
    base = [
        "You are a helpful assistant that produces clear, faithful, and concise summaries.",
        "Constraints:",
        "- Capture only the essential ideas and key facts.",
        "- Be faithful to the source; do not invent details.",
        "- Prefer short sentences and concrete wording.",
    ]
    if bullet:
        base.append("- Return the summary as bullet points.")
    else:
        base.append("- Return the summary as short paragraphs (no bullet points).")
    if instructions:
        base.append("Additional instructions:")
        base.append(instructions.strip())
    return "\n".join(base)


def _postprocess_summary(text: str) -> str:
    """
    Light post-processing for cleanliness.
    """
    text = (text or "").strip()
    # Normalize excessive blank lines to at most one.
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def _call_anthropic(
    text: str,
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str,
    api_key: Optional[str],
) -> str:
    try:
        import anthropic
    except Exception as e:
        raise SummarizationError(f"Anthropic SDK not available: {e}")

    client = anthropic.Anthropic(api_key=api_key)

    try:
        resp = client.messages.create(
            model=model,
            system=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": f"Summarize the following text:\n\n{text}"}],
        )
    except Exception as e:
        raise SummarizationError(f"Anthropic summarization failed: {e}")

    try:
        blocks: List = resp.content or []
        out = "".join(
            getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text"
        )
    except Exception as e:
        raise SummarizationError(f"Unexpected Anthropic response format: {e}")

    return _postprocess_summary(out)


def summarize_text(
    text: str,
    *,
    engine: str = "anthropic",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
    instructions: Optional[str] = None,
    bullet: bool = False,
) -> str:
    """
    Summarize a block of text using Anthropic Claude.

    Args:
        text: Source content to summarize.
        engine: Only 'anthropic' is supported.
        model: Optional model ID (defaults if None).
        temperature: Sampling temperature.
        max_tokens: Maximum tokens for the completion.
        instructions: Additional style/formatting guidance.
        bullet: If True, produce a bullet-point summary; otherwise paragraphs.

    Returns:
        str: A concise summary in plain text (Markdown-friendly).

    Raises:
        SummarizationError: On invalid engine, missing SDK/API, or provider error.
    """
    engine = (engine or "anthropic").lower().strip()
    if engine != "anthropic":
        raise SummarizationError("Only 'anthropic' engine is supported in this deployment.")

    if model is None:
        model = DEFAULT_MODELS["anthropic"]
    else:
        model = model.strip()
        valid = VALID_MODELS.get("anthropic")
        if valid and model not in valid:
            raise SummarizationError(
                f"Invalid model '{model}' for engine 'anthropic'. Valid: {sorted(valid)}"
            )

    system_prompt = _build_system_prompt(instructions=instructions, bullet=bullet)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    return _call_anthropic(
        text=text,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        api_key=api_key,
    )
