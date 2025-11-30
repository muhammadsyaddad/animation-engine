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
        df = pd.read_csv("/static/datasets/dataset_20251117_044250/Gini_by_contry.csv")
        
        # Clean and prepare data
        df = df.dropna()
        countries = df.iloc[:, 0].tolist()[:10]  # First 10 countries
        gini_values = df.iloc[:, 1].tolist()[:10]  # Gini coefficients
        
        # Normalize Gini values for bubble sizes (0.2 to 2.0 scale)
        max_gini = max(gini_values)
        min_gini = min(gini_values)
        normalized_sizes = [0.3 + 1.5 * (val - min_gini) / (max_gini - min_gini) for val in gini_values]
        
        # Create title
        title = Text("Gini Coefficient by Country", font_size=36, color=WHITE)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Create bubbles and labels
        bubbles = []
        labels = []
        
        # Arrange bubbles in a grid pattern
        positions = []
        for i in range(len(countries)):
            row = i // 5
            col = i % 5
            x = -4 + col * 2
            y = 1 - row * 2.5
            positions.append([x, y, 0])
        
        # Create and animate bubbles
        for i, (country, gini, size, pos) in enumerate(zip(countries, gini_values, normalized_sizes, positions)):
            # Create bubble with color based on Gini value
            color_intensity = (gini - min_gini) / (max_gini - min_gini)
            bubble_color = interpolate_color(BLUE, RED, color_intensity)
            
            bubble = Circle(radius=size, color=bubble_color, fill_opacity=0.7)
            bubble.move_to(pos)
            
            # Create country label
            country_label = Text(country[:8], font_size=16, color=WHITE)
            country_label.next_to(bubble, DOWN, buff=0.1)
            
            # Create Gini value label
            gini_label = Text(f"{gini:.2f}", font_size=14, color=WHITE)
            gini_label.move_to(bubble.get_center())
            
            bubbles.append(bubble)
            labels.append(VGroup(country_label, gini_label))
        
        # Animate bubbles appearing one by one
        for bubble, label in zip(bubbles, labels):
            self.play(
                GrowFromCenter(bubble),
                FadeIn(label),
                run_time=0.5
            )
        
        # Create legend
        legend_title = Text("Gini Coefficient Scale", font_size=20, color=WHITE)
        legend_title.to_corner(DR, buff=1)
        legend_title.shift(UP * 2)
        
        low_bubble = Circle(radius=0.2, color=BLUE, fill_opacity=0.7)
        low_label = Text("Low Inequality", font_size=14, color=WHITE)
        low_group = VGroup(low_bubble, low_label.next_to(low_bubble, RIGHT))
        low_group.next_to(legend_title, DOWN, aligned_edge=LEFT)
        
        high_bubble = Circle(radius=0.4, color=RED, fill_opacity=0.7)
        high_label = Text("High Inequality", font_size=14, color=WHITE)
        high_group = VGroup(high_bubble, high_label.next_to(high_bubble, RIGHT))
        high_group.next_to(low_group, DOWN, aligned_edge=LEFT)
        
        self.play(
            Write(legend_title),
            FadeIn(low_group),
            FadeIn(high_group)
        )
        
        # Final pause
        self.wait(2)
