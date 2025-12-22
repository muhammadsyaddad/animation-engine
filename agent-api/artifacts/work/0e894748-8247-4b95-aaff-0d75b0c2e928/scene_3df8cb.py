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
        # Load the Amazon dataset
        df = pd.read_csv("/static/datasets/dataset_20251219_073201/Amazon.csv")
        
        # Create title
        title = Text("Amazon Dataset Visualization", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Show dataset info
        rows, cols = df.shape
        info_text = Text(f"Dataset: {rows} rows, {cols} columns", font_size=24)
        info_text.next_to(title, DOWN, buff=0.5)
        self.play(Write(info_text))
        
        # Display column names
        columns = list(df.columns)
        col_text = Text("Columns: " + ", ".join(columns[:5]), font_size=20)
        if len(columns) > 5:
            col_text = Text("Columns: " + ", ".join(columns[:5]) + "...", font_size=20)
        col_text.next_to(info_text, DOWN, buff=0.5)
        self.play(Write(col_text))
        
        # Create animated bars for first few numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            # Take first numeric column for visualization
            col_name = numeric_cols[0]
            values = df[col_name].dropna().head(10)
            
            bars = VGroup()
            labels = VGroup()
            
            max_val = values.max()
            for i, val in enumerate(values):
                bar_height = (val / max_val) * 2
                bar = Rectangle(width=0.5, height=bar_height, color=BLUE)
                bar.shift(LEFT * 4 + RIGHT * i * 0.7 + DOWN * 1)
                
                label = Text(f"{val:.1f}", font_size=16)
                label.next_to(bar, DOWN, buff=0.1)
                
                bars.add(bar)
                labels.add(label)
            
            chart_title = Text(f"First 10 values of {col_name}", font_size=20)
            chart_title.next_to(col_text, DOWN, buff=1)
            self.play(Write(chart_title))
            
            # Animate bars growing
            for bar, label in zip(bars, labels):
                self.play(GrowFromEdge(bar, DOWN), Write(label), run_time=0.3)
        
        self.wait(2)
