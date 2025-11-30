from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251121_075222/Group_lable.csv")
        
        # Create title
        title = Text("Dataset Visualization", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Display basic info about the dataset
        info_text = Text(f"Dataset contains {len(df)} rows and {len(df.columns)} columns", font_size=24)
        info_text.next_to(title, DOWN, buff=0.5)
        self.play(Write(info_text))
        
        # Show column names
        columns_title = Text("Columns:", font_size=32)
        columns_title.next_to(info_text, DOWN, buff=0.8)
        self.play(Write(columns_title))
        
        # Display first few column names
        col_texts = []
        for i, col in enumerate(df.columns[:5]):  # Show first 5 columns
            col_text = Text(f"• {col}", font_size=20)
            if i == 0:
                col_text.next_to(columns_title, DOWN, buff=0.3)
            else:
                col_text.next_to(col_texts[i-1], DOWN, buff=0.2)
            col_texts.append(col_text)
            self.play(Write(col_text), run_time=0.5)
        
        # If there are more columns, show count
        if len(df.columns) > 5:
            more_text = Text(f"... and {len(df.columns) - 5} more columns", font_size=18, color=GRAY)
            more_text.next_to(col_texts[-1], DOWN, buff=0.2)
            self.play(Write(more_text))
        
        self.wait(2)
        
        # Fade out all elements
        self.play(*[FadeOut(mob) for mob in self.mobjects])
