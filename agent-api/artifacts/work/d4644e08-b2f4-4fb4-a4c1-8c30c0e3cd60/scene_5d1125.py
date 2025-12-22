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
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251217_095737/20150425_helpnepalcity.csv")
        
        # Create title
        title = Text("Help Nepal City Data", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Get first few rows to display
        rows_to_show = min(5, len(df))
        
        # Create table header
        if len(df.columns) > 0:
            headers = list(df.columns)[:4]  # Show first 4 columns
            header_text = Text(" | ".join(headers), font_size=24)
            header_text.next_to(title, DOWN, buff=1)
            self.play(Write(header_text))
            
            # Create data rows
            data_group = VGroup()
            for i in range(rows_to_show):
                row_data = []
                for col in headers:
                    value = str(df.iloc[i][col])[:20]  # Truncate long values
                    row_data.append(value)
                
                row_text = Text(" | ".join(row_data), font_size=20)
                data_group.add(row_text)
            
            data_group.arrange(DOWN, buff=0.3)
            data_group.next_to(header_text, DOWN, buff=0.5)
            
            # Animate each row
            for row in data_group:
                self.play(FadeIn(row), run_time=0.5)
        
        # Add summary info
        summary = Text(f"Dataset contains {len(df)} rows and {len(df.columns)} columns", 
                      font_size=32, color=YELLOW)
        summary.to_edge(DOWN)
        self.play(Write(summary))
        
        self.wait(2)
