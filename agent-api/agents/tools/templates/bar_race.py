"""
Modern Bar Race Animation Template

A story-driven, modular bar chart race animation using the primitives system.

Features:
- Story-driven narrative structure (intro, reveal, race, conclusion)
- Auto-detected insights (leader changes, big jumps)
- Elements are atomic visual components (bars, labels, time display)
- Animations are reusable and composable
- Scenes structure the narrative flow
- The composer orchestrates everything into a cohesive story
- Configurable narrative styles (documentary, explainer, cinematic, etc.)

Usage:
    from agents.tools.templates.bar_race import generate_bar_race, create_bar_race_story_config

    # Simple usage
    code = generate_bar_race(spec, csv_path, theme="youtube_dark")

    # Advanced usage with story configuration
    story = create_bar_race_story_config(
        title="Top 10 Countries by GDP",
        subtitle="1950 - 2020",
        narrative_style=NarrativeStyle.CINEMATIC,
    )
    code = generate_bar_race(spec, csv_path, story_config=story)
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

# Setup module logger
logger = logging.getLogger("animation_pipeline.templates.bar_race")

# Import primitives
from agents.tools.primitives.elements import (
    Element,
    ElementType,
    Position,
    Style,
    Anchor,
    Direction,
    BarElement,
    LabelElement,
    TitleElement,
    SubtitleElement,
    TimeDisplayElement,
    AnnotationElement,
    ElementGroup,
    create_bar,
    create_title,
    create_annotation,
)
from agents.tools.primitives.animations import (
    AnimationType,
    AnimationConfig,
    AnimationSequence,
    EasingType,
    Direction as AnimDirection,
    create_animation,
    create_staggered_animation,
    create_entrance_sequence,
    create_emphasis_animation,
    ANIMATION_PRESETS,
)
from agents.tools.primitives.scenes import (
    SceneType,
    SceneConfig,
    SceneElement,
    TransitionStyle,
    NarrativeRole,
    create_intro_scene,
    create_reveal_scene,
    create_data_scene,
    create_highlight_scene,
    create_conclusion_scene,
)
from agents.tools.primitives.composer import (
    StoryComposer,
    StoryConfig,
    StoryBeat,
    NarrativeStyle,
    create_bar_race_story,
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
class BarRaceData:
    """Parsed and processed data for bar race animation"""
    times: List[str]
    categories: List[str]
    data: Dict[str, Dict[str, float]]  # {time: {category: value}}
    max_value: float
    category_colors: Dict[str, str]


@dataclass
class RankChange:
    """Represents a change in rankings"""
    time: str
    new_leader: str
    old_leader: str
    is_new_leader: bool = True


@dataclass
class BarRaceInsight:
    """An auto-detected insight from the data"""
    time: str
    insight_type: str  # "new_leader", "big_jump", "milestone", "overtake"
    description: str
    element_ids: List[str] = field(default_factory=list)
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
    """Parse time token for sorting (handles years, dates, etc.)"""
    try:
        return float(token)
    except ValueError:
        return token


def parse_csv_data(
    csv_path: str,
    value_col: str = "value",
    time_col: str = "time",
    category_col: str = "category",
    top_k: int = 12,
    colors: List[str] = None,
) -> BarRaceData:
    """
    Parse CSV and prepare data for bar race animation.

    Args:
        csv_path: Path to CSV file
        value_col: Column name for values
        time_col: Column name for time periods
        category_col: Column name for categories/entities
        top_k: Maximum number of bars to show
        colors: Custom color list (uses default palette if None)

    Returns:
        BarRaceData with processed animation data
    """
    logger.info(f"[BAR_RACE] parse_csv_data started | csv_path={csv_path} | value_col={value_col} | time_col={time_col} | category_col={category_col} | top_k={top_k}")

    if not os.path.exists(csv_path):
        logger.error(f"[BAR_RACE] Dataset not found: {csv_path}")
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

    # Parse CSV
    headers, rows = read_csv_rows(csv_path)
    logger.info(f"[BAR_RACE] CSV headers detected: {headers}")

    # Resolve column names
    resolved_time_col = _resolve_column(headers, time_col, ["time", "year", "date", "period", "t"])
    resolved_value_col = _resolve_column(headers, value_col, ["value", "count", "score", "gdp", "population", "amount"])
    resolved_category_col = _resolve_column(headers, category_col, ["name", "entity", "country", "category", "label", "item"])

    logger.info(f"[BAR_RACE] Column resolution | time: {time_col} -> {resolved_time_col} | value: {value_col} -> {resolved_value_col} | category: {category_col} -> {resolved_category_col}")

    time_col = resolved_time_col
    value_col = resolved_value_col
    category_col = resolved_category_col

    # Collect data
    data_by_time: Dict[str, Dict[str, float]] = {}
    all_categories = set()

    for row in rows:
        t = (row.get(time_col) or "").strip()
        c = (row.get(category_col) or "").strip()
        v_str = (row.get(value_col) or "0").strip()

        if not t or not c:
            continue

        try:
            v = float(v_str.replace(",", ""))
        except ValueError:
            continue

        if t not in data_by_time:
            data_by_time[t] = {}
        data_by_time[t][c] = v
        all_categories.add(c)

    logger.info(f"[BAR_RACE] Data collection complete | time_periods={len(data_by_time)} | unique_categories={len(all_categories)}")

    # Sort times
    times = sorted(data_by_time.keys(), key=_parse_time_key)

    if not times:
        logger.error(f"[BAR_RACE] No valid data found | time_col={time_col} | value_col={value_col} | category_col={category_col} | headers={headers}")
        raise ValueError(f"No valid data found in CSV. Check that columns '{time_col}', '{value_col}', and '{category_col}' exist and contain valid data. Available columns: {headers}")

    # Select top K categories
    first_t, last_t = times[0], times[-1]

    first_ranking = sorted(data_by_time[first_t].items(), key=lambda x: x[1], reverse=True)
    last_ranking = sorted(data_by_time[last_t].items(), key=lambda x: x[1], reverse=True)

    top_from_first = [x[0] for x in first_ranking[:top_k]]
    top_from_last = [x[0] for x in last_ranking[:top_k]]

    final_categories = list(dict.fromkeys(top_from_last + top_from_first))[:top_k]

    # Build clean data matrix
    clean_data: Dict[str, Dict[str, float]] = {}
    global_max = 0.0

    for t in times:
        clean_data[t] = {}
        for cat in final_categories:
            val = data_by_time[t].get(cat, 0.0)
            clean_data[t][cat] = val
            global_max = max(global_max, val)

    # Assign colors
    category_colors = {cat: colors[i % len(colors)] for i, cat in enumerate(final_categories)}

    logger.info(f"[BAR_RACE] Data processing complete | time_points={len(times)} | categories={len(final_categories)} | max_value={global_max:.2f}")
    logger.debug(f"[BAR_RACE] Final categories: {final_categories}")

    return BarRaceData(
        times=times,
        categories=final_categories,
        data=clean_data,
        max_value=global_max,
        category_colors=category_colors,
    )


def detect_insights(data: BarRaceData) -> List[BarRaceInsight]:
    """
    Analyze data to detect interesting moments worth highlighting.

    Detects:
    - Leadership changes
    - Big jumps in ranking
    - Milestones (crossing value thresholds)
    - Close races / overtakes

    Args:
        data: Parsed bar race data

    Returns:
        List of insights sorted by time
    """
    insights = []
    prev_leader = None
    prev_rankings: Dict[str, int] = {}

    for t in data.times:
        # Get current rankings
        ranking = sorted(
            [(cat, data.data[t].get(cat, 0)) for cat in data.categories],
            key=lambda x: x[1],
            reverse=True
        )

        current_rankings = {cat: i for i, (cat, _) in enumerate(ranking)}
        current_leader = ranking[0][0] if ranking else None

        # Detect leadership change
        if prev_leader and current_leader and current_leader != prev_leader:
            insights.append(BarRaceInsight(
                time=t,
                insight_type="new_leader",
                description=f"{current_leader} takes the lead!",
                element_ids=[f"bar_{current_leader.replace(' ', '_').lower()}"],
                intensity=0.9,
            ))

        # Detect big jumps (more than 3 positions)
        for cat in data.categories:
            prev_rank = prev_rankings.get(cat, len(data.categories))
            curr_rank = current_rankings.get(cat, len(data.categories))

            if prev_rank - curr_rank >= 3:
                insights.append(BarRaceInsight(
                    time=t,
                    insight_type="big_jump",
                    description=f"{cat} surges up the rankings!",
                    element_ids=[f"bar_{cat.replace(' ', '_').lower()}"],
                    intensity=0.7,
                ))

        prev_leader = current_leader
        prev_rankings = current_rankings

    return insights


# =============================================================================
# ELEMENT CREATION
# =============================================================================

def create_bar_elements(
    data: BarRaceData,
    time: str,
    layout: Dict[str, Any],
) -> List[BarElement]:
    """
    Create bar elements for a specific time point.

    Args:
        data: Parsed bar race data
        time: Time point to create bars for
        layout: Layout configuration (margins, spacing, etc.)

    Returns:
        List of BarElement instances
    """
    bars = []

    # Get ranking for this time
    ranking = sorted(
        [(cat, data.data[time].get(cat, 0)) for cat in data.categories],
        key=lambda x: x[1],
        reverse=True
    )

    for rank, (category, value) in enumerate(ranking):
        # Calculate bar dimensions
        bar_width = (value / data.max_value) * layout["max_bar_width"] if data.max_value > 0 else 0.1
        bar_width = max(0.1, bar_width)

        y_pos = layout["top_y"] - (rank * layout["bar_spacing"])
        x_pos = layout["left_margin"] + bar_width / 2

        bar = BarElement(
            id=f"bar_{category.replace(' ', '_').lower()}",
            category=category,
            label=category,
            value=value,
            rank=rank,
            width=bar_width,
            height=layout["bar_height"],
            max_width=layout["max_bar_width"],
            position=Position(x=x_pos, y=y_pos),
            style=Style(
                fill_color=data.category_colors.get(category, "#6366F1"),
                fill_opacity=0.9,
                corner_radius=0.12,
            ),
        )
        bars.append(bar)

    return bars


def create_time_display_element(
    time: str,
    style_config: Dict[str, Any],
) -> TimeDisplayElement:
    """Create the time display element."""
    return TimeDisplayElement(
        id="time_display",
        time=time,
        position=Position(x=5.5, y=-3.0),
        style=Style(
            text_color=style_config["text_secondary"],
            font_size=72,
            font_weight="bold",
            fill_opacity=0.8,
        ),
    )


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


def generate_bar_race(
    spec: object,
    csv_path: str,
    theme: str = "youtube_dark",
    story_config: Optional[StoryConfig] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    auto_highlights: bool = True,
    time_col: Optional[str] = None,
    value_col: Optional[str] = None,
    category_col: Optional[str] = None,
) -> str:
    """
    Generate modern, story-driven bar race animation code.

    This is the main entry point for the bar race template. It uses the
    primitives system to create a narrative-driven animation.

    Args:
        spec: ChartSpec with configuration
        csv_path: Path to CSV dataset
        theme: Style theme name
        story_config: Optional StoryConfig for custom narrative
        narrative_style: Pacing style preset
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

    # Use provided columns or fall back to spec data_binding
    _value_col = value_col or (getattr(data_binding, "value_col", None) if data_binding else None)
    _time_col = time_col or (getattr(data_binding, "time_col", None) if data_binding else None)
    _category_col = category_col or (getattr(data_binding, "entity_col", None) if data_binding else None)

    total_time = getattr(timing, "total_time", 20.0) if timing else 20.0

    # Custom colors from spec
    custom_colors = getattr(style, "colors", None) if style else None

    # Parse data
    data = parse_csv_data(
        csv_path=csv_path,
        value_col=_value_col or "value",
        time_col=_time_col or "time",
        category_col=_category_col or "category",
        top_k=12,
        colors=custom_colors,
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
    else:
        # Fallback colors (YouTube Dark theme)
        bg_color = "#0F0F1A"
        text_color = "#FFFFFF"
        text_secondary = "#A1A1AA"
        surface_color = "#1A1A2E"
        accent_color = "#22D3EE"

    # Get narrative pacing
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    # Format data literals
    lit_times = _format_literal(data.times)
    lit_categories = _format_literal(data.categories)
    lit_data = _format_literal(data.data)
    lit_colors = _format_literal(data.category_colors)

    # Format insights for highlights
    lit_insights = _format_literal([
        {"time": i.time, "type": i.insight_type, "desc": i.description, "elements": i.element_ids}
        for i in insights
    ])

    # Calculate timing
    intro_duration = pacing["intro_duration"] if include_intro else 0
    outro_duration = pacing["outro_duration"] if include_conclusion else 0
    reveal_duration = 2.0

    race_duration = total_time - intro_duration - outro_duration - reveal_duration
    race_duration = max(5.0, race_duration)

    num_steps = max(1, len(data.times) - 1)
    step_time = race_duration / num_steps

    # Build the story title
    title = getattr(spec, "title", None) or "Data Race"
    subtitle = getattr(spec, "subtitle", None) or f"{data.times[0]} - {data.times[-1]}"

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# BAR RACE ANIMATION - Story-Driven Architecture
# =============================================================================
# Generated using the primitives system for modular, narrative animations
# Theme: {theme}
# Narrative Style: {narrative_style.value}
# =============================================================================

# --- Data ---
TIMES = {lit_times}
CATEGORIES = {lit_categories}
DATA = {lit_data}
COLORS = {lit_colors}
MAX_VALUE = {data.max_value}

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
RACE_DURATION = {race_duration}
OUTRO_DURATION = {outro_duration}
STEP_TIME = {step_time}
TOTAL_DURATION = {total_time}

# --- Style Configuration ---
BG_COLOR = "{bg_color}"
TEXT_COLOR = "{text_color}"
TEXT_SECONDARY = "{text_secondary}"
SURFACE_COLOR = "{surface_color}"
ACCENT_COLOR = "{accent_color}"

# --- Layout Constants ---
BAR_HEIGHT = 0.55
BAR_SPACING = 0.7
BAR_MAX_WIDTH = 9.0
LEFT_MARGIN = -5.5
TOP_Y = 3.0
CORNER_RADIUS = 0.12


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_y_position(rank: int) -> float:
    """Calculate Y position for a given rank (0 = top)"""
    return TOP_Y - (rank * BAR_SPACING)


def get_bar_width(value: float) -> float:
    """Calculate bar width proportional to value"""
    if MAX_VALUE <= 0:
        return 0.1
    return max(0.1, (value / MAX_VALUE) * BAR_MAX_WIDTH)


def format_value(value: float) -> str:
    """Format large numbers with K/M/B suffixes"""
    if value >= 1_000_000_000:
        return f"{{value / 1_000_000_000:.1f}}B"
    elif value >= 1_000_000:
        return f"{{value / 1_000_000:.1f}}M"
    elif value >= 1_000:
        return f"{{value / 1_000:.1f}}K"
    else:
        return f"{{value:.0f}}"


def get_insights_for_time(time_key: str) -> list:
    """Get any insights that should trigger at this time"""
    return [i for i in INSIGHTS if i["time"] == time_key]


# =============================================================================
# ANIMATION PRIMITIVES
# =============================================================================

def create_bar_with_label(category: str, value: float, rank: int, color: str):
    """
    Create a bar element with its associated labels.

    Returns a dict with bar, name_label, and value_label.
    """
    bar_width = get_bar_width(value)
    y_pos = get_y_position(rank)

    # Bar rectangle with rounded corners
    bar_rect = RoundedRectangle(
        corner_radius=CORNER_RADIUS,
        width=bar_width,
        height=BAR_HEIGHT,
        fill_color=color,
        fill_opacity=0.9,
        stroke_width=0,
    )
    bar_rect.move_to([LEFT_MARGIN + bar_width / 2, y_pos, 0])

    # Category name label
    name_label = Text(
        category,
        font_size=18,
        color=WHITE if bar_width > 2.5 else TEXT_COLOR,
        weight=BOLD,
    )
    if bar_width > 2.5:
        name_label.move_to([LEFT_MARGIN + 0.3, y_pos, 0], aligned_edge=LEFT)
    else:
        name_label.move_to([LEFT_MARGIN - 0.15, y_pos, 0], aligned_edge=RIGHT)

    # Value label
    value_label = Text(
        format_value(value),
        font_size=16,
        color=TEXT_COLOR,
    )
    value_label.move_to([LEFT_MARGIN + bar_width + 0.25, y_pos, 0], aligned_edge=LEFT)

    return {{
        "rect": bar_rect,
        "name": name_label,
        "value": value_label,
        "current_rank": rank,
        "current_value": value,
    }}


def create_emphasis_pulse(mobject, scale_factor=1.15, duration=0.4):
    """Create a pulse emphasis animation"""
    return Succession(
        mobject.animate.scale(scale_factor),
        mobject.animate.scale(1/scale_factor),
        run_time=duration,
    )


# =============================================================================
# SCENE CLASSES
# =============================================================================

class GenScene(Scene):
    """
    Story-driven bar race animation.

    Structure:
    1. INTRO: Title and subtitle fade in
    2. REVEAL: Bars appear with staggered animation
    3. RACE: Main data animation with time progression
    4. HIGHLIGHTS: Auto-detected insights emphasized
    5. CONCLUSION: Final state with winner emphasis
    """

    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        # Track active elements
        self.bars = {{}}
        self.time_display = None
        self.title_group = None

        # Run story scenes
        if INCLUDE_INTRO:
            self.scene_intro()

        self.scene_reveal()
        self.scene_race()

        if INCLUDE_CONCLUSION:
            self.scene_conclusion()

    # -------------------------------------------------------------------------
    # SCENE 1: INTRO
    # -------------------------------------------------------------------------
    def scene_intro(self):
        """
        Opening scene with title and subtitle.

        Sets the stage and hooks the viewer.
        """
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

        self.title_group = VGroup(title, subtitle)

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
        self.wait(INTRO_DURATION - 1.3)

        # Fade out
        self.play(
            FadeOut(self.title_group, shift=UP * 0.5),
            run_time=0.5,
        )

    # -------------------------------------------------------------------------
    # SCENE 2: REVEAL
    # -------------------------------------------------------------------------
    def scene_reveal(self):
        """
        Data reveal scene where bars first appear.

        Uses staggered animation for visual interest.
        """
        t0 = TIMES[0]

        # Create time display
        self.time_display = Text(
            str(t0),
            font_size=72,
            weight=BOLD,
            color=TEXT_SECONDARY,
        )
        self.time_display.to_corner(DR, buff=0.8)
        self.time_display.set_opacity(0.8)

        # Get initial ranking
        initial_ranking = sorted(
            [(cat, DATA[t0].get(cat, 0)) for cat in CATEGORIES],
            key=lambda x: x[1],
            reverse=True
        )

        # Create bars
        bar_anims = []
        for rank, (category, value) in enumerate(initial_ranking):
            bar_data = create_bar_with_label(
                category=category,
                value=value,
                rank=rank,
                color=COLORS.get(category, "#6366F1"),
            )

            self.bars[category] = bar_data

            # Add to scene (hidden initially)
            bar_group = VGroup(bar_data["rect"], bar_data["name"], bar_data["value"])
            bar_group.set_opacity(0)
            self.add(bar_group)

            # Create entrance animation with stagger
            bar_anims.append(
                bar_group.animate.set_opacity(1)
            )

        # Animate time display
        self.play(
            FadeIn(self.time_display),
            run_time=0.3,
        )

        # Staggered bar entrance
        self.play(
            LaggedStart(
                *[GrowFromEdge(self.bars[cat]["rect"], LEFT) for cat in [x[0] for x in initial_ranking]],
                lag_ratio=0.08,
            ),
            LaggedStart(
                *[FadeIn(self.bars[cat]["name"]) for cat in [x[0] for x in initial_ranking]],
                lag_ratio=0.08,
            ),
            LaggedStart(
                *[FadeIn(self.bars[cat]["value"]) for cat in [x[0] for x in initial_ranking]],
                lag_ratio=0.08,
            ),
            run_time=REVEAL_DURATION,
            rate_func=smooth,
        )

        self.wait(0.3)

    # -------------------------------------------------------------------------
    # SCENE 3: RACE
    # -------------------------------------------------------------------------
    def scene_race(self):
        """
        Main data animation scene.

        Bars animate through time with smooth transitions.
        Highlights are shown when insights are detected.
        """
        prev_leader = None

        for step_idx in range(1, len(TIMES)):
            t_current = TIMES[step_idx]

            # Check for insights at this time
            current_insights = get_insights_for_time(t_current)

            # Calculate new rankings
            new_ranking = sorted(
                [(cat, DATA[t_current].get(cat, 0)) for cat in CATEGORIES],
                key=lambda x: x[1],
                reverse=True
            )

            current_leader = new_ranking[0][0] if new_ranking else None
            leader_changed = prev_leader and current_leader != prev_leader

            animations = []

            # Update time display
            new_time_display = Text(
                str(t_current),
                font_size=72,
                weight=BOLD,
                color=ACCENT_COLOR if leader_changed else TEXT_SECONDARY,
            )
            new_time_display.to_corner(DR, buff=0.8)
            new_time_display.set_opacity(0.8)
            animations.append(Transform(self.time_display, new_time_display))

            # Update each bar
            for new_rank, (category, new_value) in enumerate(new_ranking):
                bar_data = self.bars[category]
                bar_rect = bar_data["rect"]
                name_label = bar_data["name"]
                value_label = bar_data["value"]

                new_width = get_bar_width(new_value)
                new_y = get_y_position(new_rank)

                # Create new bar state
                new_bar = RoundedRectangle(
                    corner_radius=CORNER_RADIUS,
                    width=new_width,
                    height=BAR_HEIGHT,
                    fill_color=COLORS.get(category, "#6366F1"),
                    fill_opacity=0.9,
                    stroke_width=0,
                )
                new_bar.move_to([LEFT_MARGIN + new_width / 2, new_y, 0])
                animations.append(Transform(bar_rect, new_bar))

                # Update name label
                new_name = Text(
                    category,
                    font_size=18,
                    color=WHITE if new_width > 2.5 else TEXT_COLOR,
                    weight=BOLD,
                )
                if new_width > 2.5:
                    new_name.move_to([LEFT_MARGIN + 0.3, new_y, 0], aligned_edge=LEFT)
                else:
                    new_name.move_to([LEFT_MARGIN - 0.15, new_y, 0], aligned_edge=RIGHT)
                animations.append(Transform(name_label, new_name))

                # Update value label
                new_value_label = Text(
                    format_value(new_value),
                    font_size=16,
                    color=TEXT_COLOR,
                )
                new_value_label.move_to([LEFT_MARGIN + new_width + 0.25, new_y, 0], aligned_edge=LEFT)
                animations.append(Transform(value_label, new_value_label))

                # Update tracking
                bar_data["current_rank"] = new_rank
                bar_data["current_value"] = new_value

            # Play animations
            self.play(
                *animations,
                run_time=STEP_TIME,
                rate_func=smooth,
            )

            # Show highlight for leader change
            if leader_changed and current_leader:
                self.show_highlight(
                    category=current_leader,
                    text=f"{{current_leader}} takes the lead!",
                )

            prev_leader = current_leader

    def show_highlight(self, category: str, text: str):
        """Show a highlight annotation for an insight"""
        bar_data = self.bars.get(category)
        if not bar_data:
            return

        # Create annotation
        annotation = Text(
            text,
            font_size=24,
            color=ACCENT_COLOR,
            weight=BOLD,
        )
        annotation.to_edge(UP, buff=0.5)

        # Animate
        self.play(
            FadeIn(annotation, shift=DOWN * 0.3),
            bar_data["rect"].animate.set_stroke(color=ACCENT_COLOR, width=3),
            run_time=0.3,
        )

        self.wait(0.5)

        self.play(
            FadeOut(annotation),
            bar_data["rect"].animate.set_stroke(width=0),
            run_time=0.3,
        )

    # -------------------------------------------------------------------------
    # SCENE 4: CONCLUSION
    # -------------------------------------------------------------------------
    def scene_conclusion(self):
        """
        Closing scene with final state emphasis.

        Highlights the winner and provides closure.
        """
        # Get final leader
        final_t = TIMES[-1]
        final_ranking = sorted(
            [(cat, DATA[final_t].get(cat, 0)) for cat in CATEGORIES],
            key=lambda x: x[1],
            reverse=True
        )

        if not final_ranking:
            self.wait(OUTRO_DURATION)
            return

        winner = final_ranking[0][0]
        winner_value = final_ranking[0][1]
        winner_bar = self.bars.get(winner, {{}}).get("rect")

        # Dim other bars
        dim_anims = []
        for cat, bar_data in self.bars.items():
            if cat != winner:
                dim_anims.append(bar_data["rect"].animate.set_opacity(0.3))
                dim_anims.append(bar_data["name"].animate.set_opacity(0.3))
                dim_anims.append(bar_data["value"].animate.set_opacity(0.3))

        if dim_anims:
            self.play(*dim_anims, run_time=0.5)

        # Emphasize winner
        if winner_bar:
            self.play(
                winner_bar.animate.set_stroke(color=ACCENT_COLOR, width=4),
                run_time=0.3,
            )

            # Glow effect
            glow = winner_bar.copy()
            glow.set_stroke(color=ACCENT_COLOR, width=8, opacity=0.5)
            glow.scale(1.05)

            self.play(
                FadeIn(glow),
                run_time=0.3,
            )

        # Final title
        final_title = Text(
            f"Winner: {{winner}}",
            font_size=36,
            color=ACCENT_COLOR,
            weight=BOLD,
        )
        final_title.to_edge(UP, buff=0.8)

        self.play(
            FadeIn(final_title, shift=DOWN * 0.3),
            run_time=0.5,
        )

        # Hold final frame
        self.wait(OUTRO_DURATION - 1.3)
'''

    return code.strip()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_bar_race_story_config(
    title: str,
    subtitle: Optional[str] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    data_duration: float = 15.0,
    theme: str = "youtube_dark",
) -> StoryConfig:
    """
    Create a story configuration for bar race animations.

    This provides fine-grained control over the narrative structure.

    Args:
        title: Story title
        subtitle: Optional subtitle
        narrative_style: Pacing preset
        data_duration: Duration of main race animation
        theme: Visual theme

    Returns:
        StoryConfig ready for use with generate_bar_race
    """
    story = create_bar_race_story(
        title=title,
        subtitle=subtitle,
        data_duration=data_duration,
        narrative_style=narrative_style,
    )
    story.theme = theme

    return story


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Bar Race Template Module Loaded Successfully")
    print("Available functions:")
    print("  - generate_bar_race(spec, csv_path, theme, ...)")
    print("  - create_bar_race_story_config(title, subtitle, ...)")
    print("  - parse_csv_data(csv_path, ...)")
    print("  - detect_insights(data)")
    print()
    print("Narrative styles available:")
    for style in NarrativeStyle:
        print(f"  - {style.value}")
