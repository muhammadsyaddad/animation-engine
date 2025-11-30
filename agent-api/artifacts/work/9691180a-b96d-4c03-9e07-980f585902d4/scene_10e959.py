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
        df = pd.read_csv("/static/datasets/dataset_20251123_143031/life_expectancy_years.csv")
        
        # Create title
        title = Text("Life Expectancy Data", font_size=48, color=BLUE)
        title.to_edge(UP)
        self.play(Write(title))
        
        # Get first few rows and columns for display
        sample_data = df.head(5).iloc[:, :4]  # First 5 rows, first 4 columns
        
        # Create table representation
        table_data = []
        
        # Add headers
        headers = list(sample_data.columns)
        header_row = [Text(str(col)[:10], font_size=24, color=YELLOW) for col in headers]
        table_data.append(header_row)
        
        # Add data rows
        for _, row in sample_data.iterrows():
            data_row = [Text(str(val)[:10], font_size=20, color=WHITE) for val in row]
            table_data.append(data_row)
        
        # Position table elements
        table_group = VGroup()
        for i, row in enumerate(table_data):
            row_group = VGroup(*row)
            row_group.arrange(RIGHT, buff=1.5)
            row_group.shift(DOWN * i * 0.8)
            table_group.add(row_group)
        
        table_group.center()
        table_group.shift(DOWN * 0.5)
        
        # Animate table creation
        for row in table_group:
            self.play(FadeIn(row), run_time=0.5)
        
        self.wait(2)
        
        # Create a simple bar chart if numeric data exists
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            self.play(FadeOut(table_group))
            
            # Use first numeric column for visualization
            col_name = numeric_cols[0]
            values = df[col_name].dropna().head(8)  # First 8 non-null values
            
            chart_title = Text(f"Chart: {col_name}", font_size=36, color=GREEN)
            chart_title.to_edge(UP)
            self.play(Transform(title, chart_title))
            
            # Create bars
            bars = VGroup()
            max_val = values.max()
            min_val = values.min()
            
            for i, val in enumerate(values):
                if pd.notna(val):
                    height = 3 * (val - min_val) / (max_val - min_val) if max_val != min_val else 1
                    bar = Rectangle(width=0.5, height=height, color=BLUE, fill_opacity=0.7)
                    bar.shift(LEFT * 3 + RIGHT * i * 0.8)
                    bar.shift(DOWN * (3 - height) / 2)
                    
                    # Add value label
                    label = Text(f"{val:.1f}", font_size=16, color=WHITE)
                    label.next_to(bar, UP, buff=0.1)
                    
                    bar_group = VGroup(bar, label)
                    bars.add(bar_group)
            
            bars.center()
            
            # Animate bars
            for bar in bars:
                self.play(GrowFromEdge(bar, DOWN), run_time=0.3)
        
        self.wait(3)
