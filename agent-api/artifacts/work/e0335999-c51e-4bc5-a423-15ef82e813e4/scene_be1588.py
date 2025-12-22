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
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251219_060255/2018-04-27_PalmedOr.csv")
        
        # Create title
        title = Text("Dataset: 2018-04-27_PalmedOr.csv", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Get basic info about the dataset
        num_rows, num_cols = df.shape
        
        # Create info text
        info_text = Text(f"Rows: {num_rows}, Columns: {num_cols}", font_size=24)
        info_text.next_to(title, DOWN, buff=0.5)
        self.play(Write(info_text))
        
        # Show column names if available
        if len(df.columns) > 0:
            cols_text = Text(f"Columns: {', '.join(df.columns[:5])}", font_size=20)
            if len(df.columns) > 5:
                cols_text = Text(f"Columns: {', '.join(df.columns[:5])}...", font_size=20)
            cols_text.next_to(info_text, DOWN, buff=0.3)
            self.play(Write(cols_text))
        
        # Create a simple bar chart if numeric data exists
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            # Use first numeric column for visualization
            col_name = numeric_cols[0]
            values = df[col_name].dropna().head(10)  # First 10 non-null values
            
            # Create bars
            bars = VGroup()
            max_val = max(values) if len(values) > 0 else 1
            
            for i, val in enumerate(values):
                height = (val / max_val) * 2 if max_val != 0 else 0.1
                bar = Rectangle(width=0.3, height=height, color=BLUE)
                bar.move_to(LEFT * 3 + RIGHT * i * 0.5 + UP * height/2)
                bars.add(bar)
            
            bars.move_to(ORIGIN)
            chart_title = Text(f"Sample Data: {col_name}", font_size=20)
            chart_title.next_to(bars, DOWN, buff=0.5)
            
            self.play(Create(bars))
            self.play(Write(chart_title))
        
        self.wait(2)
