"""Generate a professional, visually engaging infographic for Orion.

    python -m scripts.make_infographic

Produces:
  docs/orion/Orion_Infographic_Pro.png   (high-res, 300 dpi)
  docs/orion/Orion_Infographic_Pro.pdf   (vector, print-ready)

Design: clean corporate style, gradient accents, clear visual hierarchy,
data-driven callouts. No emoji — uses geometric shapes and colour coding.
"""

import pathlib
import sys
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as pe

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs" / "orion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DESIGN SYSTEM
# ============================================================================

# Primary palette
NAVY = "#0f2744"
BLUE = "#1a56db"
LIGHT_BLUE = "#3b82f6"
SKY = "#dbeafe"
SLATE = "#475569"
MUTED = "#94a3b8"
WHITE = "#ffffff"
OFF_WHITE = "#f8fafc"
LIGHT_GRAY = "#f1f5f9"

# Accent colours
TEAL = "#0d9488"
EMERALD = "#059669"
AMBER = "#d97706"
ROSE = "#e11d48"
VIOLET = "#7c3aed"

# Department colours
DEPT = {
    "Strategy": "#2563eb",
    "Finance": "#059669",
    "Branding": "#7c3aed",
    "Marketing": "#e11d48",
    "Operations": "#ea580c",
}


def draw_rounded_box(ax, x, y, w, h, color, alpha=1.0, linewidth=0, edgecolor="none", radius=0.15):
    box = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={radius}",
                         facecolor=color, edgecolor=edgecolor,
                         linewidth=linewidth, alpha=alpha, zorder=2)
    ax.add_patch(box)
    return box


def draw_arrow(ax, x1, y1, x2, y2, color=NAVY, width=2.5):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=width,
                                connectionstyle="arc3,rad=0"),
                zorder=5)


def draw_circle_icon(ax, cx, cy, r, color, text="", text_color=WHITE, fontsize=9):
    circle = Circle((cx, cy), r, facecolor=color, edgecolor="none", zorder=4)
    ax.add_patch(circle)
    if text:
        ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
                color=text_color, fontweight="bold", zorder=5)


# ============================================================================
# MAIN INFOGRAPHIC
# ============================================================================

def make_infographic():
    fig, ax = plt.subplots(figsize=(11.69, 16.53))  # A3-ish portrait
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 17)
    ax.axis("off")
    fig.patch.set_facecolor(OFF_WHITE)

    # ===== HEADER =====
    draw_rounded_box(ax, 0.3, 15.6, 11.4, 1.2, NAVY, radius=0.12)
    ax.text(6, 16.35, "ORION", fontsize=38, fontweight="bold", color=WHITE,
            ha="center", va="center", fontfamily="sans-serif",
            path_effects=[pe.withStroke(linewidth=1, foreground=LIGHT_BLUE)])
    ax.text(6, 15.9, "AI Business Operating System  |  Input - Processing - Output",
            fontsize=11, color=SKY, ha="center", va="center")

    # ===== SECTION 1: INPUT =====
    y_sec1 = 14.0

    # Section header
    draw_rounded_box(ax, 0.5, y_sec1 + 0.85, 2.2, 0.55, LIGHT_BLUE, radius=0.08)
    ax.text(1.6, y_sec1 + 1.12, "1  INPUT", fontsize=13, fontweight="bold",
            color=WHITE, ha="center", va="center")

    # Main input box
    draw_rounded_box(ax, 0.5, y_sec1 - 1.6, 11.0, 2.3, WHITE, linewidth=1.5,
                     edgecolor=LIGHT_BLUE, radius=0.12)

    # The prompt
    ax.text(6, y_sec1 + 0.3, "User provides ONE sentence:",
            fontsize=11, color=SLATE, ha="center")
    draw_rounded_box(ax, 1.5, y_sec1 - 0.5, 9.0, 0.6, LIGHT_GRAY, radius=0.08,
                     linewidth=1, edgecolor="#cbd5e1")
    ax.text(6, y_sec1 - 0.2, '"Ice cream shop in Andheri West, budget Rs 15 lakh"',
            fontsize=11.5, color=NAVY, ha="center", fontweight="bold",
            style="italic")

    # Extracted fields - as pill badges
    fields = [("Business Type", "Ice Cream Shop"),
              ("Location", "Andheri West"),
              ("Budget", "Rs 15L"),
              ("Sector", "F&B"),
              ("Scale", "Small"),
              ("Physical", "Yes")]
    pill_y = y_sec1 - 1.2
    start_x = 1.0
    for i, (label, value) in enumerate(fields):
        px = start_x + i * 1.8
        draw_rounded_box(ax, px, pill_y, 1.6, 0.4, SKY, radius=0.06)
        ax.text(px + 0.8, pill_y + 0.27, label, fontsize=7, color=BLUE,
                ha="center", fontweight="bold")
        ax.text(px + 0.8, pill_y + 0.08, value, fontsize=7.5, color=NAVY,
                ha="center")

    # Arrow
    draw_arrow(ax, 6, y_sec1 - 1.75, 6, y_sec1 - 2.1, BLUE)

    # ===== SECTION 2: PROCESSING =====
    y_sec2 = 10.2

    draw_rounded_box(ax, 0.5, y_sec2 + 0.85, 2.8, 0.55, NAVY, radius=0.08)
    ax.text(1.9, y_sec2 + 1.12, "2  PROCESSING", fontsize=13, fontweight="bold",
            color=WHITE, ha="center", va="center")

    # Processing container
    draw_rounded_box(ax, 0.5, y_sec2 - 4.3, 11.0, 5.0, WHITE, linewidth=1.5,
                     edgecolor=NAVY, radius=0.12)

    # Pipeline stages
    stages = [
        ("Intent Classification", "LLM extracts structured JSON", "~2s", BLUE),
        ("Smart Routing", "Activates relevant departments", "<0.1s", TEAL),
        ("21-Agent Execution", "5 departments work in parallel", "40-70s", VIOLET),
        ("Output Assembly", "JSON + HTML + PDF generation", "~3s", EMERALD),
    ]

    for i, (name, desc, time, color) in enumerate(stages):
        sy = y_sec2 + 0.1 - i * 0.85
        # Number circle
        draw_circle_icon(ax, 1.3, sy + 0.1, 0.22, color, str(i + 1), WHITE, 10)
        # Stage text
        ax.text(1.8, sy + 0.2, name, fontsize=10.5, color=NAVY, fontweight="bold")
        ax.text(1.8, sy - 0.05, desc, fontsize=8.5, color=MUTED)
        # Time badge
        draw_rounded_box(ax, 9.8, sy - 0.02, 1.2, 0.35, color, alpha=0.12, radius=0.05)
        ax.text(10.4, sy + 0.15, time, fontsize=9, color=color, ha="center",
                fontweight="bold")

        # Connecting line between stages
        if i < 3:
            ax.plot([1.3, 1.3], [sy - 0.12, sy - 0.52], color="#e2e8f0",
                    linewidth=2, zorder=1)

    # Department boxes
    dept_y = y_sec2 - 3.0
    ax.text(6, dept_y + 0.7, "5 DEPARTMENTS", fontsize=9, color=MUTED,
            ha="center", fontweight="bold")

    dept_w = 1.85
    for i, (name, color) in enumerate(DEPT.items()):
        dx = 0.9 + i * 2.15
        draw_rounded_box(ax, dx, dept_y, dept_w, 0.55, color, radius=0.07)
        ax.text(dx + dept_w / 2, dept_y + 0.35, name, fontsize=9,
                fontweight="bold", color=WHITE, ha="center", va="center")
        # Agent count
        ax.text(dx + dept_w / 2, dept_y - 0.2,
                f"{'5' if name == 'Strategy' else '4'} agents",
                fontsize=7.5, color=MUTED, ha="center")

    # Data sources bar
    ds_y = dept_y - 0.8
    draw_rounded_box(ax, 1.0, ds_y, 10.0, 0.45, "#fef3c7", radius=0.06,
                     linewidth=1, edgecolor=AMBER)
    ax.text(6, ds_y + 0.22, "Real Data: Google Maps + OpenStreetMap + Serper.dev (not hallucinated)",
            fontsize=8.5, color="#92400e", ha="center", fontweight="bold")

    # Stats row
    stats_y = ds_y - 0.7
    stats = [("60-90s", "Total Time"), ("21", "AI Agents"),
             ("5", "Departments"), ("3", "API Sources")]
    for i, (val, label) in enumerate(stats):
        sx = 1.5 + i * 2.7
        ax.text(sx, stats_y + 0.15, val, fontsize=16, color=NAVY,
                fontweight="bold", ha="center")
        ax.text(sx, stats_y - 0.15, label, fontsize=8, color=MUTED, ha="center")

    # Arrow
    draw_arrow(ax, 6, y_sec2 - 4.45, 6, y_sec2 - 4.8, NAVY)

    # ===== SECTION 3: OUTPUT =====
    y_sec3 = 3.8

    draw_rounded_box(ax, 0.5, y_sec3 + 0.85, 2.4, 0.55, EMERALD, radius=0.08)
    ax.text(1.7, y_sec3 + 1.12, "3  OUTPUT", fontsize=13, fontweight="bold",
            color=WHITE, ha="center", va="center")

    # Output container
    draw_rounded_box(ax, 0.5, y_sec3 - 3.0, 11.0, 3.7, WHITE, linewidth=1.5,
                     edgecolor=EMERALD, radius=0.12)

    # Format pills at top
    formats = [("Web Report", BLUE), ("PDF Document", VIOLET), ("JSON Data", TEAL)]
    for i, (fmt, color) in enumerate(formats):
        fx = 2.0 + i * 3.2
        draw_rounded_box(ax, fx, y_sec3 + 0.1, 2.4, 0.4, color, radius=0.06)
        ax.text(fx + 1.2, y_sec3 + 0.3, fmt, fontsize=9, color=WHITE,
                ha="center", fontweight="bold")

    # Output contents - two columns
    left_items = [
        "Market Sizing (TAM / SAM / SOM)",
        "Real Competitors with Ratings",
        "Full Financial Model",
        "20-Period P&L Forecast",
        "Break-even Timeline",
    ]
    right_items = [
        "Brand Identity & Colour Palette",
        "90-Day Marketing Campaign",
        "Buyer Personas (2-3 profiles)",
        "Operations Playbook",
        "Staffing Plan & Process Flow",
    ]

    for i, item in enumerate(left_items):
        iy = y_sec3 - 0.5 - i * 0.45
        draw_circle_icon(ax, 1.3, iy + 0.05, 0.12, BLUE)
        ax.text(1.6, iy, item, fontsize=9, color=SLATE, va="center")

    for i, item in enumerate(right_items):
        iy = y_sec3 - 0.5 - i * 0.45
        draw_circle_icon(ax, 6.5, iy + 0.05, 0.12, EMERALD)
        ax.text(6.8, iy, item, fontsize=9, color=SLATE, va="center")

    # ===== FOOTER: TARGET USERS =====
    footer_y = 0.3
    draw_rounded_box(ax, 0.5, footer_y, 11.0, 0.7, NAVY, radius=0.08)
    ax.text(1.5, footer_y + 0.35, "FOR:", fontsize=9, color=MUTED,
            va="center", fontweight="bold")
    users = ["Entrepreneurs", "Students", "Consultants", "Investors", "SME Owners"]
    for i, user in enumerate(users):
        ux = 3.0 + i * 1.9
        ax.text(ux, footer_y + 0.35, user, fontsize=9, color=WHITE,
                va="center", fontweight="bold")
        if i < len(users) - 1:
            ax.text(ux + 1.55, footer_y + 0.35, "|", fontsize=9,
                    color=MUTED, va="center")

    # Credit line
    ax.text(6, 0.08, "Orion  |  B.E. Computer Engineering  |  University of Mumbai  |  2026-27",
            fontsize=7.5, color=MUTED, ha="center")

    # ===== SAVE =====
    png_path = OUT_DIR / "Orion_Infographic_Pro.png"
    pdf_path = OUT_DIR / "Orion_Infographic_Pro.pdf"
    fig.savefig(str(png_path), dpi=300, bbox_inches="tight", facecolor=OFF_WHITE)
    fig.savefig(str(pdf_path), bbox_inches="tight", facecolor=OFF_WHITE)
    plt.close(fig)
    print(f"  PNG (300 dpi): {png_path}")
    print(f"  PDF (vector):  {pdf_path}")
    return png_path, pdf_path


def main():
    print("Generating professional Orion infographic...")
    make_infographic()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
