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
        df = pd.read_csv("/static/datasets/dataset_20251117_044717/Gini_by_contry.csv")
        
        # Get first 10 countries for better visualization
        df_subset = df.head(10)
        countries = df_subset.iloc[:, 0].tolist()  # First column (countries)
        gini_values = df_subset.iloc[:, 1].tolist()  # Second column (Gini values)
        
        # Create title
        title = Text("Gini Coefficient by Country", font_size=36, color=WHITE)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[0, len(countries), 1],
            y_range=[0, max(gini_values) * 1.1, 10],
            x_length=10,
            y_length=6,
            axis_config={"color": WHITE},
            tips=False
        )
        axes.shift(DOWN * 0.5)
        
        # Create y-axis label
        y_label = Text("Gini Coefficient", font_size=24, color=WHITE)
        y_label.rotate(PI/2)
        y_label.next_to(axes.y_axis, LEFT)
        
        self.play(Create(axes), Write(y_label))
        
        # Create bars
        bars = VGroup()
        bar_labels = VGroup()
        
        colors = [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, PINK, TEAL, MAROON, GRAY]
        
        for i, (country, value) in enumerate(zip(countries, gini_values)):
            # Create bar
            bar_height = (value / max(gini_values)) * 5
            bar = Rectangle(
                width=0.6,
                height=bar_height,
                color=colors[i % len(colors)],
                fill_opacity=0.8
            )
            bar.move_to(axes.coords_to_point(i + 0.5, bar_height/2))
            bars.add(bar)
            
            # Create country label
            country_label = Text(country[:8], font_size=16, color=WHITE)
            country_label.rotate(-PI/4)
            country_label.next_to(axes.coords_to_point(i + 0.5, 0), DOWN, buff=0.3)
            bar_labels.add(country_label)
            
            # Create value label on top of bar
            value_label = Text(f"{value:.1f}", font_size=14, color=WHITE)
            value_label.next_to(bar, UP, buff=0.1)
            bar_labels.add(value_label)
        
        # Animate bars growing
        for bar in bars:
            original_height = bar.height
            bar.stretch_to_fit_height(0.01)
            bar.move_to(axes.coords_to_point(bars.submobjects.index(bar) + 0.5, 0.005))
        
        self.play(Create(bar_labels))
        
        # Animate bars growing to full height
        animations = []
        for i, bar in enumerate(bars):
            target_height = (gini_values[i] / max(gini_values)) * 5
            target_bar = Rectangle(
                width=0.6,
                height=target_height,
                color=colors[i % len(colors)],
                fill_opacity=0.8
            )
            target_bar.move_to(axes.coords_to_point(i + 0.5, target_height/2))
            animations.append(Transform(bar, target_bar))
        
        self.play(*animations, run_time=2)
        
        # Add a subtitle with statistics
        avg_gini = sum(gini_values) / len(gini_values)
        subtitle = Text(f"Average Gini Coefficient: {avg_gini:.2f}", font_size=20, color=YELLOW)
        subtitle.to_edge(DOWN)
        self.play(Write(subtitle))
        
        self.wait(2)
