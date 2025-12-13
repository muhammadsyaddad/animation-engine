"""
Animation generation routes with explicit column mappings.

Provides:
  - POST /v1/animations/generate
      * Generate animation with user-specified template and column mappings
      * No auto-inference - user explicitly chooses template and maps columns

This is the new "user-controlled" flow:
  1. User uploads data -> gets column_analysis
  2. User picks template from GET /v1/templates
  3. User maps their columns to template axes
  4. User calls this endpoint with explicit mappings
  5. Animation is generated with no guessing
"""

from __future__ import annotations

import json
import os
import time
import uuid
from logging import getLogger
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from api.routes.auth import get_current_user_optional
from api.routes.templates import (
    get_template_by_id,
    validate_column_mappings,
    TEMPLATES_BY_ID,
)
from api.settings import api_settings
from api.run_registry import (
    create_run,
    set_state,
    RunState,
    complete_run,
    fail_run,
)
from api.persistence.run_store import (
    persist_run_created,
    persist_run_state,
    persist_run_completed,
    persist_run_failed,
    persist_artifact,
)

logger = getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────


class ColumnMappings(BaseModel):
    """User-specified column mappings for a template."""

    # All possible axis mappings - template defines which are required
    entity_column: Optional[str] = Field(None, description="Column for entity/item identifier")
    value_column: Optional[str] = Field(None, description="Column for numeric values")
    time_column: Optional[str] = Field(None, description="Column for time dimension")
    group_column: Optional[str] = Field(None, description="Column for grouping/coloring")
    x_column: Optional[str] = Field(None, description="Column for X axis (bubble)")
    y_column: Optional[str] = Field(None, description="Column for Y axis (bubble)")
    size_column: Optional[str] = Field(None, description="Column for size (bubble)")
    label_column: Optional[str] = Field(None, description="Column for labels (bento)")
    category_column: Optional[str] = Field(None, description="Column for categories")
    change_column: Optional[str] = Field(None, description="Column for change values (bento)")

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}


class GenerateRequest(BaseModel):
    """Request model for generating an animation with explicit mappings."""

    dataset_id: str = Field(..., description="ID of the uploaded dataset")
    template_id: str = Field(..., description="Template to use (e.g., 'bar_race', 'bubble')")
    column_mappings: ColumnMappings = Field(..., description="User-specified column to axis mappings")

    # Optional settings
    title: Optional[str] = Field(None, description="Custom title for the animation")
    top_n: Optional[int] = Field(None, description="Show top N items (for bar charts)")
    aspect_ratio: Optional[str] = Field("16:9", description="Video aspect ratio: '16:9', '9:16', '1:1'")
    quality: Optional[str] = Field("medium", description="Render quality: 'low', 'medium', 'high'")

    # Session tracking
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class GenerateResponse(BaseModel):
    """Response model for animation generation."""

    run_id: str = Field(..., description="Unique ID for this generation run")
    status: str = Field(..., description="Current status: 'processing', 'completed', 'failed'")
    message: str = Field(..., description="Status message")


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/animations", tags=["animations"])


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_animation(
    body: GenerateRequest,
    current_user=Depends(get_current_user_optional),
):
    """
    Generate an animation with explicit template and column mappings.

    This endpoint does NOT auto-infer anything. The user must:
    1. Specify which template to use
    2. Map their dataset columns to the template's required axes

    Returns a run_id that can be used to track progress via SSE.
    """
    # Validate template exists
    template = get_template_by_id(body.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template: '{body.template_id}'. Available: {list(TEMPLATES_BY_ID.keys())}",
        )

    # Validate required column mappings are provided
    mappings_dict = body.column_mappings.to_dict()
    missing = validate_column_mappings(body.template_id, mappings_dict)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required column mappings for template '{body.template_id}': {missing}",
        )

    # Validate dataset exists
    from api.routes.datasets import _DATASET_REGISTRY, _REGISTRY_LOCK

    with _REGISTRY_LOCK:
        dataset_meta = _DATASET_REGISTRY.get(body.dataset_id)

    if not dataset_meta:
        # Try to load from database
        try:
            from api.persistence.dataset_store import get_dataset_by_id

            dataset_row = get_dataset_by_id(body.dataset_id)
            if dataset_row:
                csv_path = dataset_row.storage_path
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Dataset '{body.dataset_id}' not found",
                )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{body.dataset_id}' not found",
            )
    else:
        csv_path = dataset_meta.unified_rel_url or dataset_meta.unified_path

    if not csv_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset has no associated CSV file",
        )

    # Return SSE stream for progress
    return StreamingResponse(
        animation_generate_stream(
            template_id=body.template_id,
            csv_path=csv_path,
            column_mappings=mappings_dict,
            title=body.title,
            top_n=body.top_n,
            aspect_ratio=body.aspect_ratio or "16:9",
            quality=body.quality or "medium",
            session_id=body.session_id,
            user_id=(current_user.id if current_user else None),
        ),
        media_type="text/event-stream",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SSE Stream Generator
# ─────────────────────────────────────────────────────────────────────────────


async def animation_generate_stream(
    template_id: str,
    csv_path: str,
    column_mappings: Dict[str, str],
    title: Optional[str],
    top_n: Optional[int],
    aspect_ratio: str,
    quality: str,
    session_id: Optional[str],
    user_id: Optional[str],
):
    """
    SSE stream generator for animation generation.

    Yields JSON events:
    - RunContent: progress updates
    - RunError: error messages
    - RunCompleted: final result with video URL
    """
    # Create run for tracking
    registry_user_id = user_id or "local"
    run = create_run(user_id=registry_user_id, session_id=session_id, message=f"generate:{template_id}")
    run_id = run.run_id

    def emit_event(event_type: str, content: str, **extra) -> str:
        payload = {
            "event": event_type,
            "content": content,
            "created_at": int(time.time()),
            "run_id": run_id,
        }
        if session_id:
            payload["session_id"] = session_id
        payload.update(extra)
        return f"data: {json.dumps(payload)}\n\n"

    try:
        # Initial status
        set_state(run_id, RunState.STARTING, "Starting animation generation")
        try:
            persist_run_created(run_id, user_id, session_id, "animation_generate", "STARTING", "Starting", {
                "template_id": template_id,
                "column_mappings": column_mappings,
            })
        except Exception:
            pass

        yield emit_event("RunContent", f"🎬 Starting animation generation with template: {template_id}")

        # Resolve CSV path
        from api.services.data_modules import resolve_csv_path

        resolved_path = resolve_csv_path(csv_path)
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Dataset file not found: {csv_path}")

        yield emit_event("RunContent", f"📁 Dataset loaded: {os.path.basename(resolved_path)}")

        # Build spec from column mappings
        set_state(run_id, RunState.GENERATING, "Building chart specification")
        yield emit_event("RunContent", "🔧 Building chart specification from your column mappings...")

        spec = build_spec_from_mappings(template_id, column_mappings, title=title)

        # Generate code using template
        set_state(run_id, RunState.GENERATING, "Generating Manim code")
        yield emit_event("RunContent", f"⚙️ Generating animation code for {template_id}...")

        code = generate_code_for_template(
            template_id=template_id,
            spec=spec,
            csv_path=resolved_path,
            top_n=top_n,
        )

        if not code:
            raise ValueError(f"Failed to generate code for template: {template_id}")

        yield emit_event("RunContent", "✅ Animation code generated successfully")

        # Render the animation
        set_state(run_id, RunState.RENDERING, "Rendering video")
        yield emit_event("RunContent", "🎥 Rendering animation (this may take a moment)...")

        from agents.tools.video_manim import render_manim_stream

        video_url = None
        for event in render_manim_stream(
            code=code,
            quality=quality,
            aspect_ratio=aspect_ratio,
            user_id=registry_user_id,
        ):
            event_type = event.get("event", "RunContent")
            content = event.get("content", "")

            if "videos" in event:
                video_url = event["videos"][0] if event["videos"] else None
                yield emit_event(event_type, content, videos=event["videos"])

                # Persist artifact
                if video_url:
                    try:
                        persist_artifact(run_id, "video", video_url)
                    except Exception:
                        pass
            elif event_type == "RunError":
                yield emit_event("RunError", content)
            else:
                yield emit_event("RunContent", content)

        # Complete
        if video_url:
            complete_run(run_id, "Animation completed successfully")
            try:
                persist_run_completed(run_id, "Animation completed successfully")
            except Exception:
                pass

            yield emit_event(
                "RunCompleted",
                "🎉 Animation generated successfully!",
                videos=[video_url],
            )
        else:
            raise ValueError("Rendering completed but no video was produced")

    except FileNotFoundError as e:
        error_msg = f"Dataset not found: {e}"
        fail_run(run_id, error_msg)
        try:
            persist_run_failed(run_id, error_msg)
        except Exception:
            pass
        yield emit_event("RunError", error_msg)

    except Exception as e:
        error_msg = f"Animation generation failed: {str(e)}"
        logger.exception(error_msg)
        fail_run(run_id, error_msg)
        try:
            persist_run_failed(run_id, error_msg)
        except Exception:
            pass
        yield emit_event("RunError", error_msg)


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


def build_spec_from_mappings(
    template_id: str,
    column_mappings: Dict[str, str],
    title: Optional[str] = None,
) -> object:
    """
    Build a ChartSpec object from user-provided column mappings.

    This translates the user's explicit mappings into the spec format
    expected by the template generators.
    """
    try:
        from agents.tools.specs import ChartSpec, DataBinding
    except ImportError:
        # Fallback minimal spec
        from dataclasses import dataclass

        @dataclass
        class DataBinding:
            x_col: Optional[str] = None
            y_col: Optional[str] = None
            r_col: Optional[str] = None
            value_col: Optional[str] = None
            time_col: Optional[str] = None
            group_col: Optional[str] = None
            entity_col: Optional[str] = None
            label_col: Optional[str] = None
            category_col: Optional[str] = None

        @dataclass
        class ChartSpec:
            chart_type: str = "bubble"
            data_binding: DataBinding = None
            title: Optional[str] = None

    # Map user's column names to DataBinding fields
    binding = DataBinding(
        x_col=column_mappings.get("x_column"),
        y_col=column_mappings.get("y_column"),
        r_col=column_mappings.get("size_column"),  # size_column -> r_col
        value_col=column_mappings.get("value_column"),
        time_col=column_mappings.get("time_column"),
        group_col=column_mappings.get("group_column"),
        entity_col=column_mappings.get("entity_column"),
        label_col=column_mappings.get("label_column"),
        category_col=column_mappings.get("category_column"),
    )

    spec = ChartSpec(
        chart_type=template_id,
        data_binding=binding,
    )

    # Add title if provided
    if title and hasattr(spec, "title"):
        spec.title = title

    return spec


def generate_code_for_template(
    template_id: str,
    spec: object,
    csv_path: str,
    top_n: Optional[int] = None,
) -> str:
    """
    Generate Manim code for the specified template.

    Routes to the appropriate template generator based on template_id.
    """
    from agents.tools.danim_templates import (
        generate_bubble_code,
        generate_distribution_code,
        generate_bar_race_code,
        generate_line_evolution_code,
        generate_bento_grid_code,
        generate_count_bar_code,
        generate_single_numeric_code,
    )

    # Get column mappings from spec for templates that need them
    binding = getattr(spec, "data_binding", None)
    category_col = getattr(binding, "category_col", None) if binding else None
    value_col = getattr(binding, "value_col", None) if binding else None

    # Route to appropriate generator
    if template_id == "bubble":
        return generate_bubble_code(spec, csv_path)

    elif template_id == "distribution":
        return generate_distribution_code(spec, csv_path)

    elif template_id == "bar_race":
        return generate_bar_race_code(spec, csv_path)

    elif template_id == "line_evolution":
        return generate_line_evolution_code(spec, csv_path)

    elif template_id == "bento_grid":
        return generate_bento_grid_code(spec, csv_path)

    elif template_id == "count_bar":
        return generate_count_bar_code(
            spec,
            csv_path,
            count_column=category_col,
            top_n=top_n or 15,
        )

    elif template_id == "single_numeric":
        return generate_single_numeric_code(
            spec,
            csv_path,
            category_column=category_col,
            value_column=value_col,
            top_n=top_n or 15,
        )

    else:
        raise ValueError(f"Unknown template_id: {template_id}")
