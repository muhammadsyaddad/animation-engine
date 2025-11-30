from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251117_042250/GDP_per_capita.csv")
        
        # Create title
        title = Text("GDP per Capita Animation", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Get the first few rows of data for animation
        countries = df.iloc[:5, 0].tolist() if len(df.columns) > 0 else ["Country A", "Country B", "Country C"]
        values = df.iloc[:5, 1].tolist() if len(df.columns) > 1 else [50000, 40000, 30000, 25000, 20000]
        
        # Normalize values for bar heights
        max_val = max(values) if values else 50000
        bar_heights = [3 * val / max_val for val in values]
        
        # Create bars
        bars = VGroup()
        labels = VGroup()
        
        for i, (country, height, value) in enumerate(zip(countries, bar_heights, values)):
            # Create bar
            bar = Rectangle(width=1, height=height, fill_color=BLUE, fill_opacity=0.7)
            bar.shift(LEFT * 4 + RIGHT * i * 2)
            bar.align_to(ORIGIN, DOWN)
            
            # Create country label
            country_label = Text(str(country)[:10], font_size=24)
            country_label.next_to(bar, DOWN)
            
            # Create value label
            value_label = Text(f"${value:,.0f}", font_size=20)
            value_label.next_to(bar, UP)
            
            bars.add(bar)
            labels.add(VGroup(country_label, value_label))
        
        # Animate bars growing
        self.play(
            *[GrowFromEdge(bar, DOWN) for bar in bars],
            run_time=2
        )
        
        # Add labels
        self.play(
            *[Write(label) for label in labels],
            run_time=1.5
        )
        
        # Add axis labels
        y_label = Text("GDP per Capita (USD)", font_size=32)
        y_label.rotate(PI/2)
        y_label.to_edge(LEFT)
        
        self.play(Write(y_label))
        
        self.wait(2)
