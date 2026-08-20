"""Generate the Input-Processing-Output PDF report and infographic.

    python -m scripts.make_ipo_docs

Produces:
  docs/orion/Orion_IPO_Report.pdf      — multi-page readable report
  docs/orion/Orion_Infographic.png      — single-page visual infographic
  docs/orion/Orion_Infographic.pdf      — same infographic as PDF

No network, no LLM. Uses matplotlib only.
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs" / "orion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# COLOURS
# ============================================================================
C_PRIMARY = "#1f3a5f"
C_ACCENT = "#4a90d9"
C_OK = "#15803d"
C_WARN = "#b45309"
C_BAD = "#b91c1c"
C_BG = "#f5f7fa"
C_WHITE = "#ffffff"
C_MUTED = "#6b7480"
C_LIGHT = "#eaf0f7"

# Department colours
DEPT_COLORS = {
    "Strategy": "#2563eb",
    "Finance": "#059669",
    "Branding": "#7c3aed",
    "Marketing": "#db2777",
    "Operations": "#ea580c",
}


def _text_page(pdf, title, lines, subtitle=None):
    """Add a text page to the PDF."""
    fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor(C_WHITE)

    # Title
    y = 0.92
    ax.text(0.05, y, title, fontsize=20, fontweight="bold", color=C_PRIMARY,
            va="top", fontfamily="sans-serif")
    y -= 0.04

    if subtitle:
        ax.text(0.05, y, subtitle, fontsize=11, color=C_MUTED, va="top",
                fontfamily="sans-serif")
        y -= 0.03

    y -= 0.02

    # Lines
    for line in lines:
        if line.startswith("##"):
            y -= 0.015
            ax.text(0.05, y, line.replace("## ", ""), fontsize=14,
                    fontweight="bold", color=C_PRIMARY, va="top")
            y -= 0.035
        elif line.startswith("• ") or line.startswith("- "):
            ax.text(0.07, y, line, fontsize=10, color="#1f2733", va="top",
                    fontfamily="sans-serif")
            y -= 0.025
        elif line.startswith("  "):
            ax.text(0.09, y, line.strip(), fontsize=9, color=C_MUTED, va="top",
                    fontfamily="monospace")
            y -= 0.022
        elif line == "":
            y -= 0.012
        elif line.startswith("───"):
            ax.axhline(y=y, xmin=0.05, xmax=0.95, color=C_LIGHT, linewidth=0.8)
            y -= 0.015
        else:
            ax.text(0.05, y, line, fontsize=10.5, color="#1f2733", va="top",
                    fontfamily="sans-serif", wrap=True)
            y -= 0.027

        if y < 0.04:
            pdf.savefig(fig, dpi=150)
            plt.close(fig)
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            fig.patch.set_facecolor(C_WHITE)
            y = 0.94

    pdf.savefig(fig, dpi=150)
    plt.close(fig)


# ============================================================================
# PDF REPORT
# ============================================================================

def make_pdf_report():
    path = OUT_DIR / "Orion_IPO_Report.pdf"
    with PdfPages(str(path)) as pdf:
        # Cover page
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")
        fig.patch.set_facecolor(C_PRIMARY)
        ax.text(0.5, 0.6, "ORION", fontsize=52, fontweight="bold", color=C_WHITE,
                ha="center", va="center", fontfamily="sans-serif")
        ax.text(0.5, 0.52, "AI Business Operating System", fontsize=18,
                color=C_LIGHT, ha="center", va="center", fontfamily="sans-serif")
        ax.text(0.5, 0.40, "Input → Processing → Output\nSpecification Document",
                fontsize=14, color=C_ACCENT, ha="center", va="center",
                fontfamily="sans-serif", linespacing=1.6)
        ax.text(0.5, 0.15, "B.E. Computer Engineering — University of Mumbai\n"
                "Maskare (102) • Maurya (103) • Mishra (108)",
                fontsize=11, color=C_LIGHT, ha="center", va="center",
                fontfamily="sans-serif", linespacing=1.5)
        pdf.savefig(fig, dpi=150)
        plt.close(fig)

        # Page 1: INPUT
        _text_page(pdf, "1. INPUT — What the User Provides", [
            "## User's Perspective",
            "The user provides exactly ONE thing: a single sentence.",
            "",
            '  "Ice cream shop in Andheri West, budget ₹15 lakh"',
            "",
            "No forms. No dropdowns. No multi-page questionnaires.",
            "One text field, one sentence — the system does the rest.",
            "",
            "───────────────────────────────────────",
            "## What the System Extracts",
            "",
            "• Business Type → Ice cream shop",
            "• Location → Andheri West, Mumbai",
            "• Budget → ₹15,00,000",
            "• Sector → Food & Beverage",
            "• Scale → Small (₹10L–50L)",
            "• Is Physical? → Yes (Operations dept will run)",
            "",
            "───────────────────────────────────────",
            "## Input Requirements",
            "",
            "• Length: 10–1000 characters",
            "• Language: English (supports Hindi-English mix)",
            "• Format: Free-form natural language",
            "• Required: Business type only; rest is inferred",
            "",
            "───────────────────────────────────────",
            "## What the User Does NOT Need",
            "",
            "• [X] Market research data",
            "• [X] Financial projections",
            "• [X] Competitor names",
            "• [X] Branding preferences",
            "• [X] Marketing channel knowledge",
            "• [X] Operations expertise",
            "",
            "The system produces ALL of the above autonomously.",
        ])

        # Page 2-3: PROCESSING
        _text_page(pdf, "2. PROCESSING — What Happens Inside", [
            "## Pipeline (60–90 seconds total)",
            "",
            "• Stage 1: Intent Classification (~2s)",
            "  LLM extracts structured JSON from the text",
            "",
            "• Stage 2: Routing Decision (<100ms)",
            "  Decides which departments run, in what order",
            "",
            "• Stage 3: 21 Agents Execute (40–70s)",
            "  Strategy -> Finance | Branding | Marketing -> Operations",
            "",
            "• Stage 4: Output Assembly (~3s)",
            "  JSON → HTML Report → PDF",
            "",
            "───────────────────────────────────────",
            "## The 21 Agents Across 5 Departments",
            "",
            "• Strategy (5 agents): Market Sizing, Competitors,",
            "  Positioning, SWOT, Competitive Advantage",
            "",
            "• Finance (4 agents): Cost Structure, Revenue Model,",
            "  P&L Forecast, Break-even Analysis",
            "",
            "• Branding (4 agents): Identity, Voice, Visual Direction,",
            "  Brand Story",
            "",
            "• Marketing (4 agents): Digital Plan, Buyer Personas,",
            "  Campaign Calendar, SEO & Content",
            "",
            "• Operations (4 agents, physical only): Supply Chain,",
            "  Staffing, Technology, Process Flow",
            "",
            "───────────────────────────────────────",
            "## External Data (Not Hallucinated)",
            "",
            "• Google Places / OSM → Real competitors with ratings",
            "• Serper.dev → Market research, industry data",
            "• ChromaDB → Cached results for consistency",
            "",
            "───────────────────────────────────────",
            "## Quality Controls",
            "",
            "• Every LLM response validated by Pydantic schema",
            "• Revenue cannot exceed market size (enforced in code)",
            "• Setup costs cannot exceed stated budget",
            "• Provider fallback: Groq → Gemini → Ollama",
            "• Append-only state: agents cannot overwrite each other",
        ])

        # Page 3: OUTPUT
        _text_page(pdf, "3. OUTPUT — What the System Delivers", [
            "## Output Formats",
            "",
            "• Interactive Web Report (browser, department tabs)",
            "• PDF Document (branded, cover + TOC + page numbers)",
            "• JSON Package (machine-readable, API accessible)",
            "",
            "───────────────────────────────────────",
            "## Complete Plan Contents",
            "",
            "• Market Sizing: TAM / SAM / SOM in ₹",
            "• Competitors: Real businesses from Google Maps",
            "• Setup Costs: Category-wise breakdown",
            "• Monthly Costs: Rent, staff, materials, marketing",
            "• P&L Forecast: 20-period with margins",
            "• Break-even: Timeline and assumptions",
            "• Brand: Name, tagline, voice, colours, visual style",
            "• Marketing: Personas, channels, 90-day campaign",
            "• Operations: Staff, supply chain, daily workflow",
            "• Transparency: Model, API, time metadata",
            "",
            "───────────────────────────────────────",
            "## Target Users",
            "",
            "• First-time Entrepreneur → actionable blueprint",
            "• Student / Researcher → structured case study",
            "• Small Business Owner → market validation",
            "• Freelancer / Consultant → 20–40 hours saved",
            "• Investor / Mentor → quick viability check",
            "",
            "───────────────────────────────────────",
            "## vs Generic LLM (ChatGPT etc.)",
            "",
            "• Structure: 26-field rubric vs prose paragraphs",
            "• Numbers: Sector benchmarks vs made-up figures",
            "• Competitors: Real (Google Maps) vs hallucinated",
            "• Finance: 20-period P&L vs single estimate",
            "• Consistency: Cross-dept reconciliation in code",
            "• Transparency: Full provenance vs none",
        ])

    print(f"  PDF report: {path}")
    return path


# ============================================================================
# INFOGRAPHIC
# ============================================================================

def make_infographic():
    fig, ax = plt.subplots(figsize=(12, 18))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 18)
    ax.axis("off")
    fig.patch.set_facecolor(C_BG)

    # ---- Title ----
    ax.text(6, 17.5, "ORION", fontsize=36, fontweight="bold", color=C_PRIMARY,
            ha="center", va="center")
    ax.text(6, 17.0, "AI Business Operating System — How It Works",
            fontsize=14, color=C_MUTED, ha="center", va="center")

    # ---- INPUT SECTION ----
    y_input = 15.8
    box = FancyBboxPatch((0.5, y_input - 1.2), 11, 2.2, boxstyle="round,pad=0.15",
                         facecolor=C_WHITE, edgecolor=C_ACCENT, linewidth=2)
    ax.add_patch(box)
    ax.text(6, y_input + 0.7, "[INPUT]", fontsize=16, fontweight="bold",
            color=C_ACCENT, ha="center")
    ax.text(6, y_input + 0.2, 'User types ONE sentence:',
            fontsize=11, color=C_MUTED, ha="center")
    ax.text(6, y_input - 0.2, '"Ice cream shop in Andheri West, budget ₹15 lakh"',
            fontsize=12, fontweight="bold", color=C_PRIMARY, ha="center",
            style="italic")
    ax.text(6, y_input - 0.7, "No forms • No expertise needed • 10–1000 characters",
            fontsize=9, color=C_MUTED, ha="center")

    # Arrow down
    ax.annotate("", xy=(6, 13.8), xytext=(6, 14.5),
                arrowprops=dict(arrowstyle="-|>", color=C_PRIMARY, lw=2.5))

    # ---- PROCESSING SECTION ----
    y_proc = 11.5
    box = FancyBboxPatch((0.5, y_proc - 3.5), 11, 5.2, boxstyle="round,pad=0.15",
                         facecolor=C_WHITE, edgecolor=C_PRIMARY, linewidth=2)
    ax.add_patch(box)
    ax.text(6, y_proc + 1.4, "[PROCESSING]", fontsize=16, fontweight="bold",
            color=C_PRIMARY, ha="center")
    ax.text(6, y_proc + 0.9, "60–90 seconds • 21 AI Agents • 5 Departments",
            fontsize=10, color=C_MUTED, ha="center")

    # Pipeline stages
    stages = [
        ("1. Intent Classification", "LLM → structured JSON", "~2s"),
        ("2. Smart Routing", "Activate relevant depts", "<0.1s"),
        ("3. Department Execution", "21 agents in parallel", "40–70s"),
        ("4. Output Assembly", "JSON → HTML → PDF", "~3s"),
    ]
    for i, (name, desc, time) in enumerate(stages):
        sy = y_proc + 0.2 - i * 0.7
        ax.text(1.5, sy, name, fontsize=10, fontweight="bold", color=C_PRIMARY)
        ax.text(6.5, sy, desc, fontsize=9, color=C_MUTED)
        ax.text(10.5, sy, time, fontsize=9, color=C_OK, ha="right",
                fontweight="bold")

    # Department boxes
    dy = y_proc - 2.8
    dept_w = 1.9
    for i, (name, color) in enumerate(DEPT_COLORS.items()):
        dx = 1.0 + i * 2.1
        dept_box = FancyBboxPatch((dx, dy), dept_w, 0.7,
                                  boxstyle="round,pad=0.08",
                                  facecolor=color, edgecolor="none", alpha=0.9)
        ax.add_patch(dept_box)
        ax.text(dx + dept_w / 2, dy + 0.35, name, fontsize=8.5,
                fontweight="bold", color=C_WHITE, ha="center", va="center")

    # Agent count
    ax.text(6, dy - 0.4, "5 agents  •  4 agents  •  4 agents  •  4 agents  •  4 agents",
            fontsize=8, color=C_MUTED, ha="center")

    # Real data callout
    ax.text(6, dy - 0.9, "REAL DATA: Google Maps competitors + Serper market research + OSM",
            fontsize=9, color=C_WARN, ha="center", fontweight="bold")

    # Arrow down
    ax.annotate("", xy=(6, 7.2), xytext=(6, 7.9),
                arrowprops=dict(arrowstyle="-|>", color=C_PRIMARY, lw=2.5))

    # ---- OUTPUT SECTION ----
    y_out = 5.0
    box = FancyBboxPatch((0.5, y_out - 2.8), 11, 4.8, boxstyle="round,pad=0.15",
                         facecolor=C_WHITE, edgecolor=C_OK, linewidth=2)
    ax.add_patch(box)
    ax.text(6, y_out + 1.7, "[OUTPUT]", fontsize=16, fontweight="bold",
            color=C_OK, ha="center")
    ax.text(6, y_out + 1.2, "Complete Business Plan — Web + PDF + JSON",
            fontsize=11, color=C_MUTED, ha="center")

    # Output items - left column
    outputs_left = [
        "> Market Sizing (TAM/SAM/SOM)",
        "> Real Competitors (with ratings)",
        "> Full Financial Model",
        "> 20-Period P&L Forecast",
        "> Break-even Timeline",
    ]
    outputs_right = [
        "> Brand Identity & Colours",
        "> Marketing Plan (90 days)",
        "> Buyer Personas",
        "> Operations Playbook",
        "> Staffing & Process Flow",
    ]

    for i, item in enumerate(outputs_left):
        ax.text(1.3, y_out + 0.5 - i * 0.5, item, fontsize=9.5, color=C_PRIMARY)
    for i, item in enumerate(outputs_right):
        ax.text(6.5, y_out + 0.5 - i * 0.5, item, fontsize=9.5, color=C_PRIMARY)

    # ---- TARGET USERS ----
    y_users = 1.5
    ax.text(6, y_users + 0.4, "TARGET USERS", fontsize=12, fontweight="bold",
            color=C_PRIMARY, ha="center")
    users = ["Entrepreneurs", "Students", "Consultants", "Investors", "SME Owners"]
    for i, user in enumerate(users):
        ux = 1.5 + i * 2.1
        user_box = FancyBboxPatch((ux, y_users - 0.5), 1.8, 0.6,
                                  boxstyle="round,pad=0.08",
                                  facecolor=C_LIGHT, edgecolor=C_ACCENT,
                                  linewidth=1)
        ax.add_patch(user_box)
        ax.text(ux + 0.9, y_users - 0.2, user, fontsize=8, color=C_PRIMARY,
                ha="center", va="center", fontweight="bold")

    # Footer
    ax.text(6, 0.3, "Orion • B.E. Computer Engineering • University of Mumbai • 2026",
            fontsize=8, color=C_MUTED, ha="center")

    # Save
    png_path = OUT_DIR / "Orion_Infographic.png"
    pdf_path = OUT_DIR / "Orion_Infographic.pdf"
    fig.savefig(str(png_path), dpi=200, bbox_inches="tight", facecolor=C_BG)
    fig.savefig(str(pdf_path), dpi=150, bbox_inches="tight", facecolor=C_BG)
    plt.close(fig)
    print(f"  Infographic PNG: {png_path}")
    print(f"  Infographic PDF: {pdf_path}")
    return png_path, pdf_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("Generating Orion IPO documents...")
    make_pdf_report()
    make_infographic()
    print("\nDone. Files in docs/orion/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
