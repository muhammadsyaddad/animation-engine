from manim import *
from math import *
config.frame_size = (1920, 1080)
config.frame_width = 14.22

from manim import *

class GenScene(Scene):
    def construct(self):
        # Create sample GDP data since CSV file is not available
        sample_data = [
            ("USA", 65000),
            ("Germany", 46000),
            ("Japan", 40000),
            ("UK", 42000),
            ("France", 39000)
        ]
        
        # Create title
        title = Text("GDP per Capita Animation", font_size=48)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Create bars for each country
        bars = VGroup()
        labels = VGroup()
        
        max_gdp = max([gdp for _, gdp in sample_data])
        
        for i, (country_name, gdp_value) in enumerate(sample_data):
            # Create bar
            bar_height = (gdp_value / max_gdp) * 4
            bar = Rectangle(width=0.8, height=bar_height, color=BLUE)
            bar.shift(LEFT * 4 + RIGHT * i * 1.5 + DOWN * 1)
            
            # Create label
            label = Text(country_name[:8], font_size=24)
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
