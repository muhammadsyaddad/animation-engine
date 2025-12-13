from manim import *
from math import *
import os

config.frame_size = (1280, 720)
config.frame_width = 10.0
config.frame_rate = 10


# ---- Early Exit (Preview Mode) ----
import os as _os
from manim.scene.scene import Scene as _Scene
_PREVIEW_LIMIT_ACTIONS = int(_os.environ.get("PREVIEW_LIMIT_ACTIONS", "8"))
_play_action_counter = 0
_exit_preview_now = False

_original_play = _Scene.play
_original_wait = _Scene.wait
_original_add = _Scene.add
_original_add_fg = _Scene.add_foreground_mobject

def _preview_play(self, *args, **kwargs):
    global _play_action_counter, _exit_preview_now
    if _exit_preview_now:
        return  # skip further animations
    _play_action_counter += 1
    if _play_action_counter >= _PREVIEW_LIMIT_ACTIONS:
        _exit_preview_now = True
        # Execute this final animation once, then future ones skipped
        return _original_play(self, *args, **kwargs)
    return _original_play(self, *args, **kwargs)

def _preview_wait(self, duration=0.0):
    if _exit_preview_now:
        return  # skip waits entirely
    return _original_wait(self, duration)

def _preview_add(self, *mobs):
    if _exit_preview_now:
        # Allow minimal additions to keep scene valid; or skip entirely
        return
    return _original_add(self, *mobs)

def _preview_add_fg(self, *mobs):
    if _exit_preview_now:
        return
    return _original_add_fg(self, *mobs)

_Scene.play = _preview_play
_Scene.wait = _preview_wait
_Scene.add = _preview_add
_Scene.add_foreground_mobject = _preview_add_fg


from manim import *
import math

# =============================================================================
# COUNT BAR CHART ANIMATION
# =============================================================================
# A simple, clean horizontal bar chart with staggered growth animation
# Theme: youtube_dark
# Column: Data Source
# =============================================================================

# --- Data ---
CATEGORIES = ['Last Updated Date', 'Country Name', 'Aruba', 'Africa Eastern and Southern', 'Afghanistan', 'Africa Western and Central', 'Angola', 'Albania', 'Andorra', 'Arab World', 'United Arab Emirates', 'Argentina', 'Armenia', 'American Samoa', 'Antigua and Barbuda']
COUNTS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
MAX_COUNT = 1
TOTAL_ITEMS = 268
COLUMN_NAME = "Data Source"

# --- Colors ---
BAR_COLORS = ['#6366F1', '#EC4899', '#22D3EE', '#10B981', '#F59E0B', '#8B5CF6', '#F97316', '#14B8A6', '#EF4444', '#84CC16', '#06B6D4', '#D946EF', '#6366F1', '#EC4899', '#22D3EE']
BG_COLOR = "#0F0F1A"
TEXT_COLOR = "#FFFFFF"
TEXT_SECONDARY = "#A1A1AA"

# --- Insights ---
INSIGHTS = [{'type': 'even_distribution', 'desc': 'Categories are relatively evenly distributed'}]

# --- Story Configuration ---
STORY_TITLE = "Distribution by Data Source"
STORY_SUBTITLE = "Top 15 categories • 268 total items"
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

            # Calculate bar width (scaled to
