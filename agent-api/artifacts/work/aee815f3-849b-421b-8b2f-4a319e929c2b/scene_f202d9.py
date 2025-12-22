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
from math import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Load the dataset
        df = pd.read_csv("/static/datasets/dataset_20251219_062951/StudentsPerformance.csv")
        
        # Title
        title = Text("Student Performance Analysis", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(1)
        
        # Get basic stats
        math_avg = df['math score'].mean()
        reading_avg = df['reading score'].mean()
        writing_avg = df['writing score'].mean()
        
        # Create bar chart for average scores
        axes = Axes(
            x_range=[0, 3, 1],
            y_range=[0, 100, 20],
            x_length=8,
            y_length=5,
            axis_config={"color": WHITE},
            x_axis_config={"numbers_to_show": []},
            y_axis_config={"numbers_to_show": [0, 20, 40, 60, 80, 100]}
        )
        
        # Position axes
        axes.shift(DOWN * 0.5)
        
        # Create bars
        math_bar = Rectangle(width=1.5, height=math_avg/20, color=RED, fill_opacity=0.8)
        reading_bar = Rectangle(width=1.5, height=reading_avg/20, color=GREEN, fill_opacity=0.8)
        writing_bar = Rectangle(width=1.5, height=writing_avg/20, color=BLUE, fill_opacity=0.8)
        
        # Position bars
        math_bar.move_to(axes.c2p(0.5, math_avg/2))
        reading_bar.move_to(axes.c2p(1.5, reading_avg/2))
        writing_bar.move_to(axes.c2p(2.5, writing_avg/2))
        
        # Labels
        math_label = Text("Math", font_size=24, color=RED).next_to(math_bar, DOWN)
        reading_label = Text("Reading", font_size=24, color=GREEN).next_to(reading_bar, DOWN)
        writing_label = Text("Writing", font_size=24, color=BLUE).next_to(writing_bar, DOWN)
        
        # Score values
        math_score = Text(f"{math_avg:.1f}", font_size=20, color=WHITE).next_to(math_bar, UP)
        reading_score = Text(f"{reading_avg:.1f}", font_size=20, color=WHITE).next_to(reading_bar, UP)
        writing_score = Text(f"{writing_avg:.1f}", font_size=20, color=WHITE).next_to(writing_bar, UP)
        
        # Animate chart creation
        self.play(Create(axes))
        self.play(
            GrowFromEdge(math_bar, DOWN),
            GrowFromEdge(reading_bar, DOWN),
            GrowFromEdge(writing_bar, DOWN),
            run_time=2
        )
        self.play(
            Write(math_label),
            Write(reading_label),
            Write(writing_label)
        )
        self.play(
            Write(math_score),
            Write(reading_score),
            Write(writing_score)
        )
        self.wait(2)
        
        # Show gender distribution
        gender_counts = df['gender'].value_counts()
        
        # Clear previous content
        self.play(
            FadeOut(axes),
            FadeOut(math_bar),
            FadeOut(reading_bar),
            FadeOut(writing_bar),
            FadeOut(math_label),
            FadeOut(reading_label),
            FadeOut(writing_label),
            FadeOut(math_score),
            FadeOut(reading_score),
            FadeOut(writing_score)
        )
        
        # Gender pie chart representation
        female_count = gender_counts.get('female', 0)
        male_count = gender_counts.get('male', 0)
        total = female_count + male_count
        
        female_angle = (female_count / total) * 2 * PI
        male_angle = (male_count / total) * 2 * PI
        
        # Create pie chart sectors
        female_sector = Sector(outer_radius=2, angle=female_angle, color=PINK, fill_opacity=0.8)
        male_sector = Sector(outer_radius=2, angle=male_angle, start_angle=female_angle, color=BLUE, fill_opacity=0.8)
        
        pie_group = V
