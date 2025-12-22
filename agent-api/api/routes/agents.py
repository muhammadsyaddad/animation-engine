from cmath import e
import os
from enum import Enum
from logging import getLogger
from typing import AsyncGenerator, Dict, List, Optional
import json
import time
import traceback
from typing import AsyncGenerator

from pydantic_core.core_schema import is_instance_schema
from starlette.responses import Content

from agno.agent import Agent, AgentKnowledge
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.agno_assist import get_agno_assist_knowledge
from agents.selector import AgentType, get_agent, get_available_agents
from agents.tools.code_generation import generate_manim_code, CodeGenerationError
from agents.tools.preview_manim import generate_manim_preview_stream
from agents.tools.video_manim import render_manim_stream
from agents.tools.export_ffmpeg import export_merge_stream
from sqlalchemy.orm import Session
from api.settings import api_settings
from api.run_registry import (
    create_run, set_state, RunState, complete_run, fail_run, cancel_run, get_run, list_runs,
    set_pending_template_selection, get_pending_template_selection, clear_pending_template_selection,
)
from db.session import get_db

from api.routes.auth import get_current_user_optional
from api.persistence.run_store import persist_run_created, persist_run_state, persist_run_completed, persist_run_failed, persist_artifact

# Pipeline logging
from api.pipeline_logger import (
    PipelineLogger,
    PipelineStep,
    get_pipeline_logger,
    log_pipeline_event,
    cleanup_logger,
)

# Session context for animation pipeline persistence
from api.session_context import (
    get_session_context,
    update_session_context,
    AnimationContext,
)

# Template suggestions module
from api.template_suggestions import (
    TemplateSuggestionEvents,
    TemplateSuggestionsPayload,
    build_template_suggestions_from_inference,
    format_dataset_summary,
    validate_template_selection,
)

# Column mapping validation
from api.routes.templates import (
    validate_column_mappings_with_schema,
    get_smart_column_suggestions,
)

logger = getLogger(__name__)

######################################################
## Routes for the Agent Interface
######################################################

def _quick_validate(code: str) -> tuple[bool, str]:
    """
    Fast syntax and structure validation without executing Manim:
    - Ensure 'class GenScene' exists.
    - Parse with ast to catch SyntaxError early.
    """
    import ast
    code = code or ""
    if "class GenScene" not in code:
        return False, "Missing 'class GenScene' definition."
    try:
        ast.parse(code)
    except SyntaxError as e:
        text = getattr(e, "text", "") or ""
        return False, f"SyntaxError: {e.msg} at line {e.lineno}: {text}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"
    return True, ""


def _build_fix_prompt(bad_code: str, error: str) -> str:
    return f"""
The following Manim Python code has an error.

Error:
{error}

Correct the code while preserving the original intent. Return ONLY the corrected Python code.
Rules:
- Must contain: class GenScene(Scene) with def construct(self): ...
- Do not include explanations or any markdown/backticks.
- Ensure all parentheses, brackets, and braces are balanced.
- Avoid partial lines or identifiers cut in the middle.
Original code:
{bad_code}
""".strip()


def _attempt_auto_fix(
    bad_code: str,
    error: str,
    *,
    engine: str = "anthropic",
    model: Optional[str] = None,
) -> str:
    """
    Ask the LLM to fix the code using the code generation tool with a corrective prompt.
    """
    try:
        fix_prompt = _build_fix_prompt(bad_code, error)
        return generate_manim_code(
            prompt=fix_prompt,
            engine=engine,
            model=model,
            temperature=0.1,
            max_tokens=1200,
            extra_rules="Do not add markdown or backticks. Ensure balanced parentheses/brackets/braces.",
        )
    except CodeGenerationError as e:
        # Bubble up for the caller to decide next steps
        raise e


agents_router = APIRouter(prefix="/agents", tags=["Agents"])


class Model(str, Enum):
    claude_3_5 = "claude-sonnet-4-20250514"


@agents_router.get("", response_model=List[str])
async def list_agents():
    """
    Returns a list of all available agent IDs.

    Returns:
        List[str]: List of agent identifiers
    """
    return get_available_agents()


@agents_router.get("/templates")
async def list_template_options():
    return {
        "bubble": {
            "creation_modes": [1, 2, 3],
            "description": "Animated bubble chart (x,y,r,time, optional group)"
        },
        "distribution": {
            "modes": ["basic"],
            "description": "Animated value distribution over time (histogram/kde bins)"
        },
        "bar_race": {
            "modes": ["basic"],
            "description": "Ranked bar race over time (top N categories)"
        },
        "line_evolution": {
            "modes": ["basic"],
            "description": "Multiple entities evolving over time (lines with smooth transitions)"
        },
        "bento_grid": {
            "modes": ["basic"],
            "description": "Grid of mini panels (small multiples) animated over time"
        }
    }

async def chat_response_streamer(agent: Agent, message: str) -> AsyncGenerator:
    """
    Stream agent responses chunk by chunk as SSE-style JSON lines.

    Each yielded value is an SSE 'data:' line that contains a JSON object:
    {
      "event": "RunContent" | "RunStarted" | "RunError" | "RunCompleted",
      "content": "<text or json>",
      "created_at": <unix ts>,
      "session_id": "<optional>"
      ...other fields if available...
    }
    """
    import inspect

    try:
        # Call agent.arun. It may return:
        # - an async generator (stream=True) -> iterate with `async for` (no await)
        # - or a coroutine/result (some implementations) -> await then handle
        run_response = agent.run(message, stream=True)

        # If agent.arun returned a coroutine/awaitable, await it to get the result
        if inspect.isawaitable(run_response):
            run_response = await run_response

        # Now handle async iterable (generator) or sync iterable result
        if hasattr(run_response, "__aiter__"):
            # Async generator: iterate asynchronously
            async for chunk in run_response:
                try:
                    # Normalize content to string (safe-guard)
                    content = ""
                    if hasattr(chunk, "content"):
                        if chunk.content is None:
                            content = ""
                        elif isinstance(chunk.content, str):
                            content = chunk.content
                        else:
                            try:
                                content = json.dumps(chunk.content)
                            except Exception:
                                content = str(chunk.content)
                    else:
                        content = str(chunk)

                    payload = {
                        "event": "RunContent",
                        "content": content,
                        "created_at": int(getattr(chunk, "created_at", time.time())),
                    }
                    if getattr(chunk, "session_id", None):
                        payload["session_id"] = chunk.session_id

                    yield f"data: {json.dumps(payload)}\n\n"
                except Exception as inner_e:
                    logger.exception("Error while processing chunk: %s", inner_e)
                    err_payload = {
                        "event": "RunError",
                        "content": str(inner_e),
                        "created_at": int(time.time()),
                    }
                    yield f"data: {json.dumps(err_payload)}\n\n"
        else:
            # Not an async iterable. It might be a single response object or list.
            # Normalize single response into one chunk and yield it.
            # If it's an iterable, iterate synchronously.
            if hasattr(run_response, "__iter__") and not isinstance(run_response, (str, bytes, dict)):
                for chunk in run_response:
                    content = getattr(chunk, "content", str(chunk))
                    payload = {
                        "event": "RunContent",
                        "content": content,
                        "created_at": int(getattr(chunk, "created_at", time.time())),
                    }
                    if getattr(chunk, "session_id", None):
                        payload["session_id"] = chunk.session_id
                    yield f"data: {json.dumps(payload)}\n\n"
            else:
                # Single response object
                content = getattr(run_response, "content", str(run_response))
                payload = {
                    "event": "RunContent",
                    "content": content,
                    "created_at": int(getattr(run_response, "created_at", time.time())),
                }
                if getattr(run_response, "session_id", None):
                    payload["session_id"] = run_response.session_id
                yield f"data: {json.dumps(payload)}\n\n"

        # Normal completion
        completed_payload = {
            "event": "RunCompleted",
            "content": "",
            "created_at": int(time.time()),
        }
        yield f"data: {json.dumps(completed_payload)}\n\n"

    except Exception as e:
        logger.exception("Unhandled error during chat_response_streamer: %s", e)
        err_payload = {
            "event": "RunError",
            "content": str(e),
            "created_at": int(time.time()),
        }
        try:
            yield f"data: {json.dumps(err_payload)}\n\n"
        except Exception:
            logger.exception("Failed to yield error payload")
    finally:
        try:
            final_payload = {
                "event": "RunCompleted",
                "content": "",
                "created_at": int(time.time()),
            }
            yield f"data: {json.dumps(final_payload)}\n\n"
        except Exception:
            logger.debug("Could not emit final RunCompleted payload")


class RunRequest(BaseModel):
    """Request model for an running an agent"""

    message: str
    stream: bool = True
    model: Model = Model.claude_3_5
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    # Animation intent flags (optional overrides; if None, system will auto-detect intent)
    animate_data: Optional[bool] = None          # True to force animation pipeline, False to force text-only
    chart_type: Optional[str] = None             # "bubble" | "distribution" | other custom; None lets system infer
    csv_path: Optional[str] = None               # Direct unified CSV path (e.g. /static/datasets/.../unified.csv)
    csv_dir: Optional[str] = None                # Directory containing Danim-style X/Y/R wide-form files to unify
    # Template controls
    creation_mode: Optional[int] = None          # Bubble: 1 | 2 | 3 (creation options)
    # Code generation options (exposed for animation_agent)
    code_engine: Optional[str] = None  # "openai" | "anthropic"
    code_model: Optional[str] = None   # model ID for the selected engine
    code_system_prompt: Optional[str] = None   # extra rules/system prompt for code generation
    # Preview controls
    preview_sample_every: Optional[int] = None
    preview_max_frames: Optional[int] = None
    # Render controls
    aspect_ratio: Optional[str] = None          # "16:9" | "9:16" | "1:1"
    render_quality: Optional[str] = None        # "low" | "medium" | "high"
    # Text summary toggle
    summarize: Optional[bool] = False
    # Export/Merge options (Phase 5)
    export_videos: Optional[List[str]] = None  # list of video URLs/paths to merge
    export_title_slug: Optional[str] = None    # slug for the exported filename


@agents_router.post("/{agent_id}/runs", status_code=status.HTTP_200_OK)
async def create_agent_run(agent_id: AgentType, body: RunRequest, current_user=Depends(get_current_user_optional)):
    """
    Sends a message to a specific agent and returns the response.

    Args:
        agent_id: The ID of the agent to interact with
        body: Request parameters including the message

    Returns:
        Either a streaming response or the complete agent response
    """
    logger.debug(f"RunRequest: {body}")

    # Phase 3: animation_agent with Code Generation + Preview + Render
    if agent_id == AgentType.ANIMATION_AGENT and body.stream:
        # Phase 5: Export/Merge path if export_videos provided
        if body.export_videos:
            def export_sse():
                session_id = body.session_id
                # In-memory registry keeps 'local' for anonymous; DB persistence uses NULL (None) instead of non-UUID string
                registry_user_id = (current_user.id if current_user else "local")
                db_user_id = (current_user.id if current_user else None)
                user_id = registry_user_id
                run = create_run(user_id=registry_user_id, session_id=session_id, message="export_merge")
                run_id = run.run_id
                set_state(run_id, RunState.EXPORTING, "Merging videos...")
                try:
                    agent_label = getattr(agent_id, "value", str(agent_id))
                    persist_run_created(run_id, db_user_id, session_id, agent_label, "EXPORTING", "Merging videos...", {"export_title_slug": (body.export_title_slug or "export")})
                    persist_run_state(run_id, "EXPORTING", "Merging videos...")
                except Exception:
                    pass
                from typing import cast, List
                video_urls = cast(List[str], body.export_videos)
                for event in export_merge_stream(
                    video_urls=video_urls,
                    title_slug=(body.export_title_slug or "export"),
                    user_id=user_id,
                ):
                    payload = {
                        "event": event.get("event", "RunContent"),
                        "content": event.get("content", ""),
                        "created_at": int(time.time()),
                    }
                    if session_id:
                        payload["session_id"] = session_id
                    payload["run_id"] = run_id
                    if "videos" in event:
                        payload["videos"] = event["videos"]
                        # Mark run complete when fin
                        # al video is produced
                        try:
                            for v in event["videos"]:
                                if isinstance (v,dict):
                                    storage_path = v.get("url") or ""
                                else:
                                    storage_path = str(v)

                                if not storage_path:
                                   logger.warning("file is not in storage")
                                   continue

                                persist_artifact(run_id, "video", storage_path)
                        except Exception:
                            pass
                        complete_run(run_id, "Export completed.")
                        try:
                            persist_run_completed(run_id, "Export completed.")
                        except Exception:
                            pass
                    if payload["event"] == "RunError":
                        fail_run(run_id, payload.get("content", "Export error"))
                        try:
                            persist_run_failed(run_id, payload.get("content", "Export error"))
                        except Exception:
                            pass
                    yield f"data: {json.dumps(payload)}\n\n"
            return StreamingResponse(export_sse(), media_type="text/event-stream")

        # Intent detection gate (decide whether to run animation pipeline or fallback to chat)
        should_animate = False
        detected_chart_type = None  # Store detected chart type for later use

        if body.animate_data is True:
            should_animate = True
        elif body.animate_data is False:
            should_animate = False
        else:
            try:
                from agents.tools.intent_detection import detect_animation_intent  # type: ignore
                # Pass csv_path for data-driven inference; check session context if not in body
                csv_path_for_intent = getattr(body, "csv_path", None)
                if not csv_path_for_intent and body.session_id:
                    # Try to get csv_path from session context
                    _session_ctx = get_session_context(body.session_id)
                    if _session_ctx and _session_ctx.has_dataset():
                        csv_path_for_intent = _session_ctx.get_effective_csv_path()
                intent = detect_animation_intent(body.message, csv_path=csv_path_for_intent)
                should_animate = bool(getattr(intent, "animation_requested", False))
                detected_chart_type = getattr(intent, "chart_type", "unknown")

                # FIX: If user attached a CSV dataset, treat as animation intent
                # even if message has typos (e.g., "animtae" instead of "animate")
                if not should_animate and csv_path_for_intent:
                    logger.info(f"CSV attachment detected, forcing animation intent: {csv_path_for_intent}")
                    should_animate = True
                    # Try to infer chart type from data if we haven't already
                    if detected_chart_type == "unknown":
                        try:
                            from agents.tools.chart_inference import recommend_chart
                            from api.services.data_modules import resolve_csv_path
                            resolved_path = resolve_csv_path(csv_path_for_intent)
                            if os.path.exists(resolved_path):
                                recs = recommend_chart(resolved_path, body.message)
                                if recs and recs[0].score >= 0.3:
                                    detected_chart_type = recs[0].chart_type
                        except Exception:
                            pass
            except Exception:
                # Fallback heuristic if intent module unavailable
                text = (body.message or "")
                cues = ["class GenScene", "manim", "animasi", "animate", "animation", "video", "mp4", "gif"]
                lowered = text.lower()
                should_animate = any(c.lower() in lowered for c in cues)
                # Also check if CSV is attached in the fallback
                csv_path_for_intent = getattr(body, "csv_path", None)
                if not should_animate and csv_path_for_intent:
                    should_animate = True
        if not should_animate:
            # Fall back to normal chat stream (no animation pipeline)
            try:
                agent: Agent = get_agent(
                    model_id=body.model.value,
                    agent_id=agent_id,
                    user_id=(current_user.id if current_user else "local"),
                    session_id=body.session_id,
                )
            except ValueError as e:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            return StreamingResponse(
                chat_response_streamer(agent, body.message),
                media_type="text/event-stream",
            )

        def animation_sse():
            msg = body.message or ""
            # In-memory registry keeps 'local'; DB persistence must store NULL for anonymous
            registry_user_id = (current_user.id if current_user else "local")
            db_user_id = (current_user.id if current_user else None)
            user_id = registry_user_id
            session_id = body.session_id
            # Create and track run
            run = create_run(user_id=registry_user_id, session_id=session_id, message=msg)
            run_id = run.run_id
            set_state(run_id, RunState.STARTING, "Starting")

            # Initialize pipeline logger for this run
            plog = get_pipeline_logger(run_id=run_id, session_id=session_id, user_id=user_id)
            plog.info(PipelineStep.RUN_STARTED, "Animation pipeline run started", {
                "message_length": len(msg),
                "has_csv_path": bool(getattr(body, "csv_path", None)),
                "has_csv_dir": bool(getattr(body, "csv_dir", None)),
                "chart_type_override": getattr(body, "chart_type", None),
                "code_engine": getattr(body, "code_engine", None),
                "code_model": getattr(body, "code_model", None),
            })
            try:
                agent_label = getattr(agent_id, "value", str(agent_id))
                persist_run_created(run_id, db_user_id, session_id, agent_label, "STARTING", "Starting", {})
                persist_run_state(run_id, "STARTING", "Starting")
            except Exception:
                pass
            # Initial SSE event to signal animation pipeline activation (intent-based)
            try:
                from agents.tools.intent_detection import detect_animation_intent  # type: ignore
                # Pass csv_path for smart data-driven inference; check session context if not in body
                csv_path_for_intent = getattr(body, "csv_path", None)
                if not csv_path_for_intent and session_id:
                    # Try to get csv_path from session context
                    _session_ctx_intent = get_session_context(session_id)
                    if _session_ctx_intent and _session_ctx_intent.has_dataset():
                        csv_path_for_intent = _session_ctx_intent.get_effective_csv_path()
                _intent_info = detect_animation_intent(msg, csv_path=csv_path_for_intent)
                _chart = getattr(_intent_info, "chart_type", "unknown")
                _conf = getattr(_intent_info, "confidence", 0.0)
                _data_analyzed = getattr(_intent_info, "data_analyzed", False)
                _recommended = getattr(_intent_info, "recommended_charts", [])

                if _data_analyzed and _recommended:
                    initial_msg = (
                        f"Animation intent detected (chart_type={_chart}, confidence={_conf:.2f}). "
                        f"Data analysis completed. Top recommendations: {_recommended[:3]}. "
                        f"Entering animation pipeline."
                    )
                else:
                    initial_msg = f"Animation intent detected (chart_type={_chart}, confidence={_conf:.2f}). Entering animation pipeline."
            except Exception:
                initial_msg = "Animation intent detected. Entering animation pipeline."
            init_payload = {
                "event": "RunContent",
                "content": initial_msg,
                "created_at": int(time.time()),
                "run_id": run_id,
            }
            if session_id:
                init_payload["session_id"] = session_id
            yield f"data: {json.dumps(init_payload)}\n\n"
            # Optional controls (fall back to existing defaults)
            aspect_ratio = (body.aspect_ratio or "16:9")
            preview_sample_every = (body.preview_sample_every or api_settings.preview_sample_every)
            preview_max_frames = (body.preview_max_frames or api_settings.preview_max_frames)
            quality = (body.render_quality or api_settings.default_render_quality)

            # 1) Determine or generate code
            code = None
            if "class GenScene" in msg:
                code = msg
                status = {
                    "event": "RunContent",
                    "content": "Using provided Manim code.",
                    "created_at": int(time.time()),
                }
                if session_id:
                    status["session_id"] = session_id
                status["run_id"] = run_id
                yield f"data: {json.dumps(status)}\n\n"
            else:
                status = {
                    "event": "RunContent",
                    "content": "Analyzing prompt for chart spec and generating code...",
                    "created_at": int(time.time()),
                }
                if session_id:
                    status["session_id"] = session_id
                status["run_id"] = run_id
                yield f"data: {json.dumps(status)}\n\n"
                # Attempt spec inference + bubble template (Danim-style). Fallback to LLM generation.
                # Preprocessing phase: attempt deterministic wide->long transform if a dataset path is provided.
                use_template = False
                preproc_info = None
                provisional_binding = None
                melted_dataset_path = None
                dataset_melt_applied = False
                raw_dataset_path = getattr(body, "csv_path", None)

                # Session context: retrieve stored context if csv_path is missing
                session_ctx = get_session_context(session_id) if session_id else None
                context_from_session = False

                if not raw_dataset_path and session_ctx and session_ctx.has_dataset():
                    # Use csv_path from session context
                    raw_dataset_path = session_ctx.get_effective_csv_path()
                    context_from_session = True
                    plog.info(PipelineStep.DATA_PREPROCESSING, "Using csv_path from session context", {
                        "session_id": session_id,
                        "csv_path": raw_dataset_path,
                        "original_csv_path": session_ctx.original_csv_path,
                    })
                    ctx_payload = {
                        "event": "RunContent",
                        "content": f"📁 Using previously uploaded dataset: {session_ctx.original_csv_path or raw_dataset_path}",
                        "created_at": int(time.time()),
                        "run_id": run_id,
                    }
                    if session_id:
                        ctx_payload["session_id"] = session_id
                    yield f"data: {json.dumps(ctx_payload)}\n\n"

                    # Also restore chart_type from context if not provided in body
                    if not getattr(body, "chart_type", None) and session_ctx.chart_type:
                        body.chart_type = session_ctx.chart_type
                        plog.debug(PipelineStep.DATA_PREPROCESSING, "Restored chart_type from session context", {
                            "chart_type": session_ctx.chart_type,
                        })

                    # Restore melted_dataset_path if available
                    if session_ctx.melted_dataset_path:
                        melted_dataset_path = session_ctx.melted_dataset_path
                        dataset_melt_applied = True

                    # Restore provisional_binding if available
                    if session_ctx.data_binding:
                        provisional_binding = session_ctx.data_binding

                # Store context when we have a fresh csv_path from the request
                if getattr(body, "csv_path", None) and session_id:
                    update_session_context(
                        session_id=session_id,
                        csv_path=body.csv_path,
                        original_csv_path=body.csv_path,
                        chart_type=getattr(body, "chart_type", None),
                        last_intent_message=msg,
                    )
                    plog.debug(PipelineStep.DATA_PREPROCESSING, "Stored csv_path in session context", {
                        "session_id": session_id,
                        "csv_path": body.csv_path,
                    })

                # Log diagnostic info before preprocessing check
                plog.info(PipelineStep.DATA_PREPROCESSING, "Checking raw_dataset_path", {
                    "raw_dataset_path": raw_dataset_path,
                    "raw_dataset_path_type": type(raw_dataset_path).__name__ if raw_dataset_path else "None",
                    "body_csv_path": getattr(body, "csv_path", None),
                    "will_preprocess": bool(raw_dataset_path and isinstance(raw_dataset_path, str)),
                })

                if raw_dataset_path and isinstance(raw_dataset_path, str):
                    try:
                        import os
                        import pandas as pd
                        from api.services.data_modules import preprocess_dataset, validate_for_animation, read_csv_smart, resolve_csv_path, detect_header_row  # type: ignore

                        plog.info(PipelineStep.DATA_PREPROCESSING, "Starting data preprocessing", {
                            "raw_dataset_path": raw_dataset_path,
                        })

                        # Map /static path to filesystem if needed
                        _original_path = raw_dataset_path
                        raw_dataset_path = resolve_csv_path(raw_dataset_path)
                        _path_exists = os.path.exists(raw_dataset_path)
                        plog.info(PipelineStep.DATA_PREPROCESSING, "Path resolution result", {
                            "original_path": _original_path,
                            "resolved_path": raw_dataset_path,
                            "path_changed": _original_path != raw_dataset_path,
                            "file_exists": _path_exists,
                            "cwd": os.getcwd(),
                        })
                        if _path_exists:
                            # Detect header row for World Bank and similar formats
                            header_row = detect_header_row(raw_dataset_path)
                            plog.debug(PipelineStep.DATA_PREPROCESSING, "Detected header row", {
                                "header_row": header_row,
                            })

                            # Preview for structural detection with robust CSV parsing
                            try:
                                # IMPORTANT: Use skip_blank_lines=False to match csv.reader row indexing
                                # Use utf-8-sig encoding to handle BOM (Byte Order Mark) in World Bank CSVs
                                df_preview = pd.read_csv(raw_dataset_path, nrows=100, header=header_row, skip_blank_lines=False, encoding='utf-8-sig')
                            except pd.errors.ParserError as csv_err:
                                # Try with different settings for malformed CSVs
                                try:
                                    df_preview = pd.read_csv(raw_dataset_path, nrows=100, on_bad_lines='skip', header=header_row, skip_blank_lines=False, encoding='utf-8-sig')
                                    csv_warn_payload = {
                                        "event": "RunContent",
                                        "content": f"⚠️ Some rows in your CSV were malformed and skipped. Error: {csv_err}",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        csv_warn_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(csv_warn_payload)}\n\n"
                                except Exception:
                                    # CSV is too malformed to parse
                                    csv_error_msg = (
                                        f"**CSV Parsing Failed**\n\n"
                                        f"Your CSV file could not be parsed. Error: {csv_err}\n\n"
                                        f"**How to fix:**\n"
                                        f"  • Check that your file uses commas (,) as delimiters\n"
                                        f"  • Ensure all rows have the same number of columns\n"
                                        f"  • Wrap fields containing commas in quotes\n"
                                        f"  • Re-export from Excel/Google Sheets as 'CSV UTF-8'"
                                    )
                                    csv_error_payload = {
                                        "event": "RunContent",
                                        "content": csv_error_msg,
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        csv_error_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(csv_error_payload)}\n\n"

                                    error_payload = {
                                        "event": "Error",
                                        "content": "CSV parsing failed. Please fix the file format and try again.",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        error_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(error_payload)}\n\n"

                                    final_payload = {
                                        "event": "RunResponse",
                                        "run_id": run_id,
                                        "state": "failed",
                                        "created_at": int(time.time()),
                                        "messages": [{"role": "assistant", "content": csv_error_msg}],
                                    }
                                    if session_id:
                                        final_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(final_payload)}\n\n"
                                    return
                            except UnicodeDecodeError as enc_err:
                                # Encoding issue - try different encoding
                                try:
                                    # latin-1 fallback for encoding issues (BOM already stripped by this point)
                                    df_preview = pd.read_csv(raw_dataset_path, nrows=100, encoding='latin-1', header=header_row, skip_blank_lines=False)
                                    enc_warn_payload = {
                                        "event": "RunContent",
                                        "content": "⚠️ CSV was not UTF-8 encoded. Loaded with latin-1 encoding.",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        enc_warn_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(enc_warn_payload)}\n\n"
                                except Exception:
                                    enc_error_msg = (
                                        f"**CSV Encoding Error**\n\n"
                                        f"Could not read your CSV file due to encoding issues: {enc_err}\n\n"
                                        f"**How to fix:**\n"
                                        f"  • Save your file as 'CSV UTF-8' from Excel or Google Sheets\n"
                                        f"  • Avoid special characters if possible"
                                    )
                                    enc_error_payload = {
                                        "event": "RunContent",
                                        "content": enc_error_msg,
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        enc_error_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(enc_error_payload)}\n\n"

                                    final_payload = {
                                        "event": "RunResponse",
                                        "run_id": run_id,
                                        "state": "failed",
                                        "created_at": int(time.time()),
                                        "messages": [{"role": "assistant", "content": enc_error_msg}],
                                    }
                                    if session_id:
                                        final_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(final_payload)}\n\n"
                                    return

                            # Early validation: check if data is suitable for animation
                            validation_result = validate_for_animation(df_preview, filename=os.path.basename(raw_dataset_path))
                            if not validation_result.is_valid:
                                # Send user-friendly validation error message
                                validation_msg = validation_result.to_user_message()
                                validation_payload = {
                                    "event": "RunContent",
                                    "content": validation_msg,
                                    "created_at": int(time.time()),
                                    "run_id": run_id,
                                }
                                if session_id:
                                    validation_payload["session_id"] = session_id
                                yield f"data: {json.dumps(validation_payload)}\n\n"

                                # Send error event and stop
                                error_payload = {
                                    "event": "Error",
                                    "content": "Dataset validation failed. Please fix the issues above and try again.",
                                    "created_at": int(time.time()),
                                    "run_id": run_id,
                                }
                                if session_id:
                                    error_payload["session_id"] = session_id
                                yield f"data: {json.dumps(error_payload)}\n\n"

                                # Log and finish
                                plog.warning(PipelineStep.DATA_PREPROCESSING, "Dataset validation failed", {
                                    "errors": validation_result.errors,
                                    "suggestions": validation_result.suggestions,
                                    "numeric_columns": validation_result.numeric_columns,
                                    "categorical_columns": validation_result.categorical_columns,
                                })

                                final_payload = {
                                    "event": "RunResponse",
                                    "run_id": run_id,
                                    "state": "failed",
                                    "created_at": int(time.time()),
                                    "messages": [{
                                        "role": "assistant",
                                        "content": validation_msg,
                                    }],
                                }
                                if session_id:
                                    final_payload["session_id"] = session_id
                                yield f"data: {json.dumps(final_payload)}\n\n"
                                return

                            # Log successful validation
                            plog.debug(PipelineStep.DATA_PREPROCESSING, "Dataset validation passed", {
                                "numeric_columns": validation_result.numeric_columns,
                                "categorical_columns": validation_result.categorical_columns,
                                "potential_time_column": validation_result.potential_time_column,
                                "potential_group_column": validation_result.potential_group_column,
                            })

                            preproc_info = preprocess_dataset(df_preview, filename=os.path.basename(raw_dataset_path))
                            det = preproc_info.get("detection")
                            cols = preproc_info.get("columns", {})
                            transform = preproc_info.get("transform")
                            is_wide = getattr(det, "is_wide", False)
                            applied_preview = getattr(transform, "transform_applied", False)
                            msg_pre = f"Dataset preprocessing preview: wide={is_wide}, transform_applied={applied_preview}, mapped_columns={cols}"
                            pre_payload = {
                                "event": "RunContent",
                                "content": msg_pre,
                                "created_at": int(time.time()),
                                "run_id": run_id,
                            }
                            if session_id:
                                pre_payload["session_id"] = session_id
                            yield f"data: {json.dumps(pre_payload)}\n\n"
                            if preproc_info and 'columns' in preproc_info:
                                _c = preproc_info['columns']
                                provisional_binding = {
                                    "group_col": _c.get("group"),
                                    "time_col": _c.get("time"),
                                    "value_col": _c.get("value"),
                                    "normalized_col": _c.get("normalized"),
                                    "anomaly_flag_col": _c.get("anomaly_flag"),
                                }
                                inject_payload = {
                                    "event": "RunContent",
                                    "content": f"Provisional data binding detected: {provisional_binding}",
                                    "created_at": int(time.time()),
                                    "run_id": run_id,
                                }
                                if session_id:
                                    inject_payload["session_id"] = session_id
                                yield f"data: {json.dumps(inject_payload)}\n\n"

                                # Update session context with data binding
                                if session_id and not context_from_session:
                                    update_session_context(
                                        session_id=session_id,
                                        data_binding=provisional_binding,
                                    )
                            # If dataset is wide, perform full melt on entire file to a new artifacts CSV
                            if is_wide:
                                try:
                                    # Use header_row and skip_blank_lines=False to match preview reading
                                    # Use utf-8-sig encoding to handle BOM
                                    full_df = pd.read_csv(raw_dataset_path, header=header_row, skip_blank_lines=False, encoding='utf-8-sig')
                                    # Identify year-like columns (4-digit) or numeric sequential headers
                                    year_cols = [c for c in full_df.columns if isinstance(c, str) and c.isdigit() and len(c) == 4]
                                    if not year_cols:
                                        # Fallback: treat all numeric headers except first as value columns
                                        candidate_cols = full_df.columns[1:]
                                        # Use those that are mostly numeric
                                        year_cols = [
                                            c for c in candidate_cols
                                            if pd.to_numeric(full_df[c], errors="coerce").notna().mean() > 0.5
                                        ]
                                    group_col = full_df.columns[0]
                                    if year_cols:
                                        df_long = full_df.melt(id_vars=[group_col], value_vars=year_cols,
                                                               var_name="time", value_name="value")
                                        # Cast time -> int when possible
                                        try:
                                            df_long["time"] = df_long["time"].astype(int)
                                        except Exception:
                                            pass
                                        df_long["value"] = pd.to_numeric(df_long["value"], errors="coerce")
                                        artifacts_datasets = os.path.join(os.getcwd(), "artifacts", "datasets")
                                        os.makedirs(artifacts_datasets, exist_ok=True)
                                        melted_dataset_path = os.path.join(
                                            artifacts_datasets,
                                            f"melted-{os.path.splitext(os.path.basename(raw_dataset_path))[0]}-{run_id}.csv"
                                        )
                                        df_long.to_csv(melted_dataset_path, index=False)
                                        dataset_melt_applied = True
                                        stats_payload = {
                                            "event": "RunContent",
                                            "content": f"Melted wide dataset -> {melted_dataset_path} (rows={len(df_long)}, groups={df_long[group_col].nunique()}, time_points={df_long['time'].nunique()})",
                                            "created_at": int(time.time()),
                                            "run_id": run_id,
                                        }
                                        if session_id:
                                            stats_payload["session_id"] = session_id
                                        yield f"data: {json.dumps(stats_payload)}\n\n"

                                        # Update session context with melted dataset path
                                        if session_id:
                                            update_session_context(
                                                session_id=session_id,
                                                melted_dataset_path=melted_dataset_path,
                                            )
                                    else:
                                        no_melt_payload = {
                                            "event": "RunContent",
                                            "content": "Wide detection true but no year-like columns found; skipping melt.",
                                            "created_at": int(time.time()),
                                            "run_id": run_id,
                                        }
                                        if session_id:
                                            no_melt_payload["session_id"] = session_id
                                        yield f"data: {json.dumps(no_melt_payload)}\n\n"
                                except Exception as _merr:
                                    melt_err_payload = {
                                        "event": "RunContent",
                                        "content": f"Melt failed: {_merr}",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        melt_err_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(melt_err_payload)}\n\n"
                        else:
                            # File does not exist at resolved path - log this important condition
                            plog.warning(PipelineStep.DATA_PREPROCESSING, "Dataset file not found - preprocessing SKIPPED", {
                                "resolved_path": raw_dataset_path,
                                "original_path": _original_path,
                                "path_was_resolved": _original_path != raw_dataset_path,
                            })
                            skip_payload = {
                                "event": "RunContent",
                                "content": f"⚠️ Dataset file not found at resolved path: {raw_dataset_path}",
                                "created_at": int(time.time()),
                                "run_id": run_id,
                            }
                            if session_id:
                                skip_payload["session_id"] = session_id
                            yield f"data: {json.dumps(skip_payload)}\n\n"
                    except Exception as _pe:
                        plog.error(PipelineStep.DATA_PREPROCESSING, f"Preprocessing failed: {_pe}", {
                            "raw_dataset_path": raw_dataset_path,
                            "error_type": type(_pe).__name__,
                        }, exception=_pe)
                        warn_payload = {
                            "event": "RunContent",
                            "content": f"Preprocessing skipped: {_pe}",
                            "created_at": int(time.time()),
                            "run_id": run_id,
                        }
                        if session_id:
                            warn_payload["session_id"] = session_id
                        yield f"data: {json.dumps(warn_payload)}\n\n"
                template_error = None
                spec = None
                explicit_chart = False
                requested_ct = None

                # Diagnostic: Log state before spec inference
                plog.info(PipelineStep.DATA_PREPROCESSING, "Pre-spec-inference state", {
                    "provisional_binding_set": provisional_binding is not None,
                    "provisional_binding": provisional_binding,
                    "melted_dataset_path": melted_dataset_path,
                    "dataset_melt_applied": dataset_melt_applied,
                    "body_chart_type": getattr(body, "chart_type", None),
                    "auto_select_templates": api_settings.auto_select_templates,
                })

                try:
                    import os, re, csv
                    from agents.tools.specs import infer_spec_from_prompt  # type: ignore
                    from agents.tools.danim_templates import (
                        generate_bubble_code,
                        generate_distribution_code,
                        generate_bar_race_code,
                        generate_line_evolution_code,
                        generate_bento_grid_code,
                        generate_count_bar_code,
                        generate_single_numeric_code,
                    )  # type: ignore
                    # Pass csv_path for data-driven inference
                    # Also pass auto_select_templates setting to control whether we auto-infer chart type
                    # When auto_select_templates=False, infer_spec_from_prompt returns "unknown" chart_type
                    # which triggers the template suggestion flow later in the pipeline
                    dataset_path_for_spec = getattr(body, "csv_path", None)
                    spec = infer_spec_from_prompt(
                        msg,
                        csv_path=dataset_path_for_spec,
                        auto_select_templates=api_settings.auto_select_templates,
                    )

                    plog.info(PipelineStep.DATA_PREPROCESSING, "Spec inference complete", {
                        "spec_is_none": spec is None,
                        "spec_chart_type": getattr(spec, "chart_type", None) if spec else None,
                        "spec_has_data_binding": hasattr(spec, "data_binding") if  spec else False,
                    })
                    # Inject melted dataset bindings BEFORE template routing if available
                    try:
                        if provisional_binding and hasattr(spec, "data_binding"):
                            db = getattr(spec, "data_binding")
                            # Only set if empty / default
                            if getattr(db, "time_col", None) in (None, "", "time"):
                                setattr(db, "time_col", provisional_binding.get("time_col"))
                            if getattr(db, "value_col", None) in (None, "", "value"):
                                setattr(db, "value_col", provisional_binding.get("value_col"))
                            # Map group/entity
                            gcol = provisional_binding.get("group_col")
                            if gcol:
                                if getattr(db, "group_col", None) in (None, "", "group"):
                                    setattr(db, "group_col", gcol)
                                if getattr(db, "entity_col", None) in (None, "", "entity", "name"):
                                    setattr(db, "entity_col", gcol)
                            bind_payload = {
                                "event": "RunContent",
                                "content": f"Applied data binding to spec: time={getattr(db,'time_col',None)}, value={getattr(db,'value_col',None)}, group={getattr(db,'group_col',None)}",
                                "created_at": int(time.time()),
                                "run_id": run_id,
                            }
                            if session_id:
                                bind_payload["session_id"] = session_id
                            yield f"data: {json.dumps(bind_payload)}\n\n"
                            # Auto-assign chart_type using smart inference if unknown
                            if getattr(spec, "chart_type", None) in (None, "", "unknown"):
                                # Try smart chart inference first
                                try:
                                    from agents.tools.chart_inference import recommend_chart
                                    _infer_path = dataset_path_for_spec or melted_dataset_path
                                    # Resolve /static/... URL paths to filesystem paths
                                    if _infer_path and isinstance(_infer_path, str) and _infer_path.startswith("/static/"):
                                        _artifacts_root = os.path.join(os.getcwd(), "artifacts")
                                        _rel_inside = _infer_path[len("/static/"):].lstrip("/")
                                        _fs_candidate = os.path.join(_artifacts_root, _rel_inside)
                                        if os.path.exists(_fs_candidate):
                                            _infer_path = _fs_candidate
                                    if _infer_path and os.path.exists(_infer_path):
                                        _recs = recommend_chart(_infer_path, msg)
                                        if _recs and _recs[0].score >= 0.5:
                                            # Check if auto-selection is disabled
                                            # If disabled, emit template suggestions and pause
                                            if not api_settings.auto_select_templates:
                                                # Build template suggestions from inference
                                                plog.info(PipelineStep.DATA_PREPROCESSING, "Auto-select disabled, emitting template suggestions", {
                                                    "top_recommendation": _recs[0].chart_type,
                                                    "confidence": _recs[0].score,
                                                    "num_recommendations": len(_recs),
                                                })

                                                # Format dataset summary for display (include schema info for frontend validation)
                                                _dataset_summary = None
                                                try:
                                                    from agents.tools.chart_inference import get_schema_summary
                                                    _schema_info = get_schema_summary(_infer_path)
                                                    _dataset_summary = format_dataset_summary(
                                                        csv_path=_infer_path,
                                                        row_count=_schema_info.get("row_count"),
                                                        column_names=_schema_info.get("columns"),
                                                        numeric_columns=_schema_info.get("numeric_columns"),
                                                        categorical_columns=_schema_info.get("categorical_columns"),
                                                        time_column=_schema_info.get("time_column"),
                                                        is_wide_format=_schema_info.get("is_wide_format"),
                                                    )
                                                except Exception:
                                                    pass

                                                # Build and emit template suggestions
                                                _suggestions_payload = build_template_suggestions_from_inference(
                                                    recommendations=_recs,
                                                    run_id=run_id,
                                                    session_id=session_id,
                                                    dataset_summary=_dataset_summary,
                                                )

                                                # Store pending state in run registry (always available by run_id)
                                                set_pending_template_selection(
                                                    run_id=run_id,
                                                    suggestions=[s.to_dict() for s in _suggestions_payload.suggestions],
                                                    original_message=msg,
                                                    csv_path=_infer_path,
                                                    data_binding=provisional_binding,
                                                )

                                                # Also store in session context if session_id is available
                                                if session_id:
                                                    update_session_context(
                                                        session_id=session_id,
                                                        pending_template_suggestions=[s.to_dict() for s in _suggestions_payload.suggestions],
                                                        pending_run_id=run_id,
                                                        pending_original_message=msg,
                                                        data_binding=provisional_binding,
                                                    )

                                                # Update run state to awaiting selection
                                                set_state(run_id, RunState.AWAITING_TEMPLATE_SELECTION, "Waiting for template selection")
                                                try:
                                                    persist_run_state(run_id, "AWAITING_TEMPLATE_SELECTION", "Waiting for template selection")
                                                except Exception:
                                                    pass

                                                # Emit the template suggestions event
                                                yield _suggestions_payload.to_sse_string()

                                                # Emit a RunPaused event to signal the frontend
                                                paused_payload = {
                                                    "event": "RunPaused",
                                                    "content": "Please select a template to continue.",
                                                    "run_id": run_id,
                                                    "created_at": int(time.time()),
                                                    "awaiting": "template_selection",
                                                }
                                                if session_id:
                                                    paused_payload["session_id"] = session_id
                                                yield f"data: {json.dumps(paused_payload)}\n\n"

                                                # End the SSE stream here - user must select a template
                                                plog.info(PipelineStep.DATA_PREPROCESSING, "Pipeline paused awaiting template selection", {
                                                    "run_id": run_id,
                                                    "suggestions_count": len(_suggestions_payload.suggestions),
                                                })
                                                return

                                            # Auto-selection is enabled, proceed as before
                                            spec.chart_type = _recs[0].chart_type
                                            smart_payload = {
                                                "event": "RunContent",
                                                "content": f"Smart chart inference: '{_recs[0].chart_type}' (score={_recs[0].score}, confidence={_recs[0].confidence}). Reasons: {', '.join(_recs[0].reasons[:3])}",
                                                "created_at": int(time.time()),
                                                "run_id": run_id,
                                            }
                                            if session_id:
                                                smart_payload["session_id"] = session_id
                                            yield f"data: {json.dumps(smart_payload)}\n\n"

                                            # Update session context with inferred chart_type
                                            if session_id:
                                                update_session_context(
                                                    session_id=session_id,
                                                    chart_type=_recs[0].chart_type,
                                                )
                                except Exception as _smart_err:
                                    smart_err_payload = {
                                        "event": "RunContent",
                                        "content": f"Smart chart inference skipped: {_smart_err}",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        smart_err_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(smart_err_payload)}\n\n"

                                # Fallback to distribution for wide melt if still unknown
                                if dataset_melt_applied and getattr(spec, "chart_type", None) in (None, "", "unknown"):
                                    spec.chart_type = "distribution"
                                    auto_ct_payload = {
                                        "event": "RunContent",
                                        "content": "Fallback: Auto-selected chart_type=distribution for wide year-format dataset.",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        auto_ct_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(auto_ct_payload)}\n\n"

                                    # Update session context with fallback chart_type
                                    if session_id:
                                        update_session_context(
                                            session_id=session_id,
                                            chart_type="distribution",
                                        )
                    except Exception as _inj_err:
                        inj_err_payload = {
                            "event": "RunContent",
                            "content": f"Spec binding injection failed: {_inj_err}",
                            "created_at": int(time.time()),
                            "run_id": run_id,
                        }
                        if session_id:
                            inj_err_payload["session_id"] = session_id
                        yield f"data: {json.dumps(inj_err_payload)}\n\n"
                    # Apply chart_type override if provided (force template selection)
                    explicit_chart = False
                    requested_ct = None
                    try:
                        if getattr(body, "chart_type", None):
                            ct = str(body.chart_type).strip().lower()
                            if ct in ("bubble", "distribution", "bar_race", "line_evolution", "bento_grid", "count_bar", "single_numeric"):
                                spec.chart_type = ct
                                explicit_chart = True
                                requested_ct = ct
                    except Exception:
                        pass

                    # Diagnostic: Log state before template suggestion check
                    plog.info(PipelineStep.DATA_PREPROCESSING, "Pre-template-suggestion state", {
                        "spec_chart_type": getattr(spec, "chart_type", None) if spec else None,
                        "explicit_chart": explicit_chart,
                        "requested_ct": requested_ct,
                        "auto_select_templates": api_settings.auto_select_templates,
                        "will_check_suggestions": not api_settings.auto_select_templates and not explicit_chart,
                        "dataset_path_for_spec": dataset_path_for_spec,
                        "melted_dataset_path": melted_dataset_path,
                    })
                    # Apply creation_mode override if provided (bubble template controller)
                    try:
                        if getattr(body, "creation_mode", None) is not None:
                            spec.creation_mode = int(body.creation_mode)
                    except Exception:
                        pass

                    # =========================================================
                    # TEMPLATE SUGGESTION CHECK (AUTO-SELECT BYPASS FIX)
                    # =========================================================
                    # This check runs AFTER spec inference but BEFORE code generation.
                    # If auto_select_templates is disabled and user didn't explicitly
                    # provide a chart_type, we emit template suggestions and pause.
                    # =========================================================
                    if not api_settings.auto_select_templates and not explicit_chart:
                        # Get dataset path for chart inference
                        _suggestion_dataset_path = dataset_path_for_spec or melted_dataset_path
                        _original_suggestion_path = _suggestion_dataset_path

                        # Resolve /static/ URL paths to filesystem paths
                        if _suggestion_dataset_path and isinstance(_suggestion_dataset_path, str) and _suggestion_dataset_path.startswith("/static/"):
                            _artifacts_root = os.path.join(os.getcwd(), "artifacts")
                            _rel_inside = _suggestion_dataset_path[len("/static/"):].lstrip("/")
                            _fs_candidate = os.path.join(_artifacts_root, _rel_inside)
                            _candidate_exists = os.path.exists(_fs_candidate)
                            plog.info(PipelineStep.DATA_PREPROCESSING, "Template suggestion path resolution", {
                                "original_path": _original_suggestion_path,
                                "fs_candidate": _fs_candidate,
                                "candidate_exists": _candidate_exists,
                            })
                            if _candidate_exists:
                                _suggestion_dataset_path = _fs_candidate

                        _final_path_exists = _suggestion_dataset_path and os.path.exists(_suggestion_dataset_path) if _suggestion_dataset_path else False
                        plog.info(PipelineStep.DATA_PREPROCESSING, "Template suggestion path check", {
                            "suggestion_dataset_path": _suggestion_dataset_path,
                            "path_exists": _final_path_exists,
                            "will_generate_suggestions": _final_path_exists,
                        })

                        if _suggestion_dataset_path and _final_path_exists:
                            try:
                                from agents.tools.chart_inference import recommend_chart
                                _recs = recommend_chart(_suggestion_dataset_path, msg)
                                if _recs and len(_recs) > 0:
                                    plog.info(PipelineStep.DATA_PREPROCESSING, "Auto-select disabled, emitting template suggestions", {
                                        "inferred_chart_type": spec.chart_type,
                                        "top_recommendation": _recs[0].chart_type,
                                        "confidence": _recs[0].score,
                                        "num_recommendations": len(_recs),
                                    })

                                    # Format dataset summary for display
                                    _dataset_summary = None
                                    try:
                                        from agents.tools.chart_inference import get_schema_summary
                                        _schema_info = get_schema_summary(_suggestion_dataset_path)
                                        _dataset_summary = format_dataset_summary(
                                            csv_path=_suggestion_dataset_path,
                                            row_count=_schema_info.get("row_count"),
                                            column_names=_schema_info.get("columns"),
                                            numeric_columns=_schema_info.get("numeric_columns"),
                                            categorical_columns=_schema_info.get("categorical_columns"),
                                            time_column=_schema_info.get("time_column"),
                                            is_wide_format=_schema_info.get("is_wide_format"),
                                        )
                                    except Exception:
                                        pass

                                    # Build and emit template suggestions
                                    _suggestions_payload = build_template_suggestions_from_inference(
                                        recommendations=_recs,
                                        run_id=run_id,
                                        session_id=session_id,
                                        dataset_summary=_dataset_summary,
                                    )

                                    # Store pending state in run registry (always available by run_id)
                                    set_pending_template_selection(
                                        run_id=run_id,
                                        suggestions=[s.to_dict() for s in _suggestions_payload.suggestions],
                                        original_message=msg,
                                        csv_path=_suggestion_dataset_path,
                                        data_binding=provisional_binding,
                                    )

                                    # Also store in session context if session_id is available
                                    if session_id:
                                        update_session_context(
                                            session_id=session_id,
                                            pending_template_suggestions=[s.to_dict() for s in _suggestions_payload.suggestions],
                                            pending_run_id=run_id,
                                            pending_original_message=msg,
                                            data_binding=provisional_binding,
                                        )

                                    # Update run state to awaiting selection
                                    set_state(run_id, RunState.AWAITING_TEMPLATE_SELECTION, "Waiting for template selection")
                                    try:
                                        persist_run_state(run_id, "AWAITING_TEMPLATE_SELECTION", "Waiting for template selection")
                                    except Exception:
                                        pass

                                    # Emit the template suggestions event
                                    yield _suggestions_payload.to_sse_string()

                                    # Emit a RunPaused event to signal the frontend
                                    paused_payload = {
                                        "event": "RunPaused",
                                        "content": "Please select a template to continue.",
                                        "run_id": run_id,
                                        "created_at": int(time.time()),
                                        "awaiting": "template_selection",
                                    }
                                    if session_id:
                                        paused_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(paused_payload)}\n\n"

                                    # End the SSE stream here - user must select a template
                                    plog.info(PipelineStep.DATA_PREPROCESSING, "Pipeline paused awaiting template selection", {
                                        "run_id": run_id,
                                        "suggestions_count": len(_suggestions_payload.suggestions),
                                    })
                                    return
                            except Exception as _suggest_err:
                                plog.warning(PipelineStep.DATA_PREPROCESSING, f"Template suggestion generation failed: {_suggest_err}", {
                                    "error": str(_suggest_err),
                                    "error_type": type(_suggest_err).__name__,
                                })
                                # Continue with auto-selection on error
                    else:
                        # Log why template suggestions were skipped
                        plog.info(PipelineStep.DATA_PREPROCESSING, "Template suggestion check SKIPPED", {
                            "reason": "explicit_chart is True" if explicit_chart else "auto_select_templates is True",
                            "auto_select_templates": api_settings.auto_select_templates,
                            "explicit_chart": explicit_chart,
                        })

                    # Extract csv_path and optional csv_dir for Danim-style X/Y/R
                    m_path = re.search(r"csv_path\s*=\s*([^\s]+)", msg)
                    m_dir = re.search(r"csv_dir\s*=\s*([^\s]+)", msg)
                    # Prefer request body fields, fallback to parsing message
                    dataset_path = (getattr(body, "csv_path", None) or (m_path.group(1) if m_path else None))
                    base_dir = (getattr(body, "csv_dir", None) or (m_dir.group(1) if m_dir else None))
                    # Override with melted dataset if created
                    if dataset_melt_applied and melted_dataset_path and isinstance(melted_dataset_path, str):
                        import os
                        if os.path.exists(melted_dataset_path):
                            dataset_path = melted_dataset_path
                            melted_payload = {
                                "event": "RunContent",
                                "content": f"Using melted dataset for template generation: {melted_dataset_path}",
                                "created_at": int(time.time()),
                                "run_id": run_id,
                            }
                            if session_id:
                                melted_payload["session_id"] = session_id
                            yield f"data: {json.dumps(melted_payload)}\n\n"
                    # Map /static/... URL-path (served) to filesystem path under artifacts for existence checks
                    if dataset_path and isinstance(dataset_path, str) and dataset_path.startswith("/static/"):
                        artifacts_root = os.path.join(os.getcwd(), "artifacts")
                        rel_inside = dataset_path[len("/static/"):].lstrip("/")
                        fs_candidate = os.path.join(artifacts_root, rel_inside)
                        if os.path.exists(fs_candidate):
                            dataset_path = fs_candidate
                    if base_dir and isinstance(base_dir, str) and base_dir.startswith("/static/"):
                        artifacts_root = os.path.join(os.getcwd(), "artifacts")
                        rel_inside = base_dir[len("/static/"):].lstrip("/")
                        fs_candidate_dir = os.path.join(artifacts_root, rel_inside)
                        if os.path.isdir(fs_candidate_dir):
                            base_dir = fs_candidate_dir
                    # If bubble chart and no csv_path, try unifying Danim files from csv_dir or default Danim/DATA
                    if spec.chart_type == "bubble" and not dataset_path:
                        try:
                            if not base_dir:
                                default_dir = os.path.join(os.getcwd(), "Danim", "DATA")
                                if os.path.exists(default_dir):
                                    base_dir = default_dir
                            if base_dir and os.path.isdir(base_dir):
                                from agents.tools.data_ingestion import unify_danim_files  # type: ignore
                                artifacts_datasets = os.path.join(os.getcwd(), "artifacts", "datasets")
                                os.makedirs(artifacts_datasets, exist_ok=True)
                                unified_out = os.path.join(artifacts_datasets, f"unified-{run_id}.csv")
                                ingestion = unify_danim_files(base_dir=base_dir, output_path=unified_out)
                                if os.path.exists(ingestion.unified_path):
                                    dataset_path = ingestion.unified_path
                                    status = {
                                        "event": "RunContent",
                                        "content": f"Unified Danim files from {base_dir} -> {dataset_path}",
                                        "created_at": int(time.time()),
                                    }
                                    if session_id:
                                        status["session_id"] = session_id
                                    status["run_id"] = run_id
                                    yield f"data: {json.dumps(status)}\n\n"
                        except Exception as ie:
                            template_error = f"Ingestion failed: {ie}"
                    if spec.chart_type == "bubble" and dataset_path and os.path.exists(dataset_path):
                        try:
                            # If user explicitly requested chart_type, validate CSV headers strictly
                            is_explicit = bool(getattr(body, "chart_type", None))
                            if is_explicit:
                                try:
                                    with open(dataset_path, "r", encoding="utf-8") as _f:
                                        _reader = csv.DictReader(_f)
                                        _headers = _reader.fieldnames or []
                                except Exception as _e:
                                    err_msg = f"Failed to read dataset: {dataset_path} ({_e})"
                                    err_payload = {
                                        "event": "RunError",
                                        "content": err_msg,
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        err_payload["session_id"] = session_id
                                    fail_run(run_id, err_msg)
                                    yield f"data: {json.dumps(err_payload)}\n\n"
                                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                                    return
                                _lower = {h.lower() for h in _headers}
                                _binding = getattr(spec, "data_binding", None)
                                _x = (getattr(_binding, "x_col", None) or "x").lower()
                                _y = (getattr(_binding, "y_col", None) or "y").lower()
                                _r = (getattr(_binding, "r_col", None) or "r").lower()
                                _t = (getattr(_binding, "time_col", None) or "time").lower()
                                _e = getattr(_binding, "entity_col", None)
                                _missing = []
                                for _name in [_x, _y, _r, _t]:
                                    if _name not in _lower:
                                        _missing.append(_name)
                                if _e:
                                    if _e.lower() not in _lower:
                                        _missing.append(_e.lower())
                                else:
                                    _entity_ok = any(c in _lower for c in ["entity","name","country","label","id"])
                                    if not _entity_ok:
                                        _missing.append("entity/name/country/label/id")
                                if _missing:
                                    err_msg = f"Bubble chart requested explicitly but dataset is missing required columns: {_missing}"
                                    err_payload = {
                                        "event": "RunError",
                                        "content": err_msg,
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        err_payload["session_id"] = session_id
                                    fail_run(run_id, err_msg)
                                    yield f"data: {json.dumps(err_payload)}\n\n"
                                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                                    return
                            code = generate_bubble_code(spec, dataset_path)
                            use_template = True
                            status = {
                                "event": "RunContent",
                                "content": f"Using bubble template (creation_mode={spec.creation_mode}).",
                                "created_at": int(time.time()),
                            }
                            if session_id:
                                status["session_id"] = session_id
                            status["run_id"] = run_id
                            yield f"data: {json.dumps(status)}\n\n"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    elif spec.chart_type == "distribution" and dataset_path and os.path.exists(dataset_path):
                        try:
                            # If user explicitly requested chart_type, validate CSV headers strictly
                            is_explicit = bool(getattr(body, "chart_type", None))
                            if is_explicit:
                                try:
                                    with open(dataset_path, "r", encoding="utf-8") as _f:
                                        _reader = csv.DictReader(_f)
                                        _headers = _reader.fieldnames or []
                                except Exception as _e:
                                    err_msg = f"Failed to read dataset: {dataset_path} ({_e})"
                                    err_payload = {
                                        "event": "RunError",
                                        "content": err_msg,
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        err_payload["session_id"] = session_id
                                    fail_run(run_id, err_msg)
                                    yield f"data: {json.dumps(err_payload)}\n\n"
                                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                                    return
                                _lower = {h.lower() for h in _headers}
                                _binding = getattr(spec, "data_binding", None)
                                _t = (getattr(_binding, "time_col", None) or "time").lower()
                                _v = (getattr(_binding, "value_col", None) or "value").lower()
                                _missing = []
                                if _t not in _lower:
                                    _missing.append(_t)
                                if _v not in _lower:
                                    _missing.append(_v)
                                if _missing:
                                    err_msg = f"Distribution chart requested explicitly but dataset is missing required columns: {_missing}"
                                    err_payload = {
                                        "event": "RunError",
                                        "content": err_msg,
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        err_payload["session_id"] = session_id
                                    fail_run(run_id, err_msg)
                                    yield f"data: {json.dumps(err_payload)}\n\n"
                                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                                    return
                            else:
                                try:
                                    code = generate_distribution_code(spec, dataset_path)
                                    use_template = True
                                    status = {
                                        "event": "RunContent",
                                        "content": "Using distribution template.",
                                        "created_at": int(time.time()),
                                    }
                                    if session_id:
                                        status["session_id"] = session_id
                                    status["run_id"] = run_id
                                    yield f"data: {json.dumps(status)}\n\n"
                                except Exception as te:
                                    template_error = f"Template failed: {te}"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    elif spec.chart_type == "bar_race" and dataset_path and os.path.exists(dataset_path):
                        try:
                            code = generate_bar_race_code(spec, dataset_path)
                            use_template = True
                            status = {
                                "event": "RunContent",
                                "content": "Using bar chart race template.",
                                "created_at": int(time.time()),
                            }
                            if session_id:
                                status["session_id"] = session_id
                            status["run_id"] = run_id
                            yield f"data: {json.dumps(status)}\n\n"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    elif spec.chart_type == "line_evolution" and dataset_path and os.path.exists(dataset_path):
                        try:
                            code = generate_line_evolution_code(spec, dataset_path)
                            use_template = True
                            status = {
                                "event": "RunContent",
                                "content": "Using line evolution template.",
                                "created_at": int(time.time()),
                            }
                            if session_id:
                                status["session_id"] = session_id
                            status["run_id"] = run_id
                            yield f"data: {json.dumps(status)}\n\n"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    elif spec.chart_type == "bento_grid" and dataset_path and os.path.exists(dataset_path):
                        try:
                            code = generate_bento_grid_code(spec, dataset_path)
                            use_template = True
                            status = {
                                "event": "RunContent",
                                "content": "Using bento grid template.",
                                "created_at": int(time.time()),
                            }
                            if session_id:
                                status["session_id"] = session_id
                            status["run_id"] = run_id
                            yield f"data: {json.dumps(status)}\n\n"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    elif spec.chart_type == "count_bar" and dataset_path and os.path.exists(dataset_path):
                        try:
                            # Get count column from data binding if available
                            _binding = getattr(spec, "data_binding", None)
                            _count_col = getattr(_binding, "group_col", None) if _binding else None
                            code = generate_count_bar_code(spec, dataset_path, count_column=_count_col)
                            use_template = True
                            status = {
                                "event": "RunContent",
                                "content": f"Using count bar chart template (counting by: {_count_col or 'auto-detected'}).",
                                "created_at": int(time.time()),
                            }
                            if session_id:
                                status["session_id"] = session_id
                            status["run_id"] = run_id
                            yield f"data: {json.dumps(status)}\n\n"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    elif spec.chart_type == "single_numeric" and dataset_path and os.path.exists(dataset_path):
                        try:
                            # Get category and value columns from data binding if available
                            _binding = getattr(spec, "data_binding", None)
                            _cat_col = getattr(_binding, "group_col", None) if _binding else None
                            _val_col = getattr(_binding, "value_col", None) if _binding else None
                            code = generate_single_numeric_code(spec, dataset_path, category_column=_cat_col, value_column=_val_col)
                            use_template = True
                            status = {
                                "event": "RunContent",
                                "content": f"Using single numeric bar chart template (category: {_cat_col or 'auto'}, value: {_val_col or 'auto'}).",
                                "created_at": int(time.time()),
                            }
                            if session_id:
                                status["session_id"] = session_id
                            status["run_id"] = run_id
                            yield f"data: {json.dumps(status)}\n\n"
                        except Exception as te:
                            template_error = f"Template failed: {te}"
                    else:
                        if explicit_chart and spec.chart_type in ("bubble", "distribution", "bar_race", "line_evolution", "bento_grid", "count_bar", "single_numeric") and (not dataset_path or not os.path.exists(str(dataset_path))):
                            err_msg = f"{spec.chart_type.capitalize()} chart requested explicitly but dataset is missing or not found. Provide csv_path or csv_dir."
                            err_payload = {
                                "event": "RunError",
                                "content": err_msg,
                                "created_at": int(time.time()),
                                "run_id": run_id,
                            }
                            if session_id:
                                err_payload["session_id"] = session_id
                            fail_run(run_id, err_msg)
                            yield f"data: {json.dumps(err_payload)}\n\n"
                            yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                            return
                        else:
                            # Chart type is unknown or doesn't match any template
                            # Try smart chart inference if we have a dataset
                            if (not explicit_chart) and dataset_path and os.path.exists(str(dataset_path)):
                                try:
                                    from agents.tools.chart_inference import recommend_chart
                                    _recs = recommend_chart(dataset_path, msg)
                                    if _recs and _recs[0].score >= 0.5:
                                        # Check if auto-selection is disabled (fallback path)
                                        if not api_settings.auto_select_templates:
                                            # Build template suggestions from inference
                                            plog.info(PipelineStep.DATA_PREPROCESSING, "Auto-select disabled (fallback path), emitting template suggestions", {
                                                "top_recommendation": _recs[0].chart_type,
                                                "confidence": _recs[0].score,
                                                "num_recommendations": len(_recs),
                                            })

                                            # Format dataset summary for display
                                            _dataset_summary = None
                                            try:
                                                from agents.tools.chart_inference import get_schema_summary
                                                _schema_info = get_schema_summary(dataset_path)
                                                _dataset_summary = format_dataset_summary(
                                                    csv_path=dataset_path,
                                                    row_count=_schema_info.get("row_count"),
                                                    column_names=_schema_info.get("columns"),
                                                    numeric_columns=_schema_info.get("numeric_columns"),
                                                    categorical_columns=_schema_info.get("categorical_columns"),
                                                    time_column=_schema_info.get("time_column"),
                                                    is_wide_format=_schema_info.get("is_wide_format"),
                                                )
                                            except Exception:
                                                pass

                                            # Build and emit template suggestions
                                            _suggestions_payload = build_template_suggestions_from_inference(
                                                recommendations=_recs,
                                                run_id=run_id,
                                                session_id=session_id,
                                                dataset_summary=_dataset_summary,
                                            )

                                            # Store pending state in run registry (always available by run_id)
                                            set_pending_template_selection(
                                                run_id=run_id,
                                                suggestions=[s.to_dict() for s in _suggestions_payload.suggestions],
                                                original_message=msg,
                                                csv_path=dataset_path,
                                                data_binding=provisional_binding,
                                            )

                                            # Also store in session context if session_id is available
                                            if session_id:
                                                update_session_context(
                                                    session_id=session_id,
                                                    pending_template_suggestions=[s.to_dict() for s in _suggestions_payload.suggestions],
                                                    pending_run_id=run_id,
                                                    pending_original_message=msg,
                                                    data_binding=provisional_binding,
                                                )

                                            # Update run state to awaiting selection
                                            set_state(run_id, RunState.AWAITING_TEMPLATE_SELECTION, "Waiting for template selection")
                                            try:
                                                persist_run_state(run_id, "AWAITING_TEMPLATE_SELECTION", "Waiting for template selection")
                                            except Exception:
                                                pass

                                            # Emit the template suggestions event
                                            yield _suggestions_payload.to_sse_string()

                                            # Emit a RunPaused event to signal the frontend
                                            paused_payload = {
                                                "event": "RunPaused",
                                                "content": "Please select a template to continue.",
                                                "run_id": run_id,
                                                "created_at": int(time.time()),
                                                "awaiting": "template_selection",
                                            }
                                            if session_id:
                                                paused_payload["session_id"] = session_id
                                            yield f"data: {json.dumps(paused_payload)}\n\n"

                                            # End the SSE stream here - user must select a template
                                            plog.info(PipelineStep.DATA_PREPROCESSING, "Pipeline paused awaiting template selection (fallback path)", {
                                                "run_id": run_id,
                                                "suggestions_count": len(_suggestions_payload.suggestions),
                                            })
                                            return

                                        # Auto-selection is enabled, proceed as before
                                        inferred_type = _recs[0].chart_type
                                        spec.chart_type = inferred_type
                                        infer_payload = {
                                            "event": "RunContent",
                                            "content": f"Smart inference recommends: '{inferred_type}' (score={_recs[0].score}). Attempting template...",
                                            "created_at": int(time.time()),
                                            "run_id": run_id,
                                        }
                                        if session_id:
                                            infer_payload["session_id"] = session_id
                                        yield f"data: {json.dumps(infer_payload)}\n\n"

                                        # Now try to generate code with the inferred type
                                        if inferred_type == "bubble":
                                            code = generate_bubble_code(spec, dataset_path)
                                            use_template = True
                                        elif inferred_type == "distribution":
                                            code = generate_distribution_code(spec, dataset_path)
                                            use_template = True
                                        elif inferred_type == "bar_race":
                                            code = generate_bar_race_code(spec, dataset_path)
                                            use_template = True
                                        elif inferred_type == "line_evolution":
                                            code = generate_line_evolution_code(spec, dataset_path)
                                            use_template = True
                                        elif inferred_type == "bento_grid":
                                            code = generate_bento_grid_code(spec, dataset_path)
                                            use_template = True
                                        elif inferred_type == "count_bar":
                                            _binding = getattr(spec, "data_binding", None)
                                            _count_col = getattr(_binding, "group_col", None) if _binding else None
                                            code = generate_count_bar_code(spec, dataset_path, count_column=_count_col)
                                            use_template = True
                                        elif inferred_type == "single_numeric":
                                            _binding = getattr(spec, "data_binding", None)
                                            _cat_col = getattr(_binding, "group_col", None) if _binding else None
                                            _val_col = getattr(_binding, "value_col", None) if _binding else None
                                            code = generate_single_numeric_code(spec, dataset_path, category_column=_cat_col, value_column=_val_col)
                                            use_template = True

                                        if use_template:
                                            template_msg_payload = {
                                                "event": "RunContent",
                                                "content": f"Using {inferred_type} template based on smart inference.",
                                                "created_at": int(time.time()),
                                                "run_id": run_id,
                                            }
                                            if session_id:
                                                template_msg_payload["session_id"] = session_id
                                            yield f"data: {json.dumps(template_msg_payload)}\n\n"
                                except Exception as _inf_err:
                                    infer_err_payload = {
                                        "event": "RunContent",
                                        "content": f"Smart inference failed: {_inf_err}. Falling back to LLM.",
                                        "created_at": int(time.time()),
                                        "run_id": run_id,
                                    }
                                    if session_id:
                                        infer_err_payload["session_id"] = session_id
                                    yield f"data: {json.dumps(infer_err_payload)}\n\n"

                            if explicit_chart and spec.chart_type in ("bubble", "distribution", "bar_race", "line_evolution", "bento_grid", "count_bar", "single_numeric") and (not dataset_path or not os.path.exists(str(dataset_path))):
                                err_msg = f"{spec.chart_type.capitalize()} chart requested explicitly but dataset is missing or not found. Provide csv_path or csv_dir."
                                err_payload = {
                                    "event": "RunError",
                                    "content": err_msg,
                                    "created_at": int(time.time()),
                                    "run_id": run_id,
                                }
                                if session_id:
                                    err_payload["session_id"] = session_id
                                fail_run(run_id, err_msg)
                                yield f"data: {json.dumps(err_payload)}\n\n"
                                yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                                return

                            if not use_template:
                                autodetected = False
                                if (not explicit_chart) and dataset_path and os.path.exists(str(dataset_path)):
                                    try:
                                        with open(dataset_path, "r", encoding="utf-8") as _f:
                                            _reader = csv.DictReader(_f)
                                            _headers = [h.lower() for h in (_reader.fieldnames or [])]
                                        _time_candidates = ["time", "year", "tahun", "t"]
                                        _entity_candidates = ["entity", "name", "label", "country"]
                                        _value_candidates = ["value", "val", "score", "amount", "count"]
                                        # Simple auto-detection for line evolution: time + multiple numeric series after melt scenario
                                        if any(c in _headers for c in _time_candidates) and any(c in _headers for c in _entity_candidates) and any(c in _headers for c in _value_candidates):
                                            # Could choose bar_race or line_evolution; keep existing bar_race precedence.
                                            pass
                                    except Exception:
                                        pass
                                if not autodetected:
                                    if spec.chart_type == "bubble" and not dataset_path:
                                        status_hint = "Bubble chart detected but no csv_path=... provided; falling back to LLM code generation."
                                    elif spec.chart_type == "bubble":
                                        status_hint = f"Bubble chart detected but dataset not found at {dataset_path}; falling back to LLM."
                                    elif spec.chart_type == "distribution" and not dataset_path:
                                        status_hint = "Distribution chart detected but no csv_path=... provided; falling back to LLM code generation."
                                    elif spec.chart_type == "distribution":
                                        status_hint = f"Distribution chart detected but dataset not found at {dataset_path}; falling back to LLM."
                                    elif spec.chart_type == "line_evolution":
                                        status_hint = f"Line evolution requested but dataset not found; falling back to LLM."
                                    elif spec.chart_type == "bento_grid":
                                        status_hint = f"Bento grid requested but dataset not found; falling back to LLM."
                                    elif spec.chart_type == "count_bar":
                                        status_hint = f"Count bar chart requested but dataset not found; falling back to LLM."
                                    elif spec.chart_type == "single_numeric":
                                        status_hint = f"Single numeric bar chart requested but dataset not found; falling back to LLM."
                                    else:
                                        status_hint = "No supported template match; falling back to LLM code generation."
                                    status = {
                                        "event": "RunContent",
                                        "content": status_hint,
                                        "created_at": int(time.time()),
                                    }
                                    if session_id:
                                        status["session_id"] = session_id
                                    status["run_id"] = run_id
                                    yield f"data: {json.dumps(status)}\n\n"
                except Exception as e:
                    teamplate_error = f"spec inference unavailable: {e}"
                    plog.error(PipelineStep.DATA_PREPROCESSING, f"Teamplate preprocesing is failed {e}", {
                        "error_type": type(e).__name__,
                        "error": str(e),
                    }, exception=e)

                if template_error:
                    # If user explicitly requested a template, treat template errors as terminal (no LLM fallback)
                    if explicit_chart and (requested_ct in ("bubble", "distribution", "bar_race")):
                        err_payload = {
                            "event": "RunError",
                            "content": template_error,
                            "created_at": int(time.time()),
                            "run_id": run_id,
                        }
                        if session_id:
                            err_payload["session_id"] = session_id
                        fail_run(run_id, template_error)
                        yield f"data: {json.dumps(err_payload)}\n\n"
                        yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                        return
                    else:
                        warn = {
                            "event": "RunContent",
                            "content": template_error,
                            "created_at": int(time.time()),
                        }
                        if session_id:
                            warn["session_id"] = session_id
                        warn["run_id"] = run_id
                        yield f"data: {json.dumps(warn)}\n\n"
                if not use_template:
                    # LLM Fallback path - comprehensive logging
                    plog.info(PipelineStep.LLM_FALLBACK_START, "No template matched, starting LLM fallback code generation", {
                        "engine": body.code_engine or "anthropic",
                        "model": body.code_model or "default",
                        "prompt_length": len(msg),
                        "has_extra_rules": bool(body.code_system_prompt),
                    })

                    fallback_status = {
                        "event": "RunContent",
                        "content": "No template matched. Starting LLM code generation (this may take 10-30 seconds)...",
                        "created_at": int(time.time()),
                        "run_id": run_id,
                    }
                    if session_id:
                        fallback_status["session_id"] = session_id
                    yield f"data: {json.dumps(fallback_status)}\n\n"

                    try:
                        plog.start_timer(PipelineStep.CODE_GENERATION_START)
                        plog.info(PipelineStep.CODE_GENERATION_START, "Calling LLM for code generation", {
                            "engine": body.code_engine or "anthropic",
                            "model": body.code_model or "default",
                        })

                        code = generate_manim_code(
                            prompt=msg,
                            engine=(body.code_engine or "anthropic"),
                            model=(body.code_model or None),
                            temperature=0.2,
                            max_tokens=1200,
                            extra_rules=(body.code_system_prompt or None),
                            run_id=run_id,
                        )

                        plog.step_with_duration(PipelineStep.CODE_GENERATION_COMPLETE, "LLM code generation completed successfully", {
                            "code_length": len(code) if code else 0,
                            "has_genscene": "class GenScene" in (code or ""),
                        })

                        status = {
                            "event": "RunContent",
                            "content": "Code generated. Creating preview...",
                            "created_at": int(time.time()),
                        }
                        if session_id:
                            status["session_id"] = session_id
                        status["run_id"] = run_id
                        yield f"data: {json.dumps(status)}\n\n"

                    except CodeGenerationError as e:
                        plog.error(PipelineStep.CODE_GENERATION_ERROR, f"LLM code generation failed: {e}", {
                            "engine": body.code_engine or "anthropic",
                            "model": body.code_model or "default",
                            "error_type": type(e).__name__,
                        }, exception=e)

                        err = {
                            "event": "RunError",
                            "content": str(e),
                            "created_at": int(time.time()),
                        }
                        if session_id:
                            err["session_id"] = session_id
                        err["run_id"] = run_id
                        fail_run(run_id, str(e))
                        plog.info(PipelineStep.RUN_FAILED, "Run failed due to code generation error", {"error": str(e)})
                        cleanup_logger(run_id)
                        yield f"data: {json.dumps(err)}\n\n"
                        yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                        return

                    except Exception as e:
                        plog.error(PipelineStep.CODE_GENERATION_ERROR, f"Unexpected error during LLM code generation: {e}", {
                            "engine": body.code_engine or "anthropic",
                            "error_type": type(e).__name__,
                            "traceback": traceback.format_exc(),
                        }, exception=e)

                        err = {
                            "event": "RunError",
                            "content": f"Unexpected error: {str(e)}",
                            "created_at": int(time.time()),
                        }
                        if session_id:
                            err["session_id"] = session_id
                        err["run_id"] = run_id
                        fail_run(run_id, str(e))
                        plog.info(PipelineStep.RUN_FAILED, "Run failed due to unexpected error", {"error": str(e)})
                        cleanup_logger(run_id)
                        yield f"data: {json.dumps(err)}\n\n"
                        yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                        return
                else:
                    # Template path already yielded a status; proceed directly to preview
                    status = {
                        "event": "RunContent",
                        "content": "Template code ready. Creating preview...",
                        "created_at": int(time.time()),
                    }
                    if session_id:
                        status["session_id"] = session_id
                    status["run_id"] = run_id
                    yield f"data: {json.dumps(status)}\n\n"

            # Ensure code is available
            if not isinstance(code, str) or not code.strip():
                plog.error(PipelineStep.CODE_GENERATION_ERROR, "No code was generated", {
                    "code_type": type(code).__name__,
                    "code_value": repr(code)[:100] if code else "(None)",
                })
                err_payload = {
                    "event": "RunError",
                    "content": "No code was generated for preview.",
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    err_payload["session_id"] = session_id
                fail_run(run_id, err_payload["content"])
                plog.info(PipelineStep.RUN_FAILED, "Run failed - no code generated")
                cleanup_logger(run_id)
                yield f"data: {json.dumps(err_payload)}\n\n"
                yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                return

            plog.info(PipelineStep.CODE_VALIDATION_START, "Starting code validation", {
                "code_length": len(code),
            })

            # Pre-preview: syntax validation and auto-fix loop (Point 1)
            max_fix_attempts = 2
            fix_attempt = 0
            while fix_attempt <= max_fix_attempts:
                ok, v_err = _quick_validate(code)
                if ok:
                    plog.info(PipelineStep.CODE_VALIDATION_PASS, "Code validation passed", {
                        "attempts": fix_attempt,
                    })
                    if fix_attempt > 0:
                        status = {
                            "event": "RunContent",
                            "content": f"Code fixed after {fix_attempt} attempt(s). Proceeding to preview...",
                            "created_at": int(time.time()),
                            "run_id": run_id,
                        }
                        if session_id:
                            status["session_id"] = session_id
                        yield f"data: {json.dumps(status)}\n\n"
                    break
                # Not ok
                plog.warning(PipelineStep.CODE_VALIDATION_FAIL, f"Code validation failed: {v_err}", {
                    "attempt": fix_attempt,
                    "max_attempts": max_fix_attempts,
                    "error": v_err,
                })
                if fix_attempt == max_fix_attempts:
                    plog.error(PipelineStep.CODE_VALIDATION_FAIL, "Code validation failed after all attempts", {
                        "error": v_err,
                        "attempts": fix_attempt,
                    })
                    err_payload = {
                        "event": "RunError",
                        "content": f"Code validation failed: {v_err}",
                        "created_at": int(time.time()),
                        "run_id": run_id,
                    }
                    if session_id:
                        err_payload["session_id"] = session_id
                    fail_run(run_id, err_payload["content"])
                    plog.info(PipelineStep.RUN_FAILED, "Run failed - code validation error")
                    cleanup_logger(run_id)
                    yield f"data: {json.dumps(err_payload)}\n\n"
                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                    return
                # Try auto-fix
                plog.info(PipelineStep.CODE_AUTO_FIX_START, f"Attempting auto-fix {fix_attempt + 1}/{max_fix_attempts}", {
                    "error": v_err,
                })
                notice = {
                    "event": "RunContent",
                    "content": f"Syntax issue detected ({v_err}). Attempting auto-fix {fix_attempt + 1}/{max_fix_attempts}...",
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    notice["session_id"] = session_id
                yield f"data: {json.dumps(notice)}\n\n"
                try:
                    code = _attempt_auto_fix(
                        bad_code=code,
                        error=v_err,
                        engine=(body.code_engine or "anthropic"),
                        model=(body.code_model or None),
                    )
                    plog.info(PipelineStep.CODE_AUTO_FIX_COMPLETE, "Auto-fix attempt completed", {
                        "attempt": fix_attempt + 1,
                    })
                except CodeGenerationError as fix_err:
                    plog.error(PipelineStep.CODE_AUTO_FIX_ERROR, f"Auto-fix failed: {fix_err}", {
                        "attempt": fix_attempt + 1,
                    })
                    # Keep code as-is; next loop may still pass if minor
                    pass
                fix_attempt += 1

            # 2) Preview frames with runtime auto-fix loop (Point 2)
            plog.info(PipelineStep.PREVIEW_START, "Starting preview generation", {
                "aspect_ratio": aspect_ratio,
                "sample_every": preview_sample_every,
                "max_frames": preview_max_frames,
                "quality": quality,
            })
            plog.start_timer(PipelineStep.PREVIEW_START)
            set_state(run_id, RunState.PREVIEWING, "Generating preview...")
            try:
                persist_run_state(run_id, "PREVIEWING", "Generating preview...")
            except Exception:
                pass
            max_runtime_fix_attempts = 2
            runtime_attempt = 0
            while runtime_attempt <= max_runtime_fix_attempts:
                had_runtime_error = False
                last_error_msg = ""
                allow_llm_fix = True  # classification flag from preview stream
                # Stream preview events (now includes heartbeat & progress)
                for event in generate_manim_preview_stream(
                    code=code,
                    class_name="GenScene",
                    aspect_ratio=aspect_ratio,
                    sample_every=preview_sample_every,
                    max_frames=preview_max_frames,
                    user_id=user_id,
                    project_name="demo",
                    iteration=1,
                    run_id=run_id,
                    quality=quality,
                    heartbeat_interval=5,
                    enable_progress=True,
                    preset="preview",
                    preview_frame_rate=10,
                ):
                    ev_type = event.get("event", "RunContent")
                    payload = {
                        "event": ev_type,
                        "content": event.get("content", ""),
                        "created_at": int(time.time()),
                    }
                    if session_id:
                        payload["session_id"] = session_id
                    if "images" in event:
                        payload["images"] = event["images"]
                    if "elapsed_seconds" in event:
                        payload["elapsed_seconds"] = event["elapsed_seconds"]
                    payload["run_id"] = run_id

                    # Heartbeat events: forward but do not treat as content or error
                    if ev_type == "RunHeartbeat":
                        yield f"data: {json.dumps(payload)}\n\n"
                        continue

                    if ev_type == "RunError":
                        had_runtime_error = True
                        last_error_msg = payload.get("content", "Preview error")
                        # Preview stream attaches allow_llm_fix classification flag
                        allow_llm_fix = bool(event.get("allow_llm_fix", True))
                        break  # exit loop to decide on auto-fix or abort

                    # Normal content / progress passthrough
                    yield f"data: {json.dumps(payload)}\n\n"

                if not had_runtime_error:
                    # Preview completed successfully; continue pipeline
                    plog.step_with_duration(PipelineStep.PREVIEW_COMPLETE, "Preview generation completed successfully", {
                        "runtime_attempts": runtime_attempt,
                    })
                    break

                # We had a preview error (classified)
                plog.error(PipelineStep.PREVIEW_ERROR, f"Preview error: {last_error_msg}", {
                    "attempt": runtime_attempt,
                    "max_attempts": max_runtime_fix_attempts,
                    "allow_llm_fix": allow_llm_fix,
                })
                if (runtime_attempt == max_runtime_fix_attempts) or (not allow_llm_fix):
                    # Give up early if classification forbids LLM fix OR attempts exhausted
                    plog.error(PipelineStep.PREVIEW_ERROR, "Preview failed after all attempts or LLM fix not allowed", {
                        "last_error": last_error_msg,
                        "attempts": runtime_attempt,
                        "allow_llm_fix": allow_llm_fix,
                    })
                    fail_payload = {
                        "event": "RunError",
                        "content": last_error_msg or "Preview error",
                        "created_at": int(time.time()),
                        "run_id": run_id,
                        "allow_llm_fix": allow_llm_fix,
                    }
                    if session_id:
                        fail_payload["session_id"] = session_id
                    fail_run(run_id, fail_payload["content"])
                    plog.info(PipelineStep.RUN_FAILED, "Run failed - preview error")
                    cleanup_logger(run_id)
                    yield f"data: {json.dumps(fail_payload)}\n\n"
                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                    return

                # Attempt runtime auto-fix (classification allowed)
                fix_notice = {
                    "event": "RunContent",
                    "content": f"Preview error detected. Attempting auto-fix {runtime_attempt + 1}/{max_runtime_fix_attempts}...",
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    fix_notice["session_id"] = session_id
                yield f"data: {json.dumps(fix_notice)}\n\n"

                try:
                    code = _attempt_auto_fix(
                        bad_code=code,
                        error=last_error_msg,
                        engine=(body.code_engine or "anthropic"),
                        model=(body.code_model or None),
                    )
                except CodeGenerationError:
                    # Keep existing code; next loop may still succeed or terminate
                    pass

                runtime_attempt += 1

            # 3) Final render to MP4
            plog.info(PipelineStep.RENDER_START, "Starting video render", {
                "aspect_ratio": aspect_ratio,
                "quality": quality,
            })
            plog.start_timer(PipelineStep.RENDER_START)
            set_state(run_id, RunState.RENDERING, "Rendering video...")
            try:
                persist_run_state(run_id, "RENDERING", "Rendering video...")
            except Exception:
                pass
            for event in render_manim_stream(
                code=code,
                file_class="GenScene",
                aspect_ratio=aspect_ratio,
                project_name="demo",
                user_id=user_id,
                iteration=1,
                run_id=run_id,
                quality=quality,
            ):
                payload = {
                    "event": event.get("event", "RunContent"),
                    "content": event.get("content", ""),
                    "created_at": int(time.time()),
                }
                if session_id:
                    payload["session_id"] = session_id
                if "videos" in event:
                    payload["videos"] = event["videos"]
                    try:
                        for v in event["videos"]:
                            if isinstance (v, dict):
                                storage_session = v.get("url") or ""
                            else:
                                storage_session = str(v)

                            if not storage_session:
                                logger.warning("session is not in storage")
                                continue

                            persist_artifact(run_id, "video", storage_session)
                    except Exception:
                        pass
                    plog.step_with_duration(PipelineStep.RENDER_COMPLETE, "Video render completed successfully", {
                        "num_videos": len(event["videos"]),
                    })
                    complete_run(run_id, "Render completed.")
                    try:
                        persist_run_completed(run_id, "Render completed.")
                    except Exception:
                        pass
                payload["run_id"] = run_id
                if payload["event"] == "RunError":
                    plog.error(PipelineStep.RENDER_ERROR, f"Render error: {payload.get('content', 'Unknown')}", {
                        "error": payload.get("content", "Render error"),
                    })
                    fail_run(run_id, payload.get("content", "Render error"))
                    try:
                        persist_run_failed(run_id, payload.get("content", "Render error"))
                    except Exception:
                        pass
                    plog.info(PipelineStep.RUN_FAILED, "Run failed - render error")
                    cleanup_logger(run_id)
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                    return
                yield f"data: {json.dumps(payload)}\n\n"

            # 4) Done
            plog.info(PipelineStep.RUN_COMPLETED, "Animation pipeline completed successfully", {
                "summary": plog.get_summary(),
            })
            complete_run(run_id, "Completed")
            try:
                persist_run_completed(run_id, "Completed")
            except Exception:
                pass
            # Optional: emit a text summary of the generated animation
            try:
                if getattr(body, "summarize", False):
                    try:
                        from agents.tools.summarization import summarize_text  # local import to avoid top-level dependency
                    except Exception:
                        summarize_text = None
                    if summarize_text:
                        summary = summarize_text(
                            text=f"User request:\n{msg}\n\nGenerated code:\n{code}",
                            engine=(body.code_engine or "anthropic"),
                            model=(body.code_model or None),
                            temperature=0.2,
                            max_tokens=400,
                            instructions="Summarize what the resulting animation shows and its key steps. Keep it concise.",
                            bullet=True,
                        )
                        summary_payload = {
                            "event": "RunContent",
                            "content": summary,
                            "created_at": int(time.time()),
                            "run_id": run_id,
                        }
                        if session_id:
                            summary_payload["session_id"] = session_id
                        yield f"data: {json.dumps(summary_payload)}\n\n"
            except Exception:
                # Ignore summarization failures; still complete the run
                pass

            done = {
                "event": "RunCompleted",
                "content": "",
                "created_at": int(time.time()),
            }
            if session_id:
                done["session_id"] = session_id
            done["run_id"] = run_id
            cleanup_logger(run_id)
            yield f"data: {json.dumps(done)}\n\n"

        return StreamingResponse(
            animation_sse(),
            media_type="text/event-stream",
        )

    try:
        agent: Agent = get_agent(
            model_id=body.model.value,
            agent_id=agent_id,
            user_id=body.user_id,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if body.stream:
        return StreamingResponse(
            chat_response_streamer(agent, body.message),
            media_type="text/event-stream",
        )
    else:
        response = await agent.arun(body.message, stream=False)
        # In this case, the response.content only contains the text response from the Agent.
        # For advanced use cases, we should yield the entire response
        # that contains the tool calls and intermediate steps.
        return response.content


@agents_router.post("/runs/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_run_endpoint(run_id: str):
    """
    Cancel a running job by run_id.
    """
    ok = cancel_run(run_id, reason="user_request")
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return {"run_id": run_id, "status": "canceled"}


@agents_router.get("/runs/{run_id}", status_code=status.HTTP_200_OK)
async def get_run_status(run_id: str):
    """
    Return the status and metadata for a specific run.
    """
    info = get_run(run_id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return info.to_dict()


@agents_router.get("/runs", status_code=status.HTTP_200_OK)
async def list_all_runs():
    """
    List all known runs with their current state and metadata.
    """
    return list_runs()


class TemplateSelectionRequest(BaseModel):
    """Request model for selecting a template."""
    template_id: str = Field(..., description="The template ID to use (e.g., 'bar_race', 'bubble')")
    session_id: Optional[str] = Field(None, description="The session ID")
    column_mapping: Optional[Dict[str, Optional[str]]] = Field(
        None,
        description="User-specified column mappings for the template (e.g., {'time_col': 'year', 'value_col': 'sales'})"
    )


@agents_router.post("/runs/{run_id}/select_template", status_code=status.HTTP_200_OK)
async def select_template_for_run(
    run_id: str,
    body: TemplateSelectionRequest,
    current_user=Depends(get_current_user_optional),
):
    """
    Select a template for a run that is awaiting template selection.

    This endpoint is used when the auto_select_templates setting is disabled
    and the system has emitted a TemplateSuggestions event. The user selects
    a template and this endpoint resumes the animation pipeline.

    Args:
        run_id: The run ID that is awaiting template selection
        body: The template selection request

    Returns:
        StreamingResponse with the animation pipeline SSE events
    """
    # Initialize pipeline logger early for request tracking
    plog_init = get_pipeline_logger(run_id=run_id)
    plog_init.info(PipelineStep.REQUEST_RECEIVED, "Template selection request received", {
        "run_id": run_id,
        "template_id": body.template_id,
        "session_id": body.session_id,
        "column_mapping": body.column_mapping,
    })

    # Validate template selection
    is_valid, error_msg = validate_template_selection(body.template_id)
    if not is_valid:
        plog_init.warning(PipelineStep.REQUEST_VALIDATED, f"Invalid template selection: {error_msg}", {
            "template_id": body.template_id,
        })
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    plog_init.info(PipelineStep.REQUEST_VALIDATED, "Template selection validated", {
        "template_id": body.template_id,
    })

    # Get the run info
    run_info = get_run(run_id)
    if not run_info:
        plog_init.error(PipelineStep.RUN_FAILED, "Run not found", {"run_id": run_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    plog_init.debug(PipelineStep.REQUEST_VALIDATED, "Run info retrieved", {
        "run_state": run_info.state.name if run_info.state else "unknown",
        "session_id": run_info.session_id,
    })

    # Check if run is in the correct state
    if run_info.state != RunState.AWAITING_TEMPLATE_SELECTION:
        plog_init.warning(PipelineStep.RUN_FAILED, "Run not in correct state for template selection", {
            "current_state": run_info.state.name if run_info.state else "unknown",
            "expected_state": "AWAITING_TEMPLATE_SELECTION",
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Run is not awaiting template selection. Current state: {run_info.state.name}"
        )

    # Get pending data from run registry (primary) or session context (fallback)
    plog_init.debug(PipelineStep.DATA_BINDING, "Retrieving pending template selection data", {
        "run_id": run_id,
    })
    pending_data = get_pending_template_selection(run_id)
    session_id = body.session_id or run_info.session_id

    plog_init.debug(PipelineStep.DATA_BINDING, "Session ID resolved", {
        "session_id": session_id,
        "from_body": bool(body.session_id),
        "from_run_info": bool(run_info.session_id),
    })

    # Always get session context if session_id exists (needed for data_binding later)
    session_ctx = get_session_context(session_id) if session_id else None

    plog_init.debug(PipelineStep.DATA_BINDING, "Session context lookup", {
        "session_ctx_exists": session_ctx is not None,
        "has_data_binding": bool(session_ctx and session_ctx.data_binding) if session_ctx else False,
    })

    # Track where we got the data from, so we can clear it after successful validation
    pending_data_source = None  # Will be "run_registry" or "session_context"

    if pending_data:
        # Use run-based storage (more reliable, doesn't require session_id)
        original_message = pending_data.get("original_message") or ""
        csv_path = pending_data.get("csv_path")
        plog_init.info(PipelineStep.DATA_BINDING, "Retrieved pending data from run registry", {
            "csv_path": csv_path,
            "original_message_length": len(original_message),
            "data_binding": pending_data.get("data_binding"),
        })
        # NOTE: Don't clear pending state yet - wait until validation passes
        # This allows users to retry with corrected mappings if validation fails
        pending_data_source = "run_registry"
    else:
        # Fallback to session context (for backward compatibility)
        plog_init.warning(PipelineStep.DATA_BINDING, "No pending data in run registry, trying session context", {
            "session_id": session_id,
        })
        if not session_ctx or not session_ctx.has_pending_template_selection():
            plog_init.error(PipelineStep.RUN_FAILED, "No pending template selection found", {
                "run_id": run_id,
                "session_id": session_id,
                "session_ctx_exists": session_ctx is not None,
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending template selection found for this run"
            )

        # Get the pending data from session context
        original_message = session_ctx.pending_original_message or ""
        csv_path = session_ctx.get_effective_csv_path()
        plog_init.info(PipelineStep.DATA_BINDING, "Retrieved pending data from session context", {
            "csv_path": csv_path,
            "original_message_length": len(original_message),
        })

        # NOTE: Don't clear pending state yet - wait until validation passes
        # This allows users to retry with corrected mappings if validation fails
        pending_data_source = "session_context"

    # Update the session context with the selected chart type (if session exists)
    if session_id:
        update_session_context(
            session_id=session_id,
            chart_type=body.template_id,
        )
        plog_init.debug(PipelineStep.DATA_BINDING, "Updated session context with selected template", {
            "template_id": body.template_id,
        })

    plog_init.info(PipelineStep.TEMPLATE_SELECTED, "Template selection validated, starting pipeline resume", {
        "template_id": body.template_id,
        "csv_path": csv_path,
        "session_id": session_id,
    })

    # =========================================================================
    # COLUMN MAPPING VALIDATION
    # Validate that user-provided column mappings are compatible with the
    # template requirements AND the actual dataset schema.
    # =========================================================================

    # Create a mutable copy of column mappings that we can augment
    effective_column_mapping = dict(body.column_mapping) if body.column_mapping else {}

    if csv_path:
        plog_init.info(PipelineStep.DATA_BINDING, "Validating column mappings against dataset schema", {
            "template_id": body.template_id,
            "column_mapping": effective_column_mapping,
            "csv_path": csv_path,
        })

        # Get schema information from chart inference
        try:
            from agents.tools.chart_inference import analyze_schema

            # Resolve the CSV path
            resolved_csv_path = csv_path
            if csv_path.startswith("/static/"):
                resolved_csv_path = csv_path.replace("/static/", "artifacts/", 1)
                if not os.path.isabs(resolved_csv_path):
                    resolved_csv_path = os.path.join(os.getcwd(), resolved_csv_path)

            if os.path.exists(resolved_csv_path):
                schema = analyze_schema(resolved_csv_path)

                # =========================================================
                # AUTO-FILL MISSING REQUIRED MAPPINGS
                # If the user didn't provide a time_column but the schema
                # detected one, auto-fill it to reduce friction
                # =========================================================
                from api.routes.templates import get_smart_column_suggestions, TEMPLATES_BY_ID

                template_def = TEMPLATES_BY_ID.get(body.template_id)
                if template_def:
                    # Get smart suggestions for this template
                    smart_suggestions = get_smart_column_suggestions(
                        template_id=body.template_id,
                        numeric_columns=schema.numeric_columns,
                        categorical_columns=schema.categorical_columns,
                        time_column=schema.time_column,
                    )

                    # Auto-fill missing required mappings with suggestions
                    auto_filled = []
                    for axis in template_def.axes:
                        if not axis.required:
                            continue

                        # Check if this axis is already mapped
                        axis_name = axis.name
                        short_name = axis_name.replace("_column", "_col")

                        is_mapped = (
                            effective_column_mapping.get(axis_name) or
                            effective_column_mapping.get(short_name)
                        )

                        if not is_mapped and axis_name in smart_suggestions:
                            # Auto-fill this mapping
                            effective_column_mapping[axis_name] = smart_suggestions[axis_name]
                            auto_filled.append(f"{axis_name}={smart_suggestions[axis_name]}")

                    if auto_filled:
                        plog_init.info(PipelineStep.DATA_BINDING, "Auto-filled missing required mappings", {
                            "auto_filled": auto_filled,
                            "effective_mapping": effective_column_mapping,
                        })

                # Validate column mappings against template requirements and schema
                validation_result = validate_column_mappings_with_schema(
                    template_id=body.template_id,
                    mappings=effective_column_mapping,
                    csv_path=csv_path,
                    numeric_columns=schema.numeric_columns,
                    categorical_columns=schema.categorical_columns,
                    time_column=schema.time_column,
                    all_columns=schema.columns,
                    is_wide_format=schema.is_wide_format,
                )

                if not validation_result.is_valid:
                    plog_init.error(PipelineStep.DATA_BINDING, "Column mapping validation failed", {
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings,
                        "suggestions": validation_result.suggestions,
                    })

                    # Build a helpful error message with suggestions
                    error_details = {
                        "message": "Invalid column mappings for the selected template.",
                        "errors": validation_result.errors,
                        "suggestions": validation_result.suggestions,
                        "available_columns": {
                            "numeric": schema.numeric_columns[:10],
                            "categorical": schema.categorical_columns[:10],
                            "time": schema.time_column,
                        },
                    }

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_details,
                    )

                # Log warnings if any
                if validation_result.warnings:
                    plog_init.warning(PipelineStep.DATA_BINDING, "Column mapping warnings", {
                        "warnings": validation_result.warnings,
                    })

                plog_init.info(PipelineStep.DATA_BINDING, "Column mapping validation passed", {
                    "template_id": body.template_id,
                })

                # NOW clear pending state - validation passed, so user won't need to retry
                if pending_data_source == "run_registry":
                    clear_pending_template_selection(run_id)
                    plog_init.debug(PipelineStep.DATA_BINDING, "Cleared pending state from run registry after successful validation", {})
                elif pending_data_source == "session_context" and session_ctx:
                    session_ctx.clear_pending_template_selection()
                    plog_init.debug(PipelineStep.DATA_BINDING, "Cleared pending state from session context after successful validation", {})
            else:
                plog_init.warning(PipelineStep.DATA_BINDING, "Could not validate column mappings - CSV not found", {
                    "csv_path": csv_path,
                    "resolved_path": resolved_csv_path,
                })
                # Still clear pending state - we're proceeding without validation
                if pending_data_source == "run_registry":
                    clear_pending_template_selection(run_id)
                elif pending_data_source == "session_context" and session_ctx:
                    session_ctx.clear_pending_template_selection()

        except ImportError as e:
            plog_init.warning(PipelineStep.DATA_BINDING, f"Could not import chart_inference for validation: {e}", {})
            # Clear pending state on import error - we're proceeding anyway
            if pending_data_source == "run_registry":
                clear_pending_template_selection(run_id)
            elif pending_data_source == "session_context" and session_ctx:
                session_ctx.clear_pending_template_selection()
        except HTTPException:
            # Re-raise HTTP exceptions - DO NOT clear pending state, user can retry
            raise
        except Exception as e:
            # Log but don't fail - let the pipeline handle validation errors downstream
            plog_init.warning(PipelineStep.DATA_BINDING, f"Column mapping validation error (non-fatal): {e}", {
                "error_type": type(e).__name__,
            })
            # Clear pending state on non-fatal error - we're proceeding anyway
            if pending_data_source == "run_registry":
                clear_pending_template_selection(run_id)
            elif pending_data_source == "session_context" and session_ctx:
                session_ctx.clear_pending_template_selection()
    else:
        # No column_mapping or csv_path - clear pending state and proceed
        plog_init.debug(PipelineStep.DATA_BINDING, "Skipping column mapping validation - no mappings or csv_path provided", {
            "has_column_mapping": bool(body.column_mapping),
            "has_csv_path": bool(csv_path),
        })
        if pending_data_source == "run_registry":
            clear_pending_template_selection(run_id)
        elif pending_data_source == "session_context" and session_ctx:
            session_ctx.clear_pending_template_selection()

    # Resume the animation pipeline with the selected template
    def resume_animation_sse():
        registry_user_id = (current_user.id if current_user else "local")
        db_user_id = (current_user.id if current_user else None)
        user_id = registry_user_id

        # Initialize pipeline logger
        plog = get_pipeline_logger(run_id=run_id, session_id=session_id, user_id=user_id)
        plog.info(PipelineStep.RUN_STARTED, "=== ANIMATION PIPELINE RESUME STARTED ===", {
            "template_id": body.template_id,
            "csv_path": csv_path,
            "user_id": user_id,
            "column_mapping": effective_column_mapping,
        })

        # Update run state
        set_state(run_id, RunState.STARTING, f"Template selected: {body.template_id}")
        plog.debug(PipelineStep.RUN_STARTED, "Run state updated to STARTING", {})
        try:
            persist_run_state(run_id, "STARTING", f"Template selected: {body.template_id}")
            plog.debug(PipelineStep.RUN_STARTED, "Run state persisted to database", {})
        except Exception as e:
            plog.warning(PipelineStep.RUN_STARTED, f"Failed to persist run state: {e}", {})

        # Emit template selected event
        plog.info(PipelineStep.TEMPLATE_SELECTED, "Emitting template selected SSE event", {
            "template_id": body.template_id,
        })
        selected_payload = {
            "event": TemplateSuggestionEvents.TEMPLATE_SELECTED,
            "content": f"Template selected: **{body.template_id}**. Generating animation...",
            "template_id": body.template_id,
            "run_id": run_id,
            "created_at": int(time.time()),
        }
        if session_id:
            selected_payload["session_id"] = session_id
        yield f"data: {json.dumps(selected_payload)}\n\n"

        # Now generate code using the selected template
        plog.info(PipelineStep.CODE_GENERATION_START, "=== CODE GENERATION PHASE STARTED ===", {
            "template_id": body.template_id,
            "csv_path": csv_path,
        })
        try:
            import os
            from agents.tools.specs import infer_spec_from_prompt
            from agents.tools.danim_templates import (
                generate_bubble_code,
                generate_distribution_code,
                generate_bar_race_code,
                generate_line_evolution_code,
                generate_bento_grid_code,
                generate_count_bar_code,
                generate_single_numeric_code,
            )

            # Infer spec from original message
            plog.debug(PipelineStep.SPEC_INFERENCE_START, "Inferring spec from original message", {
                "original_message_length": len(original_message),
                "csv_path": csv_path,
            })
            spec = infer_spec_from_prompt(original_message, csv_path=csv_path)
            spec.chart_type = body.template_id
            plog.info(PipelineStep.SPEC_INFERENCE_COMPLETE, "Spec inference complete", {
                "chart_type": spec.chart_type,
                "has_data_binding": hasattr(spec, "data_binding"),
            })

            # Get user-specified column mapping (if provided)
            # Use effective_column_mapping which includes auto-filled required mappings
            col_map = effective_column_mapping or {}
            plog.debug(PipelineStep.DATA_BINDING, "Column mapping (including auto-filled)", {
                "col_map": col_map,
                "has_mapping": bool(col_map),
            })

            # Restore data binding from session context if available
            if session_ctx and session_ctx.data_binding:
                plog.debug(PipelineStep.DATA_BINDING, "Restoring data binding from session context", {
                    "session_data_binding": session_ctx.data_binding,
                })
                if hasattr(spec, "data_binding"):
                    db = spec.data_binding
                    binding = session_ctx.data_binding
                    if binding.get("time_col"):
                        setattr(db, "time_col", binding["time_col"])
                    if binding.get("value_col"):
                        setattr(db, "value_col", binding["value_col"])
                    if binding.get("group_col"):
                        setattr(db, "group_col", binding["group_col"])
                        setattr(db, "entity_col", binding["group_col"])
                    plog.info(PipelineStep.DATA_BINDING, "Data binding restored from session", {
                        "time_col": getattr(db, "time_col", None),
                        "value_col": getattr(db, "value_col", None),
                        "group_col": getattr(db, "group_col", None),
                    })

            # Override with user-specified column mappings
            if col_map and hasattr(spec, "data_binding"):
                plog.debug(PipelineStep.DATA_BINDING, "Applying user-specified column mappings", {
                    "col_map": col_map,
                })
                db = spec.data_binding
                if col_map.get("time_col"):
                    setattr(db, "time_col", col_map["time_col"])
                if col_map.get("value_col"):
                    setattr(db, "value_col", col_map["value_col"])
                if col_map.get("group_col"):
                    setattr(db, "group_col", col_map["group_col"])
                if col_map.get("category_col"):
                    setattr(db, "group_col", col_map["category_col"])
                    setattr(db, "entity_col", col_map["category_col"])
                if col_map.get("entity_col"):
                    setattr(db, "entity_col", col_map["entity_col"])
                if col_map.get("x_col"):
                    setattr(db, "x_col", col_map["x_col"])
                if col_map.get("y_col"):
                    setattr(db, "y_col", col_map["y_col"])
                if col_map.get("r_col"):
                    setattr(db, "r_col", col_map["r_col"])
                plog.info(PipelineStep.DATA_BINDING, "User column mappings applied to spec", {
                    "final_time_col": getattr(db, "time_col", None),
                    "final_value_col": getattr(db, "value_col", None),
                    "final_group_col": getattr(db, "group_col", None),
                    "final_x_col": getattr(db, "x_col", None),
                    "final_y_col": getattr(db, "y_col", None),
                    "final_r_col": getattr(db, "r_col", None),
                })

            dataset_path = csv_path
            code = None
            use_template = False

            plog.info(PipelineStep.TEMPLATE_GENERATION, "Starting template code generation", {
                "template_id": body.template_id,
                "dataset_path": dataset_path,
                "dataset_exists": os.path.exists(dataset_path) if dataset_path else False,
            })

            # Generate code based on selected template with user column mappings
            if body.template_id == "bubble" and dataset_path and os.path.exists(dataset_path):
                # Bubble chart: x_col, y_col, r_col, entity_col, time_col, group_col
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating bubble chart code", {
                    "x_col": col_map.get("x_col"),
                    "y_col": col_map.get("y_col"),
                    "r_col": col_map.get("r_col"),
                    "entity_col": col_map.get("entity_col"),
                    "time_col": col_map.get("time_col"),
                    "group_col": col_map.get("group_col"),
                })
                from agents.tools.templates.bubble_chart import generate_bubble_chart
                code = generate_bubble_chart(
                    spec, dataset_path,
                    theme="youtube_dark",
                    x_col=col_map.get("x_col"),
                    y_col=col_map.get("y_col"),
                    r_col=col_map.get("r_col"),
                    entity_col=col_map.get("entity_col"),
                    time_col=col_map.get("time_col"),
                    group_col=col_map.get("group_col"),
                )
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Bubble chart code generated successfully", {
                    "code_length": len(code) if code else 0,
                })
            elif body.template_id == "distribution" and dataset_path and os.path.exists(dataset_path):
                # Distribution: value_col, group_col
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating distribution chart code", {
                    "value_col": col_map.get("value_col"),
                    "group_col": col_map.get("group_col"),
                })
                from agents.tools.templates.distribution import generate_distribution
                code = generate_distribution(
                    spec, dataset_path,
                    theme="youtube_dark",
                    value_col=col_map.get("value_col"),
                    group_col=col_map.get("group_col"),
                )
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Distribution chart code generated successfully", {
                    "code_length": len(code) if code else 0,
                })
            elif body.template_id == "bar_race" and dataset_path and os.path.exists(dataset_path):
                # Bar race: time_col, value_col, category_col
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating bar race chart code", {
                    "time_col": col_map.get("time_col"),
                    "value_col": col_map.get("value_col"),
                    "category_col": col_map.get("category_col"),
                })
                from agents.tools.templates.bar_race import generate_bar_race
                code = generate_bar_race(
                    spec, dataset_path,
                    theme="youtube_dark",
                    time_col=col_map.get("time_col"),
                    value_col=col_map.get("value_col"),
                    category_col=col_map.get("category_col"),
                )
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Bar race chart code generated successfully", {
                    "code_length": len(code) if code else 0,
                })
            elif body.template_id == "line_evolution" and dataset_path and os.path.exists(dataset_path):
                # Line evolution: time_col, value_col, group_col
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating line evolution chart code", {
                    "time_col": col_map.get("time_col"),
                    "value_col": col_map.get("value_col"),
                    "group_col": col_map.get("group_col"),
                })
                from agents.tools.templates.line_evolution import generate_line_evolution
                code = generate_line_evolution(
                    spec, dataset_path,
                    theme="youtube_dark",
                    time_col=col_map.get("time_col"),
                    value_col=col_map.get("value_col"),
                    group_col=col_map.get("group_col"),
                )
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Line evolution chart code generated successfully", {
                    "code_length": len(code) if code else 0,
                })
            elif body.template_id == "bento_grid" and dataset_path and os.path.exists(dataset_path):
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating bento grid code", {})
                code = generate_bento_grid_code(spec, dataset_path)
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Bento grid code generated successfully", {
                    "code_length": len(code) if code else 0,
                })
            elif body.template_id == "count_bar" and dataset_path and os.path.exists(dataset_path):
                # Count bar: count_column
                count_col = col_map.get("count_column")
                if not count_col:
                    _binding = getattr(spec, "data_binding", None)
                    count_col = getattr(_binding, "group_col", None) if _binding else None
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating count bar chart code", {
                    "count_column": count_col,
                })
                code = generate_count_bar_code(spec, dataset_path, count_column=count_col)
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Count bar chart code generated successfully", {
                    "code_length": len(code) if code else 0,
                })
            elif body.template_id == "single_numeric" and dataset_path and os.path.exists(dataset_path):
                # Single numeric: category_column, value_column
                cat_col = col_map.get("category_column")
                val_col = col_map.get("value_column")
                if not cat_col or not val_col:
                    _binding = getattr(spec, "data_binding", None)
                    if not cat_col:
                        cat_col = getattr(_binding, "group_col", None) if _binding else None
                    if not val_col:
                        val_col = getattr(_binding, "value_col", None) if _binding else None
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Generating single numeric chart code", {
                    "category_column": cat_col,
                    "value_column": val_col,
                })
                code = generate_single_numeric_code(spec, dataset_path, category_column=cat_col, value_column=val_col)
                use_template = True
                plog.info(PipelineStep.TEMPLATE_GENERATION, "Single numeric chart code generated successfully", {
                    "code_length": len(code) if code else 0,
                })

            if not use_template or not code:
                # Fallback to LLM code generation
                plog.warning(PipelineStep.LLM_FALLBACK_START, "Template generation failed or not available, falling back to LLM", {
                    "template_id": body.template_id,
                    "use_template": use_template,
                    "code_generated": bool(code),
                    "dataset_path": dataset_path,
                    "dataset_exists": os.path.exists(dataset_path) if dataset_path else False,
                })
                status_payload = {
                    "event": "RunContent",
                    "content": f"Template {body.template_id} not available for this dataset. Falling back to LLM code generation...",
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    status_payload["session_id"] = session_id
                yield f"data: {json.dumps(status_payload)}\n\n"

                plog.info(PipelineStep.LLM_API_CALL_START, "Starting LLM code generation", {
                    "engine": "anthropic",
                    "prompt_length": len(original_message),
                })
                code = generate_manim_code(
                    prompt=original_message,
                    engine="anthropic",
                    model=None,
                    temperature=0.2,
                    max_tokens=1200,
                )
                plog.info(PipelineStep.LLM_API_CALL_COMPLETE, "LLM code generation complete", {
                    "code_length": len(code) if code else 0,
                })

            # Emit code generated event
            plog.info(PipelineStep.CODE_GENERATION_COMPLETE, "=== CODE GENERATION PHASE COMPLETE ===", {
                "template_id": body.template_id,
                "code_length": len(code) if code else 0,
                "use_template": use_template,
            })
            code_payload = {
                "event": "RunContent",
                "content": f"Code generated using {body.template_id} template. Starting preview...",
                "created_at": int(time.time()),
                "run_id": run_id,
            }
            if session_id:
                code_payload["session_id"] = session_id
            yield f"data: {json.dumps(code_payload)}\n\n"

            # Now proceed to preview and render (simplified - full implementation continues in main pipeline)
            # For now, emit the code and mark as ready for preview
            aspect_ratio = (session_ctx.aspect_ratio if session_ctx else None) or "16:9"
            preview_sample_every = api_settings.preview_sample_every
            preview_max_frames = api_settings.preview_max_frames
            quality = (session_ctx.render_quality if session_ctx else None) or api_settings.default_render_quality

            plog.info(PipelineStep.PREVIEW_START, "=== PREVIEW GENERATION PHASE STARTED ===", {
                "aspect_ratio": aspect_ratio,
                "preview_sample_every": preview_sample_every,
                "preview_max_frames": preview_max_frames,
            })

            # Generate preview
            set_state(run_id, RunState.PREVIEWING, "Generating preview...")
            try:
                persist_run_state(run_id, "PREVIEWING", "Generating preview...")
            except Exception as e:
                plog.warning(PipelineStep.PREVIEW_START, f"Failed to persist preview state: {e}", {})

            preview_frame_count = 0
            for preview_event in generate_manim_preview_stream(
                code,
                run_id=run_id,
                sample_every=preview_sample_every,
                max_frames=preview_max_frames,
                aspect_ratio=aspect_ratio,
            ):
                preview_payload = {
                    "event": preview_event.get("event", "RunContent"),
                    "content": preview_event.get("content", ""),
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    preview_payload["session_id"] = session_id
                if "images" in preview_event:
                    preview_payload["images"] = preview_event["images"]
                    preview_frame_count += len(preview_event["images"])
                    plog.debug(PipelineStep.PREVIEW_FRAME_GENERATED, f"Preview frames generated: {preview_frame_count}", {
                        "frames_in_event": len(preview_event["images"]),
                    })
                yield f"data: {json.dumps(preview_payload)}\n\n"

            plog.info(PipelineStep.PREVIEW_COMPLETE, "=== PREVIEW GENERATION PHASE COMPLETE ===", {
                "total_frames": preview_frame_count,
            })

            # Generate final video
            plog.info(PipelineStep.RENDER_START, "=== RENDER PHASE STARTED ===", {
                "quality": quality,
                "aspect_ratio": aspect_ratio,
            })
            set_state(run_id, RunState.RENDERING, "Rendering final video...")
            try:
                persist_run_state(run_id, "RENDERING", "Rendering final video...")
            except Exception as e:
                plog.warning(PipelineStep.RENDER_START, f"Failed to persist render state: {e}", {})

            for render_event in render_manim_stream(
                code,
                run_id=run_id,
                quality=quality,
                aspect_ratio=aspect_ratio,
                user_id=user_id,
            ):
                render_payload = {
                    "event": render_event.get("event", "RunContent"),
                    "content": render_event.get("content", ""),
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    render_payload["session_id"] = session_id
                if "videos" in render_event:
                    render_payload["videos"] = render_event["videos"]
                    plog.info(PipelineStep.RENDER_COMPLETE, "Video render complete", {
                        "video_count": len(render_event["videos"]),
                        "videos": [v.get("url") if isinstance(v, dict) else str(v) for v in render_event["videos"]],
                    })
                    # Persist video artifacts
                    try:
                        for v in render_event["videos"]:
                            storage_path = v.get("url") if isinstance(v, dict) else str(v)
                            if storage_path:
                                persist_artifact(run_id, "video", storage_path)
                                plog.debug(PipelineStep.RENDER_COMPLETE, "Video artifact persisted", {
                                    "storage_path": storage_path,
                                })
                    except Exception as e:
                        plog.warning(PipelineStep.RENDER_ERROR, f"Failed to persist video artifact: {e}", {})
                yield f"data: {json.dumps(render_payload)}\n\n"

            # Mark run as completed
            plog.info(PipelineStep.RUN_COMPLETED, "=== ANIMATION PIPELINE COMPLETED SUCCESSFULLY ===", {
                "run_id": run_id,
                "template_id": body.template_id,
            })
            complete_run(run_id, "Animation completed successfully.")
            try:
                persist_run_completed(run_id, "Animation completed successfully.")
            except Exception as e:
                plog.warning(PipelineStep.RUN_COMPLETED, f"Failed to persist run completed: {e}", {})

            final_payload = {
                "event": "RunCompleted",
                "content": "Animation completed successfully!",
                "run_id": run_id,
                "created_at": int(time.time()),
            }
            if session_id:
                final_payload["session_id"] = session_id
            yield f"data: {json.dumps(final_payload)}\n\n"

            # Cleanup logger
            cleanup_logger(run_id)

        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            error_msg = f"Animation pipeline failed: {str(e)}"
            plog.error(PipelineStep.RUN_FAILED, "=== ANIMATION PIPELINE FAILED ===", {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": tb_str,
                "template_id": body.template_id,
                "csv_path": csv_path,
            }, exception=e)
            fail_run(run_id, error_msg)
            try:
                persist_run_failed(run_id, error_msg)
            except Exception as persist_err:
                plog.warning(PipelineStep.RUN_FAILED, f"Failed to persist run failure: {persist_err}", {})

            error_payload = {
                "event": "RunError",
                "content": error_msg,
                "run_id": run_id,
                "created_at": int(time.time()),
            }
            if session_id:
                error_payload["session_id"] = session_id
            yield f"data: {json.dumps(error_payload)}\n\n"

            # Cleanup logger
            cleanup_logger(run_id)

    return StreamingResponse(resume_animation_sse(), media_type="text/event-stream")


@agents_router.post("/{agent_id}/knowledge/load", status_code=status.HTTP_200_OK)
async def load_agent_knowledge(agent_id: AgentType):
    """
    Loads the knowledge base for a specific agent.

    Args:
        agent_id: The ID of the agent to load knowledge for.

    Returns:
        A success message if the knowledge base is loaded.
    """
    agent_knowledge: Optional[AgentKnowledge] = None

    if agent_id == AgentType.AGNO_ASSIST:
        agent_knowledge = get_agno_assist_knowledge()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent {agent_id} does not have a knowledge base.",
        )

    try:
        await agent_knowledge.aload(upsert=True)
    except Exception as e:
        logger.error(f"Error loading knowledge base for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load knowledge base for {agent_id}.",
        )

    return {"message": f"Knowledge base for {agent_id} loaded successfully."}
