"""
Modern Line Evolution Animation Template

A story-driven, modular line chart animation using the primitives system.

Features:
- Story-driven narrative structure (intro, reveal, draw, conclusion)
- Smooth line drawing animation with tracking dot
- Glowing tracking dot effect
- Animated value counter
- Auto-detected insights (peaks, valleys, milestones)
- Modern color palette with area fill
- Configurable narrative styles

Perfect for: Stock prices, temperatures, trends over time, single-variable time series

Usage:
    from agents.tools.templates.line_evolution import generate_line_evolution

    # Simple usage
    code = generate_line_evolution(spec, csv_path, theme="youtube_dark")

    # With custom narrative style
    from agents.tools.templates import NarrativeStyle
    code = generate_line_evolution(
        spec, csv_path,
        theme="youtube_dark",
        narrative_style=NarrativeStyle.CINEMATIC,
        include_intro=True,
        include_conclusion=True,
    )
"""

from __future__ import annotations

import csv
import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from agents.tools.templates.csv_utils import read_csv_rows,  detect_header_row

# Setup module logger
logger = logging.getLogger("animation_pipeline.templates.line_evolution")

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
class LineEvolutionData:
    """Parsed and processed data for line evolution animation"""
    times: List[str]
    values: List[float]
    min_value: float
    max_value: float
    y_min: float  # Padded for visual space
    y_max: float  # Padded for visual space


@dataclass
class LineInsight:
    """An auto-detected insight from the data"""
    index: int
    time: str
    value: float
    insight_type: str  # "peak", "valley", "milestone", "big_change"
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
    value_col: str = "value",
    time_col: str = "time",
) -> LineEvolutionData:
    """
    Parse CSV and prepare data for line evolution animation.

    Args:
        csv_path: Path to CSV file
        value_col: Column name for values
        time_col: Column name for time periods

    Returns:
        LineEvolutionData with processed animation data
    """
    logger.info(f"[LINE_EVOLUTION] parse_csv_data started | csv_path={csv_path} | value_col={value_col} | time_col={time_col}")

    if not os.path.exists(csv_path):
        logger.error(f"[LINE_EVOLUTION] Dataset not found: {csv_path}")
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    headers, rows = read_csv_rows(csv_path)
    logger.info(f"[LINE_EVOLUTION] csv headers detected: {headers}")

    resolved_time_col = _resolve_column(
        headers, time_col,
        ["time", "date", "year", "month", "day", "period", "t", "timestamp"]
    )

    resolved_value_col = _resolve_column(
        headers, value_col,
        ["value", "close", "price", "amount", "total", "count", "score", "y"]
    )

    logger.info(f"[LINE_EVOLUTION] Column resolution | requested_time={time_col} -> resolved_time={resolved_time_col} | requested_value={value_col} -> resolved_value={resolved_value_col}")

    time_col = resolved_time_col
    value_col = resolved_value_col

    raw_data: List[Tuple[str, float]] = []
    skipped_rows = 0

    for row in rows:
        t = (row.get(time_col) or "").strip()
        v_str = (row.get(value_col) or "").strip()

        if not t or not v_str:
            skipped_rows += 1
            continue

        try:
            v = float(v_str.replace(",", ""))
            raw_data.append((t, v))
        except ValueError:
            skipped_rows += 1
            continue

    logger.info(f"[LINE_EVOLUTION] Data collection complete | valid_rows={len(raw_data)} | skipped_rows={skipped_rows}")


def detect_insights(data: LineEvolutionData) -> List[LineInsight]:
    """
    Analyze data to detect interesting moments worth highlighting.

    Detects:
    - Peaks (local maxima)
    - Valleys (local minima)
    - Big changes (significant jumps)
    - Global max/min

    Args:
        data: Parsed line evolution data

    Returns:
        List of insights sorted by index
    """
    insights = []
    values = data.values
    times = data.times
    n = len(values)

    if n < 3:
        return insights

    # Find global max and min
    max_idx = values.index(max(values))
    min_idx = values.index(min(values))

    insights.append(LineInsight(
        index=max_idx,
        time=times[max_idx],
        value=values[max_idx],
        insight_type="peak",
        description=f"Peak: {values[max_idx]:.1f}",
        intensity=0.9,
    ))

    if min_idx != max_idx:
        insights.append(LineInsight(
            index=min_idx,
            time=times[min_idx],
            value=values[min_idx],
            insight_type="valley",
            description=f"Low: {values[min_idx]:.1f}",
            intensity=0.7,
        ))

    # Find big changes (more than 20% of range in one step)
    value_range = data.max_value - data.min_value
    threshold = value_range * 0.2

    for i in range(1, n):
        change = abs(values[i] - values[i - 1])
        if change >= threshold:
            direction = "surge" if values[i] > values[i - 1] else "drop"
            insights.append(LineInsight(
                index=i,
                time=times[i],
                value=values[i],
                insight_type="big_change",
                description=f"Big {direction}!",
                intensity=0.8,
            ))

    # Sort by index and remove duplicates
    seen_indices = set()
    unique_insights = []
    for insight in sorted(insights, key=lambda x: x.index):
        if insight.index not in seen_indices:
            seen_indices.add(insight.index)
            unique_insights.append(insight)

    return unique_insights


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


def generate_line_evolution(
    spec: object,
    csv_path: str,
    theme: str = "youtube_dark",
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    auto_highlights: bool = True,
    time_col: Optional[str] = None,
    value_col: Optional[str] = None,
    group_col: Optional[str] = None,
) -> str:
    """
    Generate modern, story-driven line evolution animation code.

    This is the main entry point for the line evolution template. It uses the
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
    logger.info(f"[LINE_EVOLUTION] ========== GENERATE LINE EVOLUTION STARTED ==========")
    logger.info(f"[LINE_EVOLUTION] Input parameters | csv_path={csv_path} | theme={theme} | narrative_style={narrative_style}")
    logger.info(f"[LINE_EVOLUTION] Column overrides | time_col={time_col} | value_col={value_col} | group_col={group_col}")

    # Extract configuration from spec
    data_binding = getattr(spec, "data_binding", None)
    timing = getattr(spec, "timing", None)
    style = getattr(spec, "style", None)
    axes_config = getattr(spec, "axes", None)

    logger.debug(f"[LINE_EVOLUTION] Spec extraction | has_data_binding={data_binding is not None} | has_timing={timing is not None} | has_style={style is not None} | has_axes={axes_config is not None}")

    # Use provided columns or fall back to spec data_binding
    _value_col = value_col or (getattr(data_binding, "value_col", None) if data_binding else None)
    _time_col = time_col or (getattr(data_binding, "time_col", None) if data_binding else None)
    _group_col = group_col or (getattr(data_binding, "group_col", None) if data_binding else None)

    logger.info(f"[LINE_EVOLUTION] Resolved columns | time_col={_time_col} | value_col={_value_col} | group_col={_group_col}")

    total_time = getattr(timing, "total_time", 12.0) if timing else 12.0

    # Axis labels
    x_label = getattr(axes_config, "x_label", None) if axes_config else None
    y_label = getattr(axes_config, "y_label", None) if axes_config else None

    logger.debug(f"[LINE_EVOLUTION] Axis labels | x_label={x_label} | y_label={y_label} | total_time={total_time}")

    # Parse data
    logger.info(f"[LINE_EVOLUTION] Starting CSV data parsing...")
    try:
        data = parse_csv_data(
            csv_path=csv_path,
            value_col=_value_col or "value",
            time_col=_time_col or "time",
        )
        logger.info(f"[LINE_EVOLUTION] CSV parsing successful | data_points={len(data.values)} | time_range={data.times[0] if data.times else 'N/A'} to {data.times[-1] if data.times else 'N/A'} | value_range={data.min_value:.2f} to {data.max_value:.2f}")
    except Exception as e:
        logger.error(f"[LINE_EVOLUTION] CSV parsing FAILED | error={str(e)} | error_type={type(e).__name__}")
        raise

    # Detect insights for highlights
    insights = detect_insights(data) if auto_highlights else []

    # Get theme colors
    theme_style = get_theme(theme) if get_theme else None

    if theme_style:
        bg_color = theme_style.palette.background
        text_color = theme_style.palette.text_primary
        text_secondary = theme_style.palette.text_secondary
        primary_color = theme_style.palette.primary
        accent_color = theme_style.palette.accent
        surface_color = theme_style.palette.surface
    else:
        # Fallback colors (YouTube Dark / Neon theme)
        bg_color = "#0F0F1A"
        text_color = "#FFFFFF"
        text_secondary = "#A1A1AA"
        primary_color = "#22D3EE"  # Cyan
        accent_color = "#6366F1"   # Indigo
        surface_color = "#1A1A2E"

    # Get narrative pacing
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    # Format data literals
    lit_times = _format_literal(data.times)
    lit_values = _format_literal(data.values)

    # Format insights for highlights
    lit_insights = _format_literal([
        {"index": i.index, "time": i.time, "value": i.value, "type": i.insight_type, "desc": i.description}
        for i in insights
    ])

    # Calculate number of x-axis labels to show
    num_points = len(data.times)
    if num_points <= 5:
        label_indices = list(range(num_points))
    elif num_points <= 10:
        label_indices = [0, num_points // 2, num_points - 1]
    else:
        step = (num_points - 1) // 4
        label_indices = [0, step, step * 2, step * 3, num_points - 1]

    lit_label_indices = _format_literal(label_indices)

    # Calculate timing
    intro_duration = pacing["intro_duration"] if include_intro else 0
    outro_duration = pacing["outro_duration"] if include_conclusion else 0
    reveal_duration = 1.0

    draw_duration = total_time - intro_duration - outro_duration - reveal_duration
    draw_duration = max(3.0, draw_duration)

    # Build the story title
    title = getattr(spec, "title", None) or "Data Evolution"
    subtitle = getattr(spec, "subtitle", None) or f"{data.times[0]} - {data.times[-1]}"

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# LINE EVOLUTION ANIMATION - Story-Driven Architecture
# =============================================================================
# Generated using the primitives system for modular, narrative animations
# Theme: {theme}
# Narrative Style: {narrative_style.value}
# =============================================================================

# --- Data ---
TIMES = {lit_times}
VALUES = {lit_values}
Y_MIN = {data.y_min}
Y_MAX = {data.y_max}
VALUE_MIN = {data.min_value}
VALUE_MAX = {data.max_value}
NUM_POINTS = {num_points}
LABEL_INDICES = {lit_label_indices}

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
DRAW_DURATION = {draw_duration}
OUTRO_DURATION = {outro_duration}
TOTAL_DURATION = {total_time}

# --- Style Configuration ---
BG_COLOR = "{bg_color}"
TEXT_COLOR = "{text_color}"
TEXT_SECONDARY = "{text_secondary}"
LINE_COLOR = "{primary_color}"
ACCENT_COLOR = "{accent_color}"
AREA_COLOR = "{primary_color}"
SURFACE_COLOR = "{surface_color}"

# --- Layout Constants ---
AXES_WIDTH = 10.0
AXES_HEIGHT = 5.5
DOT_RADIUS = 0.12
GLOW_RADIUS = 0.25
GLOW_OPACITY = 0.4


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_value(value: float) -> str:
    """Format numbers with appropriate precision"""
    if abs(value) >= 1_000_000_000:
        return f"{{value / 1_000_000_000:.1f}}B"
    elif abs(value) >= 1_000_000:
        return f"{{value / 1_000_000:.1f}}M"
    elif abs(value) >= 1_000:
        return f"{{value / 1_000:.1f}}K"
    elif abs(value) >= 100:
        return f"{{value:.0f}}"
    elif abs(value) >= 1:
        return f"{{value:.1f}}"
    else:
        return f"{{value:.2f}}"


def get_insight_at_index(index: int):
    """Get insight at a specific data index, if any"""
    for insight in INSIGHTS:
        if insight["index"] == index:
            return insight
    return None


# =============================================================================
# SCENE CLASS
# =============================================================================

class GenScene(Scene):
    """
    Story-driven line evolution animation.

    Structure:
    1. INTRO: Title and subtitle fade in
    2. REVEAL: Axes and labels appear
    3. DRAW: Line draws with tracking dot
    4. HIGHLIGHTS: Insights emphasized during draw
    5. CONCLUSION: Final value emphasis and summary
    """

    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        # Track elements
        self.axes = None
        self.line_path = None
        self.dot = None
        self.glow = None
        self.value_label = None
        self.tracker = None

        # Run story scenes
        if INCLUDE_INTRO:
            self.scene_intro()

        self.scene_reveal()
        self.scene_draw()

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
        subtitle = Text(
            STORY_SUBTITLE,
            font_size=28,
            color=TEXT_SECONDARY,
        )
        subtitle.move_to([0, -0.3, 0])
        subtitle.set_opacity(0.8)

        title_group = VGroup(title, subtitle)

        # Animate entrance
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
        """Reveal axes and prepare for drawing."""
        # Create Axes
        x_range_max = NUM_POINTS - 1
        x_step = max(1, x_range_max // 5)
        y_step = (Y_MAX - Y_MIN) / 5

        self.axes = Axes(
            x_range=[0, x_range_max, x_step],
            y_range=[Y_MIN, Y_MAX, y_step],
            x_length=AXES_WIDTH,
            y_length=AXES_HEIGHT,
            axis_config={{
                "color": TEXT_SECONDARY,
                "stroke_width": 2,
                "include_ticks": True,
                "tick_size": 0.1,
            }},
            x_axis_config={{
                "include_numbers": False,
            }},
            y_axis_config={{
                "include_numbers": True,
                "font_size": 18,
                "decimal_number_config": {{"num_decimal_places": 0}},
            }},
            tips=False,
        )
        self.axes.to_edge(LEFT, buff=1.2)
        self.axes.shift(DOWN * 0.3)

        # Custom X-Axis Labels
        x_labels = VGroup()
        for i in LABEL_INDICES:
            if i < NUM_POINTS:
                label = Text(
                    str(TIMES[i]),
                    font_size=16,
                    color=TEXT_SECONDARY,
                )
                label.next_to(self.axes.c2p(i, Y_MIN), DOWN, buff=0.3)
                x_labels.add(label)

        # Axis Labels
        y_axis_label = Text(
            "{y_label or 'Value'}",
            font_size=20,
            color=TEXT_SECONDARY,
        )
        y_axis_label.rotate(90 * DEGREES)
        y_axis_label.next_to(self.axes.y_axis, LEFT, buff=0.6)

        x_axis_label = Text(
            "{x_label or 'Time'}",
            font_size=20,
            color=TEXT_SECONDARY,
        )
        x_axis_label.next_to(self.axes.x_axis, DOWN, buff=0.8)

        # Animate reveal
        self.play(
            Create(self.axes, lag_ratio=0.1),
            run_time=REVEAL_DURATION * 0.6,
        )
        self.play(
            FadeIn(x_labels),
            FadeIn(y_axis_label),
            FadeIn(x_axis_label),
            run_time=REVEAL_DURATION * 0.4,
        )

        self.wait(0.2)

    # -------------------------------------------------------------------------
    # SCENE 3: DRAW
    # -------------------------------------------------------------------------
    def scene_draw(self):
        """Main animation: draw line with tracking dot."""
        # Create the Line Path
        line_points = [self.axes.c2p(i, val) for i, val in enumerate(VALUES)]

        self.line_path = VMobject()
        self.line_path.set_points_smoothly(line_points)
        self.line_path.set_color(LINE_COLOR)
        self.line_path.set_stroke(width=4)

        # Area Under Curve
        area_points = line_points.copy()
        area_points.append(self.axes.c2p(NUM_POINTS - 1, Y_MIN))
        area_points.append(self.axes.c2p(0, Y_MIN))

        area = Polygon(*area_points)
        area.set_stroke(width=0)
        area.set_fill(AREA_COLOR, opacity=0.15)

        # Glowing Tracking Dot
        initial_point = self.axes.c2p(0, VALUES[0])

        self.glow = Dot(
            point=initial_point,
            radius=GLOW_RADIUS,
            color=LINE_COLOR,
        )
        self.glow.set_opacity(GLOW_OPACITY)

        self.dot = Dot(
            point=initial_point,
            radius=DOT_RADIUS,
            color=WHITE,
        )

        # Value Label
        self.value_label = Text(
            format_value(VALUES[0]),
            font_size=24,
            color=TEXT_COLOR,
            weight=BOLD,
        )
        self.value_label.add_background_rectangle(
            color=SURFACE_COLOR,
            opacity=0.9,
            buff=0.15,
        )
        self.value_label.next_to(self.dot, UP, buff=0.3)

        # Progress Tracker
        self.tracker = ValueTracker(0)

        # Updaters
        def update_dot(mob):
            t = self.tracker.get_value()
            if NUM_POINTS <= 1:
                return
            proportion = t / (NUM_POINTS - 1)
            proportion = min(max(proportion, 0), 1)
            point = self.line_path.point_from_proportion(proportion)
            mob.move_to(point)

        def update_glow(mob):
            mob.move_to(self.dot.get_center())

        def update_value_label(mob):
            t = self.tracker.get_value()
            idx = int(round(t))
            idx = min(max(idx, 0), NUM_POINTS - 1)

            new_text = Text(
                format_value(VALUES[idx]),
                font_size=24,
                color=TEXT_COLOR,
                weight=BOLD,
            )
            new_text.add_background_rectangle(
                color=SURFACE_COLOR,
                opacity=0.9,
                buff=0.15,
            )
            new_text.next_to(self.dot, UP, buff=0.3)

            # Keep label on screen
            if new_text.get_right()[0] > 6:
                new_text.next_to(self.dot, LEFT, buff=0.3)
            elif new_text.get_left()[0] < -6:
                new_text.next_to(self.dot, RIGHT, buff=0.3)

            mob.become(new_text)

        self.dot.add_updater(update_dot)
        self.glow.add_updater(update_glow)
        self.value_label.add_updater(update_value_label)

        # Fade in tracking elements
        self.play(
            FadeIn(self.dot),
            FadeIn(self.glow),
            FadeIn(self.value_label),
            run_time=0.5,
        )

        # Main Animation: Draw Line + Move Tracker
        self.play(
            Create(self.line_path, rate_func=linear),
            FadeIn(area, rate_func=linear),
            self.tracker.animate.set_value(NUM_POINTS - 1),
            run_time=DRAW_DURATION,
            rate_func=linear,
        )

        # Remove updaters
        self.dot.clear_updaters()
        self.glow.clear_updaters()
        self.value_label.clear_updaters()

        self.wait(0.3)

    # -------------------------------------------------------------------------
    # SCENE 4: CONCLUSION
    # -------------------------------------------------------------------------
    def scene_conclusion(self):
        """Closing scene with final value emphasis."""
        # Pulse effect on final dot
        self.play(
            self.glow.animate.scale(1.8).set_opacity(0.7),
            run_time=0.4,
            rate_func=smooth,
        )
        self.play(
            self.glow.animate.scale(1/1.8).set_opacity(GLOW_OPACITY),
            run_time=0.4,
            rate_func=smooth,
        )

        # Show final summary
        final_value = VALUES[-1]
        start_value = VALUES[0]
        change = final_value - start_value
        change_pct = (change / start_value * 100) if start_value != 0 else 0

        if change >= 0:
            change_text = f"+{{change_pct:.1f}}%"
            change_color = "#10B981"  # Green
        else:
            change_text = f"{{change_pct:.1f}}%"
            change_color = "#EF4444"  # Red

        # Summary card
        summary = VGroup()

        final_label = Text(
            f"Final: {{format_value(final_value)}}",
            font_size=32,
            color=TEXT_COLOR,
            weight=BOLD,
        )

        change_label = Text(
            change_text,
            font_size=28,
            color=change_color,
            weight=BOLD,
        )
        change_label.next_to(final_label, DOWN, buff=0.2)

        summary.add(final_label, change_label)
        summary.to_edge(UP, buff=0.8)

        self.play(
            FadeIn(summary, shift=DOWN * 0.3),
            run_time=0.5,
        )

        # Hold
        self.wait(OUTRO_DURATION - 0.5)
'''

    return code.strip()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_line_evolution_story_config(
    title: str,
    subtitle: Optional[str] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    draw_duration: float = 8.0,
    theme: str = "youtube_dark",
) -> StoryConfig:
    """
    Create a story configuration for line evolution animations.

    Args:
        title: Story title
        subtitle: Optional subtitle
        narrative_style: Pacing preset
        draw_duration: Duration of main draw animation
        theme: Visual theme

    Returns:
        StoryConfig ready for use with generate_line_evolution
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
        total_duration=draw_duration + pacing["intro_duration"] + pacing["outro_duration"],
    )


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Line Evolution Template Module Loaded Successfully")
    print("Available functions:")
    print("  - generate_line_evolution(spec, csv_path, theme, ...)")
    print("  - create_line_evolution_story_config(title, subtitle, ...)")
    print("  - parse_csv_data(csv_path, ...)")
    print("  - detect_insights(data)")
    print()
    print("Narrative styles available:")
    for style in NarrativeStyle:
        print(f"  - {style.value}")
