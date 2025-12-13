"""
Modern Bento Grid KPI Dashboard Animation Template

A story-driven, modular KPI dashboard animation using the primitives system.

Features:
- Story-driven narrative structure (intro, reveal, count, conclusion)
- Glassmorphism card design with subtle gradients
- Animated counting numbers with K/M/B formatting
- Optional change indicators (up/down arrows with percentages)
- Flexible grid layouts (auto or manual)
- Staggered reveal animations
- Configurable narrative styles

Perfect for: Business dashboards, quarterly reports, social media stats,
             financial summaries, performance metrics

Usage:
    from agents.tools.templates.bento_grid import generate_bento_grid

    # Simple usage
    code = generate_bento_grid(spec, csv_path, theme="youtube_dark")

    # With custom narrative style
    from agents.tools.templates import NarrativeStyle
    code = generate_bento_grid(
        spec, csv_path,
        theme="youtube_dark",
        narrative_style=NarrativeStyle.CINEMATIC,
        include_intro=True,
        include_conclusion=True,
    )
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union

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
    )
except ImportError:
    get_theme = lambda x: None
    get_palette_by_name = lambda x: None


# =============================================================================
# NUMBER FORMATTING
# =============================================================================

def format_number(value: float, precision: int = 1) -> str:
    """
    Format large numbers with K/M/B suffixes for readable display.

    Examples:
        1234 -> "1.2K"
        1234567 -> "1.2M"
        1234567890 -> "1.2B"
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


def format_percentage(value: float, precision: int = 1) -> str:
    """Format a decimal as percentage"""
    return f"{value:.{precision}f}%"


def format_currency(value: float, symbol: str = "$", precision: int = 0) -> str:
    """Format number as currency with K/M/B suffixes"""
    formatted = format_number(abs(value), precision)
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{formatted}"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class KPIItem:
    """Single KPI metric for the dashboard"""
    label: str
    value: float
    change: Optional[float] = None  # Percentage change (e.g., +12.5 or -5.2)
    prefix: str = ""  # e.g., "$" for currency
    suffix: str = ""  # e.g., "%" for percentages
    icon: Optional[str] = None  # Icon name (future use)
    color: Optional[str] = None  # Custom color override


@dataclass
class BentoGridData:
    """Parsed data for bento grid animation"""
    items: List[KPIItem]
    title: Optional[str] = None
    subtitle: Optional[str] = None


@dataclass
class BentoInsight:
    """An auto-detected insight from the data"""
    index: int
    label: str
    insight_type: str  # "top_performer", "big_gain", "big_loss", "milestone"
    description: str
    intensity: float = 0.7


# =============================================================================
# DATA PARSING
# =============================================================================

def _resolve_column(headers: List[str], target: str, candidates: List[str]) -> str:
    """Smart column name resolution with fuzzy matching"""
    if target in headers:
        return target

    lower_map = {h.lower(): h for h in headers}

    for candidate in candidates:
        if candidate in headers:
            return candidate
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return target


def parse_csv_data(
    csv_path: str,
    label_col: str = "label",
    value_col: str = "value",
    change_col: Optional[str] = None,
    prefix_col: Optional[str] = None,
    suffix_col: Optional[str] = None,
    max_items: int = 9,
) -> BentoGridData:
    """
    Parse CSV and prepare data for bento grid animation.

    Args:
        csv_path: Path to CSV file
        label_col: Column name for metric labels
        value_col: Column name for metric values
        change_col: Optional column for change percentages
        prefix_col: Optional column for value prefix (e.g., "$")
        suffix_col: Optional column for value suffix (e.g., "%")
        max_items: Maximum items to show (default 9 for 3x3 grid)

    Returns:
        BentoGridData with parsed KPI items
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    items: List[KPIItem] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Resolve column names
        label_col = _resolve_column(
            headers, label_col,
            ["label", "name", "metric", "kpi", "title", "category", "item", "indicator"]
        )
        value_col = _resolve_column(
            headers, value_col,
            ["value", "amount", "total", "count", "number", "score", "result"]
        )

        # Optional columns
        change_col_resolved = None
        if change_col:
            change_col_resolved = _resolve_column(
                headers, change_col,
                ["change", "delta", "growth", "diff", "percent_change", "yoy", "mom"]
            )
        else:
            # Try to auto-detect change column
            for candidate in ["change", "delta", "growth", "percent_change", "yoy"]:
                if candidate in headers or candidate.lower() in [h.lower() for h in headers]:
                    change_col_resolved = _resolve_column(headers, candidate, [candidate])
                    break

        prefix_col_resolved = None
        if prefix_col:
            prefix_col_resolved = _resolve_column(headers, prefix_col, ["prefix", "symbol", "currency"])

        suffix_col_resolved = None
        if suffix_col:
            suffix_col_resolved = _resolve_column(headers, suffix_col, ["suffix", "unit", "units"])

        for row in reader:
            label = (row.get(label_col) or "").strip()
            value_str = (row.get(value_col) or "").strip()

            if not label or not value_str:
                continue

            # Parse value (handle currency symbols, commas, etc.)
            try:
                clean_val = value_str.replace(",", "").replace("$", "").replace("%", "").replace("€", "").replace("£", "")
                value = float(clean_val)
            except ValueError:
                continue

            # Parse optional change
            change = None
            if change_col_resolved and row.get(change_col_resolved):
                try:
                    change_str = row.get(change_col_resolved, "").strip()
                    change_str = change_str.replace("%", "").replace("+", "")
                    change = float(change_str)
                except ValueError:
                    pass

            # Get prefix/suffix
            prefix = ""
            if prefix_col_resolved and row.get(prefix_col_resolved):
                prefix = row.get(prefix_col_resolved, "").strip()
            elif "$" in value_str or "€" in value_str or "£" in value_str:
                # Auto-detect currency prefix from value
                for sym in ["$", "€", "£"]:
                    if sym in value_str:
                        prefix = sym
                        break

            suffix = ""
            if suffix_col_resolved and row.get(suffix_col_resolved):
                suffix = row.get(suffix_col_resolved, "").strip()
            elif "%" in value_str:
                suffix = "%"

            items.append(KPIItem(
                label=label,
                value=value,
                change=change,
                prefix=prefix,
                suffix=suffix,
            ))

            if len(items) >= max_items:
                break

    if not items:
        raise ValueError("No valid KPI data found in CSV")

    return BentoGridData(items=items)


def detect_insights(data: BentoGridData) -> List[BentoInsight]:
    """
    Analyze data to detect interesting KPIs worth highlighting.

    Detects:
    - Top performer (highest value)
    - Big gains (large positive change)
    - Big losses (large negative change)

    Args:
        data: Parsed bento grid data

    Returns:
        List of insights
    """
    insights = []
    items = data.items

    if not items:
        return insights

    # Find top performer by value
    max_idx = 0
    max_val = items[0].value
    for i, item in enumerate(items):
        if item.value > max_val:
            max_val = item.value
            max_idx = i

    insights.append(BentoInsight(
        index=max_idx,
        label=items[max_idx].label,
        insight_type="top_performer",
        description=f"{items[max_idx].label} leads!",
        intensity=0.9,
    ))

    # Find big gains and losses
    for i, item in enumerate(items):
        if item.change is not None:
            if item.change >= 20:
                insights.append(BentoInsight(
                    index=i,
                    label=item.label,
                    insight_type="big_gain",
                    description=f"{item.label}: +{item.change:.1f}%",
                    intensity=0.8,
                ))
            elif item.change <= -20:
                insights.append(BentoInsight(
                    index=i,
                    label=item.label,
                    insight_type="big_loss",
                    description=f"{item.label}: {item.change:.1f}%",
                    intensity=0.7,
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
    elif obj is None:
        return "None"
    else:
        return repr(obj)


def _calculate_grid_layout(n: int) -> Tuple[int, int]:
    """Calculate optimal grid rows and columns for n items"""
    if n == 1:
        return (1, 1)
    elif n == 2:
        return (1, 2)
    elif n == 3:
        return (1, 3)
    elif n == 4:
        return (2, 2)
    elif n <= 6:
        return (2, 3)
    elif n <= 9:
        return (3, 3)
    else:
        cols = min(4, math.ceil(math.sqrt(n)))
        rows = math.ceil(n / cols)
        return (rows, cols)


def generate_bento_grid(
    spec: object,
    csv_path: str,
    theme: str = "youtube_dark",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    auto_highlights: bool = True,
) -> str:
    """
    Generate modern, story-driven bento grid KPI dashboard animation code.

    This is the main entry point for the bento grid template. It uses the
    primitives system to create a narrative-driven animation.

    Args:
        spec: ChartSpec with configuration
        csv_path: Path to CSV dataset
        theme: Style theme name
        narrative_style: Pacing preset
        include_intro: Whether to include intro scene
        include_conclusion: Whether to include conclusion scene
        auto_highlights: Whether to auto-detect and highlight insights

    Returns:
        Complete Manim code string with class GenScene(Scene)
    """
    # Extract configuration from spec
    data_binding = getattr(spec, "data_binding", None)
    timing = getattr(spec, "timing", None)
    style = getattr(spec, "style", None)

    # Data binding columns
    label_col = getattr(data_binding, "label_col", None) or getattr(data_binding, "entity_col", None) if data_binding else None
    value_col = getattr(data_binding, "value_col", None) if data_binding else None
    change_col = getattr(data_binding, "change_col", None) if data_binding else None

    # Timing
    total_time = getattr(timing, "total_time", 10.0) if timing else 10.0
    count_duration = getattr(timing, "count_duration", 2.0) if timing else 2.0

    # Style options
    show_change = getattr(style, "show_change", True) if style else True
    card_style = getattr(style, "card_style", "glassmorphism") if style else "glassmorphism"
    max_items = getattr(style, "max_items", 9) if style else 9

    # Title from spec
    title = getattr(spec, "title", None) or "Key Metrics"
    subtitle = getattr(spec, "subtitle", None)

    # Parse data
    data = parse_csv_data(
        csv_path=csv_path,
        label_col=label_col or "label",
        value_col=value_col or "value",
        change_col=change_col,
        max_items=max_items,
    )

    # Detect insights for highlights
    insights = detect_insights(data) if auto_highlights else []

    # Get theme colors
    theme_style = get_theme(theme) if get_theme else None

    if theme_style:
        bg_color = theme_style.palette.background
        text_color = theme_style.palette.text_primary
        text_secondary = theme_style.palette.text_secondary
        surface_color = theme_style.palette.surface
        accent_color = theme_style.palette.accent
        success_color = theme_style.palette.success
        error_color = theme_style.palette.error
        chart_colors = theme_style.palette.chart_colors
    else:
        # Fallback colors (YouTube Dark theme)
        bg_color = "#0F0F1A"
        text_color = "#FFFFFF"
        text_secondary = "#A1A1AA"
        surface_color = "#1A1A2E"
        accent_color = "#22D3EE"
        success_color = "#10B981"
        error_color = "#EF4444"
        chart_colors = [
            "#6366F1", "#EC4899", "#22D3EE", "#10B981",
            "#F59E0B", "#8B5CF6", "#F97316", "#14B8A6", "#EF4444"
        ]

    # Get narrative pacing
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    # Prepare items data for embedding
    items_data = []
    for i, item in enumerate(data.items):
        items_data.append({
            "label": item.label,
            "value": item.value,
            "change": item.change,
            "prefix": item.prefix,
            "suffix": item.suffix,
            "color": chart_colors[i % len(chart_colors)],
        })

    # Format insights
    lit_insights = _format_literal([
        {"index": i.index, "label": i.label, "type": i.insight_type, "desc": i.description}
        for i in insights
    ])

    # Calculate grid layout
    n_items = len(items_data)
    rows, cols = _calculate_grid_layout(n_items)

    # Format literals
    lit_items = _format_literal(items_data)
    lit_chart_colors = _format_literal(chart_colors)

    # Calculate timing
    intro_duration = pacing["intro_duration"] if include_intro else 0
    outro_duration = pacing["outro_duration"] if include_conclusion else 0
    reveal_duration = 1.5

    count_time = count_duration
    hold_time = total_time - intro_duration - outro_duration - reveal_duration - count_time
    hold_time = max(1.0, hold_time)

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# BENTO GRID KPI DASHBOARD - Story-Driven Architecture
# =============================================================================
# Generated using the primitives system for modular, narrative animations
# Theme: {theme}
# Narrative Style: {narrative_style.value}
# =============================================================================

# --- Data ---
KPI_ITEMS = {lit_items}
GRID_ROWS = {rows}
GRID_COLS = {cols}

# --- Insights (Auto-Detected) ---
INSIGHTS = {lit_insights}

# --- Story Configuration ---
STORY_TITLE = "{title}"
STORY_SUBTITLE = {repr(subtitle) if subtitle else 'None'}
INCLUDE_INTRO = {include_intro}
INCLUDE_CONCLUSION = {include_conclusion}

# --- Timing (Narrative Style: {narrative_style.value}) ---
INTRO_DURATION = {intro_duration}
REVEAL_DURATION = {reveal_duration}
COUNT_DURATION = {count_time}
HOLD_DURATION = {hold_time}
OUTRO_DURATION = {outro_duration}
TOTAL_DURATION = {total_time}

# --- Style Configuration ---
BG_COLOR = "{bg_color}"
TEXT_COLOR = "{text_color}"
TEXT_SECONDARY = "{text_secondary}"
SURFACE_COLOR = "{surface_color}"
ACCENT_COLOR = "{accent_color}"
SUCCESS_COLOR = "{success_color}"
ERROR_COLOR = "{error_color}"
CHART_COLORS = {lit_chart_colors}

# --- Layout Constants ---
CARD_WIDTH = 3.8
CARD_HEIGHT = 2.4
CARD_SPACING = 0.35
CORNER_RADIUS = 0.2


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_display_number(value: float, prefix: str = "", suffix: str = "") -> str:
    """Format number with K/M/B suffixes and prefix/suffix"""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1_000_000_000:
        formatted = f"{{abs_val / 1_000_000_000:.1f}}B"
    elif abs_val >= 1_000_000:
        formatted = f"{{abs_val / 1_000_000:.1f}}M"
    elif abs_val >= 1_000:
        formatted = f"{{abs_val / 1_000:.1f}}K"
    elif abs_val >= 100:
        formatted = f"{{abs_val:.0f}}"
    elif abs_val >= 1:
        formatted = f"{{abs_val:.1f}}"
    elif abs_val > 0:
        formatted = f"{{abs_val:.2f}}"
    else:
        formatted = "0"

    return f"{{sign}}{{prefix}}{{formatted}}{{suffix}}"


def get_decimal_places(value: float) -> int:
    """Determine appropriate decimal places for value"""
    abs_val = abs(value)
    if abs_val >= 1000:
        return 0
    elif abs_val >= 10:
        return 1
    elif abs_val >= 1:
        return 1
    else:
        return 2


def get_top_performer_index() -> int:
    """Get the index of the top performer from insights"""
    for insight in INSIGHTS:
        if insight["type"] == "top_performer":
            return insight["index"]
    return 0


# =============================================================================
# SCENE CLASS
# =============================================================================

class GenScene(Scene):
    """
    Story-driven bento grid KPI dashboard animation.

    Structure:
    1. INTRO: Title and subtitle fade in
    2. REVEAL: Cards appear with staggered animation
    3. COUNT: Values count up with animated numbers
    4. HIGHLIGHTS: Top performer emphasized
    5. CONCLUSION: Hold and optional shimmer effect
    """

    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        if not KPI_ITEMS:
            no_data = Text("No data available", color=TEXT_COLOR, font_size=36)
            self.play(Write(no_data))
            return

        # Track elements
        self.title_group = None
        self.cards = None
        self.value_trackers = []

        # Run story scenes
        if INCLUDE_INTRO:
            self.scene_intro()

        self.scene_reveal()
        self.scene_count()

        if INCLUDE_CONCLUSION:
            self.scene_conclusion()

    # -------------------------------------------------------------------------
    # SCENE 1: INTRO
    # -------------------------------------------------------------------------
    def scene_intro(self):
        """Opening scene with title and subtitle."""
        # Create title
        title = Text(
            STORY_TITLE,
            font_size=56,
            color=TEXT_COLOR,
            weight=BOLD,
        )
        title.move_to([0, 0.5, 0])

        # Create subtitle
        subtitle_text = None
        if STORY_SUBTITLE:
            subtitle_text = Text(
                STORY_SUBTITLE,
                font_size=28,
                color=TEXT_SECONDARY,
            )
            subtitle_text.move_to([0, -0.3, 0])
            subtitle_text.set_opacity(0.8)

        title_group = VGroup(title)
        if subtitle_text:
            title_group.add(subtitle_text)

        # Animate entrance
        self.play(
            FadeIn(title, shift=UP * 0.3),
            run_time=0.8,
            rate_func=smooth,
        )

        if subtitle_text:
            self.play(
                FadeIn(subtitle_text, shift=UP * 0.2),
                run_time=0.5,
                rate_func=smooth,
            )

        # Hold
        self.wait(INTRO_DURATION - 1.8)

        # Fade out
        self.play(
            FadeOut(title_group, shift=UP * 0.5),
            run_time=0.5,
        )

    # -------------------------------------------------------------------------
    # SCENE 2: REVEAL
    # -------------------------------------------------------------------------
    def scene_reveal(self):
        """Reveal cards with staggered animation."""
        self.cards = VGroup()
        self.value_trackers = []

        for i, item in enumerate(KPI_ITEMS):
            label = item["label"]
            target_value = item["value"]
            change = item["change"]
            prefix = item["prefix"]
            suffix = item["suffix"]
            card_color = item["color"]

            # Card Background (Glassmorphism)
            card_bg = RoundedRectangle(
                corner_radius=CORNER_RADIUS,
                width=CARD_WIDTH,
                height=CARD_HEIGHT,
                fill_color=SURFACE_COLOR,
                fill_opacity=0.6,
                stroke_color=card_color,
                stroke_width=2,
                stroke_opacity=0.8,
            )

            # Subtle gradient overlay (top highlight)
            highlight = RoundedRectangle(
                corner_radius=CORNER_RADIUS,
                width=CARD_WIDTH,
                height=CARD_HEIGHT * 0.3,
                fill_opacity=0.08,
                stroke_width=0,
            )
            highlight.set_fill(WHITE)
            highlight.align_to(card_bg, UP)
            highlight.shift(DOWN * 0.02)

            # Label (Top of card)
            label_text = Text(
                str(label).upper(),
                font_size=16,
                weight=BOLD,
                color=TEXT_SECONDARY,
            )
            label_text.move_to(card_bg.get_top() + DOWN * 0.45)

            # Value (Center, large)
            decimal_places = get_decimal_places(target_value)

            value_display = DecimalNumber(
                0,
                num_decimal_places=decimal_places,
                font_size=48,
                color=TEXT_COLOR,
            )
            value_display.move_to(card_bg.get_center() + UP * 0.1)

            # Change Indicator (Bottom of card)
            change_group = None
            if change is not None:
                is_positive = change >= 0
                change_color = SUCCESS_COLOR if is_positive else ERROR_COLOR
                arrow_char = "▲" if is_positive else "▼"
                change_str = f"{{arrow_char}} {{abs(change):.1f}}%"

                change_text = Text(
                    change_str,
                    font_size=16,
                    color=change_color,
                )
                change_text.move_to(card_bg.get_bottom() + UP * 0.45)
                change_group = change_text

            # Accent bar at bottom
            accent_bar = Rectangle(
                width=CARD_WIDTH * 0.3,
                height=0.06,
                fill_color=card_color,
                fill_opacity=0.9,
                stroke_width=0,
            )
            accent_bar.move_to(card_bg.get_bottom() + UP * 0.12)

            # Assemble Card
            card_elements = VGroup(card_bg, highlight, label_text, value_display, accent_bar)
            if change_group:
                card_elements.add(change_group)

            self.cards.add(card_elements)

            # Setup value tracker for counting animation
            tracker = ValueTracker(0)
            self.value_trackers.append((tracker, target_value, value_display))

            # Add updater to animate the number
            def make_updater(dec_mob, trk, card_center):
                def updater(m):
                    m.set_value(trk.get_value())
                    m.move_to(card_center + UP * 0.1)
                return updater

            value_display.add_updater(
                make_updater(value_display, tracker, card_bg.get_center())
            )

        # Arrange Grid
        self.cards.arrange_in_grid(
            rows=GRID_ROWS,
            cols=GRID_COLS,
            buff=CARD_SPACING,
        )

        # Scale to fit screen if needed
        max_width = config.frame_width - 1.5
        max_height = config.frame_height - 1.5

        if self.cards.width > max_width:
            self.cards.scale_to_fit_width(max_width)
        if self.cards.height > max_height:
            self.cards.scale_to_fit_height(max_height)

        self.cards.move_to(ORIGIN)

        # Staggered entrance
        card_anims = []
        for card in self.cards:
            card_anims.append(FadeIn(card, shift=UP * 0.3, scale=0.92))

        self.play(
            LaggedStart(*card_anims, lag_ratio=0.08),
            run_time=REVEAL_DURATION,
        )

        self.wait(0.2)

    # -------------------------------------------------------------------------
    # SCENE 3: COUNT
    # -------------------------------------------------------------------------
    def scene_count(self):
        """Animate values counting up."""
        count_anims = []
        for tracker, target, _ in self.value_trackers:
            count_anims.append(tracker.animate.set_value(target))

        self.play(
            *count_anims,
            run_time=COUNT_DURATION,
            rate_func=rate_functions.ease_out_cubic,
        )

        self.wait(0.3)

    # -------------------------------------------------------------------------
    # SCENE 4: CONCLUSION
    # -------------------------------------------------------------------------
    def scene_conclusion(self):
        """Closing scene with highlights and hold."""
        # Highlight top performer
        top_idx = get_top_performer_index()
        if top_idx < len(self.cards):
            top_card_bg = self.cards[top_idx][0]
            self.play(
                top_card_bg.animate.set_stroke(color=ACCENT_COLOR, width=4),
                run_time=0.4,
            )

        # Hold
        self.wait(HOLD_DURATION * 0.5)

        # Shimmer effect across all cards
        if len(self.cards) > 1:
            shimmer_anims = []
            for i, card in enumerate(self.cards):
                card_bg = card[0]
                shimmer_anims.append(
                    Succession(
                        Wait(i * 0.08),
                        card_bg.animate(rate_func=there_and_back, run_time=0.3).set_stroke(opacity=1.0),
                    )
                )

            self.play(*shimmer_anims)

        # Final hold
        self.wait(OUTRO_DURATION - 0.5)
'''

    return code.strip()


# Alias for backward compatibility
generate_bento_grid_code = generate_bento_grid


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_bento_grid_story_config(
    title: str,
    subtitle: Optional[str] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    count_duration: float = 2.0,
    theme: str = "youtube_dark",
) -> StoryConfig:
    """
    Create a story configuration for bento grid animations.

    Args:
        title: Story title
        subtitle: Optional subtitle
        narrative_style: Pacing preset
        count_duration: Duration of counting animation
        theme: Visual theme

    Returns:
        StoryConfig ready for use with generate_bento_grid
    """
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    return StoryConfig(
        title=title,
        subtitle=subtitle,
        theme=theme,
        narrative_style=narrative_style,
        total_duration=count_duration + pacing["intro_duration"] + pacing["outro_duration"] + 3.0,
    )


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test number formatting
    print("Number formatting tests:")
    test_values = [0, 500, 1234, 12345, 123456, 1234567, 12345678, 123456789, 1234567890]
    for v in test_values:
        print(f"  {v:>15} -> {format_number(v)}")

    print("\nBento Grid Template Module Loaded Successfully")
    print("Available functions:")
    print("  - generate_bento_grid(spec, csv_path, theme, ...)")
    print("  - create_bento_grid_story_config(title, subtitle, ...)")
    print("  - parse_csv_data(csv_path, ...)")
    print("  - detect_insights(data)")
    print()
    print("Narrative styles available:")
    for style in NarrativeStyle:
        print(f"  - {style.value}")
