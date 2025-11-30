from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Load the GDP per capita data
        df = pd.read_csv("/static/datasets/dataset_20251121_075148/GDP_per_capita.csv")
        
        # Create title
        title = Text("GDP per Capita by Country", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Get top 10 countries by GDP per capita
        df_sorted = df.nlargest(10, df.columns[-1])  # Assuming last column is most recent year
        
        # Create bar chart
        bars = VGroup()
        labels = VGroup()
        values = VGroup()
        
        max_value = df_sorted.iloc[:, -1].max()
        
        for i, (idx, row) in enumerate(df_sorted.iterrows()):
            country = row.iloc[0]  # Assuming first column is country name
            gdp_value = row.iloc[-1]  # Last column value
            
            # Create bar
            bar_height = (gdp_value / max_value) * 4
            bar = Rectangle(width=0.6, height=bar_height, fill_color=BLUE, fill_opacity=0.7)
            bar.move_to(LEFT * 4 + RIGHT * i * 0.8 + UP * bar_height/2)
            
            # Create country label
            label = Text(country[:8], font_size=16)  # Truncate long names
            label.next_to(bar, DOWN)
            label.rotate(-PI/4)
            
            # Create value label
            value_text = Text(f"${gdp_value:,.0f}", font_size=14)
            value_text.next_to(bar, UP, buff=0.1)
            
            bars.add(bar)
            labels.add(label)
            values.add(value_text)
        
        # Animate bars growing
        self.play(LaggedStart(*[GrowFromEdge(bar, DOWN) for bar in bars], lag_ratio=0.1))
        
        # Add labels
        self.play(Write(labels))
        self.play(Write(values))
        
        # Add axis labels
        y_label = Text("GDP per Capita (USD)", font_size=20)
        y_label.rotate(PI/2)
        y_label.to_edge(LEFT)
        
        x_label = Text("Countries", font_size=20)
        x_label.to_edge(DOWN)
        
        self.play(Write(y_label), Write(x_label))
        
        self.wait(3)
