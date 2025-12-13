"""
Admin API routes for system management tasks.

Provides:
  - POST /v1/admin/previews/regenerate
      * Trigger regeneration of preview placeholders and optionally GIFs
  - GET /v1/admin/previews/status
      * Check status of preview files
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ─────────────────────────────────────────────────────────────────────────────
# Schema Definitions
# ─────────────────────────────────────────────────────────────────────────────

class PreviewFileStatus(BaseModel):
    """Status of a single preview file."""
    template_id: str
    gif_exists: bool
    gif_path: Optional[str] = None
    placeholder_exists: bool
    placeholder_path: Optional[str] = None


class PreviewStatusResponse(BaseModel):
    """Response for preview status check."""
    previews_dir: str
    templates: List[PreviewFileStatus]
    total_gifs: int
    total_placeholders: int
    all_placeholders_exist: bool
    all_gifs_exist: bool


class RegenerateRequest(BaseModel):
    """Request to regenerate previews."""
    regenerate_placeholders: bool = Field(
        True, description="Regenerate SVG placeholder images"
    )
    regenerate_gifs: bool = Field(
        False, description="Regenerate animated GIF previews (slower)"
    )
    templates: Optional[List[str]] = Field(
        None, description="Specific templates to regenerate (None = all)"
    )
    async_gifs: bool = Field(
        True, description="Generate GIFs in background thread"
    )


class RegenerateResponse(BaseModel):
    """Response from regenerate request."""
    status: Literal["started", "completed", "partial"]
    message: str
    placeholders_generated: int = 0
    gifs_started: bool = False
    errors: List[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_IDS = [
    "bar_race",
    "bubble",
    "line_evolution",
    "distribution",
    "bento_grid",
    "count_bar",
    "single_numeric",
]


def get_previews_dir() -> Path:
    """Get the previews directory."""
    artifacts_dir = Path(os.getcwd()) / "artifacts"
    previews_dir = artifacts_dir / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    return previews_dir


def check_preview_status() -> PreviewStatusResponse:
    """Check the status of all preview files."""
    previews_dir = get_previews_dir()

    templates = []
    total_gifs = 0
    total_placeholders = 0

    for template_id in TEMPLATE_IDS:
        gif_path = previews_dir / f"{template_id}.gif"
        placeholder_path = previews_dir / f"{template_id}_placeholder.svg"

        gif_exists = gif_path.exists()
        placeholder_exists = placeholder_path.exists()

        if gif_exists:
            total_gifs += 1
        if placeholder_exists:
            total_placeholders += 1

        templates.append(PreviewFileStatus(
            template_id=template_id,
            gif_exists=gif_exists,
            gif_path=str(gif_path) if gif_exists else None,
            placeholder_exists=placeholder_exists,
            placeholder_path=str(placeholder_path) if placeholder_exists else None,
        ))

    return PreviewStatusResponse(
        previews_dir=str(previews_dir),
        templates=templates,
        total_gifs=total_gifs,
        total_placeholders=total_placeholders,
        all_placeholders_exist=total_placeholders == len(TEMPLATE_IDS),
        all_gifs_exist=total_gifs == len(TEMPLATE_IDS),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/previews/status", response_model=PreviewStatusResponse)
def get_preview_status() -> PreviewStatusResponse:
    """
    Check the status of preview files.

    Returns information about which preview files (GIFs and placeholders)
    exist for each template.
    """
    return check_preview_status()


@router.post("/previews/regenerate", response_model=RegenerateResponse)
def regenerate_previews(request: RegenerateRequest) -> RegenerateResponse:
    """
    Regenerate preview images.

    - Placeholders (SVG): Generated synchronously, fast
    - GIFs: Generated in background thread by default (slow, requires Manim)

    Set `async_gifs=false` to wait for GIF generation to complete
    (not recommended for production).
    """
    errors: List[str] = []
    placeholders_generated = 0
    gifs_started = False

    # Validate template IDs if provided
    if request.templates:
        invalid = [t for t in request.templates if t not in TEMPLATE_IDS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template IDs: {invalid}. Valid IDs: {TEMPLATE_IDS}"
            )

    templates_to_generate = request.templates or TEMPLATE_IDS

    # Generate placeholders
    if request.regenerate_placeholders:
        try:
            from scripts.previews.create_placeholders import (
                SVG_TEMPLATES,
                get_previews_dir,
            )

            previews_dir = get_previews_dir()

            for template_id in templates_to_generate:
                if template_id in SVG_TEMPLATES:
                    svg_content = SVG_TEMPLATES[template_id]
                    output_path = previews_dir / f"{template_id}_placeholder.svg"
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(svg_content.strip())
                    placeholders_generated += 1
                    logger.info(f"Generated placeholder: {output_path}")
                else:
                    errors.append(f"No SVG template for: {template_id}")

        except Exception as e:
            logger.error(f"Failed to generate placeholders: {e}")
            errors.append(f"Placeholder generation error: {str(e)}")

    # Generate GIFs
    if request.regenerate_gifs:
        def generate_gifs():
            try:
                from scripts.previews.generate_previews import (
                    generate_preview,
                    TEMPLATE_CONFIGS,
                )
                from scripts.previews.sample_data import create_all_sample_data

                sample_data_paths = create_all_sample_data()

                for template_id in templates_to_generate:
                    if template_id in TEMPLATE_CONFIGS:
                        try:
                            success = generate_preview(template_id, sample_data_paths)
                            if success:
                                logger.info(f"Generated GIF: {template_id}")
                            else:
                                logger.warning(f"Failed to generate GIF: {template_id}")
                        except Exception as e:
                            logger.error(f"Error generating GIF for {template_id}: {e}")
                    else:
                        logger.warning(f"No template config for: {template_id}")

            except Exception as e:
                logger.error(f"GIF generation failed: {e}")

        if request.async_gifs:
            # Run in background thread
            thread = threading.Thread(target=generate_gifs, daemon=True)
            thread.start()
            gifs_started = True
            logger.info("Started GIF generation in background thread")
        else:
            # Run synchronously (blocking)
            generate_gifs()
            gifs_started = True

    # Determine overall status
    if errors:
        status_val = "partial"
        message = f"Completed with {len(errors)} error(s)"
    elif request.regenerate_gifs and request.async_gifs:
        status_val = "started"
        message = "Placeholders generated. GIF generation started in background."
    else:
        status_val = "completed"
        message = "Preview regeneration completed successfully"

    return RegenerateResponse(
        status=status_val,
        message=message,
        placeholders_generated=placeholders_generated,
        gifs_started=gifs_started,
        errors=errors,
    )


@router.delete("/previews/gifs")
def delete_gif_previews(templates: Optional[List[str]] = None) -> dict:
    """
    Delete GIF preview files.

    Useful for forcing regeneration or cleaning up disk space.
    Does not delete placeholder SVGs.
    """
    previews_dir = get_previews_dir()
    templates_to_delete = templates or TEMPLATE_IDS

    # Validate template IDs if provided
    if templates:
        invalid = [t for t in templates if t not in TEMPLATE_IDS]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template IDs: {invalid}. Valid IDs: {TEMPLATE_IDS}"
            )

    deleted = []
    not_found = []

    for template_id in templates_to_delete:
        gif_path = previews_dir / f"{template_id}.gif"
        if gif_path.exists():
            gif_path.unlink()
            deleted.append(template_id)
        else:
            not_found.append(template_id)

    return {
        "deleted": deleted,
        "not_found": not_found,
        "message": f"Deleted {len(deleted)} GIF file(s)"
    }
