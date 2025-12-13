#!/usr/bin/env python
"""
Demo Script: Smart Chart Inference

This script demonstrates the new data-driven chart inference system.
Run it to see how the system analyzes CSV data and recommends chart types.

Usage:
    python scripts/demo_chart_inference.py
    python scripts/demo_chart_inference.py /path/to/your/data.csv
"""

import sys
import os
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.tools.chart_inference import (
    analyze_schema,
    recommend_chart,
    get_best_chart,
    get_schema_summary,
    CHART_REQUIREMENTS,
)
from agents.tools.intent_detection import detect_animation_intent


# =============================================================================
# SAMPLE DATA
# =============================================================================

SAMPLE_BAR_RACE = """country,year,gdp
USA,2000,10000
USA,2001,10500
USA,2002,11000
China,2000,5000
China,2001,6000
China,2002,7500
Japan,2000,4500
Japan,2001,4600
Japan,2002,4700
Germany,2000,3000
Germany,2001,3100
Germany,2002,3200
UK,2000,2500
UK,2001,2600
UK,2002,2700
"""

SAMPLE_BUBBLE = """entity,x,y,r,time,group
USA,75,2.1,330,2000,Americas
USA,76,2.0,335,2001,Americas
China,70,1.7,1400,2000,Asia
China,72,1.6,1410,2001,Asia
Japan,82,1.4,126,2000,Asia
Japan,83,1.3,125,2001,Asia
"""

SAMPLE_WIDE = """country,2000,2001,2002,2003,2004
USA,100,110,120,130,140
China,50,60,75,90,110
Japan,80,82,84,86,88
Germany,70,72,74,76,78
"""


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_schema(csv_path: str):
    """Print analyzed schema for a CSV file"""
    print_header("DATA SCHEMA ANALYSIS")

    summary = get_schema_summary(csv_path)

    print(f"\n📊 Columns: {summary['columns']}")
    print(f"📝 Row count: {summary['row_count']}")
    print(f"⏱️  Has time column: {summary['has_time']} ({summary['time_column']})")
    print(f"🔢 Numeric columns: {summary['numeric_columns']}")
    print(f"📁 Categorical columns: {summary['categorical_columns']}")
    print(f"👥 Entity count: {summary['entity_count']}")
    print(f"📐 Is wide format: {summary['is_wide_format']}")

    print("\n📋 Column Types:")
    for col, col_type in summary['column_types'].items():
        print(f"   - {col}: {col_type}")


def print_recommendations(csv_path: str, user_prompt: str = None):
    """Print chart recommendations"""
    print_header("CHART RECOMMENDATIONS")

    if user_prompt:
        print(f"\n💬 User prompt: \"{user_prompt}\"")
    else:
        print("\n💬 User prompt: (none)")

    recommendations = recommend_chart(csv_path, user_prompt)

    print("\n🏆 Ranked Recommendations:\n")

    for i, rec in enumerate(recommendations, 1):
        # Emoji based on confidence
        if rec.confidence == "high":
            emoji = "🟢"
        elif rec.confidence == "medium":
            emoji = "🟡"
        else:
            emoji = "🔴"

        print(f"{i}. {emoji} {rec.chart_type.upper()}")
        print(f"   Score: {rec.score:.2f} | Confidence: {rec.confidence}")

        if rec.reasons:
            print("   Reasons:")
            for reason in rec.reasons[:3]:
                print(f"     {reason}")

        if rec.warnings:
            print("   Warnings:")
            for warning in rec.warnings[:2]:
                print(f"     ⚠️  {warning}")
        print()


def print_best_chart(csv_path: str, user_prompt: str = None):
    """Print the single best recommendation"""
    print_header("BEST CHART RECOMMENDATION")

    best = get_best_chart(csv_path, user_prompt, min_confidence="low")

    if best:
        print(f"\n✅ Recommended Chart: {best.chart_type.upper()}")
        print(f"   Score: {best.score:.2f}")
        print(f"   Confidence: {best.confidence}")
        print("\n   Why this chart:")
        for reason in best.reasons:
            print(f"   {reason}")
    else:
        print("\n❌ No confident recommendation available")


def print_intent_detection(message: str, csv_path: str = None):
    """Print intent detection results"""
    print_header("INTENT DETECTION")

    print(f"\n💬 Message: \"{message}\"")

    result = detect_animation_intent(message, csv_path)

    print(f"\n🎬 Animation Requested: {result.animation_requested}")
    print(f"📊 Chart Type: {result.chart_type}")
    print(f"🎯 Confidence: {result.confidence:.2f}")
    print(f"📈 Data Analyzed: {result.data_analyzed}")

    if result.recommended_charts:
        print(f"📋 Recommended Charts: {result.recommended_charts}")

    if result.reasons:
        print("\n📝 Reasons:")
        for reason in result.reasons[:5]:
            print(f"   - {reason}")


def demo_sample_data(name: str, csv_content: str, prompts: list):
    """Run demo with sample data"""
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        print("\n" + "#" * 60)
        print(f"# DEMO: {name}")
        print("#" * 60)

        # Show schema
        print_schema(csv_path)

        # Show recommendations without prompt
        print_recommendations(csv_path)

        # Show recommendations with prompts
        for prompt in prompts:
            print_recommendations(csv_path, prompt)

        # Show best chart
        print_best_chart(csv_path, prompts[0] if prompts else None)

        # Show intent detection
        if prompts:
            print_intent_detection(prompts[0], csv_path)

    finally:
        os.unlink(csv_path)


def main():
    print("\n" + "🚀 " * 20)
    print("\n   SMART CHART INFERENCE DEMO")
    print("\n" + "🚀 " * 20)

    # Check