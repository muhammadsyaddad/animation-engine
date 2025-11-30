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
        df = pd.read_csv("/static/datasets/dataset_20251123_142001/life_expectancy_years.csv")
        
        # Create title
        title = Text("Life Expectancy Over Time", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[1950, 2020, 10],
            y_range=[40, 85, 5],
            x_length=10,
            y_length=6,
            axis_config={"color": BLUE},
            x_axis_config={
                "numbers_to_include": np.arange(1950, 2021, 10),
                "font_size": 24,
            },
            y_axis_config={
                "numbers_to_include": np.arange(40, 86, 10),
                "font_size": 24,
            },
        )
        
        # Add axis labels
        x_label = axes.get_x_axis_label("Year")
        y_label = axes.get_y_axis_label("Life Expectancy (Years)")
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        
        # Animate data points for a few countries
        countries = df.columns[1:6] if len(df.columns) > 6 else df.columns[1:]
        colors = [RED, GREEN, YELLOW, PURPLE, ORANGE]
        
        for i, country in enumerate(countries):
            if country in df.columns:
                # Get data points
                years = df.iloc[:, 0].values
                values = df[country].values
                
                # Filter out NaN values
                valid_data = [(year, val) for year, val in zip(years, values) if not pd.isna(val)]
                
                if valid_data:
                    # Create line graph
                    points = [axes.coords_to_point(year, val) for year, val in valid_data]
                    line = VMobject()
                    line.set_points_as_corners(points)
                    line.set_color(colors[i % len(colors)])
                    
                    # Create country label
                    label = Text(str(country), font_size=24, color=colors[i % len(colors)])
                    label.next_to(points[-1], RIGHT)
                    
                    self.play(Create(line), Write(label), run_time=2)
        
        self.wait(2)
