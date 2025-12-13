"""
Single Numeric Bar Chart Animation Template

A simple, clean horizontal bar chart animation for datasets with one numeric column.
Shows actual values per category with animated bar growth.

Features:
- Horizontal bar chart with animated growth
- Staggered entrance animation for visual interest
- Value labels at the end of each bar with K/M/B formatting
- Clean, modern styling using the current color palette
- Optional sorting by value (descending) or preserve original order
- Perfect for datasets with one categorical + one numeric column

Use Cases:
- Revenue by product/region
- Population by country
- Scores by team/player
- Any category-value pair data

Usage:
    from agents.tools.templates.single_numeric import generate_single_numeric

    # Simple usage
    code = generate_single_numeric(spec, csv_path, theme="youtube_dark")

    # With explicit columns
    code = generate_single_numeric(
        spec, csv_path,
        category_column="product",
        value_column="revenue",
        top_n=10,
        sort_descending=True
    )
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

# Import primitives
from agents.tools.primitives.elements import (
    Element,
    ElementType,
    Position,
    Style,
)
from agents.tools.primitives.animations import (
    AnimationType,
    AnimationConfig,
    EasingType,
    ANIMATION_PRESETS,
)
from agents.tools.primitives.scenes import (
    SceneType,
    SceneConfig,
    TransitionStyle,
    NarrativeRole,
)
from agents.tools.primitives.composer import (
    StoryConfig,
    NarrativeStyle,
    NARRATIVE_STYLE_PRESETS,
)

# Import styles
try:
    from agents.tools.styles import (
        get_theme,
        get_palette_by_name,
        AnimationStyle,
        ColorPalette,
        DEFAULT_THEME,
    )
except ImportError:
    DEFAULT_THEME = None
    get_theme = lambda x: None
    get_palette_by_name = lambda x: None


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SingleNumericData:
    """Parsed and processed data for single numeric bar animation"""
    categories: List[str]        # Category names
    values: List[float]          # Corresponding numeric values
    max_value: float             # Maximum value (for scaling)
    min_value: float             # Minimum value
    total_value: float           # Sum of all values
    category_column: str         # Name of the category column
    value_column: str            # Name of the value column


@dataclass
class SingleNumericInsight:
    """An auto-detected insight from the data"""
    insight_type: str  # "dominant", "outlier_high", "outlier_low", "balanced"
    description: str
    intensity: float = 0.7


# =============================================================================
# NUMBER FORMATTING
# =============================================================================

def format_value(value: float, precision: int = 1) -> str:
    """
    Format numeric values with K/M/B suffixes for readable labels.

    Examples:
        1234 -> "1.2K"
        1234567 -> "1.2M"
        1234567890 -> "1.2B"
        500 -> "500"
        0.5 -> "0.5"
    """
    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        return f"{sign}{abs_value / 1_000_000_000:.{precision}f}B"
    elif abs_value >= 1_000_000:
        return f"{sign}{abs_value / 1_000_000:.{precision}f}M"
    elif abs_value >= 1_000:
        return f"{sign}{abs_value / 1_000:.{precision}f}K"
    elif abs_value >= 100:
        return f"{sign}{abs_value:.0f}"
    elif abs_value >= 1:
        return f"{sign}{abs_value:.{precision}f}"
    elif abs_value > 0:
        return f"{sign}{abs_value:.2f}"
    else:
        return "0"


# =============================================================================
# DATA PARSING
# =============================================================================

def _resolve_column(headers: List[str], target: str, candidates: List[str]) -> Optional[str]:
    """Smart column name resolution with fuzzy matching"""
    if target in headers:
        return target

    lower_map = {h.lower(): h for h in headers}

    # Try exact target (lowercase)
    if target.lower() in lower_map:
        return lower_map[target.lower()]

    # Try candidates
    for candidate in candidates:
        if candidate in headers:
            return candidate
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


def _find_numeric_column(headers: List[str], rows: List[Dict[str, str]]) -> Optional[str]:
    """Find the first column that contains mostly numeric values"""
    for header in headers:
        numeric_count = 0
        total_count = 0
        for row in rows[:50]:  # Check first 50 rows
            val = row.get(header, "").strip()
            if val:
                total_count += 1
                try:
                    float(val.replace(",", "").replace("$", "").replace("%", ""))
                    numeric_count += 1
                except ValueError:
                    pass
        if total_count > 0 and numeric_count / total_count >= 0.7:
            return header
    return None


def _find_categorical_column(headers: List[str], rows: List[Dict[str, str]], exclude: List[str]) -> Optional[str]:
    """Find the first column that contains categorical (non-numeric) values"""
    categorical_candidates = [
        "name", "category", "label", "item", "product", "country", "region",
        "area", "type", "group", "team", "player", "company", "brand"
    ]

    # First try known categorical patterns
    for candidate in categorical_candidates:
        col = _resolve_column(headers, candidate, [candidate])
        if col and col not in exclude:
            return col

    # Fall back to first non-numeric, non-excluded column
    for header in headers:
        if header in exclude:
            continue
        numeric_count = 0
        total_count = 0
        for row in rows[:50]:
            val = row.get(header, "").strip()
            if val:
                total_count += 1
                try:
                    float(val.replace(",", "").replace("$", "").replace("%", ""))
                    numeric_count += 1
                except ValueError:
                    pass
        if total_count > 0 and numeric_count / total_count < 0.5:
            return header
    return None


def parse_csv_data(
    csv_path: str,
    category_column: Optional[str] = None,
    value_column: Optional[str] = None,
    top_n: int = 15,
    sort_descending: bool = True,
) -> SingleNumericData:
    """
    Parse CSV and extract category-value pairs.

    Args:
        csv_path: Path to CSV file
        category_column: Column name for categories (auto-detect if None)
        value_column: Column name for values (auto-detect if None)
        top_n: Maximum number of categories to include
        sort_descending: Whether to sort by value descending

    Returns:
        SingleNumericData with processed animation data
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        if not headers:
            raise ValueError("CSV file has no headers")

        # Read all rows for analysis
        rows = list(reader)

    if not rows:
        raise ValueError("CSV file has no data rows")

    # Auto-detect value column if not provided
    resolved_value_col = None
    if value_column:
        resolved_value_col = _resolve_column(
            headers, value_column,
            ["value", "amount", "total", "sum", "count", "score", "revenue", "sales", "population"]
        )
    if not resolved_value_col:
        resolved_value_col = _find_numeric_column(headers, rows)

    if not resolved_value_col:
        raise ValueError("No numeric column found in dataset")

    # Auto-detect category column if not provided
    resolved_cat_col = None
    if category_column:
        resolved_cat_col = _resolve_column(
            headers, category_column,
            [category_column.lower(), category_column.upper(), category_column.title()]
        )
    if not resolved_cat_col:
        resolved_cat_col = _find_categorical_column(headers, rows, exclude=[resolved_value_col])

    if not resolved_cat_col:
        # Fallback to first column that isn't the value column
        for h in headers:
            if h != resolved_value_col:
                resolved_cat_col = h
                break

    if not resolved_cat_col:
        raise ValueError("No categorical column found in dataset")

    # Extract category-value pairs
    data_pairs: List[Tuple[str, float]] = []

    for row in rows:
        cat = (row.get(resolved_cat_col) or "").strip()
        val_str = (row.get(resolved_value_col) or "").strip()

        if not cat or not val_str:
            continue

        try:
            # Clean and parse value
            val_clean = val_str.replace(",", "").replace("$", "").replace("%", "")
            val = float(val_clean)
            data_pairs.append((cat, val))
        except ValueError:
            continue

    if not data_pairs:
        raise ValueError(f"No valid data found in columns '{resolved_cat_col}' and '{resolved_value_col}'")

    # Aggregate if there are duplicate categories (sum values)
    aggregated: Dict[str, float] = {}
    for cat, val in data_pairs:
        aggregated[cat] = aggregated.get(cat, 0) + val

    # Convert to sorted list
    items = list(aggregated.items())

    if sort_descending:
        items.sort(key=lambda x: x[1], reverse=True)

    # Limit to top_n
    items = items[:top_n]

    categories = [item[0] for item in items]
    values = [item[1] for item in items]

    max_value = max(values) if values else 0
    min_value = min(values) if values else 0
    total_value = sum(values)

    return SingleNumericData(
        categories=categories,
        values=values,
        max_value=max_value,
        min_value=min_value,
        total_value=total_value,
        category_column=resolved_cat_col,
        value_column=resolved_value_col,
    )


def detect_insights(data: SingleNumericData) -> List[SingleNumericInsight]:
    """
    Analyze data to detect interesting patterns.

    Detects:
    - Dominant category (top category has > 40% of total)
    - High outlier (top value is > 3x the median)
    - Low outlier (bottom value is < 0.2x the median)
    - Balanced distribution (top category has < 20% of total)

    Args:
        data: Parsed single numeric data

    Returns:
        List of insights
    """
    insights = []

    if not data.values or data.total_value == 0:
        return insights

    top_value = data.values[0]
    top_pct = top_value / data.total_value

    # Calculate median
    sorted_values = sorted(data.values)
    n = len(sorted_values)
    if n % 2 == 0:
        median = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        median = sorted_values[n//2]

    # Check for dominant category
    if top_pct > 0.40:
        insights.append(SingleNumericInsight(
            insight_type="dominant",
            description=f"'{data.categories[0]}' dominates with {top_pct:.0%} of total",
            intensity=0.9,
        ))

    # Check for high outlier
    if median > 0 and top_value > median * 3:
        insights.append(SingleNumericInsight(
            insight_type="outlier_high",
            description=f"'{data.categories[0]}' is {top_value/median:.1f}x the median",
            intensity=0.8,
        ))

    # Check for low outlier
    if len(data.values) > 1 and median > 0:
        bottom_value = data.values[-1]
        if bottom_value < median * 0.2:
            insights.append(SingleNumericInsight(
                insight_type="outlier_low",
                description=f"'{data.categories[-1]}' is significantly below average",
                intensity=0.6,
            ))

    # Check for balanced distribution
    if top_pct < 0.20 and len(data.values) >= 5:
        insights.append(SingleNumericInsight(
            insight_type="balanced",
            description="Values are relatively evenly distributed",
            intensity=0.5,
        ))

    return insights


# =============================================================================
# CODE GENERATION
# =============================================================================

def _format_literal(obj: Any) -> str:
    """Format Python object as code literal"""
    if isinstance(obj, str):
        return repr(obj)
    elif isinstance(obj, dict):
        items = ", ".join(f"{_format_literal(k)}: {_format_literal(v)}" for k, v in obj.items())
        return "{" + items + "}"
    elif isinstance(obj, (list, tuple)):
        items = ", ".join(_format_literal(x) for x in obj)
        return "[" + items + "]"
    else:
        return repr(obj)


def generate_single_numeric(
    spec: object,
    csv_path: str,
    category_column: Optional[str] = None,
    value_column: Optional[str] = None,
    top_n: int = 15,
    sort_descending: bool = True,
    theme: str = "youtube_dark",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    bar_height: float = 0.5,
    bar_spacing: float = 0.15,
    stagger_delay: float = 0.1,
) -> str:
    """
    Generate modern, animated single numeric bar chart code.

    This is the main entry point for the single numeric template. It creates a
    horizontal bar chart with staggered growth animation showing actual values.

    Args:
        spec: ChartSpec with configuration
        csv_path: Path to CSV dataset
        category_column: Column for categories (None = auto-detect)
        value_column: Column for values (None = auto-detect)
        top_n: Maximum number of categories to show
        sort_descending: Whether to sort by value descending
        theme: Style theme name
        narrative_style: Pacing preset
        include_intro: Whether to include intro scene
        include_conclusion: Whether to include conclusion scene
        bar_height: Height of each bar
        bar_spacing: Vertical spacing between bars
        stagger_delay: Delay between each bar's animation

    Returns:
        Complete Manim code string with class GenScene(Scene)
    """
    # Extract configuration from spec
    data_binding = getattr(spec, "data_binding", None)
    timing = getattr(spec, "timing", None)

    # Get columns from spec if not provided
    if not category_column and data_binding:
        category_column = (
            getattr(data_binding, "group_col", None) or
            getattr(data_binding, "category_col", None) or
            getattr(data_binding, "entity_col", None)
        )
    if not value_column and data_binding:
        value_column = getattr(data_binding, "value_col", None)

    total_time = getattr(timing, "total_time", 12.0) if timing else 12.0
    creation_time = getattr(timing, "creation_time", 2.0) if timing else 2.0

    # Parse data
    data = parse_csv_data(
        csv_path=csv_path,
        category_column=category_column,
        value_column=value_column,
        top_n=top_n,
        sort_descending=sort_descending,
    )

    # Detect insights
    insights = detect_insights(data)

    # Get theme colors
    theme_style = get_theme(theme) if get_theme else None

    if theme_style:
        bg_color = theme_style.palette.background
        text_color = theme_style.palette.text_primary
        text_secondary = theme_style.palette.text_secondary
        primary_color = theme_style.palette.primary
        accent_color = theme_style.palette.accent
        chart_colors = theme_style.palette.chart_colors[:len(data.categories)]
    else:
        # Fallback colors (Modern Dark theme)
        bg_color = "#0F0F1A"
        text_color = "#FFFFFF"
        text_secondary = "#A1A1AA"
        primary_color = "#6366F1"
        accent_color = "#22D3EE"
        # Modern color palette for bars
        chart_colors = [
            "#6366F1",  # Indigo
            "#8B5CF6",  # Purple
            "#EC4899",  # Pink
            "#F43F5E",  # Rose
            "#F97316",  # Orange
            "#EAB308",  # Yellow
            "#22C55E",  # Green
            "#14B8A6",  # Teal
            "#06B6D4",  # Cyan
            "#3B82F6",  # Blue
            "#A855F7",  # Violet
            "#D946EF",  # Fuchsia
            "#10B981",  # Emerald
            "#84CC16",  # Lime
            "#FBBF24",  # Amber
        ]

    # Ensure we have enough colors
    while len(chart_colors) < len(data.categories):
        chart_colors = chart_colors + chart_colors

    # Get narrative pacing
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    # Format data literals
    lit_categories = _format_literal(data.categories)
    lit_values = _format_literal(data.values)
    lit_colors = _format_literal(chart_colors[:len(data.categories)])

    # Format insights
    lit_insights = _format_literal([
        {"type": i.insight_type, "desc": i.description}
        for i in insights
    ])

    # Calculate timing
    intro_duration = pacing["intro_duration"] if include_intro else 0
    outro_duration = pacing["outro_duration"] if include_conclusion else 0

    reveal_duration = creation_time
    hold_duration = total_time - intro_duration - outro_duration - reveal_duration
    hold_duration = max(2.0, hold_duration)

    total_stagger = stagger_delay * (len(data.categories) - 1)
    bar_grow_time = max(0.5, reveal_duration - total_stagger)

    # Build title from spec or data
    title = getattr(spec, "title", None) or f"{data.value_column} by {data.category_column}"
    subtitle = getattr(spec, "subtitle", None) or f"Top {len(data.categories)} • Total: {format_value(data.total_value)}"

    # Calculate layout
    num_bars = len(data.categories)
    chart_top = 2.0  # Leave room for title

    # Max bar width (leave room for labels)
    max_bar_width = 8.0
    value_margin = 0.5

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# SINGLE NUMERIC BAR CHART ANIMATION
# =============================================================================
# A clean horizontal bar chart showing values by category
# Theme: {theme}
# Category Column: {data.category_column}
# Value Column: {data.value_column}
# =============================================================================

# --- Data ---
CATEGORIES = {lit_categories}
VALUES = {lit_values}
MAX_VALUE = {data.max_value}
MIN_VALUE = {data.min_value}
TOTAL_VALUE = {data.total_value}
CATEGORY_COLUMN = "{data.category_column}"
VALUE_COLUMN = "{data.value_column}"

# --- Colors ---
BAR_COLORS = {lit_colors}
BG_COLOR = "{bg_color}"
TEXT_COLOR = "{text_color}"
TEXT_SECONDARY = "{text_secondary}"

# --- Insights ---
INSIGHTS = {lit_insights}

# --- Story Configuration ---
STORY_TITLE = "{title}"
STORY_SUBTITLE = "{subtitle}"
INCLUDE_INTRO = {include_intro}
INCLUDE_CONCLUSION = {include_conclusion}

# --- Timing ---
INTRO_DURATION = {intro_duration}
REVEAL_DURATION = {reveal_duration}
HOLD_DURATION = {hold_duration}
OUTRO_DURATION = {outro_duration}
BAR_GROW_TIME = {bar_grow_time}
STAGGER_DELAY = {stagger_delay}

# --- Layout ---
BAR_HEIGHT = {bar_height}
BAR_SPACING = {bar_spacing}
MAX_BAR_WIDTH = {max_bar_width}
CHART_TOP = {chart_top}
VALUE_MARGIN = {value_margin}


def format_value(value: float) -> str:
    """Format value with K/M/B suffix"""
    abs_value = abs(value)
    sign = "-" if value < 0 else ""

    if abs_value >= 1_000_000_000:
        return f"{{sign}}{{abs_value / 1_000_000_000:.1f}}B"
    elif abs_value >= 1_000_000:
        return f"{{sign}}{{abs_value / 1_000_000:.1f}}M"
    elif abs_value >= 1_000:
        return f"{{sign}}{{abs_value / 1_000:.1f}}K"
    elif abs_value >= 100:
        return f"{{sign}}{{abs_value:.0f}}"
    elif abs_value >= 1:
        return f"{{sign}}{{abs_value:.1f}}"
    elif abs_value > 0:
        return f"{{sign}}{{abs_value:.2f}}"
    else:
        return "0"


class GenScene(Scene):
    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        # --- Intro Scene ---
        if INCLUDE_INTRO:
            self.play_intro()

        # --- Main Chart ---
        self.play_chart()

        # --- Conclusion Scene ---
        if INCLUDE_CONCLUSION:
            self.play_conclusion()

    def play_intro(self):
        """Animated title sequence"""
        title = Text(
            STORY_TITLE,
            font_size=48,
            color=TEXT_COLOR,
            weight=BOLD,
        ).move_to(UP * 0.5)

        subtitle = Text(
            STORY_SUBTITLE,
            font_size=24,
            color=TEXT_SECONDARY,
        ).next_to(title, DOWN, buff=0.3)

        # Animate in
        self.play(
            FadeIn(title, shift=UP * 0.3),
            run_time=0.8,
        )
        self.play(
            FadeIn(subtitle, shift=UP * 0.2),
            run_time=0.5,
        )

        self.wait(INTRO_DURATION - 1.3)

        # Animate out
        self.play(
            FadeOut(title, shift=UP * 0.3),
            FadeOut(subtitle, shift=UP * 0.3),
            run_time=0.5,
        )

    def play_chart(self):
        """Main chart animation with staggered bar growth"""
        num_bars = len(CATEGORIES)

        # Create all bar components
        bars = []
        labels = []
        value_texts = []

        # Calculate vertical positions
        start_y = CHART_TOP - BAR_HEIGHT / 2

        for i, (category, value) in enumerate(zip(CATEGORIES, VALUES)):
            y_pos = start_y - i * (BAR_HEIGHT + BAR_SPACING)

            # Calculate bar width (scaled to max value)
            # Handle negative values by using absolute value for width
            abs_value = abs(value)
            width_ratio = abs_value / MAX_VALUE if MAX_VALUE > 0 else 0
            bar_width = width_ratio * MAX_BAR_WIDTH

            # Category label (left side)
            label = Text(
                category[:20] + "..." if len(category) > 20 else category,
                font_size=18,
                color=TEXT_COLOR,
            ).move_to(LEFT * 6 + UP * y_pos)
            label.align_to(LEFT * 5.5, RIGHT)
            labels.append(label)

            # Bar (starts at width 0)
            bar = Rectangle(
                width=0.001,  # Start nearly invisible
                height=BAR_HEIGHT,
                fill_color=BAR_COLORS[i % len(BAR_COLORS)],
                fill_opacity=0.9,
                stroke_width=0,
            )
            bar.move_to(LEFT * 5 + UP * y_pos)
            bar.align_to(LEFT * 5, LEFT)
            bar.target_width = bar_width  # Store target width
            bars.append(bar)

            # Value label (will appear at end of bar)
            value_text = Text(
                format_value(value),
                font_size=16,
                color=TEXT_COLOR,
                weight=BOLD,
            )
            value_text.move_to(LEFT * 5 + RIGHT * bar_width + RIGHT * VALUE_MARGIN + UP * y_pos)
            value_text.set_opacity(0)
            value_texts.append(value_text)

        # Add small title at top
        chart_title = Text(
            STORY_TITLE,
            font_size=28,
            color=TEXT_COLOR,
            weight=BOLD,
        ).move_to(UP * 3.2)

        # Animate: First show labels and title
        self.play(
            FadeIn(chart_title, shift=DOWN * 0.2),
            *[FadeIn(label, shift=RIGHT * 0.2) for label in labels],
            run_time=0.6,
        )

        # Animate: Staggered bar growth
        bar_animations = []
        for i, (bar, value_text) in enumerate(zip(bars, value_texts)):
            # Create custom animation for bar growth
            target_width = bar.target_width

            def grow_bar(mob, alpha, tw=target_width):
                new_width = max(0.001, tw * alpha)
                mob.stretch_to_fit_width(new_width)
                mob.align_to(LEFT * 5, LEFT)
                return mob

            bar_anim = UpdateFromAlphaFunc(
                bar,
                grow_bar,
                run_time=BAR_GROW_TIME,
                rate_func=rate_functions.ease_out_cubic,
            )

            # Value appears as bar finishes
            value_anim = Succession(
                Wait(BAR_GROW_TIME * 0.7),
                AnimationGroup(
                    value_text.animate.set_opacity(1),
                    run_time=BAR_GROW_TIME * 0.3,
                ),
            )

            bar_animations.append(
                Succession(
                    Wait(i * STAGGER_DELAY),
                    AnimationGroup(bar_anim, value_anim),
                )
            )

        # Add bars to scene first
        for bar in bars:
            self.add(bar)
        for vt in value_texts:
            self.add(vt)

        # Play staggered animations
        self.play(*bar_animations)

        # Hold on final result
        self.wait(HOLD_DURATION)

        # Store for cleanup
        self.chart_elements = [chart_title] + labels + bars + value_texts

    def play_conclusion(self):
        """Conclusion with optional insight callout"""
        # Fade out chart elements
        if hasattr(self, 'chart_elements'):
            self.play(
                *[FadeOut(elem) for elem in self.chart_elements],
                run_time=0.5,
            )

        # Show insight if available
        if INSIGHTS:
            insight = INSIGHTS[0]
            insight_text = Text(
                insight["desc"],
                font_size=32,
                color=TEXT_COLOR,
            ).move_to(ORIGIN)

            self.play(FadeIn(insight_text, shift=UP * 0.3), run_time=0.5)
            self.wait(OUTRO_DURATION - 1.0)
            self.play(FadeOut(insight_text, shift=UP * 0.3), run_time=0.5)
        else:
            # Simple fade to end
            self.wait(OUTRO_DURATION)
'''

    return code.strip()


def create_single_numeric_story_config(
    title: str = "Values by Category",
    subtitle: str = "",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
) -> StoryConfig:
    """
    Create a story configuration for single numeric animation.

    Args:
        title: Main title text
        subtitle: Subtitle text
        narrative_style: Pacing preset

    Returns:
        StoryConfig for the single numeric animation
    """
    return StoryConfig(
        title=title,
        subtitle=subtitle,
        narrative_style=narrative_style,
        scenes=[
            SceneConfig(
                scene_type=SceneType.INTRO,
                duration=2.0,
                narrative_role=NarrativeRole.HOOK,
            ),
            SceneConfig(
                scene_type=SceneType.REVEAL,
                duration=3.0,
                narrative_role=NarrativeRole.REVEAL,
            ),
            SceneConfig(
                scene_type=SceneType.DATA,
                duration=5.0,
                narrative_role=NarrativeRole.EVIDENCE,
            ),
            SceneConfig(
                scene_type=SceneType.CONCLUSION,
                duration=2.0,
                narrative_role=NarrativeRole.TAKEAWAY,
            ),
        ],
    )
