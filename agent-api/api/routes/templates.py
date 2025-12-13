"""
Template registry and routes.

Provides:
  - GET /v1/templates
      * List all available animation templates with their axis requirements
  - GET /v1/templates/{template_id}
      * Get details for a specific template

Each template defines:
  - template_id: unique identifier (e.g., "bar_race")
  - display_name: human-readable name (e.g., "Bar Chart Race")
  - description: what the template does
  - preview_url: optional preview image/gif
  - preview_fallback_url: SVG placeholder fallback
  - axes: list of required/optional column mappings
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Preview URL Helper
# ─────────────────────────────────────────────────────────────────────────────

ARTIFACTS_DIR = Path(os.getcwd()) / "artifacts"
PREVIEWS_DIR = ARTIFACTS_DIR / "previews"


def get_preview_urls(template_id: str) -> tuple[Optional[str], Optional[str]]:
    """
    Get preview URLs for a template, checking which files actually exist.

    Returns:
        Tuple of (preview_url, fallback_url)
        - preview_url: Path to GIF if it exists, else None
        - fallback_url: Path to SVG placeholder if it exists, else None
    """
    gif_path = PREVIEWS_DIR / f"{template_id}.gif"
    svg_path = PREVIEWS_DIR / f"{template_id}_placeholder.svg"

    preview_url = f"/static/previews/{template_id}.gif" if gif_path.exists() else None
    fallback_url = f"/static/previews/{template_id}_placeholder.svg" if svg_path.exists() else None

    return preview_url, fallback_url


# ─────────────────────────────────────────────────────────────────────────────
# Schema Definitions
# ─────────────────────────────────────────────────────────────────────────────

class AxisRequirement(BaseModel):
    """Defines a single axis/column binding requirement for a template."""

    name: str = Field(..., description="Internal name for this axis (e.g., 'entity_column')")
    label: str = Field(..., description="Human-readable question (e.g., 'Who/what is racing?')")
    required: bool = Field(True, description="Whether this axis must be provided")
    data_type: Literal["numeric", "categorical", "time", "any"] = Field(
        ..., description="Expected data type for this axis"
    )
    description: Optional[str] = Field(
        None, description="Additional help text explaining this axis"
    )


class TemplateSchema(BaseModel):
    """Full schema for an animation template."""

    template_id: str = Field(..., description="Unique identifier for the template")
    display_name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="What this template creates")
    preview_url: Optional[str] = Field(None, description="URL to preview image/gif")
    preview_fallback_url: Optional[str] = Field(None, description="URL to SVG placeholder fallback")
    category: str = Field("general", description="Template category for grouping")
    axes: List[AxisRequirement] = Field(..., description="Required and optional axis bindings")


class TemplateListResponse(BaseModel):
    """Response for listing all templates."""

    templates: List[TemplateSchema]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Template Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Define templates with static preview paths
# Actual URL resolution happens at request time to check file existence
_TEMPLATE_DEFINITIONS: List[dict] = [
    dict(
        template_id="bar_race",
        display_name="Bar Chart Race",
        description="Animated ranking bars racing over time. Perfect for showing how rankings change over years.",
        category="ranking",
        axes=[
            AxisRequirement(
                name="entity_column",
                label="Who/what is racing?",
                required=True,
                data_type="categorical",
                description="The items that will be represented as bars (e.g., Country, Company, Product)"
            ),
            AxisRequirement(
                name="value_column",
                label="What value determines bar length?",
                required=True,
                data_type="numeric",
                description="The numeric value that determines how long each bar is (e.g., GDP, Revenue, Population)"
            ),
            AxisRequirement(
                name="time_column",
                label="Over what time period?",
                required=True,
                data_type="time",
                description="The time dimension to animate over (e.g., Year, Month, Date)"
            ),
            AxisRequirement(
                name="group_column",
                label="Color bars by group?",
                required=False,
                data_type="categorical",
                description="Optional grouping for color coding (e.g., Region, Category)"
            ),
        ]
    ),

    dict(
        template_id="bubble",
        display_name="Bubble Chart",
        description="Multi-dimensional scatter plot with size encoding. Great for showing relationships between multiple variables.",
        category="correlation",
        axes=[
            AxisRequirement(
                name="x_column",
                label="What column for X axis?",
                required=True,
                data_type="numeric",
                description="The value for horizontal position (e.g., GDP per capita)"
            ),
            AxisRequirement(
                name="y_column",
                label="What column for Y axis?",
                required=True,
                data_type="numeric",
                description="The value for vertical position (e.g., Life Expectancy)"
            ),
            AxisRequirement(
                name="size_column",
                label="What column for bubble size?",
                required=True,
                data_type="numeric",
                description="The value that determines bubble size (e.g., Population)"
            ),
            AxisRequirement(
                name="time_column",
                label="What column for animation time?",
                required=True,
                data_type="time",
                description="The time dimension to animate over (e.g., Year)"
            ),
            AxisRequirement(
                name="entity_column",
                label="What identifies each bubble?",
                required=True,
                data_type="categorical",
                description="Unique identifier for each bubble (e.g., Country name)"
            ),
            AxisRequirement(
                name="group_column",
                label="Group/color bubbles by?",
                required=False,
                data_type="categorical",
                description="Optional grouping for color coding (e.g., Continent, Region)"
            ),
        ]
    ),

    dict(
        template_id="line_evolution",
        display_name="Line Evolution",
        description="Animated line chart showing trends over time. Perfect for tracking a single value's journey.",
        category="trend",
        axes=[
            AxisRequirement(
                name="value_column",
                label="What value to track?",
                required=True,
                data_type="numeric",
                description="The numeric value to plot (e.g., Stock Price, Temperature)"
            ),
            AxisRequirement(
                name="time_column",
                label="Over what time?",
                required=True,
                data_type="time",
                description="The time dimension for the X axis (e.g., Date, Year)"
            ),
            AxisRequirement(
                name="entity_column",
                label="Compare multiple lines?",
                required=False,
                data_type="categorical",
                description="Optional: Compare multiple entities (e.g., different companies)"
            ),
            AxisRequirement(
                name="group_column",
                label="Color lines by group?",
                required=False,
                data_type="categorical",
                description="Optional grouping for color coding"
            ),
        ]
    ),

    dict(
        template_id="distribution",
        display_name="Distribution / Histogram",
        description="Animated histogram showing how values are distributed, changing over time.",
        category="distribution",
        axes=[
            AxisRequirement(
                name="value_column",
                label="What values to distribute?",
                required=True,
                data_type="numeric",
                description="The numeric values to create histogram from (e.g., Income, Score)"
            ),
            AxisRequirement(
                name="time_column",
                label="Animate over what time?",
                required=True,
                data_type="time",
                description="The time dimension to animate the distribution (e.g., Year)"
            ),
            AxisRequirement(
                name="entity_column",
                label="Label for each data point?",
                required=False,
                data_type="categorical",
                description="Optional identifier for individual data points"
            ),
        ]
    ),

    dict(
        template_id="bento_grid",
        display_name="Bento Grid / KPI Dashboard",
        description="Animated dashboard grid showing multiple KPI metrics. Perfect for summary statistics.",
        category="dashboard",
        axes=[
            AxisRequirement(
                name="label_column",
                label="What is each KPI called?",
                required=True,
                data_type="categorical",
                description="Names for each metric (e.g., 'Revenue', 'Users', 'Growth')"
            ),
            AxisRequirement(
                name="value_column",
                label="What are the values?",
                required=True,
                data_type="numeric",
                description="The numeric values for each KPI"
            ),
            AxisRequirement(
                name="change_column",
                label="Show percentage change?",
                required=False,
                data_type="numeric",
                description="Optional: percentage change to display (e.g., +15%, -3%)"
            ),
        ]
    ),

    dict(
        template_id="count_bar",
        display_name="Count Bar Chart",
        description="Horizontal bar chart showing counts of categorical values. Great for frequency analysis.",
        category="categorical",
        axes=[
            AxisRequirement(
                name="category_column",
                label="What to count?",
                required=True,
                data_type="categorical",
                description="The categorical column to count occurrences of (e.g., Country, Product Type)"
            ),
        ]
    ),

    dict(
        template_id="single_numeric",
        display_name="Simple Bar Chart",
        description="Horizontal bar chart showing one value per category. Clean and straightforward.",
        category="comparison",
        axes=[
            AxisRequirement(
                name="category_column",
                label="What are the items?",
                required=True,
                data_type="categorical",
                description="The categories/items to show (e.g., Country, Product)"
            ),
            AxisRequirement(
                name="value_column",
                label="What is the value?",
                required=True,
                data_type="numeric",
                description="The numeric value for each item (e.g., Sales, Population)"
            ),
        ]
    ),
]


def _build_template_with_preview(defn: dict) -> TemplateSchema:
    """Build a TemplateSchema with resolved preview URLs."""
    template_id = defn["template_id"]
    preview_url, fallback_url = get_preview_urls(template_id)

    return TemplateSchema(
        template_id=template_id,
        display_name=defn["display_name"],
        description=defn["description"],
        preview_url=preview_url or f"/static/previews/{template_id}.gif",  # Expected path even if not yet created
        preview_fallback_url=fallback_url,
        category=defn["category"],
        axes=defn["axes"],
    )


def get_templates() -> List[TemplateSchema]:
    """Get all templates with resolved preview URLs."""
    return [_build_template_with_preview(defn) for defn in _TEMPLATE_DEFINITIONS]


# Legacy: Build static lookup for helper functions (preview URLs won't update dynamically here)
TEMPLATES: List[TemplateSchema] = get_templates()
TEMPLATES_BY_ID: dict[str, TemplateSchema] = {t.template_id: t for t in TEMPLATES}


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def list_templates() -> TemplateListResponse:
    """
    List all available animation templates.

    Returns templates with their display names, descriptions, and axis requirements.
    Use this to show a template gallery in the UI.

    Preview URLs are resolved at request time to check for actual file existence.
    """
    # Rebuild templates to check current preview file existence
    templates = get_templates()
    return TemplateListResponse(
        templates=templates,
        total=len(templates)
    )


@router.get("/{template_id}", response_model=TemplateSchema)
def get_template(template_id: str) -> TemplateSchema:
    """
    Get details for a specific template.

    Returns the template's axis requirements, which define what columns
    the user needs to map from their dataset.
    """
    # Find the template definition
    defn = next((d for d in _TEMPLATE_DEFINITIONS if d["template_id"] == template_id), None)
    if not defn:
        available = [d["template_id"] for d in _TEMPLATE_DEFINITIONS]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found. Available templates: {available}"
        )
    # Build with current preview URL status
    return _build_template_with_preview(defn)


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions (for use by other modules)
# ─────────────────────────────────────────────────────────────────────────────

def get_template_by_id(template_id: str) -> Optional[TemplateSchema]:
    """Get a template by ID, or None if not found."""
    return TEMPLATES_BY_ID.get(template_id)


def get_required_axes(template_id: str) -> List[str]:
    """Get list of required axis names for a template."""
    template = TEMPLATES_BY_ID.get(template_id)
    if not template:
        return []
    return [axis.name for axis in template.axes if axis.required]


def get_all_axes(template_id: str) -> List[str]:
    """Get list of all axis names (required + optional) for a template."""
    template = TEMPLATES_BY_ID.get(template_id)
    if not template:
        return []
    return [axis.name for axis in template.axes]


def validate_column_mappings(template_id: str, mappings: dict[str, Optional[str]]) -> List[str]:
    """
    Validate that all required axes are provided in the mappings.

    Returns list of missing required axes (empty list if valid).
    """
    template = TEMPLATES_BY_ID.get(template_id)
    if not template:
        return [f"Unknown template: {template_id}"]

    missing = []
    for axis in template.axes:
        if axis.required:
            value = mappings.get(axis.name)
            if not value:
                missing.append(axis.name)

    return missing
