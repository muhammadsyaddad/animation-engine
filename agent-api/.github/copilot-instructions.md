# Copilot Instructions

Purpose: help Copilot act safely and consistently in this repo (animation-engine) across Python FastAPI backend, Next.js frontends, and docs.

## General
- Prefer deterministic paths first (templates/helpers) before generating from scratch.
- Keep changes minimal, scoped, and reversible; avoid touching files unrelated to the task.
- Never commit or suggest secrets, API keys, or private URLs; use env vars and example placeholders.
- Maintain concise, helpful comments only where code is non-obvious.

## Python (agent-api)
- Follow existing patterns in `agents/tools` and `api/routes`; keep functions pure where possible.
- Type hints on new public functions; avoid broad `except` without logging.
- Log with existing pipeline logging helpers when inside the animation pipeline.
- Write small, testable units; prefer dependency injection over globals.

## Frontend (agent-ui, marketing-page)
- Use existing design system and utilities; avoid introducing new UI libraries without approval.
- Keep React components small; move side effects into hooks; prefer server actions/page conventions already present.
- Respect TypeScript strictness; add types instead of `any`; reuse shared types from `src/types`.

## LLM/Manim pipeline
- Stay template-first for animations; only fall back to LLM codegen when no template fits.
- Enforce `GenScene(Scene)` contract for generated Manim code; no markdown/backticks in outputs.
- Validate/guardrail LLM outputs (AST parse, class checks) before render paths.

## Security and data handling
- Never log sensitive user content or uploaded data paths verbatim; prefer hashed/short identifiers.
- Keep file writes inside `artifacts/` and configured temp locations; do not write to repo roots.

## Tests and docs
- Add or update tests when behavior changes; keep docs in `docs/` aligned with code.
- For docs, keep concise, ASCII, and link to source files when referencing behavior.

## Pull request hygiene
- Explain why (not just what) in PR descriptions; note risk areas and test coverage.
- Avoid large mixed changes; split into logical commits where possible.
