"""
Modern Bubble Chart Animation Template

A story-driven, modular bubble chart animation using the primitives system.

Features:
- Story-driven narrative structure (intro, reveal, evolution, conclusion)
- X/Y axes with proper scaling and labels
- Size-encoded bubbles (area-proportional)
- Category coloring with legend
- Smooth transitions over time
- Auto-detected insights (leaders, big movers)
- Configurable narrative styles

Perfect for: Gapminder-style visualizations, economic data, population vs GDP,
             multi-dimensional time series

Usage:
    from agents.tools.templates.bubble_chart import generate_bubble_chart

    # Simple usage
    code = generate_bubble_chart(spec, csv_path, theme="youtube_dark")

    # With custom narrative style
    from agents.tools.templates import NarrativeStyle
    code = generate_bubble_chart(
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
# NUMBER FORMATTING
# =============================================================================

def format_number(value: float, precision: int = 1) -> str:
    """
    Format large numbers with K/M/B suffixes for readable axis labels.
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


def format_axis_value(value: float, decimals: int = 0) -> str:
    """Format axis value with appropriate precision"""
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{decimals}f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.{decimals}f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.{decimals}f}K"
    else:
        if decimals == 0:
            return f"{value:.0f}"
        return f"{value:.{decimals}f}"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class BubbleEntity:
    """Data for a single bubble entity across time"""
    name: str
    group: str
    data_by_time: Dict[str, Dict[str, float]]  # {time: {"x": val, "y": val, "r": val}}


@dataclass
class BubbleChartData:
    """Parsed and processed data for bubble chart animation"""
    times: List[str]
    entities: List[str]
    groups: List[str]
    entity_group: Dict[str, str]  # {entity_name: group_name}
    data: Dict[str, Dict[str, Dict[str, float]]]  # {time: {entity: {x, y, r}}}
    x_range: Tuple[float, float]
    y_range: Tuple[float, float]
    r_range: Tuple[float, float]
    group_colors: Dict[str, str]


@dataclass
class BubbleInsight:
    """An auto-detected insight from the data"""
    time: str
    entity: str
    insight_type: str  # "leader", "big_mover", "new_entry", "exit"
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


def _parse_time_key(token: str):
    """Parse time token for sorting"""
    try:
        return float(token)
    except ValueError:
        return token


def parse_csv_data(
    csv_path: str,
    x_col: str = "x",
    y_col: str = "y",
    r_col: str = "r",
    time_col: str = "time",
    entity_col: str = "entity",
    group_col: str = "group",
    colors: List[str] = None,
) -> BubbleChartData:
    """
    Parse CSV and prepare data for bubble chart animation.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    # Default vibrant color palette
    default_colors = [
        "#6366F1",  # Indigo
        "#EC4899",  # Pink
        "#22D3EE",  # Cyan
        "#10B981",  # Emerald
        "#F59E0B",  # Amber
        "#8B5CF6",  # Purple
        "#F97316",  # Orange
        "#14B8A6",  # Teal
        "#EF4444",  # Red
        "#84CC16",  # Lime
        "#06B6D4",  # Sky
        "#D946EF",  # Fuchsia
    ]
    colors = colors or default_colors

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Resolve column names with smart matching
        x_col = _resolve_column(headers, x_col, ["x", "gdp", "income", "gdp_per_capita", "wealth"])
        y_col = _resolve_column(headers, y_col, ["y", "life_expectancy", "lifeexp", "health", "score"])
        r_col = _resolve_column(headers, r_col, ["r", "size", "population", "pop", "radius", "count"])
        time_col = _resolve_column(headers, time_col, ["time", "year", "date", "period", "t"])
        entity_col = _resolve_column(headers, entity_col, ["entity", "name", "country", "region", "item", "label"])
        group_col = _resolve_column(headers, group_col, ["group", "category", "continent", "region", "type", "class"])

        # Collect data
        data_by_time: Dict[str, Dict[str, Dict[str, float]]] = {}
        entity_group_map: Dict[str, str] = {}
        all_entities: set = set()
        all_groups: set = set()

        # Track value ranges
        x_vals, y_vals, r_vals = [], [], []

        for row in reader:
            t = (row.get(time_col) or "").strip()
            entity = (row.get(entity_col) or "").strip()

            if not entity:
                continue

            # If no time column, use "1" as default (single snapshot)
            if not t:
                t = "1"

            # Parse numeric values
            try:
                x_val = float((row.get(x_col) or "0").strip().replace(",", ""))
                y_val = float((row.get(y_col) or "0").strip().replace(",", ""))
                r_val = float((row.get(r_col) or "1").strip().replace(",", ""))
            except ValueError:
                continue

            # Get group (use "ALL" if not specified)
            group = (row.get(group_col) or "ALL").strip()
            if not group:
                group = "ALL"

            # Store data
            if t not in data_by_time:
                data_by_time[t] = {}

            data_by_time[t][entity] = {"x": x_val, "y": y_val, "r": r_val}
            entity_group_map[entity] = group
            all_entities.add(entity)
            all_groups.add(group)

            x_vals.append(x_val)
            y_vals.append(y_val)
            r_vals.append(r_val)

    if not data_by_time or not x_vals:
        raise ValueError("No valid data found for bubble chart")

    # Sort times
    times = sorted(data_by_time.keys(), key=_parse_time_key)
    entities = sorted(all_entities)
    groups = sorted(all_groups)

    # Calculate value ranges with padding
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    r_min, r_max = min(r_vals), max(r_vals)

    # Add 10% padding to axes
    x_pad = (x_max - x_min) * 0.1 or 1.0
    y_pad = (y_max - y_min) * 0.1 or 1.0

    x_range = (x_min - x_pad, x_max + x_pad)
    y_range = (y_min - y_pad, y_max + y_pad)
    r_range = (max(r_min, 0.001), max(r_max, 0.001))

    # Assign colors to groups
    group_colors = {g: colors[i % len(colors)] for i, g in enumerate(groups)}

    return BubbleChartData(
        times=times,
        entities=entities,
        groups=groups,
        entity_group=entity_group_map,
        data=data_by_time,
        x_range=x_range,
        y_range=y_range,
        r_range=r_range,
        group_colors=group_colors,
    )


def detect_insights(data: BubbleChartData) -> List[BubbleInsight]:
    """
    Analyze data to detect interesting moments worth highlighting.

    Detects:
    - Leaders (largest bubble by r)
    - Big movers (large position changes)
    """
    insights = []
    prev_positions: Dict[str, Tuple[float, float]] = {}

    for t in data.times:
        time_data = data.data.get(t, {})

        # Find leader (largest r value)
        if time_data:
            leader = max(time_data.items(), key=lambda x: x[1].get("r", 0))
            leader_entity = leader[0]

            # Only add insight at first and last time
            if t == data.times[0] or t == data.times[-1]:
                insights.append(BubbleInsight(
                    time=t,
                    entity=leader_entity,
                    insight_type="leader",
                    description=f"{leader_entity} leads",
                    intensity=0.8,
                ))

        # Detect big movers
        for entity, vals in time_data.items():
            curr_pos = (vals["x"], vals["y"])

            if entity in prev_positions:
                prev_pos = prev_positions[entity]
                dx = curr_pos[0] - prev_pos[0]
                dy = curr_pos[1] - prev_pos[1]
                distance = math.sqrt(dx * dx + dy * dy)

                # Calculate relative movement
                x_range = data.x_range[1] - data.x_range[0]
                y_range = data.y_range[1] - data.y_range[0]
                max_range = max(x_range, y_range)

                if max_range > 0 and distance / max_range > 0.15:
                    insights.append(BubbleInsight(
                        time=t,
                        entity=entity,
                        insight_type="big_mover",
                        description=f"{entity} moves significantly",
                        intensity=0.7,
                    ))

            prev_positions[entity] = curr_pos

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


def generate_bubble_chart(
    spec: object,
    csv_path: str,
    theme: str = "youtube_dark",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    auto_highlights: bool = True,
) -> str:
    """
    Generate modern, story-driven bubble chart animation code.

    This is the main entry point for the bubble chart template. It uses the
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
    axes_config = getattr(spec, "axes", None)

    # Data binding columns
    x_col = getattr(data_binding, "x", None) or getattr(data_binding, "x_col", None) if data_binding else None
    y_col = getattr(data_binding, "y", None) or getattr(data_binding, "y_col", None) if data_binding else None
    r_col = getattr(data_binding, "r", None) or getattr(data_binding, "r_col", None) if data_binding else None
    time_col = getattr(data_binding, "time", None) or getattr(data_binding, "time_col", None) if data_binding else None
    entity_col = getattr(data_binding, "entity", None) or getattr(data_binding, "entity_col", None) if data_binding else None
    group_col = getattr(data_binding, "group", None) or getattr(data_binding, "group_col", None) if data_binding else None

    # Timing
    total_time = getattr(timing, "total_time", 25.0) if timing else 25.0
    creation_time = getattr(timing, "creation_time", 2.0) if timing else 2.0

    # Style options
    fill_opacity = getattr(style, "fill_opacity", 0.75) if style else 0.75
    show_labels = getattr(style, "show_labels", True) if style else True
    show_legend = getattr(style, "show_legend", True) if style else True
    custom_colors = getattr(style, "colors", None) if style else None
    color_map = getattr(style, "color_map", None) if style else None

    # Axis configuration
    x_label = getattr(axes_config, "x_label", None) if axes_config else None
    y_label = getattr(axes_config, "y_label", None) if axes_config else None
    x_decimals = getattr(axes_config, "x_decimals", 0) if axes_config else 0
    y_decimals = getattr(axes_config, "y_decimals", 0) if axes_config else 0

    # Parse data
    data = parse_csv_data(
        csv_path=csv_path,
        x_col=x_col or "x",
        y_col=y_col or "y",
        r_col=r_col or "r",
        time_col=time_col or "time",
        entity_col=entity_col or "entity",
        group_col=group_col or "group",
        colors=custom_colors,
    )

    # Detect insights for highlights
    insights = detect_insights(data) if auto_highlights else []

    # Apply any custom color map from spec
    if color_map:
        for group, color in color_map.items():
            if group in data.group_colors:
                data.group_colors[group] = color

    # Get theme colors
    theme_style = get_theme(theme) if get_theme else None

    if theme_style:
        bg_color = theme_style.palette.background
        text_color = theme_style.palette.text_primary
        text_secondary = theme_style.palette.text_secondary
        accent_color = theme_style.palette.accent
        surface_color = theme_style.palette.surface
    else:
        # Fallback colors (YouTube Dark theme)
        bg_color = "#0F0F1A"
        text_color = "#FFFFFF"
        text_secondary = "#A1A1AA"
        accent_color = "#22D3EE"
        surface_color = "#1A1A2E"

    # Get narrative pacing
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    # Format data literals
    lit_times = _format_literal(data.times)
    lit_entities = _format_literal(data.entities)
    lit_groups = _format_literal(data.groups)
    lit_entity_group = _format_literal(data.entity_group)
    lit_data = _format_literal(data.data)
    lit_group_colors = _format_literal(data.group_colors)

    # Format insights
    lit_insights = _format_literal([
        {"time": i.time, "entity": i.entity, "type": i.insight_type, "desc": i.description}
        for i in insights
    ])

    # Calculate timing
    intro_duration = pacing["intro_duration"] if include_intro else 0
    outro_duration = pacing["outro_duration"] if include_conclusion else 0
    reveal_duration = creation_time

    evolution_duration = total_time - intro_duration - outro_duration - reveal_duration
    evolution_duration = max(5.0, evolution_duration)

    num_steps = max(1, len(data.times) - 1)
    per_step_time = evolution_duration / num_steps if num_steps > 0 else 1.0

    # Axis ranges
    x_min, x_max = data.x_range
    y_min, y_max = data.y_range
    r_min, r_max = data.r_range

    # Calculate nice axis steps
    def nice_step(range_val: float, target_steps: int = 5) -> float:
        raw_step = range_val / target_steps
        magnitude = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
        nice_steps = [1, 2, 2.5, 5, 10]
        normalized = raw_step / magnitude
        for ns in nice_steps:
            if normalized <= ns:
                return ns * magnitude
        return 10 * magnitude

    x_step = nice_step(x_max - x_min)
    y_step = nice_step(y_max - y_min)

    # Build the story title
    title = getattr(spec, "title", None) or "Bubble Chart"
    subtitle = getattr(spec, "subtitle", None) or f"{data.times[0]} - {data.times[-1]}" if len(data.times) > 1 else ""

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# BUBBLE CHART ANIMATION - Story-Driven Architecture
# =============================================================================
# Generated using the primitives system for modular, narrative animations
# Theme: {theme}
# Narrative Style: {narrative_style.value}
# =============================================================================

# --- Data ---
TIMES = {lit_times}
ENTITIES = {lit_entities}
GROUPS = {lit_groups}
ENTITY_GROUP = {lit_entity_group}
DATA = {lit_data}
GROUP_COLORS = {lit_group_colors}

# --- Insights (Auto-Detected) ---
INSIGHTS = {lit_insights}

# --- Story Configuration ---
STORY_TITLE = "{title}"
STORY_SUBTITLE = "{subtitle}"
INCLUDE_INTRO = {include_intro}
INCLUDE_CONCLUSION = {include_conclusion}

# --- Timing (Narrative Style: {narrative_style.value}) ---
INTRO_DURATION = {intro_duration}
REVEAL_DURATION = {reveal_duration}
EVOLUTION_DURATION = {evolution_duration}
OUTRO_DURATION = {outro_duration}
PER_STEP_TIME = {per_step_time}
TOTAL_DURATION = {total_time}

# --- Axis Configuration ---
X_MIN, X_MAX = {x_min}, {x_max}
Y_MIN, Y_MAX = {y_min}, {y_max}
X_STEP = {x_step}
Y_STEP = {y_step}
X_LABEL = "{x_label or 'X Axis'}"
Y_LABEL = "{y_label or 'Y Axis'}"
X_DECIMALS = {x_decimals}
Y_DECIMALS = {y_decimals}

# --- Radius Configuration ---
R_MIN, R_MAX = {r_min}, {r_max}
RADIUS_MIN = 0.08
RADIUS_MAX = 0.65

# --- Style Configuration ---
BG_COLOR = "{bg_color}"
TEXT_COLOR = "{text_color}"
TEXT_SECONDARY = "{text_secondary}"
ACCENT_COLOR = "{accent_color}"
SURFACE_COLOR = "{surface_color}"
FILL_OPACITY = {fill_opacity}
SHOW_LABELS = {show_labels}
SHOW_LEGEND = {show_legend}

# --- Layout Constants ---
CHART_WIDTH = 10.0
CHART_HEIGHT = 6.0


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def compute_radius(r_value: float) -> float:
    """Convert data value to visual radius using sqrt scaling (area-proportional)."""
    r_min_safe = max(R_MIN, 1e-9)
    r_max_safe = max(R_MAX, r_min_safe + 1e-9)

    sqrt_val = math.sqrt(max(r_value, 0))
    sqrt_min = math.sqrt(r_min_safe)
    sqrt_max = math.sqrt(r_max_safe)

    if sqrt_max <= sqrt_min:
        return 0.5 * (RADIUS_MIN + RADIUS_MAX)

    t = (sqrt_val - sqrt_min) / (sqrt_max - sqrt_min)
    t = max(0.0, min(1.0, t))

    return RADIUS_MIN + t * (RADIUS_MAX - RADIUS_MIN)


def format_axis_number(value: float, decimals: int = 0) -> str:
    """Format large numbers with K/M/B suffixes"""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1_000_000_000:
        return f"{{sign}}{{abs_val / 1_000_000_000:.{{decimals}}f}}B"
    elif abs_val >= 1_000_000:
        return f"{{sign}}{{abs_val / 1_000_000:.{{decimals}}f}}M"
    elif abs_val >= 1_000:
        return f"{{sign}}{{abs_val / 1_000:.{{decimals}}f}}K"
    else:
        if decimals == 0 and abs_val == int(abs_val):
            return f"{{sign}}{{int(abs_val)}}"
        return f"{{sign}}{{abs_val:.{{decimals}}f}}"


def get_entity_color(entity: str) -> str:
    """Get color for entity based on its group"""
    group = ENTITY_GROUP.get(entity, "ALL")
    return GROUP_COLORS.get(group, "#6366F1")


def get_insight_at_time(time_key: str):
    """Get insight at a specific time, if any"""
    for insight in INSIGHTS:
        if insight["time"] == time_key:
            return insight
    return None


# =============================================================================
# SCENE CLASS
# =============================================================================

class GenScene(Scene):
    """
    Story-driven bubble chart animation.

    Structure:
    1. INTRO: Title and subtitle fade in
    2. REVEAL: Axes and bubbles appear
    3. EVOLUTION: Bubbles animate through time
    4. HIGHLIGHTS: Insights emphasized during evolution
    5. CONCLUSION: Final state with leader emphasis
    """

    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        if not TIMES or not ENTITIES:
            no_data = Text("No data available", color=TEXT_COLOR, font_size=36)
            self.play(Write(no_data))
            return

        # Track elements
        self.axes = None
        self.bubbles = {{}}
        self.time_display = None
        self.legend = None

        # Run story scenes
        if INCLUDE_INTRO:
            self.scene_intro()

        self.scene_reveal()
        self.scene_evolution()

        if INCLUDE_CONCLUSION:
            self.scene_conclusion()

    # -------------------------------------------------------------------------
    # SCENE 1: INTRO
    # -------------------------------------------------------------------------
    def scene_intro(self):
        """Opening scene with title and subtitle."""
        title = Text(
            STORY_TITLE,
            font_size=56,
            color=TEXT_COLOR,
            weight=BOLD,
        )
        title.move_to([0, 0.5, 0])

        subtitle = Text(
            STORY_SUBTITLE,
            font_size=28,
            color=TEXT_SECONDARY,
        )
        subtitle.move_to([0, -0.3, 0])
        subtitle.set_opacity(0.8)

        title_group = VGroup(title, subtitle)

        self.play(
            FadeIn(title, shift=UP * 0.3),
            run_time=0.8,
            rate_func=smooth,
        )
        self.play(
            FadeIn(subtitle, shift=UP * 0.2),
            run_time=0.5,
            rate_func=smooth,
        )

        self.wait(INTRO_DURATION - 1.8)

        self.play(
            FadeOut(title_group, shift=UP * 0.5),
            run_time=0.5,
        )

    # -------------------------------------------------------------------------
    # SCENE 2: REVEAL
    # -------------------------------------------------------------------------
    def scene_reveal(self):
        """Reveal axes, legend, and initial bubbles."""
        # Create Axes
        self.axes = Axes(
            x_range=[X_MIN, X_MAX, X_STEP],
            y_range=[Y_MIN, Y_MAX, Y_STEP],
            x_length=CHART_WIDTH,
            y_length=CHART_HEIGHT,
            axis_config={{
                "color": TEXT_SECONDARY,
                "stroke_width": 2,
                "include_ticks": True,
                "tick_size": 0.1,
            }},
            x_axis_config={{"include_numbers": False}},
            y_axis_config={{"include_numbers": False}},
            tips=False,
        )
        self.axes.to_edge(DOWN, buff=1.2)
        self.axes.shift(LEFT * 0.8)

        # Custom X-axis labels
        x_labels = VGroup()
        x_tick_vals = [X_MIN + i * X_STEP for i in range(int((X_MAX - X_MIN) / X_STEP) + 1)]
        for val in x_tick_vals:
            if val > X_MAX:
                break
            label = Text(
                format_axis_number(val, X_DECIMALS),
                font_size=14,
                color=TEXT_SECONDARY,
            )
            x_pos = self.axes.c2p(val, Y_MIN)[0]
            label.move_to([x_pos, self.axes.c2p(X_MIN, Y_MIN)[1] - 0.35, 0])
            x_labels.add(label)

        # Custom Y-axis labels
        y_labels = VGroup()
        y_tick_vals = [Y_MIN + i * Y_STEP for i in range(int((Y_MAX - Y_MIN) / Y_STEP) + 1)]
        for val in y_tick_vals:
            if val > Y_MAX:
                break
            label = Text(
                format_axis_number(val, Y_DECIMALS),
                font_size=14,
                color=TEXT_SECONDARY,
            )
            y_pos = self.axes.c2p(X_MIN, val)[1]
            label.move_to([self.axes.c2p(X_MIN, Y_MIN)[0] - 0.5, y_pos, 0])
            y_labels.add(label)

        # Axis labels
        x_axis_label = Text(X_LABEL, font_size=22, color=TEXT_SECONDARY)
        x_axis_label.next_to(self.axes.x_axis, DOWN, buff=0.8)

        y_axis_label = Text(Y_LABEL, font_size=22, color=TEXT_SECONDARY)
        y_axis_label.rotate(90 * DEGREES)
        y_axis_label.next_to(self.axes.y_axis, LEFT, buff=0.9)

        # Time Display
        self.time_display = Text(
            str(TIMES[0]),
            font_size=72,
            weight=BOLD,
            color=ACCENT_COLOR,
        )
        self.time_display.to_corner(UR, buff=0.8)
        self.time_display.set_opacity(0.85)

        # Legend
        if SHOW_LEGEND and len(GROUPS) > 1:
            legend_items = VGroup()
            for group in GROUPS:
                color = GROUP_COLORS.get(group, "#6366F1")
                swatch = Circle(radius=0.12, fill_color=color, fill_opacity=0.9, stroke_width=0)
                group_label = Text(str(group), font_size=16, color=TEXT_COLOR)
                group_label.next_to(swatch, RIGHT, buff=0.15)
                item = VGroup(swatch, group_label)
                legend_items.add(item)

            legend_items.arrange(DOWN, aligned_edge=LEFT, buff=0.2)

            legend_bg = RoundedRectangle(
                corner_radius=0.15,
                width=legend_items.get_width() + 0.5,
                height=legend_items.get_height() + 0.4,
                fill_color=SURFACE_COLOR,
                fill_opacity=0.8,
                stroke_width=1,
                stroke_color=TEXT_SECONDARY,
                stroke_opacity=0.3,
            )

            self.legend = VGroup(legend_bg, legend_items)
            legend_items.move_to(legend_bg.get_center())
            self.legend.to_corner(UL, buff=0.5)

        # Create Bubbles
        t0 = TIMES[0]
        for entity in ENTITIES:
            entity_data = DATA.get(t0, {{}}).get(entity)

            if entity_data:
                x_val = entity_data["x"]
                y_val = entity_data["y"]
                r_val = entity_data["r"]
            else:
                x_val = (X_MIN + X_MAX) / 2
                y_val = (Y_MIN + Y_MAX) / 2
                r_val = R_MIN

            pos = self.axes.c2p(x_val, y_val)
            radius = compute_radius(r_val)
            color = get_entity_color(entity)

            bubble = Circle(
                radius=radius,
                fill_color=color,
                fill_opacity=FILL_OPACITY,
                stroke_color=color,
                stroke_width=2,
                stroke_opacity=0.9,
            )
            bubble.move_to(pos)

            entity_label = None
            if SHOW_LABELS:
                display_name = entity[:12] + "..." if len(entity) > 15 else entity
                entity_label = Text(display_name, font_size=11, color=WHITE, weight=BOLD)
                entity_label.move_to(bubble.get_center())
                if radius < 0.2:
                    entity_label.set_opacity(0)

            self.bubbles[entity] = {{
                "circle": bubble,
                "label": entity_label,
                "current_pos": pos,
                "current_radius": radius,
            }}

        # Animate reveal
        self.play(
            Create(self.axes),
            FadeIn(x_labels),
            FadeIn(y_labels),
            FadeIn(x_axis_label),
            FadeIn(y_axis_label),
            run_time=REVEAL_DURATION * 0.4,
        )

        if self.legend:
            self.play(FadeIn(self.legend), run_time=0.3)

        self.play(FadeIn(self.time_display), run_time=0.3)

        # Bubbles appear
        bubble_circles = [self.bubbles[e]["circle"] for e in ENTITIES]
        bubble_labels = [self.bubbles[e]["label"] for e in ENTITIES if self.bubbles[e]["label"]]

        self.play(
            LaggedStart(
                *[GrowFromCenter(b) for b in bubble_circles],
                lag_ratio=0.02,
            ),
            run_time=REVEAL_DURATION * 0.6,
        )

        if bubble_labels:
            self.add(*bubble_labels)

        self.wait(0.3)

    # -------------------------------------------------------------------------
    # SCENE 3: EVOLUTION
    # -------------------------------------------------------------------------
    def scene_evolution(self):
        """Main animation: evolve through time."""
        for step_idx in range(1, len(TIMES)):
            t_current = TIMES[step_idx]
            insight = get_insight_at_time(t_current)

            animations = []

            # Update time display
            new_time_display = Text(
                str(t_current),
                font_size=72,
                weight=BOLD,
                color=ACCENT_COLOR,
            )
            new_time_display.to_corner(UR, buff=0.8)
            new_time_display.set_opacity(0.85)
            animations.append(Transform(self.time_display, new_time_display))

            # Update each bubble
            for entity in ENTITIES:
                entity_data = DATA.get(t_current, {{}}).get(entity)

                if not entity_data:
                    continue

                x_val = entity_data["x"]
                y_val = entity_data["y"]
                r_val = entity_data["r"]

                new_pos = self.axes.c2p(x_val, y_val)
                new_radius = compute_radius(r_val)
                color = get_entity_color(entity)

                bubble_data = self.bubbles[entity]
                circle = bubble_data["circle"]
                label = bubble_data["label"]

                new_circle = Circle(
                    radius=new_radius,
                    fill_color=color,
                    fill_opacity=FILL_OPACITY,
                    stroke_color=color,
                    stroke_width=2,
                    stroke_opacity=0.9,
                )
                new_circle.move_to(new_pos)
                animations.append(Transform(circle, new_circle))

                if label:
                    new_label = label.copy()
                    new_label.move_to(new_pos)
                    if new_radius < 0.2:
                        new_label.set_opacity(0)
                    else:
                        new_label.set_opacity(1)
                    animations.append(Transform(label, new_label))

                bubble_data["current_pos"] = new_pos
                bubble_data["current_radius"] = new_radius

            self.play(
                *animations,
                run_time=PER_STEP_TIME,
                rate_func=smooth,
            )

            # Show insight if any
            if insight:
                self.show_insight(insight)

    def show_insight(self, insight):
        """Show a highlight annotation for an insight."""
        entity = insight["entity"]
        if entity not in self.bubbles:
            return

        bubble_data = self.bubbles[entity]
        circle = bubble_data["circle"]

        # Highlight the bubble
        self.play(
            circle.animate.set_stroke(color=ACCENT_COLOR, width=4),
            run_time=0.3,
        )

        self.wait(0.2)

        self.play(
            circle.animate.set_stroke(color=get_entity_color(entity), width=2),
            run_time=0.3,
        )

    # -------------------------------------------------------------------------
    # SCENE 4: CONCLUSION
    # -------------------------------------------------------------------------
    def scene_conclusion(self):
        """Closing scene with leader emphasis."""
        # Find the leader (largest bubble)
        final_time = TIMES[-1]
        final_data = DATA.get(final_time, {{}})

        leader = None
        max_r = -1
        for entity, vals in final_data.items():
            if vals["r"] > max_r:
                max_r = vals["r"]
                leader = entity

        if leader and leader in self.bubbles:
            leader_circle = self.bubbles[leader]["circle"]

            # Dim other bubbles
            dim_anims = []
            for entity, bubble_data in self.bubbles.items():
                if entity != leader:
                    dim_anims.append(bubble_data["circle"].animate.set_opacity(0.3))
                    if bubble_data["label"]:
                        dim_anims.append(bubble_data["label"].animate.set_opacity(0.1))

            if dim_anims:
                self.play(*dim_anims, run_time=0.5)

            # Emphasize leader
            self.play(
                leader_circle.animate.set_stroke(color=ACCENT_COLOR, width=5),
                run_time=0.4,
            )

            # Show leader annotation
            leader_label = Text(
                f"Leader: {{leader}}",
                font_size=28,
                color=ACCENT_COLOR,
                weight=BOLD,
            )
            leader_label.to_edge(UP, buff=0.5)

            self.play(
                FadeIn(leader_label, shift=DOWN * 0.3),
                run_time=0.4,
            )

        # Final hold
        self.wait(OUTRO_DURATION - 1.0)
'''

    return code.strip()


# Alias for backward compatibility
generate_bubble_code = generate_bubble_chart


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_bubble_chart_story_config(
    title: str,
    subtitle: Optional[str] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    evolution_duration: float = 20.0,
    theme: str = "youtube_dark",
) -> StoryConfig:
    """
    Create a story configuration for bubble chart animations.

    Args:
        title: Story title
        subtitle: Optional subtitle
        narrative_style: Pacing preset
        evolution_duration: Duration of main evolution animation
        theme: Visual theme

    Returns:
        StoryConfig ready for use with generate_bubble_chart
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
        total_duration=evolution_duration + pacing["intro_duration"] + pacing["outro_duration"],
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

    print("\nBubble Chart Template Module Loaded Successfully")
    print("Available functions:")
    print("  - generate_bubble_chart(spec, csv_path, theme, ...)")
    print("  - create_bubble_chart_story_config(title, subtitle, ...)")
    print("  - parse_csv_data(csv_path, ...)")
    print("  - detect_insights(data)")
    print()
    print("Narrative styles available:")
    for style in NarrativeStyle:
        print(f"  - {style.value}")
