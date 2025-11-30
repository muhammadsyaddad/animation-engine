from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Read the CSV data
        df = pd.read_csv("/static/datasets/dataset_20251123_063013/GDP_per_capita.csv")
        
        # Create title
        title = Text("GDP per Capita Animation", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Assuming the CSV has columns like 'Country' and 'GDP_per_capita'
        # Get first few countries for animation
        countries = df.iloc[:5]  # First 5 countries
        
        # Create bars for each country
        bars = VGroup()
        labels = VGroup()
        
        max_gdp = countries.iloc[:, 1].max() if len(countries.columns) > 1 else 50000
        
        for i, (idx, row) in enumerate(countries.iterrows()):
            country_name = str(row.iloc[0])  # First column as country name
            gdp_value = float(row.iloc[1]) if len(row) > 1 else 30000  # Second column as GDP
            
            # Create bar
            bar_height = (gdp_value / max_gdp) * 4
            bar = Rectangle(width=0.8, height=bar_height, color=BLUE)
            bar.shift(LEFT * 4 + RIGHT * i * 1.5 + DOWN * 1)
            
            # Create label
            label = Text(country_name[:8], font_size=24)  # Truncate long names
            label.next_to(bar, DOWN)
            
            # Create value text
            value_text = Text(f"${gdp_value:,.0f}", font_size=20)
            value_text.next_to(bar, UP)
            
            bars.add(bar)
            labels.add(VGroup(label, value_text))
        
        # Animate bars growing
        for bar, label in zip(bars, labels):
            self.play(GrowFromEdge(bar, DOWN), Write(label), run_time=0.8)
        
        # Add axis labels
        x_label = Text("Countries", font_size=32)
        x_label.shift(DOWN * 3)
        
        y_label = Text("GDP per Capita (USD)", font_size=32)
        y_label.rotate(PI/2)
        y_label.shift(LEFT * 6)
        
        self.play(Write(x_label), Write(y_label))
        
        self.wait(2)
