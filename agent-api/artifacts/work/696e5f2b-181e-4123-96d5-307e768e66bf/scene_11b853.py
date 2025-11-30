from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
from math import *
import random

class GenScene(Scene):
    def construct(self):
        # Create dummy data
        categories = ["A", "B", "C", "D", "E"]
        values = [25, 40, 15, 30, 35]
        
        # Title
        title = Text("Data Visualization Animation", font_size=36, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))
        self.wait(0.5)
        
        # Bar Chart Animation
        bar_title = Text("Bar Chart", font_size=24, color=GREEN)
        bar_title.next_to(title, DOWN, buff=0.5)
        self.play(Write(bar_title))
        
        bars = VGroup()
        labels = VGroup()
        
        for i, (cat, val) in enumerate(zip(categories, values)):
            bar = Rectangle(width=0.8, height=val/10, color=BLUE, fill_opacity=0.7)
            bar.shift(LEFT*4 + RIGHT*i*1.2 + UP*val/20)
            
            label = Text(cat, font_size=18)
            label.next_to(bar, DOWN, buff=0.1)
            
            value_text = Text(str(val), font_size=14, color=WHITE)
            value_text.move_to(bar.get_center())
            
            bars.add(VGroup(bar, value_text))
            labels.add(label)
        
        self.play(Create(bars), Write(labels), run_time=2)
        self.wait(1)
        
        # Transform to Line Chart
        self.play(FadeOut(bars), FadeOut(labels), FadeOut(bar_title))
        
        line_title = Text("Line Chart", font_size=24, color=RED)
        line_title.next_to(title, DOWN, buff=0.5)
        self.play(Write(line_title))
        
        # Create axes
        axes = Axes(
            x_range=[0, 6, 1],
            y_range=[0, 50, 10],
            x_length=8,
            y_length=4,
            axis_config={"color": WHITE}
        )
        axes.shift(DOWN*0.5)
        
        self.play(Create(axes))
        
        # Plot points and line
        points = []
        dots = VGroup()
        
        for i, val in enumerate(values):
            point = axes.coords_to_point(i+1, val)
            points.append(point)
            dot = Dot(point, color=YELLOW, radius=0.08)
            dots.add(dot)
        
        line = VMobject()
        line.set_points_as_corners(points)
        line.set_stroke(RED, width=3)
        
        self.play(Create(dots))
        self.play(Create(line), run_time=2)
        self.wait(1)
        
        # Transform to Pie Chart
        self.play(FadeOut(axes), FadeOut(dots), FadeOut(line), FadeOut(line_title))
        
        pie_title = Text("Pie Chart", font_size=24, color=PURPLE)
        pie_title.next_to(title, DOWN, buff=0.5)
        self.play(Write(pie_title))
        
        # Create pie chart
        total = sum(values)
        angles = [val/total * 2*PI for val in values]
        colors = [RED, BLUE, GREEN, YELLOW, PURPLE]
        
        pie_slices = VGroup()
        current_angle = 0
        
        for i, (angle, color) in enumerate(zip(angles, colors)):
            slice = Sector(
                inner_radius=0,
                outer_radius=2,
                start_angle=current_angle,
                angle=angle,
                color=color,
                fill_opacity=0.8
            )
            pie_slices.add(slice)
            current_angle += angle
        
        self.play(Create(pie_slices), run_time=3)
        
        # Add percentage labels
        current_angle = 0
        percentages = VGroup()
        
        for i, (angle, val) in enumerate(zip(angles, values)):
            percentage = val/total * 100
            mid_angle = current_angle + angle/2
            label_pos = 1.5 * np.array([cos(mid_angle), sin(mid_angle), 0])
            
            percent_text = Text(f"{percentage:.1f}%", font_size=14, color=WHITE)
            percent_text.move_to(label_pos)
            percentages.add(percent_
