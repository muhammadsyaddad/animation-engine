from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
from math import *
import pandas as pd

class GenScene(Scene):
    def construct(self):
        # Load the dataset
        df = pd.read_csv("/static/datasets/dataset_20251123_063326/life_expectancy_years.csv")
        
        # Get a sample of countries and years for animation
        countries = df.columns[1:6].tolist()  # First 5 countries after index
        years = df.iloc[:20, 0].tolist()  # First 20 years
        
        # Create title
        title = Text("Life Expectancy Distribution Animation", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[0, len(countries), 1],
            y_range=[40, 85, 10],
            x_length=10,
            y_length=6,
            axis_config={"color": BLUE},
            x_axis_config={"numbers_to_include": range(len(countries))},
            y_axis_config={"numbers_to_include": range(40, 90, 10)},
        )
        axes.center()
        
        # Create country labels
        country_labels = VGroup()
        for i, country in enumerate(countries):
            label = Text(country[:8], font_size=20)  # Truncate long names
            label.next_to(axes.c2p(i, 40), DOWN)
            country_labels.add(label)
        
        self.play(Create(axes), Write(country_labels))
        
        # Create bars for distribution
        bars = VGroup()
        for i in range(len(countries)):
            bar = Rectangle(width=0.6, height=0.1, color=BLUE, fill_opacity=0.7)
            bar.move_to(axes.c2p(i, 40))
            bars.add(bar)
        
        self.play(Create(bars))
        
        # Animate through years
        year_text = Text(f"Year: {years[0]}", font_size=24)
        year_text.to_corner(UR)
        self.play(Write(year_text))
        
        for year_idx, year in enumerate(years):
            new_bars = VGroup()
            
            for i, country in enumerate(countries):
                try:
                    # Get life expectancy value for this country and year
                    value = df[df.iloc[:, 0] == year][country].iloc[0]
                    if pd.notna(value):
                        height = max(0.1, (value - 40) / 45 * 6)  # Scale to fit axes
                        color = interpolate_color(RED, GREEN, (value - 40) / 45)
                    else:
                        height = 0.1
                        color = GRAY
                except:
                    height = 0.1
                    color = GRAY
                
                new_bar = Rectangle(width=0.6, height=height, color=color, fill_opacity=0.7)
                new_bar.align_to(axes.c2p(i, 40), DOWN)
                new_bars.add(new_bar)
            
            # Update year text
            new_year_text = Text(f"Year: {year}", font_size=24)
            new_year_text.to_corner(UR)
            
            # Animate transformation
            if year_idx == 0:
                self.play(Transform(bars, new_bars), Transform(year_text, new_year_text), run_time=0.5)
            else:
                self.play(Transform(bars, new_bars), Transform(year_text, new_year_text), run_time=0.3)
        
        self.wait(2)
