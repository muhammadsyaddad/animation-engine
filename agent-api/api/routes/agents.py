from cmath import e
import os
from enum import Enum
from logging import getLogger
from typing import AsyncGenerator, List, Optional
import json
import time
from typing import AsyncGenerator

from pydantic_core.core_schema import is_instance_schema
from starlette.responses import Content

from agno.agent import Agent, AgentKnowledge
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.agno_assist import get_agno_assist_knowledge
from agents.selector import AgentType, get_agent, get_available_agents
from agents.tools.code_generation import generate_manim_code, CodeGenerationError
from agents.tools.preview_manim import generate_manim_preview_stream
from agents.tools.video_manim import render_manim_stream
from agents.tools.export_ffmpeg import export_merge_stream
from sqlalchemy.orm import Session
from api.settings import api_settings
from api.run_registry import create_run, set_state, RunState, complete_run, fail_run, cancel_run, get_run, list_runs
from db.session import get_db

from api.routes.auth import get_current_user_optional
from api.persistence.run_store import persist_run_created, persist_run_state, persist_run_completed, persist_run_failed, persist_artifact

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
        if body.animate_data is True:
            should_animate = True
        elif body.animate_data is False:
            should_animate = False
        else:
            try:
                from agents.tools.intent_detection import detect_animation_intent  # type: ignore
                intent = detect_animation_intent(body.message)
                should_animate = bool(getattr(intent, "animation_requested", False))
            except Exception:
                # Fallback heuristic if intent module unavailable
                text = (body.message or "")
                cues = ["class GenScene", "manim", "animasi", "animate", "animation", "video", "mp4", "gif"]
                lowered = text.lower()
                should_animate = any(c.lower() in lowered for c in cues)
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
            try:
                agent_label = getattr(agent_id, "value", str(agent_id))
                persist_run_created(run_id, db_user_id, session_id, agent_label, "STARTING", "Starting", {})
                persist_run_state(run_id, "STARTING", "Starting")
            except Exception:
                pass
            # Initial SSE event to signal animation pipeline activation (intent-based)
            try:
                from agents.tools.intent_detection import detect_animation_intent  # type: ignore
                _intent_info = detect_animation_intent(msg)
                _chart = getattr(_intent_info, "chart_type", "unknown")
                _conf = getattr(_intent_info, "confidence", 0.0)
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
                if raw_dataset_path and isinstance(raw_dataset_path, str):
                    try:
                        import os
                        import pandas as pd
                        from api.services.data_modules import preprocess_dataset  # type: ignore
                        # Map /static path to filesystem if needed
                        if raw_dataset_path.startswith("/static/"):
                            artifacts_root = os.path.join(os.getcwd(), "artifacts")
                            rel_inside = raw_dataset_path[len("/static/"):].lstrip("/")
                            fs_candidate = os.path.join(artifacts_root, rel_inside)
                            if os.path.exists(fs_candidate):
                                raw_dataset_path = fs_candidate
                        if os.path.exists(raw_dataset_path):
                            # Preview for structural detection
                            df_preview = pd.read_csv(raw_dataset_path, nrows=100)
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
                            # If dataset is wide, perform full melt on entire file to a new artifacts CSV
                            if is_wide:
                                try:
                                    full_df = pd.read_csv(raw_dataset_path)
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
                    except Exception as _pe:
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
                try:
                    import os, re, csv
                    from agents.tools.specs import infer_spec_from_prompt  # type: ignore
                    from agents.tools.danim_templates import (
                        generate_bubble_code,
                        generate_distribution_code,
                        generate_bar_race_code,
                        generate_line_evolution_code,
                        generate_bento_grid_code,
                    )  # type: ignore
                    spec = infer_spec_from_prompt(msg)
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
                            # Auto-assign chart_type to distribution if wide melt applied and chart_type unknown
                            if dataset_melt_applied and (getattr(spec, "chart_type", None) in (None, "", "unknown")):
                                spec.chart_type = "distribution"
                                auto_ct_payload = {
                                    "event": "RunContent",
                                    "content": "Auto-selected chart_type=distribution for wide year-format dataset.",
                                    "created_at": int(time.time()),
                                    "run_id": run_id,
                                }
                                if session_id:
                                    auto_ct_payload["session_id"] = session_id
                                yield f"data: {json.dumps(auto_ct_payload)}\n\n"
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
                            if ct in ("bubble", "distribution", "bar_race", "line_evolution", "bento_grid"):
                                spec.chart_type = ct
                                explicit_chart = True
                                requested_ct = ct
                    except Exception:
                        pass
                    # Apply creation_mode override if provided (bubble template controller)
                    try:
                        if getattr(body, "creation_mode", None) is not None:
                            spec.creation_mode = int(body.creation_mode)
                    except Exception:
                        pass
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
                    else:
                        if explicit_chart and spec.chart_type in ("bubble", "distribution", "bar_race", "line_evolution", "bento_grid") and (not dataset_path or not os.path.exists(str(dataset_path))):
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
                    template_error = f"Spec inference unavailable: {e}"
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
                    try:
                        code = generate_manim_code(
                            prompt=msg,
                            engine=(body.code_engine or "anthropic"),
                            model=(body.code_model or None),
                            temperature=0.2,
                            max_tokens=1200,
                            extra_rules=(body.code_system_prompt or None),
                        )
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
                        err = {
                            "event": "RunError",
                            "content": str(e),
                            "created_at": int(time.time()),
                        }
                        if session_id:
                            err["session_id"] = session_id
                        err["run_id"] = run_id
                        fail_run(run_id, str(e))
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
                err_payload = {
                    "event": "RunError",
                    "content": "No code was generated for preview.",
                    "created_at": int(time.time()),
                    "run_id": run_id,
                }
                if session_id:
                    err_payload["session_id"] = session_id
                fail_run(run_id, err_payload["content"])
                yield f"data: {json.dumps(err_payload)}\n\n"
                yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                return

            # Pre-preview: syntax validation and auto-fix loop (Point 1)
            max_fix_attempts = 2
            fix_attempt = 0
            while fix_attempt <= max_fix_attempts:
                ok, v_err = _quick_validate(code)
                if ok:
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
                if fix_attempt == max_fix_attempts:
                    err_payload = {
                        "event": "RunError",
                        "content": f"Code validation failed: {v_err}",
                        "created_at": int(time.time()),
                        "run_id": run_id,
                    }
                    if session_id:
                        err_payload["session_id"] = session_id
                    fail_run(run_id, err_payload["content"])
                    yield f"data: {json.dumps(err_payload)}\n\n"
                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                    return
                # Try auto-fix
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
                except CodeGenerationError:
                    # Keep code as-is; next loop may still pass if minor
                    pass
                fix_attempt += 1

            # 2) Preview frames with runtime auto-fix loop (Point 2)
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
                    break

                # We had a preview error (classified)
                if (runtime_attempt == max_runtime_fix_attempts) or (not allow_llm_fix):
                    # Give up early if classification forbids LLM fix OR attempts exhausted
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
                    complete_run(run_id, "Render completed.")
                    try:
                        persist_run_completed(run_id, "Render completed.")
                    except Exception:
                        pass
                payload["run_id"] = run_id
                if payload["event"] == "RunError":
                    fail_run(run_id, payload.get("content", "Render error"))
                    try:
                        persist_run_failed(run_id, payload.get("content", "Render error"))
                    except Exception:
                        pass
                    yield f"data: {json.dumps(payload)}\n\n"
                    yield f"data: {json.dumps({'event': 'RunCompleted', 'content': '', 'created_at': int(time.time()), 'run_id': run_id})}\n\n"
                    return
                yield f"data: {json.dumps(payload)}\n\n"

            # 4) Done
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
