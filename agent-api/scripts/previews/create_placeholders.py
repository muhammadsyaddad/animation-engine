"""
Create placeholder SVG images for template previews.

These serve as immediate fallbacks before actual GIF previews are generated.
Each placeholder shows a stylized representation of what the template produces.

Usage:
    python -m scripts.previews.create_placeholders
"""

from __future__ import annotations

import os
from pathlib import Path


def get_artifacts_dir() -> Path:
    """Get the artifacts directory, handling both local and Docker environments."""
    # Try relative to this file first
    file_based = Path(__file__).parent.parent.parent / "artifacts"
    if file_based.exists():
        return file_based

    # Fall back to working directory (for Docker)
    cwd_based = Path(os.getcwd()) / "artifacts"
    cwd_based.mkdir(parents=True, exist_ok=True)
    return cwd_based


def get_previews_dir() -> Path:
    """Get the previews directory, creating it if necessary."""
    previews_dir = get_artifacts_dir() / "previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    return previews_dir


# Legacy constants for backward compatibility
ARTIFACTS_DIR = get_artifacts_dir()
PREVIEWS_DIR = get_previews_dir()


# SVG templates for each animation type
SVG_TEMPLATES = {
    "bar_race": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_bar_race" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="bar1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#60a5fa;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="bar2" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#a78bfa;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="bar3" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ec4899;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#f472b6;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="bar4" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#10b981;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#34d399;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="bar5" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#f59e0b;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#fbbf24;stop-opacity:1"/>
    </linearGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg_bar_race)"/>
  <!-- Bars -->
  <rect x="80" y="50" width="320" height="28" rx="4" fill="url(#bar1)" opacity="0.9"/>
  <rect x="80" y="88" width="260" height="28" rx="4" fill="url(#bar2)" opacity="0.9"/>
  <rect x="80" y="126" width="200" height="28" rx="4" fill="url(#bar3)" opacity="0.9"/>
  <rect x="80" y="164" width="150" height="28" rx="4" fill="url(#bar4)" opacity="0.9"/>
  <rect x="80" y="202" width="100" height="28" rx="4" fill="url(#bar5)" opacity="0.9"/>
  <!-- Labels -->
  <text x="70" y="70" font-family="system-ui, sans-serif" font-size="12" fill="#94a3b8" text-anchor="end">USA</text>
  <text x="70" y="108" font-family="system-ui, sans-serif" font-size="12" fill="#94a3b8" text-anchor="end">China</text>
  <text x="70" y="146" font-family="system-ui, sans-serif" font-size="12" fill="#94a3b8" text-anchor="end">Japan</text>
  <text x="70" y="184" font-family="system-ui, sans-serif" font-size="12" fill="#94a3b8" text-anchor="end">Germany</text>
  <text x="70" y="222" font-family="system-ui, sans-serif" font-size="12" fill="#94a3b8" text-anchor="end">UK</text>
  <!-- Year label -->
  <text x="400" y="250" font-family="system-ui, sans-serif" font-size="36" fill="#ffffff" opacity="0.15" font-weight="bold">2024</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",

    "bubble": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_bubble" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <radialGradient id="bubble1" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#60a5fa;stop-opacity:0.8"/>
      <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:0.6"/>
    </radialGradient>
    <radialGradient id="bubble2" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#a78bfa;stop-opacity:0.8"/>
      <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:0.6"/>
    </radialGradient>
    <radialGradient id="bubble3" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#34d399;stop-opacity:0.8"/>
      <stop offset="100%" style="stop-color:#10b981;stop-opacity:0.6"/>
    </radialGradient>
    <radialGradient id="bubble4" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#f472b6;stop-opacity:0.8"/>
      <stop offset="100%" style="stop-color:#ec4899;stop-opacity:0.6"/>
    </radialGradient>
    <radialGradient id="bubble5" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#fbbf24;stop-opacity:0.8"/>
      <stop offset="100%" style="stop-color:#f59e0b;stop-opacity:0.6"/>
    </radialGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg_bubble)"/>
  <!-- Axes -->
  <line x1="60" y1="230" x2="440" y2="230" stroke="#4b5563" stroke-width="1"/>
  <line x1="60" y1="40" x2="60" y2="230" stroke="#4b5563" stroke-width="1"/>
  <!-- Grid lines -->
  <line x1="60" y1="135" x2="440" y2="135" stroke="#374151" stroke-width="0.5" stroke-dasharray="4"/>
  <line x1="250" y1="40" x2="250" y2="230" stroke="#374151" stroke-width="0.5" stroke-dasharray="4"/>
  <!-- Bubbles -->
  <circle cx="350" cy="80" r="45" fill="url(#bubble1)"/>
  <circle cx="150" cy="180" r="35" fill="url(#bubble2)"/>
  <circle cx="280" cy="140" r="28" fill="url(#bubble3)"/>
  <circle cx="180" cy="100" r="22" fill="url(#bubble4)"/>
  <circle cx="380" cy="170" r="18" fill="url(#bubble5)"/>
  <circle cx="120" cy="120" r="15" fill="url(#bubble1)" opacity="0.7"/>
  <!-- Axis labels -->
  <text x="250" y="255" font-family="system-ui, sans-serif" font-size="10" fill="#6b7280" text-anchor="middle">GDP per Capita →</text>
  <text x="25" y="135" font-family="system-ui, sans-serif" font-size="10" fill="#6b7280" text-anchor="middle" transform="rotate(-90 25 135)">Life Expectancy →</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",

    "line_evolution": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_line" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="areaGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.3"/>
      <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:0"/>
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <rect width="480" height="270" fill="url(#bg_line)"/>
  <!-- Grid -->
  <line x1="60" y1="230" x2="440" y2="230" stroke="#4b5563" stroke-width="1"/>
  <line x1="60" y1="40" x2="60" y2="230" stroke="#4b5563" stroke-width="1"/>
  <line x1="60" y1="135" x2="440" y2="135" stroke="#374151" stroke-width="0.5" stroke-dasharray="4"/>
  <line x1="60" y1="85" x2="440" y2="85" stroke="#374151" stroke-width="0.5" stroke-dasharray="4"/>
  <line x1="60" y1="185" x2="440" y2="185" stroke="#374151" stroke-width="0.5" stroke-dasharray="4"/>
  <!-- Area fill -->
  <path d="M60,180 Q120,160 180,140 T300,100 T380,70 L380,230 L60,230 Z" fill="url(#areaGrad)"/>
  <!-- Line -->
  <path d="M60,180 Q120,160 180,140 T300,100 T380,70" stroke="url(#lineGrad)" stroke-width="3" fill="none" stroke-linecap="round" filter="url(#glow)"/>
  <!-- Tracking dot -->
  <circle cx="380" cy="70" r="8" fill="#8b5cf6" filter="url(#glow)"/>
  <circle cx="380" cy="70" r="4" fill="#ffffff"/>
  <!-- Value label -->
  <rect x="350" y="40" width="50" height="20" rx="4" fill="rgba(139,92,246,0.2)"/>
  <text x="375" y="54" font-family="system-ui, sans-serif" font-size="11" fill="#a78bfa" text-anchor="middle">$275</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",

    "distribution": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_dist" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="histBar" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f97316;stop-opacity:0.9"/>
      <stop offset="100%" style="stop-color:#ea580c;stop-opacity:0.7"/>
    </linearGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg_dist)"/>
  <!-- Axes -->
  <line x1="60" y1="230" x2="420" y2="230" stroke="#4b5563" stroke-width="1"/>
  <line x1="60" y1="40" x2="60" y2="230" stroke="#4b5563" stroke-width="1"/>
  <!-- Histogram bars -->
  <rect x="80" y="200" width="30" height="30" fill="url(#histBar)" rx="2"/>
  <rect x="115" y="170" width="30" height="60" fill="url(#histBar)" rx="2"/>
  <rect x="150" y="130" width="30" height="100" fill="url(#histBar)" rx="2"/>
  <rect x="185" y="90" width="30" height="140" fill="url(#histBar)" rx="2"/>
  <rect x="220" y="60" width="30" height="170" fill="url(#histBar)" rx="2"/>
  <rect x="255" y="80" width="30" height="150" fill="url(#histBar)" rx="2"/>
  <rect x="290" y="110" width="30" height="120" fill="url(#histBar)" rx="2"/>
  <rect x="325" y="150" width="30" height="80" fill="url(#histBar)" rx="2"/>
  <rect x="360" y="190" width="30" height="40" fill="url(#histBar)" rx="2"/>
  <!-- Normal curve overlay -->
  <path d="M80,215 Q120,200 160,150 T240,60 T320,150 T400,215" stroke="#fbbf24" stroke-width="2" fill="none" stroke-dasharray="6" opacity="0.6"/>
  <!-- Labels -->
  <text x="240" y="255" font-family="system-ui, sans-serif" font-size="10" fill="#6b7280" text-anchor="middle">Score Distribution</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",

    "bento_grid": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_bento" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="card1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:#1e40af;stop-opacity:0.1"/>
    </linearGradient>
    <linearGradient id="card2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:#6d28d9;stop-opacity:0.1"/>
    </linearGradient>
    <linearGradient id="card3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981;stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:#059669;stop-opacity:0.1"/>
    </linearGradient>
    <linearGradient id="card4" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b;stop-opacity:0.2"/>
      <stop offset="100%" style="stop-color:#d97706;stop-opacity:0.1"/>
    </linearGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg_bento)"/>
  <!-- Card 1 - Revenue -->
  <rect x="30" y="30" width="140" height="100" rx="12" fill="url(#card1)" stroke="#3b82f6" stroke-width="1" stroke-opacity="0.3"/>
  <text x="50" y="55" font-family="system-ui, sans-serif" font-size="11" fill="#6b7280">Revenue</text>
  <text x="50" y="85" font-family="system-ui, sans-serif" font-size="24" fill="#ffffff" font-weight="bold">$2.5M</text>
  <text x="50" y="110" font-family="system-ui, sans-serif" font-size="11" fill="#10b981">↑ 15.3%</text>
  <!-- Card 2 - Users -->
  <rect x="180" y="30" width="140" height="100" rx="12" fill="url(#card2)" stroke="#8b5cf6" stroke-width="1" stroke-opacity="0.3"/>
  <text x="200" y="55" font-family="system-ui, sans-serif" font-size="11" fill="#6b7280">Users</text>
  <text x="200" y="85" font-family="system-ui, sans-serif" font-size="24" fill="#ffffff" font-weight="bold">125K</text>
  <text x="200" y="110" font-family="system-ui, sans-serif" font-size="11" fill="#10b981">↑ 22.1%</text>
  <!-- Card 3 - Orders -->
  <rect x="330" y="30" width="120" height="100" rx="12" fill="url(#card3)" stroke="#10b981" stroke-width="1" stroke-opacity="0.3"/>
  <text x="350" y="55" font-family="system-ui, sans-serif" font-size="11" fill="#6b7280">Orders</text>
  <text x="350" y="85" font-family="system-ui, sans-serif" font-size="24" fill="#ffffff" font-weight="bold">45K</text>
  <text x="350" y="110" font-family="system-ui, sans-serif" font-size="11" fill="#10b981">↑ 8.7%</text>
  <!-- Card 4 - Large NPS Card -->
  <rect x="30" y="140" width="200" height="100" rx="12" fill="url(#card4)" stroke="#f59e0b" stroke-width="1" stroke-opacity="0.3"/>
  <text x="50" y="170" font-family="system-ui, sans-serif" font-size="11" fill="#6b7280">NPS Score</text>
  <text x="50" y="210" font-family="system-ui, sans-serif" font-size="32" fill="#ffffff" font-weight="bold">72</text>
  <text x="100" y="210" font-family="system-ui, sans-serif" font-size="14" fill="#10b981">↑ 12%</text>
  <!-- Card 5 - Retention -->
  <rect x="240" y="140" width="210" height="100" rx="12" fill="url(#card1)" stroke="#3b82f6" stroke-width="1" stroke-opacity="0.3"/>
  <text x="260" y="170" font-family="system-ui, sans-serif" font-size="11" fill="#6b7280">Retention Rate</text>
  <text x="260" y="210" font-family="system-ui, sans-serif" font-size="32" fill="#ffffff" font-weight="bold">87.5%</text>
  <text x="355" y="210" font-family="system-ui, sans-serif" font-size="14" fill="#10b981">↑ 2.3%</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",

    "count_bar": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_count" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="countBar" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ec4899;stop-opacity:0.9"/>
      <stop offset="100%" style="stop-color:#f472b6;stop-opacity:0.7"/>
    </linearGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg_count)"/>
  <!-- Bars with counts -->
  <text x="90" y="50" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Electronics</text>
  <rect x="100" y="38" width="280" height="20" rx="4" fill="url(#countBar)"/>
  <text x="390" y="52" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">45</text>

  <text x="90" y="82" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Clothing</text>
  <rect x="100" y="70" width="235" height="20" rx="4" fill="url(#countBar)" opacity="0.9"/>
  <text x="345" y="84" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">38</text>

  <text x="90" y="114" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Food</text>
  <rect x="100" y="102" width="200" height="20" rx="4" fill="url(#countBar)" opacity="0.85"/>
  <text x="310" y="116" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">32</text>

  <text x="90" y="146" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Books</text>
  <rect x="100" y="134" width="155" height="20" rx="4" fill="url(#countBar)" opacity="0.8"/>
  <text x="265" y="148" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">25</text>

  <text x="90" y="178" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Sports</text>
  <rect x="100" y="166" width="125" height="20" rx="4" fill="url(#countBar)" opacity="0.75"/>
  <text x="235" y="180" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">20</text>

  <text x="90" y="210" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Home</text>
  <rect x="100" y="198" width="110" height="20" rx="4" fill="url(#countBar)" opacity="0.7"/>
  <text x="220" y="212" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">18</text>

  <text x="90" y="242" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Beauty</text>
  <rect x="100" y="230" width="95" height="20" rx="4" fill="url(#countBar)" opacity="0.65"/>
  <text x="205" y="244" font-family="system-ui, sans-serif" font-size="11" fill="#f472b6">15</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",

    "single_numeric": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 270" width="480" height="270">
  <defs>
    <linearGradient id="bg_single" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#16213e;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="singleBar1" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#06b6d4;stop-opacity:0.9"/>
      <stop offset="100%" style="stop-color:#22d3ee;stop-opacity:0.7"/>
    </linearGradient>
  </defs>
  <rect width="480" height="270" fill="url(#bg_single)"/>
  <!-- Title -->
  <text x="240" y="25" font-family="system-ui, sans-serif" font-size="14" fill="#ffffff" text-anchor="middle" font-weight="600">Sales by Region</text>
  <!-- Bars with values -->
  <text x="100" y="60" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">N. America</text>
  <rect x="110" y="48" width="300" height="22" rx="4" fill="url(#singleBar1)"/>
  <text x="420" y="63" font-family="system-ui, sans-serif" font-size="10" fill="#22d3ee">$4.5M</text>

  <text x="100" y="95" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Europe</text>
  <rect x="110" y="83" width="253" height="22" rx="4" fill="url(#singleBar1)" opacity="0.9"/>
  <text x="373" y="98" font-family="system-ui, sans-serif" font-size="10" fill="#22d3ee">$3.8M</text>

  <text x="100" y="130" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Asia Pacific</text>
  <rect x="110" y="118" width="213" height="22" rx="4" fill="url(#singleBar1)" opacity="0.85"/>
  <text x="333" y="133" font-family="system-ui, sans-serif" font-size="10" fill="#22d3ee">$3.2M</text>

  <text x="100" y="165" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Latin America</text>
  <rect x="110" y="153" width="100" height="22" rx="4" fill="url(#singleBar1)" opacity="0.8"/>
  <text x="220" y="168" font-family="system-ui, sans-serif" font-size="10" fill="#22d3ee">$1.5M</text>

  <text x="100" y="200" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Middle East</text>
  <rect x="110" y="188" width="60" height="22" rx="4" fill="url(#singleBar1)" opacity="0.75"/>
  <text x="180" y="203" font-family="system-ui, sans-serif" font-size="10" fill="#22d3ee">$900K</text>

  <text x="100" y="235" font-family="system-ui, sans-serif" font-size="11" fill="#94a3b8" text-anchor="end">Africa</text>
  <rect x="110" y="223" width="40" height="22" rx="4" fill="url(#singleBar1)" opacity="0.7"/>
  <text x="160" y="238" font-family="system-ui, sans-serif" font-size="10" fill="#22d3ee">$600K</text>
  <!-- Play indicator -->
  <circle cx="440" cy="40" r="16" fill="rgba(255,255,255,0.1)"/>
  <polygon points="436,32 436,48 448,40" fill="rgba(255,255,255,0.5)"/>
</svg>""",
}


def create_placeholder_svgs() -> dict[str, str]:
    """
    Create SVG placeholder images for all templates.

    Returns:
        Dictionary mapping template_id to the created file path.
    """
    previews_dir = get_previews_dir()

    created = {}
    for template_id, svg_content in SVG_TEMPLATES.items():
        output_path = previews_dir / f"{template_id}_placeholder.svg"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(svg_content.strip())
        created[template_id] = str(output_path)
        print(f"Created: {output_path}")

    return created


def create_placeholder_as_png() -> dict[str, str]:
    """
    Attempt to convert SVG placeholders to PNG using cairosvg if available.

    Falls back to keeping SVG if cairosvg is not installed.

    Returns:
        Dictionary mapping template_id to the created file path.
    """
    try:
        import cairosvg
    except ImportError:
        print("cairosvg not installed, keeping SVG format")
        return create_placeholder_svgs()

    previews_dir = get_previews_dir()

    created = {}
    for template_id, svg_content in SVG_TEMPLATES.items():
        output_path = previews_dir / f"{template_id}_placeholder.png"
        cairosvg.svg2png(
            bytestring=svg_content.encode("utf-8"),
            write_to=str(output_path),
            output_width=480,
            output_height=270,
        )
        created[template_id] = str(output_path)
        print(f"Created: {output_path}")

    return created


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create placeholder preview images")
    parser.add_argument(
        "--format",
        "-f",
        choices=["svg", "png"],
        default="svg",
        help="Output format (default: svg)",
    )
    args = parser.parse_args()

    print(f"Creating {args.format.upper()} placeholders...")
    print(f"Output directory: {get_previews_dir()}")
    print()

    if args.format == "png":
        paths = create_placeholder_as_png()
    else:
        paths = create_placeholder_svgs()

    print()
    print(f"Created {len(paths)} placeholder images.")
