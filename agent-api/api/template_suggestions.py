"""
Template Suggestions Module

This module handles the template suggestion flow for the animation pipeline.
When auto_select_templates is disabled, the system will emit template suggestions
to the user instead of automatically selecting and proceeding.

Key Features:
- Build template suggestions from chart inference results
- Format SSE events for template suggestions
- Helper functions for template selection flow
"""

from __future__ import annotations

import json
import time
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict

from api.routes.templates import get_templates, get_preview_urls


logger = logging.getLogger(__name__)


# SSE Event names for template suggestion flow
class TemplateSuggestionEvents:
    """SSE event names for template suggestion flow."""
    TEMPLATE_SUGGESTIONS = "TemplateSuggestions"
    TEMPLATE_SELECTED = "TemplateSelected"
    TEMPLATE_SELECTION_TIMEOUT = "TemplateSelectionTimeout"


@dataclass
class TemplateSuggestion:
    """A single template suggestion with metadata."""
    template_id: str
    display_name: str
    description: str
    preview_url: Optional[str] = None
    preview_fallback_url: Optional[str] = None
    category: str = "general"
    confidence_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    is_recommended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "template_id": self.template_id,
            "display_name": self.display_name,
            "description": self.description,
            "preview_url": self.preview_url,
            "preview_fallback_url": self.preview_fallback_url,
            "category": self.category,
            "confidence_score": self.confidence_score,
            "reasons": self.reasons,
            "is_recommended": self.is_recommended,
        }


@dataclass
class TemplateSuggestionsPayload:
    """Payload for the TemplateSuggestions SSE event."""
    suggestions: List[TemplateSuggestion]
    run_id: str
    session_id: Optional[str] = None
    message: str = "Please select a template for your animation:"
    dataset_summary: Optional[Dict[str, Any]] = None
    auto_select_countdown: Optional[int] = None  # Seconds before auto-selection (optional)

    def to_sse_payload(self) -> Dict[str, Any]:
        """Convert to SSE payload format."""
        payload = {
            "event": TemplateSuggestionEvents.TEMPLATE_SUGGESTIONS,
            "content": self.message,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "run_id": self.run_id,
            "created_at": int(time.time()),
        }
        if self.session_id:
            payload["session_id"] = self.session_id
        if self.dataset_summary:
            payload["dataset_summary"] = self.dataset_summary
        if self.auto_select_countdown is not None:
            payload["auto_select_countdown"] = self.auto_select_countdown
        return payload

    def to_sse_string(self) -> str:
        """Convert to SSE string format."""
        return f"data: {json.dumps(self.to_sse_payload())}\n\n"


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a template definition by its ID.

    Args:
        template_id: The template identifier (e.g., 'bar_race', 'bubble')

    Returns:
        Template definition dict or None if not found
    """
    templates = get_templates()
    for template in templates:
        if template.template_id == template_id:
            return template.model_dump()
    return None


def build_template_suggestions_from_inference(
    recommendations: List[Any],
    run_id: str,
    session_id: Optional[str] = None,
    dataset_summary: Optional[Dict[str, Any]] = None,
    max_suggestions: int = 5,
) -> TemplateSuggestionsPayload:
    """
    Build template suggestions from chart inference recommendations.

    Args:
        recommendations: List of ChartRecommendation objects from chart_inference
        run_id: The current run ID
        session_id: Optional session ID
        dataset_summary: Optional summary of the dataset (columns, rows, etc.)
        max_suggestions: Maximum number of suggestions to include

    Returns:
        TemplateSuggestionsPayload ready for SSE emission
    """
    suggestions: List[TemplateSuggestion] = []
    templates = get_templates()
    template_map = {t.template_id: t for t in templates}

    # Map chart types to template IDs
    # Some chart types map directly, others need translation
    CHART_TO_TEMPLATE = {
        "bubble": "bubble",
        "distribution": "distribution",
        "bar_race": "bar_race",
        "line_evolution": "line_evolution",
        "bento_grid": "bento_grid",
        "count_bar": "count_bar",
        "single_numeric": "single_numeric",
    }

    seen_templates = set()

    # Add recommendations as suggestions
    for i, rec in enumerate(recommendations[:max_suggestions]):
        chart_type = getattr(rec, "chart_type", None)
        if not chart_type:
            continue

        template_id = CHART_TO_TEMPLATE.get(chart_type, chart_type)

        # Skip if we've already added this template
        if template_id in seen_templates:
            continue
        seen_templates.add(template_id)

        template = template_map.get(template_id)
        if not template:
            logger.warning(f"No template found for chart type: {chart_type}")
            continue

        # Get preview URLs
        preview_url, fallback_url = get_preview_urls(template_id)

        # Build suggestion
        suggestion = TemplateSuggestion(
            template_id=template_id,
            display_name=template.display_name,
            description=template.description,
            preview_url=preview_url,
            preview_fallback_url=fallback_url,
            category=template.category,
            confidence_score=getattr(rec, "score", 0.0),
            reasons=getattr(rec, "reasons", [])[:3],  # Limit reasons
            is_recommended=(i == 0),  # First recommendation is the primary one
        )
        suggestions.append(suggestion)

    # If we have fewer than 3 suggestions, add some fallback templates
    fallback_order = ["bar_race", "line_evolution", "distribution", "count_bar", "single_numeric"]
    for template_id in fallback_order:
        if len(suggestions) >= 3:
            break
        if template_id in seen_templates:
            continue

        template = template_map.get(template_id)
        if not template:
            continue

        preview_url, fallback_url = get_preview_urls(template_id)

        suggestion = TemplateSuggestion(
            template_id=template_id,
            display_name=template.display_name,
            description=template.description,
            preview_url=preview_url,
            preview_fallback_url=fallback_url,
            category=template.category,
            confidence_score=0.0,
            reasons=["Available as an alternative option"],
            is_recommended=False,
        )
        suggestions.append(suggestion)
        seen_templates.add(template_id)

    # Build the message
    if suggestions and suggestions[0].is_recommended:
        top_name = suggestions[0].display_name
        top_score = suggestions[0].confidence_score
        message = (
            f"Based on your data, I recommend using **{top_name}** "
            f"(confidence: {top_score:.0%}). "
            f"Please select a template to continue:"
        )
    else:
        message = "Please select a template for your animation:"

    return TemplateSuggestionsPayload(
        suggestions=suggestions,
        run_id=run_id,
        session_id=session_id,
        message=message,
        dataset_summary=dataset_summary,
    )


def build_template_suggestions_from_templates(
    template_ids: List[str],
    run_id: str,
    session_id: Optional[str] = None,
    recommended_id: Optional[str] = None,
) -> TemplateSuggestionsPayload:
    """
    Build template suggestions from a list of template IDs.

    Args:
        template_ids: List of template IDs to suggest
        run_id: The current run ID
        session_id: Optional session ID
        recommended_id: Optional ID of the recommended template

    Returns:
        TemplateSuggestionsPayload ready for SSE emission
    """
    suggestions: List[TemplateSuggestion] = []
    templates = get_templates()
    template_map = {t.template_id: t for t in templates}

    for template_id in template_ids:
        template = template_map.get(template_id)
        if not template:
            continue

        preview_url, fallback_url = get_preview_urls(template_id)

        suggestion = TemplateSuggestion(
            template_id=template_id,
            display_name=template.display_name,
            description=template.description,
            preview_url=preview_url,
            preview_fallback_url=fallback_url,
            category=template.category,
            confidence_score=1.0 if template_id == recommended_id else 0.5,
            reasons=[],
            is_recommended=(template_id == recommended_id),
        )
        suggestions.append(suggestion)

    return TemplateSuggestionsPayload(
        suggestions=suggestions,
        run_id=run_id,
        session_id=session_id,
        message="Please select a template for your animation:",
    )


def format_dataset_summary(
    csv_path: str,
    row_count: Optional[int] = None,
    column_names: Optional[List[str]] = None,
    numeric_columns: Optional[List[str]] = None,
    categorical_columns: Optional[List[str]] = None,
    time_column: Optional[str] = None,
    is_wide_format: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Format a dataset summary for display in the template suggestions.

    Args:
        csv_path: Path to the dataset
        row_count: Number of rows in the dataset
        column_names: List of column names
        numeric_columns: List of numeric column names
        categorical_columns: List of categorical column names
        time_column: Name of the detected time column
        is_wide_format: Whether the dataset is in wide format (dates/years as column headers)

    Returns:
        Dictionary with formatted dataset summary
    """
    import os

    summary = {
        "filename": os.path.basename(csv_path),
    }

    if row_count is not None:
        summary["row_count"] = row_count

    if column_names:
        summary["column_count"] = len(column_names)
        summary["columns"] = column_names[:10]  # Limit to first 10
        if len(column_names) > 10:
            summary["columns_truncated"] = True

    if numeric_columns:
        summary["numeric_columns"] = numeric_columns[:5]

    if categorical_columns:
        summary["categorical_columns"] = categorical_columns[:5]

    if time_column:
        summary["time_column"] = time_column

    if is_wide_format is not None:
        summary["is_wide_format"] = is_wide_format

    return summary


def validate_template_selection(template_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate that a template selection is valid.

    Args:
        template_id: The template ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    templates = get_templates()
    valid_ids = {t.template_id for t in templates}

    if not template_id:
        return False, "No template ID provided"

    if template_id not in valid_ids:
        return False, f"Invalid template ID: {template_id}. Valid options: {sorted(valid_ids)}"

    return True, None
