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
        df = pd.read_csv("/static/datasets/dataset_20251121_074828/Gini_by_contry.csv")
        
        # Create title
        title = Text("Gini Coefficient by Country", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Get top 10 countries for visualization
        df_sorted = df.nlargest(10, df.columns[1])  # Assuming second column has Gini values
        
        # Create bar chart
        bars = VGroup()
        labels = VGroup()
        
        max_value = df_sorted.iloc[:, 1].max()
        bar_width = 0.6
        bar_spacing = 0.8
        
        for i, (idx, row) in enumerate(df_sorted.iterrows()):
            country = str(row.iloc[0])[:10]  # Truncate long country names
            value = float(row.iloc[1])
            
            # Create bar
            bar_height = (value / max_value) * 4
            bar = Rectangle(width=bar_width, height=bar_height, color=BLUE)
            bar.move_to(LEFT * 4 + RIGHT * i * bar_spacing + UP * bar_height/2)
            
            # Create label
            label = Text(country, font_size=16)
            label.next_to(bar, DOWN)
            label.rotate(-PI/4)
            
            # Create value text
            value_text = Text(f"{value:.1f}", font_size=14)
            value_text.next_to(bar, UP, buff=0.1)
            
            bars.add(bar)
            labels.add(VGroup(label, value_text))
        
        # Animate bars
        self.play(Create(bars), run_time=2)
        self.play(Write(labels), run_time=2)
        
        # Add axis labels
        x_label = Text("Countries", font_size=24)
        x_label.to_edge(DOWN)
        y_label = Text("Gini Coefficient", font_size=24)
        y_label.rotate(PI/2)
        y_label.to_edge(LEFT)
        
        self.play(Write(x_label), Write(y_label))
        self.wait(2)
