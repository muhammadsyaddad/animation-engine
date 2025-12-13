"""
Sample datasets for generating template preview animations.

Each dataset is designed to showcase the template's capabilities
with visually appealing, recognizable data.
"""

import csv
import os
from pathlib import Path


def get_sample_data_dir() -> Path:
    """Get or create the sample data directory."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def create_bar_race_data() -> str:
    """
    Create sample data for Bar Chart Race template.
    Shows smartphone market share over years.
    """
    data = [
        # Year 2010
        {"Brand": "Nokia", "Year": 2010, "MarketShare": 35, "Region": "Europe"},
        {"Brand": "Samsung", "Year": 2010, "MarketShare": 21, "Region": "Asia"},
        {"Brand": "Apple", "Year": 2010, "MarketShare": 16, "Region": "Americas"},
        {"Brand": "LG", "Year": 2010, "MarketShare": 8, "Region": "Asia"},
        {"Brand": "Sony", "Year": 2010, "MarketShare": 5, "Region": "Asia"},
        {"Brand": "Huawei", "Year": 2010, "MarketShare": 2, "Region": "Asia"},
        # Year 2012
        {"Brand": "Samsung", "Year": 2012, "MarketShare": 31, "Region": "Asia"},
        {"Brand": "Apple", "Year": 2012, "MarketShare": 23, "Region": "Americas"},
        {"Brand": "Nokia", "Year": 2012, "MarketShare": 18, "Region": "Europe"},
        {"Brand": "LG", "Year": 2012, "MarketShare": 6, "Region": "Asia"},
        {"Brand": "Huawei", "Year": 2012, "MarketShare": 5, "Region": "Asia"},
        {"Brand": "Sony", "Year": 2012, "MarketShare": 4, "Region": "Asia"},
        # Year 2014
        {"Brand": "Samsung", "Year": 2014, "MarketShare": 28, "Region": "Asia"},
        {"Brand": "Apple", "Year": 2014, "MarketShare": 18, "Region": "Americas"},
        {"Brand": "Huawei", "Year": 2014, "MarketShare": 8, "Region": "Asia"},
        {"Brand": "Xiaomi", "Year": 2014, "MarketShare": 6, "Region": "Asia"},
        {"Brand": "LG", "Year": 2014, "MarketShare": 5, "Region": "Asia"},
        {"Brand": "Nokia", "Year": 2014, "MarketShare": 4, "Region": "Europe"},
        # Year 2016
        {"Brand": "Samsung", "Year": 2016, "MarketShare": 22, "Region": "Asia"},
        {"Brand": "Apple", "Year": 2016, "MarketShare": 15, "Region": "Americas"},
        {"Brand": "Huawei", "Year": 2016, "MarketShare": 12, "Region": "Asia"},
        {"Brand": "Oppo", "Year": 2016, "MarketShare": 7, "Region": "Asia"},
        {"Brand": "Xiaomi", "Year": 2016, "MarketShare": 6, "Region": "Asia"},
        {"Brand": "Vivo", "Year": 2016, "MarketShare": 5, "Region": "Asia"},
        # Year 2018
        {"Brand": "Samsung", "Year": 2018, "MarketShare": 21, "Region": "Asia"},
        {"Brand": "Apple", "Year": 2018, "MarketShare": 14, "Region": "Americas"},
        {"Brand": "Huawei", "Year": 2018, "MarketShare": 15, "Region": "Asia"},
        {"Brand": "Xiaomi", "Year": 2018, "MarketShare": 9, "Region": "Asia"},
        {"Brand": "Oppo", "Year": 2018, "MarketShare": 8, "Region": "Asia"},
        {"Brand": "Vivo", "Year": 2018, "MarketShare": 7, "Region": "Asia"},
        # Year 2020
        {"Brand": "Samsung", "Year": 2020, "MarketShare": 20, "Region": "Asia"},
        {"Brand": "Apple", "Year": 2020, "MarketShare": 16, "Region": "Americas"},
        {"Brand": "Huawei", "Year": 2020, "MarketShare": 14, "Region": "Asia"},
        {"Brand": "Xiaomi", "Year": 2020, "MarketShare": 12, "Region": "Asia"},
        {"Brand": "Oppo", "Year": 2020, "MarketShare": 9, "Region": "Asia"},
        {"Brand": "Vivo", "Year": 2020, "MarketShare": 8, "Region": "Asia"},
    ]

    path = get_sample_data_dir() / "bar_race_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Brand", "Year", "MarketShare", "Region"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_bubble_data() -> str:
    """
    Create sample data for Bubble Chart template.
    Shows GDP vs Life Expectancy with population as bubble size (Gapminder style).
    """
    data = [
        # Year 2000
        {"Country": "USA", "Year": 2000, "GDP": 35000, "LifeExpectancy": 77, "Population": 282, "Continent": "Americas"},
        {"Country": "China", "Year": 2000, "GDP": 2000, "LifeExpectancy": 72, "Population": 1270, "Continent": "Asia"},
        {"Country": "India", "Year": 2000, "GDP": 1500, "LifeExpectancy": 63, "Population": 1050, "Continent": "Asia"},
        {"Country": "Japan", "Year": 2000, "GDP": 32000, "LifeExpectancy": 81, "Population": 127, "Continent": "Asia"},
        {"Country": "Germany", "Year": 2000, "GDP": 28000, "LifeExpectancy": 78, "Population": 82, "Continent": "Europe"},
        {"Country": "Brazil", "Year": 2000, "GDP": 8000, "LifeExpectancy": 70, "Population": 175, "Continent": "Americas"},
        # Year 2010
        {"Country": "USA", "Year": 2010, "GDP": 48000, "LifeExpectancy": 78, "Population": 310, "Continent": "Americas"},
        {"Country": "China", "Year": 2010, "GDP": 5000, "LifeExpectancy": 75, "Population": 1340, "Continent": "Asia"},
        {"Country": "India", "Year": 2010, "GDP": 2500, "LifeExpectancy": 66, "Population": 1200, "Continent": "Asia"},
        {"Country": "Japan", "Year": 2010, "GDP": 40000, "LifeExpectancy": 83, "Population": 128, "Continent": "Asia"},
        {"Country": "Germany", "Year": 2010, "GDP": 42000, "LifeExpectancy": 80, "Population": 82, "Continent": "Europe"},
        {"Country": "Brazil", "Year": 2010, "GDP": 12000, "LifeExpectancy": 73, "Population": 195, "Continent": "Americas"},
        # Year 2020
        {"Country": "USA", "Year": 2020, "GDP": 63000, "LifeExpectancy": 78, "Population": 331, "Continent": "Americas"},
        {"Country": "China", "Year": 2020, "GDP": 12000, "LifeExpectancy": 77, "Population": 1400, "Continent": "Asia"},
        {"Country": "India", "Year": 2020, "GDP": 3500, "LifeExpectancy": 70, "Population": 1380, "Continent": "Asia"},
        {"Country": "Japan", "Year": 2020, "GDP": 42000, "LifeExpectancy": 84, "Population": 126, "Continent": "Asia"},
        {"Country": "Germany", "Year": 2020, "GDP": 50000, "LifeExpectancy": 81, "Population": 83, "Continent": "Europe"},
        {"Country": "Brazil", "Year": 2020, "GDP": 9000, "LifeExpectancy": 76, "Population": 213, "Continent": "Americas"},
    ]

    path = get_sample_data_dir() / "bubble_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Country", "Year", "GDP", "LifeExpectancy", "Population", "Continent"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_line_evolution_data() -> str:
    """
    Create sample data for Line Evolution template.
    Shows stock price over time.
    """
    data = [
        {"Date": "2023-01", "Price": 150, "Company": "TechCorp"},
        {"Date": "2023-02", "Price": 165, "Company": "TechCorp"},
        {"Date": "2023-03", "Price": 145, "Company": "TechCorp"},
        {"Date": "2023-04", "Price": 180, "Company": "TechCorp"},
        {"Date": "2023-05", "Price": 195, "Company": "TechCorp"},
        {"Date": "2023-06", "Price": 210, "Company": "TechCorp"},
        {"Date": "2023-07", "Price": 185, "Company": "TechCorp"},
        {"Date": "2023-08", "Price": 220, "Company": "TechCorp"},
        {"Date": "2023-09", "Price": 240, "Company": "TechCorp"},
        {"Date": "2023-10", "Price": 255, "Company": "TechCorp"},
        {"Date": "2023-11", "Price": 230, "Company": "TechCorp"},
        {"Date": "2023-12", "Price": 275, "Company": "TechCorp"},
    ]

    path = get_sample_data_dir() / "line_evolution_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Price", "Company"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_distribution_data() -> str:
    """
    Create sample data for Distribution/Histogram template.
    Shows test score distribution over years.
    """
    import random
    random.seed(42)

    data = []
    for year in [2020, 2021, 2022]:
        # Generate scores with a shifting mean
        base_mean = 65 + (year - 2020) * 5
        for i in range(50):
            score = max(0, min(100, int(random.gauss(base_mean, 12))))
            data.append({"Year": year, "Score": score, "Student": f"S{i+1}"})

    path = get_sample_data_dir() / "distribution_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Year", "Score", "Student"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_bento_grid_data() -> str:
    """
    Create sample data for Bento Grid/KPI Dashboard template.
    Shows company KPIs.
    """
    data = [
        {"Metric": "Revenue", "Value": 2500000, "Change": 15.3},
        {"Metric": "Users", "Value": 125000, "Change": 22.1},
        {"Metric": "Orders", "Value": 45000, "Change": 8.7},
        {"Metric": "Avg Order", "Value": 55.6, "Change": 5.2},
        {"Metric": "Retention", "Value": 87.5, "Change": 2.3},
        {"Metric": "NPS Score", "Value": 72, "Change": 12.0},
    ]

    path = get_sample_data_dir() / "bento_grid_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Metric", "Value", "Change"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_count_bar_data() -> str:
    """
    Create sample data for Count Bar Chart template.
    Shows product categories (to be counted).
    """
    data = []
    categories = [
        ("Electronics", 45),
        ("Clothing", 38),
        ("Food", 32),
        ("Books", 25),
        ("Sports", 20),
        ("Home", 18),
        ("Beauty", 15),
        ("Toys", 12),
    ]

    for category, count in categories:
        for i in range(count):
            data.append({"Category": category, "ItemID": f"{category[:3]}-{i+1:03d}"})

    path = get_sample_data_dir() / "count_bar_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Category", "ItemID"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_single_numeric_data() -> str:
    """
    Create sample data for Simple Bar Chart template.
    Shows sales by region.
    """
    data = [
        {"Region": "North America", "Sales": 4500000},
        {"Region": "Europe", "Sales": 3800000},
        {"Region": "Asia Pacific", "Sales": 3200000},
        {"Region": "Latin America", "Sales": 1500000},
        {"Region": "Middle East", "Sales": 900000},
        {"Region": "Africa", "Sales": 600000},
    ]

    path = get_sample_data_dir() / "single_numeric_sample.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Region", "Sales"])
        writer.writeheader()
        writer.writerows(data)

    return str(path)


def create_all_sample_data() -> dict[str, str]:
    """
    Create all sample datasets and return a mapping of template_id to file path.
    """
    return {
        "bar_race": create_bar_race_data(),
        "bubble": create_bubble_data(),
        "line_evolution": create_line_evolution_data(),
        "distribution": create_distribution_data(),
        "bento_grid": create_bento_grid_data(),
        "count_bar": create_count_bar_data(),
        "single_numeric": create_single_numeric_data(),
    }


if __name__ == "__main__":
    paths = create_all_sample_data()
    print("Created sample datasets:")
    for template_id, path in paths.items():
        print(f"  {template_id}: {path}")
