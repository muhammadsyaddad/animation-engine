"""
Count Bar Chart Animation Template

A simple, clean horizontal bar chart animation for categorical-only datasets.
Converts categorical data to counts and animates bars growing with staggered timing.

Features:
- Horizontal bar chart with animated growth
- Staggered entrance animation for visual interest
- Value labels at the end of each bar
- Clean, modern styling using the current color palette
- Auto-sorted by count (descending) for visual hierarchy
- Perfect for purely categorical datasets with no numeric columns

Use Cases:
- Counting occurrences of categories (country, region, product type, etc.)
- Showing frequency distributions of categorical variables
- Simple data exploration when users upload categorical-only CSVs

Usage:
    from agents.tools.templates.count_bar import generate_count_bar

    # Simple usage
    code = generate_count_bar(spec, csv_path, count_column="country", theme="youtube_dark")

    # With top N limit
    code = generate_count_bar(spec, csv_path, count_column="region", top_n=10)
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
class CountBarData:
    """Parsed and processed data for count bar animation"""
    categories: List[str]        # Category names (sorted by count desc)
    counts: List[int]            # Corresponding counts
    max_count: int               # Maximum count (for scaling)
    total_items: int             # Total number of items counted
    column_name: str             # Name of the column being counted


@dataclass
class CountBarInsight:
    """An auto-detected insight from the count data"""
    insight_type: str  # "dominant", "long_tail", "even_distribution"
    description: str
    intensity: float = 0.7


# =============================================================================
# NUMBER FORMATTING
# =============================================================================

def format_count(value: int) -> str:
    """
    Format count numbers with K/M suffixes for readable labels.

    Examples:
        1234 -> "1.2K"
        1234567 -> "1.2M"
        500 -> "500"
    """
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)


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


def parse_csv_data(
    csv_path: str,
    count_column: Optional[str] = None,
    top_n: int = 15,
) -> CountBarData:
    """
    Parse CSV and count occurrences of categorical values.

    Args:
        csv_path: Path to CSV file
        count_column: Column name to count (if None, uses first categorical column)
        top_n: Maximum number of categories to include

    Returns:
        CountBarData with processed animation data
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        if not headers:
            raise ValueError("CSV file has no headers")

        # Resolve count column
        resolved_column = None
        if count_column:
            resolved_column = _resolve_column(
                headers, count_column,
                [count_column.lower(), count_column.upper(), count_column.title()]
            )

        # If no column specified or resolved, try common patterns
        if not resolved_column:
            categorical_candidates = [
                "category", "name", "country", "region", "area", "type", "group",
                "label", "item", "product", "status", "class", "sector"
            ]
            for candidate in categorical_candidates:
                resolved_column = _resolve_column(headers, candidate, [candidate])
                if resolved_column:
                    break

        # Fallback to first column
        if not resolved_column:
            resolved_column = headers[0]

        # Count occurrences
        counts: Dict[str, int] = {}
        total_items = 0

        for row in reader:
            value = (row.get(resolved_column) or "").strip()
            if value:
                counts[value] = counts.get(value, 0) + 1
                total_items += 1

    if not counts:
        raise ValueError(f"No valid data found in column '{resolved_column}'")

    # Sort by count (descending) and limit to top_n
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    categories = [item[0] for item in sorted_items]
    count_values = [item[1] for item in sorted_items]
    max_count = max(count_values) if count_values else 1

    return CountBarData(
        categories=categories,
        counts=count_values,
        max_count=max_count,
        total_items=total_items,
        column_name=resolved_column,
    )


def detect_insights(data: CountBarData) -> List[CountBarInsight]:
    """
    Analyze data to detect interesting patterns.

    Detects:
    - Dominant category (top category has > 30% of total)
    - Long tail (top 3 categories have > 70% of total)
    - Even distribution (no category has > 20% of total)

    Args:
        data: Parsed count bar data

    Returns:
        List of insights
    """
    insights = []

    if not data.counts or data.total_items == 0:
        return insights

    top_count = data.counts[0]
    top_pct = top_count / data.total_items

    # Check for dominant category
    if top_pct > 0.30:
        insights.append(CountBarInsight(
            insight_type="dominant",
            description=f"'{data.categories[0]}' dominates with {top_pct:.0%} of all items",
            intensity=0.9,
        ))

    # Check for long tail
    if len(data.counts) >= 3:
        top3_sum = sum(data.counts[:3])
        top3_pct = top3_sum / data.total_items
        if top3_pct > 0.70:
            insights.append(CountBarInsight(
                insight_type="long_tail",
                description=f"Top 3 categories account for {top3_pct:.0%} of all items",
                intensity=0.7,
            ))

    # Check for even distribution
    if top_pct < 0.20:
        insights.append(CountBarInsight(
            insight_type="even_distribution",
            description="Categories are relatively evenly distributed",
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


def generate_count_bar(
    spec: object,
    csv_path: str,
    count_column: Optional[str] = None,
    top_n: int = 15,
    theme: str = "youtube_dark",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    bar_height: float = 0.5,
    bar_spacing: float = 0.15,
    stagger_delay: float = 0.1,
) -> str:
    """
    Generate modern, animated count bar chart code.

    This is the main entry point for the count bar template. It creates a
    horizontal bar chart with staggered growth animation.

    Args:
        spec: ChartSpec with configuration
        csv_path: Path to CSV dataset
        count_column: Column to count (None = auto-detect)
        top_n: Maximum number of categories to show
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

    # Get count column from spec if not provided
    if not count_column and data_binding:
        count_column = getattr(data_binding, "group_col", None) or getattr(data_binding, "category_col", None)

    total_time = getattr(timing, "total_time", 12.0) if timing else 12.0
    creation_time = getattr(timing, "creation_time", 2.0) if timing else 2.0

    # Parse data
    data = parse_csv_data(
        csv_path=csv_path,
        count_column=count_column,
        top_n=top_n,
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
    lit_counts = _format_literal(data.counts)
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
    title = getattr(spec, "title", None) or f"Distribution by {data.column_name}"
    subtitle = getattr(spec, "subtitle", None) or f"Top {len(data.categories)} categories • {data.total_items:,} total items"

    # Calculate layout
    num_bars = len(data.categories)
    total_bar_height = num_bars * bar_height + (num_bars - 1) * bar_spacing
    chart_top = 2.0  # Leave room for title

    # Max bar width (leave room for labels)
    max_bar_width = 8.0
    label_margin = 0.3
    value_margin = 0.5

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# COUNT BAR CHART ANIMATION
# =============================================================================
# A simple, clean horizontal bar chart with staggered growth animation
# Theme: {theme}
# Column: {data.column_name}
# =============================================================================

# --- Data ---
CATEGORIES = {lit_categories}
COUNTS = {lit_counts}
MAX_COUNT = {data.max_count}
TOTAL_ITEMS = {data.total_items}
COLUMN_NAME = "{data.column_name}"

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
LABEL_MARGIN = {label_margin}
VALUE_MARGIN = {value_margin}


def format_count(value: int) -> str:
    """Format count with K/M suffix"""
    if value >= 1_000_000:
        return f"{{value / 1_000_000:.1f}}M"
    elif value >= 1_000:
        return f"{{value / 1_000:.1f}}K"
    else:
        return str(value)


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

        for i, (category, count) in enumerate(zip(CATEGORIES, COUNTS)):
            y_pos = start_y - i * (BAR_HEIGHT + BAR_SPACING)

            # Calculate bar width (scaled to max count)
            width_ratio = count / MAX_COUNT if MAX_COUNT > 0 else 0
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
                format_count(count),
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


def create_count_bar_story_config(
    title: str = "Category Distribution",
    subtitle: str = "",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
) -> StoryConfig:
    """
    Create a story configuration for count bar animation.

    Args:
        title: Main title text
        subtitle: Subtitle text
        narrative_style: Pacing preset

    Returns:
        StoryConfig for the count bar animation
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


# =============================================================================
# TRANSFORMATION UTILITIES
# =============================================================================

def transform_count_by_column(
    csv_path: str,
    count_column: str,
    output_path: str,
    top_n: int = 15,
) -> str:
    """
    Transform a categorical dataset into a count aggregation CSV.

    This creates a new CSV with columns: category, count
    Sorted by count descending.

    Args:
        csv_path: Path to source CSV
        count_column: Column to count
        output_path: Path for output CSV
        top_n: Maximum categories to include

    Returns:
        Path to the created CSV file
    """
    import os

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source dataset not found: {csv_path}")

    # Parse and count
    data = parse_csv_data(csv_path, count_column=count_column, top_n=top_n)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Write aggregated CSV
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "count"])
        for category, count in zip(data.categories, data.counts):
            writer.writerow([category, count])

    return output_path
