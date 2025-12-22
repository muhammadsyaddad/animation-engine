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

Column Mapping Validation:
  - validate_column_mappings_with_schema() validates user-provided column mappings
    against both template requirements AND actual dataset schema
  - Ensures numeric axes get numeric columns, categorical axes get categorical columns, etc.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional, Dict, Any, Tuple

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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

    return _build_template_with_preview(defn)


class ColumnSuggestionsRequest(BaseModel):
    """Request for smart column suggestions."""
    template_id: str = Field(..., description="Template ID to get suggestions for")
    numeric_columns: List[str] = Field(default_factory=list, description="List of numeric column names")
    categorical_columns: List[str] = Field(default_factory=list, description="List of categorical column names")
    time_column: Optional[str] = Field(None, description="Detected time column (if any)")


class ColumnSuggestionsResponse(BaseModel):
    """Response with smart column suggestions."""
    template_id: str
    suggestions: Dict[str, str] = Field(..., description="Mapping of axis name to suggested column")
    template_axes: List[AxisRequirement] = Field(..., description="Template axis requirements for reference")


@router.post("/suggestions", response_model=ColumnSuggestionsResponse)
def get_column_suggestions(body: ColumnSuggestionsRequest) -> ColumnSuggestionsResponse:
    """
    Get smart column suggestions for a template based on dataset schema.

    This endpoint analyzes the provided column metadata and suggests
    appropriate columns for each axis of the selected template.

    Use this to pre-populate the column mapping modal in the UI.
    """
    template = TEMPLATES_BY_ID.get(body.template_id)
    if not template:
        available = list(TEMPLATES_BY_ID.keys())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{body.template_id}' not found. Available templates: {available}"
        )

    suggestions = get_smart_column_suggestions(
        template_id=body.template_id,
        numeric_columns=body.numeric_columns,
        categorical_columns=body.categorical_columns,
        time_column=body.time_column,
    )

    return ColumnSuggestionsResponse(
        template_id=body.template_id,
        suggestions=suggestions,
        template_axes=template.axes,
    )


class ValidateMappingsRequest(BaseModel):
    """Request for validating column mappings."""
    template_id: str = Field(..., description="Template ID to validate against")
    mappings: Dict[str, Optional[str]] = Field(..., description="Column mappings to validate")
    numeric_columns: List[str] = Field(default_factory=list, description="List of numeric column names")
    categorical_columns: List[str] = Field(default_factory=list, description="List of categorical column names")
    time_column: Optional[str] = Field(None, description="Detected time column (if any)")
    all_columns: List[str] = Field(default_factory=list, description="List of all column names")
    is_wide_format: bool = Field(False, description="Whether dataset is in wide format (dates/years as column headers)")


class ValidateMappingsResponse(BaseModel):
    """Response for column mapping validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: Dict[str, str] = Field(default_factory=dict, description="Suggested corrections")


@router.post("/validate-mappings", response_model=ValidateMappingsResponse)
def validate_mappings_endpoint(body: ValidateMappingsRequest) -> ValidateMappingsResponse:
    """
    Validate column mappings against template requirements and dataset schema.

    This endpoint checks:
    1. All required axes have column mappings
    2. Mapped columns exist in the dataset
    3. Column data types match axis requirements (numeric, categorical, time)
    4. Common mistakes (e.g., same column for X and Y in bubble chart)

    Use this for client-side validation before submitting template selection.
    """
    result = validate_column_mappings_with_schema(
        template_id=body.template_id,
        mappings=body.mappings,
        csv_path="(validation request)",  # Not needed for validation-only
        numeric_columns=body.numeric_columns,
        categorical_columns=body.categorical_columns,
        time_column=body.time_column,
        all_columns=body.all_columns if body.all_columns else None,
        is_wide_format=body.is_wide_format,
    )

    return ValidateMappingsResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
        suggestions=result.suggestions,
    )


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


# =============================================================================
# COLUMN MAPPING VALIDATION WITH SCHEMA
# =============================================================================

@dataclass
class ColumnMappingValidationResult:
    """Result of validating column mappings against template and schema."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: Dict[str, str] = field(default_factory=dict)  # axis_name -> suggested_column

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


def _normalize_column_mapping_keys(mappings: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """
    Normalize column mapping keys to match template axis names.

    The frontend may send keys like 'x_col' but templates use 'x_column'.
    This function handles both formats.
    """
    # Mapping from short form (frontend) to long form (template)
    key_aliases = {
        "x_col": "x_column",
        "y_col": "y_column",
        "r_col": "size_column",
        "size_col": "size_column",
        "time_col": "time_column",
        "entity_col": "entity_column",
        "group_col": "group_column",
        "value_col": "value_column",
        "category_col": "category_column",
        "label_col": "label_column",
        "change_col": "change_column",
    }

    normalized = {}
    for key, value in mappings.items():
        # Convert to the template's axis name format
        normalized_key = key_aliases.get(key, key)
        normalized[normalized_key] = value

        # Also keep original key for backward compatibility
        if key not in normalized:
            normalized[key] = value

    return normalized


def _get_schema_column_type(
    column_name: str,
    numeric_columns: List[str],
    categorical_columns: List[str],
    time_column: Optional[str],
) -> str:
    """Determine the type of a column based on schema analysis."""
    if column_name == time_column:
        return "time"
    if column_name in numeric_columns:
        return "numeric"
    if column_name in categorical_columns:
        return "categorical"
    return "unknown"


def _is_type_compatible(required_type: str, actual_type: str) -> bool:
    """
    Check if an actual column type is compatible with a required type.

    Type compatibility rules:
    - "any" accepts everything
    - "numeric" requires numeric
    - "categorical" requires categorical
    - "time" requires time (but numeric years can work too)
    """
    if required_type == "any":
        return True

    if required_type == actual_type:
        return True

    # Time columns are often numeric (years) so allow numeric for time
    if required_type == "time" and actual_type == "numeric":
        return True

    return False


def _suggest_column_for_axis(
    axis: AxisRequirement,
    numeric_columns: List[str],
    categorical_columns: List[str],
    time_column: Optional[str],
    already_used: set,
) -> Optional[str]:
    """
    Suggest a column for an axis based on its required data type.

    Returns the first suitable unused column, or None if no match found.

    Note: For time columns, we only suggest the detected time_column. We do NOT
    fall back to suggesting arbitrary numeric columns, as this leads to confusing
    suggestions (e.g., suggesting a ranking column named 'Apr 11 2018' as a time column
    when the data is in wide format with dates as column headers).
    """
    required_type = axis.data_type

    if required_type == "time":
        # Only suggest the properly detected time column
        # Do NOT fall back to numeric columns - this causes confusing suggestions
        # for wide-format datasets where date strings are column headers (numeric values)
        if time_column and time_column not in already_used:
            return time_column
        # No fallback - if there's no detected time column, return None
        # The validation error will be clearer: "no suitable time column found"
        return None

    elif required_type == "numeric":
        for col in numeric_columns:
            if col not in already_used:
                return col

    elif required_type == "categorical":
        for col in categorical_columns:
            if col not in already_used:
                return col

    elif required_type == "any":
        # Prefer categorical for "any" type
        for col in categorical_columns:
            if col not in already_used:
                return col
        for col in numeric_columns:
            if col not in already_used:
                return col

    return None


def validate_column_mappings_with_schema(
    template_id: str,
    mappings: Dict[str, Optional[str]],
    csv_path: str,
    numeric_columns: Optional[List[str]] = None,
    categorical_columns: Optional[List[str]] = None,
    time_column: Optional[str] = None,
    all_columns: Optional[List[str]] = None,
    is_wide_format: bool = False,
) -> ColumnMappingValidationResult:
    """
    Validate column mappings against both template requirements AND dataset schema.

    This function performs comprehensive validation:
    1. Checks that all required axes have column mappings
    2. Verifies that mapped columns actually exist in the dataset
    3. Validates that column data types match axis requirements
    4. Warns about potential issues (same column used multiple times, etc.)
    5. Suggests appropriate columns for missing or invalid mappings

    Args:
        template_id: The template to validate against (e.g., "bubble", "bar_race")
        mappings: User-provided column mappings (e.g., {"x_col": "Year", "y_col": "Value"})
        csv_path: Path to the CSV file (for logging/error messages)
        numeric_columns: List of numeric column names from schema analysis
        categorical_columns: List of categorical column names from schema analysis
        time_column: Detected time column from schema analysis
        all_columns: List of all column names in the dataset
        is_wide_format: Whether the dataset is in wide format (dates/years as column headers)

    Returns:
        ColumnMappingValidationResult with validation status, errors, warnings, and suggestions
    """
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: Dict[str, str] = {}

    # Normalize input lists
    numeric_columns = numeric_columns or []
    categorical_columns = categorical_columns or []
    all_columns = all_columns or (numeric_columns + categorical_columns + ([time_column] if time_column else []))

    # Get template definition
    template = TEMPLATES_BY_ID.get(template_id)
    if not template:
        return ColumnMappingValidationResult(
            is_valid=False,
            errors=[f"Unknown template: '{template_id}'. Available templates: {list(TEMPLATES_BY_ID.keys())}"],
        )

    # Normalize mapping keys
    normalized_mappings = _normalize_column_mapping_keys(mappings)

    logger.info(f"[VALIDATION] Validating column mappings for template '{template_id}'")
    logger.debug(f"[VALIDATION] Mappings: {normalized_mappings}")
    logger.debug(f"[VALIDATION] Schema - numeric: {numeric_columns}, categorical: {categorical_columns}, time: {time_column}")

    used_columns = set()

    for axis in template.axes:
        axis_name = axis.name
        required_type = axis.data_type
        is_required = axis.required

        # Get the mapped column (check both normalized and original keys)
        mapped_column = normalized_mappings.get(axis_name)

        # Also check short-form keys that might not have been normalized
        if not mapped_column:
            short_key = axis_name.replace("_column", "_col")
            mapped_column = normalized_mappings.get(short_key)

        logger.debug(f"[VALIDATION] Axis '{axis_name}' (required={is_required}, type={required_type}): mapped to '{mapped_column}'")

        # Check if required axis is missing
        if not mapped_column:
            if is_required:
                # Generate suggestion for missing required axis
                suggestion = _suggest_column_for_axis(
                    axis, numeric_columns, categorical_columns, time_column, used_columns
                )
                if suggestion:
                    suggestions[axis_name] = suggestion
                    errors.append(
                        f"Missing required mapping for '{axis.label}' ({axis_name}). "
                        f"Expected a {required_type} column. Suggested: '{suggestion}'"
                    )
                else:
                    # Provide more helpful error message based on the type
                    if required_type == "time":
                        # Special message for time columns - often indicates wide-format data
                        if is_wide_format:
                            # We know the data is wide format - give specific guidance
                            errors.append(
                                f"Missing required mapping for '{axis.label}' ({axis_name}). "
                                f"Your dataset is in 'wide format' (dates/periods as column headers like 'Apr 10 2018'). "
                                f"This template requires a time column as row values, not column headers. "
                                f"Options: 1) Use a template that works with wide data (bar_race, line_evolution), "
                                f"2) Transform your data to 'long format' with a dedicated time column."
                            )
                        else:
                            errors.append(
                                f"Missing required mapping for '{axis.label}' ({axis_name}). "
                                f"This template requires a time column for animation, but no time column was detected. "
                                f"Your dataset may need a column with dates/years/timestamps as row values. "
                                f"Consider choosing a different template that doesn't require time-based animation."
                            )
                    else:
                        errors.append(
                            f"Missing required mapping for '{axis.label}' ({axis_name}). "
                            f"Expected a {required_type} column, but no suitable column found in dataset."
                        )
            continue

        # Check if column exists in dataset
        if all_columns and mapped_column not in all_columns:
            errors.append(
                f"Column '{mapped_column}' for axis '{axis.label}' does not exist in dataset. "
                f"Available columns: {all_columns[:10]}{'...' if len(all_columns) > 10 else ''}"
            )
            # Suggest an alternative
            suggestion = _suggest_column_for_axis(
                axis, numeric_columns, categorical_columns, time_column, used_columns
            )
            if suggestion:
                suggestions[axis_name] = suggestion
            continue

        # Check data type compatibility
        actual_type = _get_schema_column_type(
            mapped_column, numeric_columns, categorical_columns, time_column
        )

        if not _is_type_compatible(required_type, actual_type):
            errors.append(
                f"Column '{mapped_column}' has type '{actual_type}' but axis '{axis.label}' "
                f"requires type '{required_type}'. "
                f"{'Numeric columns: ' + str(numeric_columns[:5]) if required_type == 'numeric' else ''}"
                f"{'Categorical columns: ' + str(categorical_columns[:5]) if required_type == 'categorical' else ''}"
            )
            # Suggest a compatible column
            suggestion = _suggest_column_for_axis(
                axis, numeric_columns, categorical_columns, time_column, used_columns
            )
            if suggestion:
                suggestions[axis_name] = suggestion
            continue

        # Check for duplicate column usage (warning, not error)
        if mapped_column in used_columns:
            # Same column used for multiple axes - this might be intentional for some cases
            # but is often a mistake
            warnings.append(
                f"Column '{mapped_column}' is used for multiple axes. "
                f"This may be intentional, but could also indicate a mapping error."
            )

        used_columns.add(mapped_column)

    # Additional validation: check for obviously wrong patterns
    x_col = normalized_mappings.get("x_column") or normalized_mappings.get("x_col")
    y_col = normalized_mappings.get("y_column") or normalized_mappings.get("y_col")

    if template_id == "bubble" and x_col and y_col:
        # For bubble charts, x and y being the same categorical column is almost certainly wrong
        if x_col == y_col:
            x_type = _get_schema_column_type(x_col, numeric_columns, categorical_columns, time_column)
            if x_type == "categorical":
                errors.append(
                    f"Bubble chart has the same categorical column '{x_col}' for both X and Y axes. "
                    f"X and Y should typically be different numeric columns representing different dimensions."
                )

    is_valid = len(errors) == 0

    # Log validation result
    if is_valid:
        logger.info(f"[VALIDATION] Column mappings valid for template '{template_id}'")
        if warnings:
            logger.warning(f"[VALIDATION] Warnings: {warnings}")
    else:
        logger.warning(f"[VALIDATION] Column mappings INVALID for template '{template_id}'")
        logger.warning(f"[VALIDATION] Errors: {errors}")
        if suggestions:
            logger.info(f"[VALIDATION] Suggestions: {suggestions}")

    return ColumnMappingValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
    )


def get_smart_column_suggestions(
    template_id: str,
    numeric_columns: List[str],
    categorical_columns: List[str],
    time_column: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate smart column suggestions for a template based on dataset schema.

    This provides sensible defaults that the frontend can use to pre-populate
    the column mapping modal.

    Args:
        template_id: The template to generate suggestions for
        numeric_columns: List of numeric column names
        categorical_columns: List of categorical column names
        time_column: Detected time column (if any)

    Returns:
        Dict mapping axis names to suggested column names
    """
    template = TEMPLATES_BY_ID.get(template_id)
    if not template:
        return {}

    suggestions: Dict[str, str] = {}
    used_columns: set = set()

    for axis in template.axes:
        suggestion = _suggest_column_for_axis(
            axis, numeric_columns, categorical_columns, time_column, used_columns
        )
        if suggestion:
            suggestions[axis.name] = suggestion
            used_columns.add(suggestion)

    logger.debug(f"[SUGGESTIONS] Generated suggestions for '{template_id}': {suggestions}")
    return suggestions
