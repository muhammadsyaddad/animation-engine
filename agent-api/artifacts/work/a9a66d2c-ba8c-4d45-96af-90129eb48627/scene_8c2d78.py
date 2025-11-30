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
        df = pd.read_csv("/static/datasets/dataset_20251121_075036/children_per_woman_total_fertility.csv")
        
        # Get the first few countries and years for animation
        countries = df.columns[1:6]  # Skip first column (years) and take 5 countries
        years = df.iloc[:10, 0].values  # Take first 10 years
        
        # Create title
        title = Text("Total Fertility Rate by Country", font_size=36)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Create axes
        axes = Axes(
            x_range=[0, len(years), 1],
            y_range=[0, 8, 1],
            x_length=10,
            y_length=6,
            axis_config={"color": BLUE},
            x_axis_config={"numbers_to_include": range(0, len(years), 2)},
            y_axis_config={"numbers_to_include": range(0, 9, 1)},
        )
        axes.shift(DOWN * 0.5)
        
        # Add axis labels
        x_label = Text("Years", font_size=24)
        x_label.next_to(axes.x_axis, DOWN)
        y_label = Text("Children per Woman", font_size=24)
        y_label.next_to(axes.y_axis, LEFT).rotate(PI/2)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        
        # Colors for different countries
        colors = [RED, GREEN, YELLOW, PURPLE, ORANGE]
        
        # Create and animate lines for each country
        for i, country in enumerate(countries):
            if country in df.columns:
                # Get data for this country
                country_data = []
                for year in years:
                    year_row = df[df.iloc[:, 0] == year]
                    if not year_row.empty and not pd.isna(year_row[country].iloc[0]):
                        country_data.append(float(year_row[country].iloc[0]))
                    else:
                        country_data.append(0)
                
                # Create points for the line
                points = []
                for j, value in enumerate(country_data):
                    point = axes.coords_to_point(j, value)
                    points.append(point)
                
                # Create the line
                if len(points) > 1:
                    line = VMobject()
                    line.set_points_as_corners(points)
                    line.set_color(colors[i % len(colors)])
                    line.set_stroke(width=3)
                    
                    # Create country label
                    label = Text(country[:15], font_size=20, color=colors[i % len(colors)])
                    label.next_to(axes, RIGHT).shift(UP * (2 - i * 0.5))
                    
                    # Animate the line and label
                    self.play(Create(line), Write(label), run_time=1.5)
        
        self.wait(2)
