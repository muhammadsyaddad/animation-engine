"""
Modern Distribution (Histogram) Animation Template

A story-driven, modular histogram animation using the primitives system.

Features:
- Story-driven narrative structure (intro, reveal, evolution, conclusion)
- Properly formatted axis labels (K/M/B suffixes)
- Smart bin labeling that doesn't overlap
- Smooth bar transitions over time
- Auto-detected insights (distribution shifts, peaks)
- Modern color palette
- Configurable narrative styles

Perfect for: Population distributions, value distributions over time, frequency analysis

Usage:
    from agents.tools.templates.distribution import generate_distribution

    # Simple usage
    code = generate_distribution(spec, csv_path, theme="youtube_dark")

    # With custom narrative style
    from agents.tools.templates import NarrativeStyle
    code = generate_distribution(
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


def format_range_label(low: float, high: float) -> str:
    """
    Format a bin range as a clean label.

    Examples:
        (0, 1000000) -> "0-1M"
        (1000000, 10000000) -> "1M-10M"
    """
    return f"{format_number(low, 0)}-{format_number(high, 0)}"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class DistributionData:
    """Parsed and processed data for distribution animation"""
    times: List[str]
    bin_edges: List[float]
    bin_labels: List[str]
    histograms: Dict[str, List[int]]  # {time: [count_per_bin]}
    max_count: int
    value_min: float
    value_max: float


@dataclass
class DistributionInsight:
    """An auto-detected insight from the data"""
    time: str
    insight_type: str  # "peak_shift", "spread_change", "mode_change"
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
    num_bins: int = 10,
) -> DistributionData:
    """
    Parse CSV and prepare data for distribution animation.

    Args:
        csv_path: Path to CSV file
        value_col: Column name for values
        time_col: Column name for time periods
        num_bins: Number of histogram bins

    Returns:
        DistributionData with processed animation data
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # Resolve column names
        time_col = _resolve_column(
            headers, time_col,
            ["time", "year", "date", "period", "t"]
        )
        value_col = _resolve_column(
            headers, value_col,
            ["value", "population", "count", "amount", "score", "gdp"]
        )

        # Collect values by time
        values_by_time: Dict[str, List[float]] = {}
        all_values: List[float] = []

        for row in reader:
            t = (row.get(time_col) or "").strip()
            v_str = (row.get(value_col) or "").strip()

            if not t or not v_str:
                continue

            try:
                v = float(v_str.replace(",", ""))
                values_by_time.setdefault(t, []).append(v)
                all_values.append(v)
            except ValueError:
                continue

    if not values_by_time or not all_values:
        raise ValueError("No valid data found for distribution")

    # Sort times
    times = sorted(values_by_time.keys(), key=_parse_time_key)

    # Calculate bin edges
    v_min = min(all_values)
    v_max = max(all_values)

    if v_min == v_max:
        v_min -= 0.5
        v_max += 0.5

    span = v_max - v_min
    step = span / num_bins

    # Create bin edges
    bin_edges = [v_min + i * step for i in range(num_bins + 1)]

    # Create readable bin labels
    bin_labels = [format_range_label(bin_edges[i], bin_edges[i + 1]) for i in range(num_bins)]

    # Calculate histograms for each time
    histograms: Dict[str, List[int]] = {}
    max_count = 1

    for t in times:
        counts = [0] * num_bins
        for v in values_by_time.get(t, []):
            # Find bin index
            if step > 0:
                idx = int((v - v_min) / step)
            else:
                idx = 0
            idx = max(0, min(idx, num_bins - 1))
            counts[idx] += 1

        histograms[t] = counts
        max_count = max(max_count, max(counts) if counts else 0)

    return DistributionData(
        times=times,
        bin_edges=bin_edges,
        bin_labels=bin_labels,
        histograms=histograms,
        max_count=max_count,
        value_min=v_min,
        value_max=v_max,
    )


def detect_insights(data: DistributionData) -> List[DistributionInsight]:
    """
    Analyze data to detect interesting distribution changes.

    Detects:
    - Peak shifts (mode changes)
    - Spread changes (variance changes)
    - Significant count changes

    Args:
        data: Parsed distribution data

    Returns:
        List of insights sorted by time
    """
    insights = []
    prev_peak_bin = None
    prev_total = None

    for t in data.times:
        counts = data.histograms.get(t, [])
        if not counts:
            continue

        # Find peak bin (mode)
        peak_bin = counts.index(max(counts))
        total = sum(counts)

        # Detect peak shift
        if prev_peak_bin is not None and peak_bin != prev_peak_bin:
            direction = "right" if peak_bin > prev_peak_bin else "left"
            insights.append(DistributionInsight(
                time=t,
                insight_type="peak_shift",
                description=f"Distribution shifts {direction}",
                intensity=0.8,
            ))

        # Detect big count changes
        if prev_total is not None:
            change_ratio = total / prev_total if prev_total > 0 else 1
            if change_ratio > 1.5:
                insights.append(DistributionInsight(
                    time=t,
                    insight_type="growth",
                    description="Significant growth!",
                    intensity=0.7,
                ))
            elif change_ratio < 0.67:
                insights.append(DistributionInsight(
                    time=t,
                    insight_type="decline",
                    description="Notable decline",
                    intensity=0.7,
                ))

        prev_peak_bin = peak_bin
        prev_total = total

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


def generate_distribution(
    spec: object,
    csv_path: str,
    theme: str = "youtube_dark",
    num_bins: int = 10,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    include_intro: bool = True,
    include_conclusion: bool = True,
    auto_highlights: bool = True,
) -> str:
    """
    Generate modern, story-driven distribution animation code.

    This is the main entry point for the distribution template. It uses the
    primitives system to create a narrative-driven animation.

    Args:
        spec: ChartSpec with configuration
        csv_path: Path to CSV dataset
        theme: Style theme name
        num_bins: Number of histogram bins (default 10)
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
    axes_config = getattr(spec, "axes", None)

    value_col = getattr(data_binding, "value_col", None) if data_binding else None
    time_col = getattr(data_binding, "time_col", None) if data_binding else None

    total_time = getattr(timing, "total_time", 20.0) if timing else 20.0
    creation_time = getattr(timing, "creation_time", 1.5) if timing else 1.5

    # Axis labels
    x_label = getattr(axes_config, "x_label", None) if axes_config else None
    y_label = getattr(axes_config, "y_label", None) if axes_config else None

    # Parse data
    data = parse_csv_data(
        csv_path=csv_path,
        value_col=value_col or "value",
        time_col=time_col or "time",
        num_bins=num_bins,
    )

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
    else:
        # Fallback colors (YouTube Dark theme)
        bg_color = "#0F0F1A"
        text_color = "#FFFFFF"
        text_secondary = "#A1A1AA"
        primary_color = "#6366F1"
        accent_color = "#22D3EE"

    # Get narrative pacing
    pacing = NARRATIVE_STYLE_PRESETS.get(
        narrative_style,
        NARRATIVE_STYLE_PRESETS[NarrativeStyle.EXPLAINER]
    )

    # Format data literals
    lit_times = _format_literal(data.times)
    lit_bin_labels = _format_literal(data.bin_labels)
    lit_histograms = _format_literal(data.histograms)

    # Format insights for highlights
    lit_insights = _format_literal([
        {"time": i.time, "type": i.insight_type, "desc": i.description}
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

    # Y-axis max with padding
    y_max = int(math.ceil(data.max_count * 1.15))
    y_step = max(1, y_max // 5)

    # Build the story title
    title = getattr(spec, "title", None) or "Distribution Over Time"
    subtitle = getattr(spec, "subtitle", None) or f"{data.times[0]} - {data.times[-1]}" if len(data.times) > 1 else ""

    # Generate the Manim code
    code = f'''
from manim import *
import math

# =============================================================================
# DISTRIBUTION ANIMATION - Story-Driven Architecture
# =============================================================================
# Generated using the primitives system for modular, narrative animations
# Theme: {theme}
# Narrative Style: {narrative_style.value}
# =============================================================================

# --- Data ---
TIMES = {lit_times}
BIN_LABELS = {lit_bin_labels}
HISTOGRAMS = {lit_histograms}
Y_MAX = {y_max}
Y_STEP = {y_step}
NUM_BINS = {num_bins}

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

# --- Style Configuration ---
BG_COLOR = "{bg_color}"
TEXT_COLOR = "{text_color}"
TEXT_SECONDARY = "{text_secondary}"
PRIMARY_COLOR = "{primary_color}"
ACCENT_COLOR = "{accent_color}"

# --- Axis Labels ---
X_LABEL = "{x_label or 'Value'}"
Y_LABEL = "{y_label or 'Count'}"

# --- Layout Constants ---
CHART_WIDTH = 10.0
CHART_HEIGHT = 5.0
BAR_WIDTH_RATIO = 0.7


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_number(value: float) -> str:
    """Format large numbers with K/M/B suffixes"""
    if abs(value) >= 1_000_000_000:
        return f"{{value / 1_000_000_000:.1f}}B"
    elif abs(value) >= 1_000_000:
        return f"{{value / 1_000_000:.1f}}M"
    elif abs(value) >= 1_000:
        return f"{{value / 1_000:.1f}}K"
    else:
        return f"{{value:.0f}}"


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
    Story-driven distribution animation.

    Structure:
    1. INTRO: Title and subtitle fade in
    2. REVEAL: Axes and initial bars appear
    3. EVOLUTION: Bars animate through time
    4. HIGHLIGHTS: Insights emphasized during evolution
    5. CONCLUSION: Final state with summary
    """

    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        if not TIMES:
            no_data = Text("No data available", color=TEXT_COLOR)
            self.play(Write(no_data))
            return

        # Track elements
        self.axes = None
        self.bars = None
        self.time_display = None

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
        """Reveal axes and initial bars."""
        # Create Axes
        self.axes = Axes(
            x_range=[0, NUM_BINS, 1],
            y_range=[0, Y_MAX, Y_STEP],
            x_length=CHART_WIDTH,
            y_length=CHART_HEIGHT,
            axis_config={{
                "color": TEXT_SECONDARY,
                "stroke_width": 2,
                "include_ticks": True,
            }},
            x_axis_config={{
                "include_numbers": False,
            }},
            y_axis_config={{
                "include_numbers": True,
                "font_size": 18,
            }},
            tips=False,
        )
        self.axes.to_edge(DOWN, buff=1.0)
        self.axes.shift(LEFT * 0.5)

        # Custom X-Axis Labels (Bin Ranges)
        x_labels = VGroup()

        if NUM_BINS <= 5:
            label_step = 1
        elif NUM_BINS <= 10:
            label_step = 2
        else:
            label_step = max(1, NUM_BINS // 5)

        for i in range(0, NUM_BINS, label_step):
            label = Text(
                BIN_LABELS[i],
                font_size=14,
                color=TEXT_SECONDARY,
            )
            x_pos = self.axes.c2p(i + 0.5, 0)[0]
            label.move_to([x_pos, self.axes.c2p(0, 0)[1] - 0.4, 0])
            label.rotate(-45 * DEGREES)
            x_labels.add(label)

        # Axis Labels
        x_axis_label = Text(
            X_LABEL,
            font_size=22,
            color=TEXT_SECONDARY,
        )
        x_axis_label.next_to(self.axes.x_axis, DOWN, buff=1.2)

        y_axis_label = Text(
            Y_LABEL,
            font_size=22,
            color=TEXT_SECONDARY,
        )
        y_axis_label.rotate(90 * DEGREES)
        y_axis_label.next_to(self.axes.y_axis, LEFT, buff=0.6)

        # Time Display
        self.time_display = Text(
            str(TIMES[0]),
            font_size=72,
            weight=BOLD,
            color=ACCENT_COLOR,
        )
        self.time_display.to_corner(UL, buff=0.8)
        self.time_display.set_opacity(0.9)

        # Create Initial Bars
        t0 = TIMES[0]
        initial_counts = HISTOGRAMS.get(t0, [0] * NUM_BINS)
        self.bars = self.create_bars(initial_counts)

        # Animate reveal
        self.play(
            Create(self.axes, lag_ratio=0.1),
            run_time=REVEAL_DURATION * 0.4,
        )
        self.play(
            FadeIn(x_labels),
            FadeIn(x_axis_label),
            FadeIn(y_axis_label),
            FadeIn(self.time_display),
            run_time=REVEAL_DURATION * 0.3,
        )
        self.play(
            LaggedStart(
                *[GrowFromEdge(bar, DOWN) for bar in self.bars],
                lag_ratio=0.05,
            ),
            run_time=REVEAL_DURATION * 0.3,
        )

        self.wait(0.3)

    def create_bars(self, counts):
        """Create histogram bars for given counts."""
        bars = VGroup()
        bar_width = (CHART_WIDTH / NUM_BINS) * BAR_WIDTH_RATIO

        for i, count in enumerate(counts):
            if Y_MAX > 0:
                height = (count / Y_MAX) * CHART_HEIGHT
            else:
                height = 0
            height = max(0.01, height)

            bar = RoundedRectangle(
                corner_radius=0.08,
                width=bar_width,
                height=height,
                fill_color=PRIMARY_COLOR,
                fill_opacity=0.85,
                stroke_width=0,
            )

            x_pos = self.axes.c2p(i + 0.5, 0)[0]
            y_pos = self.axes.c2p(0, 0)[1] + height / 2
            bar.move_to([x_pos, y_pos, 0])

            bars.add(bar)

        return bars

    # -------------------------------------------------------------------------
    # SCENE 3: EVOLUTION
    # -------------------------------------------------------------------------
    def scene_evolution(self):
        """Main animation: evolve through time."""
        for step_idx in range(1, len(TIMES)):
            t_current = TIMES[step_idx]
            new_counts = HISTOGRAMS.get(t_current, [0] * NUM_BINS)

            # Check for insights
            insight = get_insight_at_time(t_current)

            # Create new bars
            new_bars = self.create_bars(new_counts)

            # Update time display
            new_time_display = Text(
                str(t_current),
                font_size=72,
                weight=BOLD,
                color=ACCENT_COLOR if insight else ACCENT_COLOR,
            )
            new_time_display.to_corner(UL, buff=0.8)
            new_time_display.set_opacity(0.9)

            # Animate transition
            animations = [Transform(self.time_display, new_time_display)]

            for old_bar, new_bar in zip(self.bars, new_bars):
                animations.append(Transform(old_bar, new_bar))

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
        annotation = Text(
            insight["desc"],
            font_size=24,
            color=ACCENT_COLOR,
            weight=BOLD,
        )
        annotation.to_edge(UP, buff=0.5)

        self.play(
            FadeIn(annotation, shift=DOWN * 0.3),
            run_time=0.3,
        )

        self.wait(0.4)

        self.play(
            FadeOut(annotation),
            run_time=0.3,
        )

    # -------------------------------------------------------------------------
    # SCENE 4: CONCLUSION
    # -------------------------------------------------------------------------
    def scene_conclusion(self):
        """Closing scene with summary."""
        # Calculate summary statistics
        final_counts = HISTOGRAMS.get(TIMES[-1], [0] * NUM_BINS)
        total = sum(final_counts)
        peak_bin = final_counts.index(max(final_counts)) if final_counts else 0
        peak_range = BIN_LABELS[peak_bin] if peak_bin < len(BIN_LABELS) else ""

        # Summary card
        summary = VGroup()

        total_label = Text(
            f"Total: {{format_number(total)}}",
            font_size=32,
            color=TEXT_COLOR,
            weight=BOLD,
        )

        peak_label = Text(
            f"Peak: {{peak_range}}",
            font_size=28,
            color=TEXT_SECONDARY,
        )
        peak_label.next_to(total_label, DOWN, buff=0.2)

        summary.add(total_label, peak_label)
        summary.to_corner(UR, buff=0.8)

        # Highlight peak bar
        if peak_bin < len(self.bars):
            peak_bar = self.bars[peak_bin]
            self.play(
                FadeIn(summary, shift=LEFT * 0.3),
                peak_bar.animate.set_fill(ACCENT_COLOR, opacity=0.95),
                run_time=0.5,
            )
        else:
            self.play(
                FadeIn(summary, shift=LEFT * 0.3),
                run_time=0.5,
            )

        # Hold
        self.wait(OUTRO_DURATION - 0.5)
'''

    return code.strip()


# Alias for backward compatibility
generate_distribution_code = generate_distribution


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_distribution_story_config(
    title: str,
    subtitle: Optional[str] = None,
    narrative_style: NarrativeStyle = NarrativeStyle.EXPLAINER,
    evolution_duration: float = 15.0,
    theme: str = "youtube_dark",
) -> StoryConfig:
    """
    Create a story configuration for distribution animations.

    Args:
        title: Story title
        subtitle: Optional subtitle
        narrative_style: Pacing preset
        evolution_duration: Duration of main evolution animation
        theme: Visual theme

    Returns:
        StoryConfig ready for use with generate_distribution
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

    print("\nRange label tests:")
    test_ranges = [(0, 1000), (1000, 10000), (10000, 100000), (100000, 1000000), (1000000, 10000000)]
    for low, high in test_ranges:
        print(f"  ({low}, {high}) -> {format_range_label(low, high)}")

    print("\nDistribution Template Module Loaded Successfully")
    print("Available functions:")
    print("  - generate_distribution(spec, csv_path, theme, ...)")
    print("  - create_distribution_story_config(title, subtitle, ...)")
    print("  - parse_csv_data(csv_path, ...)")
    print("  - detect_insights(data)")
    print()
    print("Narrative styles available:")
    for style in NarrativeStyle:
        print(f"  - {style.value}")
