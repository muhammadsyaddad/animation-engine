from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
from math import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251117_042736/population_total.csv")
        
        # Create title
        title = Text("Population Data Visualization", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Assuming the CSV has columns like 'year' and 'population' or similar
        # Create a simple bar chart representation
        bars = VGroup()
        
        # Get first 10 rows of data for visualization
        data_subset = df.head(10)
        
        # Create bars based on the data
        max_height = 3
        bar_width = 0.5
        
        for i, (index, row) in enumerate(data_subset.iterrows()):
            # Assume second column contains the values to visualize
            value = float(row.iloc[1]) if len(row) > 1 else i + 1
            
            # Normalize the height
            normalized_height = (value / data_subset.iloc[:, 1].max()) * max_height
            
            bar = Rectangle(
                width=bar_width,
                height=normalized_height,
                color=BLUE,
                fill_opacity=0.7
            )
            
            # Position bars horizontally
            bar.move_to(LEFT * 4 + RIGHT * i * 0.8 + DOWN * 0.5)
            bars.add(bar)
            
            # Add label
            label = Text(str(row.iloc[0])[:4], font_size=16)
            label.next_to(bar, DOWN)
            bars.add(label)
        
        # Animate the bars
        self.play(Create(bars), run_time=3)
        
        # Add a simple legend or description
        description = Text("Data visualization from CSV", font_size=24)
        description.to_edge(DOWN)
        self.play(Write(description))
        
        self.wait(2)
