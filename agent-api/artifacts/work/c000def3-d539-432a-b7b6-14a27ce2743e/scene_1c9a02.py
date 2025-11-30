from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251121_035803/population_total.csv")
        
        # Create title
        title = Text("Population Data Visualization", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Assuming the CSV has columns like 'Year' and 'Population' or similar
        # Create a simple bar chart representation
        axes = Axes(
            x_range=[0, len(df), 1],
            y_range=[0, df.iloc[:, 1].max() * 1.1, df.iloc[:, 1].max() / 5],
            x_length=10,
            y_length=6,
            axis_config={"color": BLUE},
        )
        
        # Add axes
        self.play(Create(axes))
        
        # Create bars for data points
        bars = VGroup()
        for i, row in df.iterrows():
            if i < 10:  # Limit to first 10 data points for visibility
                bar_height = row.iloc[1] / df.iloc[:, 1].max() * 6
                bar = Rectangle(
                    width=0.8,
                    height=bar_height,
                    color=BLUE,
                    fill_opacity=0.7
                )
                bar.move_to(axes.c2p(i + 0.5, bar_height/2))
                bars.add(bar)
        
        # Animate bars appearing
        self.play(Create(bars), run_time=3)
        
        # Add data labels
        labels = VGroup()
        for i, bar in enumerate(bars):
            if i < len(df):
                label = Text(f"{df.iloc[i, 1]:.0f}", font_size=24)
                label.next_to(bar, UP, buff=0.1)
                labels.add(label)
        
        self.play(Write(labels))
        
        # Final pause
        self.wait(2)
