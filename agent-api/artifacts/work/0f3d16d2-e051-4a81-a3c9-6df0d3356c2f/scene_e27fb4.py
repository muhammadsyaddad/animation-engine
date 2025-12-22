from manim import *
from math import *
config.frame_size = (1920, 1080)
config.frame_width = 14.22

from manim import *
import math

# =============================================================================
# COUNT BAR CHART ANIMATION
# =============================================================================
# A simple, clean horizontal bar chart with staggered growth animation
# Theme: youtube_dark
# Column: Search interest in Jeb Bush by state, following his 6/15 announcement
# =============================================================================

# --- Data ---
CATEGORIES = ['city', 'District of Columbia (United States)', 'Florida (United States)', 'New York (United States)', 'Connecticut (United States)', 'Virginia (United States)', 'Delaware (United States)', 'Maryland (United States)', 'New Jersey (United States)', 'Massachusetts (United States)', 'Arizona (United States)', 'New Hampshire (United States)', 'Georgia (United States)', 'Oregon (United States)', 'Nevada (United States)']
COUNTS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
MAX_COUNT = 1
TOTAL_ITEMS = 52
COLUMN_NAME = "Search interest in Jeb Bush by state, following his 6/15 announcement"

# --- Colors ---
BAR_COLORS = ['#6366F1', '#EC4899', '#22D3EE', '#10B981', '#F59E0B', '#8B5CF6', '#F97316', '#14B8A6', '#EF4444', '#84CC16', '#06B6D4', '#D946EF', '#6366F1', '#EC4899', '#22D3EE']
BG_COLOR = "#0F0F1A"
TEXT_COLOR = "#FFFFFF"
TEXT_SECONDARY = "#A1A1AA"

# --- Insights ---
INSIGHTS = [{'type': 'even_distribution', 'desc': 'Categories are relatively evenly distributed'}]

# --- Story Configuration ---
STORY_TITLE = "Distribution by Search interest in Jeb Bush by state, following his 6/15 announcement"
STORY_SUBTITLE = "Top 15 categories • 52 total items"
INCLUDE_INTRO = True
INCLUDE_CONCLUSION = True

# --- Timing ---
INTRO_DURATION = 3.0
REVEAL_DURATION = 2.0
HOLD_DURATION = 22.5
OUTRO_DURATION = 2.5
BAR_GROW_TIME = 0.5999999999999999
STAGGER_DELAY = 0.1

# --- Layout ---
BAR_HEIGHT = 0.5
BAR_SPACING = 0.15
MAX_BAR_WIDTH = 8.0
CHART_TOP = 2.0
LABEL_MARGIN = 0.3
VALUE_MARGIN = 0.5


def format_count(value: int) -> str:
    """Format count with K/M suffix"""
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
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
