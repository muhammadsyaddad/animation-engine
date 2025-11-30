from manim import *
from math import *
config.frame_size = (1280, 720)
config.frame_width = 10.0

from manim import *
from math import *

class GenScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-2*PI, 2*PI, PI/2],
            y_range=[-1.5, 1.5, 0.5],
            x_length=10,
            y_length=6,
            axis_config={"color": WHITE},
            x_axis_config={"numbers_to_include": [-2*PI, -PI, 0, PI, 2*PI]},
            y_axis_config={"numbers_to_include": [-1, 0, 1]}
        )
        
        sine_graph = axes.plot(lambda x: sin(x), x_range=[-2*PI, 2*PI], color=GREEN)
        
        title = Text("Wave of Life", font_size=48, color=WHITE)
        title.to_edge(UP)
        title.shift(LEFT * 8)
        
        self.play(Create(axes))
        self.play(Create(sine_graph))
        self.play(title.animate.shift(RIGHT * 8), run_time=2)
        self.wait(2)
