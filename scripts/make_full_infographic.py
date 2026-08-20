"""Generate a comprehensive multi-page infographic showing every agent and output.

    python -m scripts.make_full_infographic

Produces:
  docs/orion/Orion_Full_Infographic.png   (single tall image, 300 dpi)
  docs/orion/Orion_Full_Infographic.pdf   (multi-page A4 PDF)

Shows: User Input → Intent Extraction → Routing → Every Agent in Every Department
       → What Each Agent Produces → Final Output Assembly
"""

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patheffects as pe

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs" / "orion"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# DESIGN SYSTEM
# ============================================================================
NAVY = "#0f2744"
BLUE = "#1a56db"
LIGHT_BLUE = "#3b82f6"
SKY = "#dbeafe"
SLATE = "#475569"
MUTED = "#94a3b8"
WHITE = "#ffffff"
OFF_WHITE = "#f8fafc"
LIGHT_GRAY = "#f1f5f9"
TEAL = "#0d9488"
EMERALD = "#059669"
AMBER = "#d97706"
ROSE = "#e11d48"
VIOLET = "#7c3aed"

DEPT_COLORS = {
    "Strategy": "#2563eb",
    "Finance": "#059669",
    "Branding": "#7c3aed",
    "Marketing": "#e11d48",
    "Operations": "#ea580c",
}

# All 21 agents and their outputs
AGENTS = {
    "Strategy": [
        ("Market Sizing Agent", [
            "TAM (Total Addressable Market) in Rs",
            "SAM (Serviceable Addressable Market)",
            "SOM (Serviceable Obtainable Market)",
            "Market growth rate %",
        ]),
        ("Competitor Analysis Agent", [
            "Real businesses within 2km (from Google Maps/OSM)",
            "Each competitor: name, rating, review count",
            "Price level comparison",
            "Gap analysis and white spaces",
        ]),
        ("Positioning Agent", [
            "Unique Selling Proposition (USP)",
            "Target customer segment definition",
            "Differentiation strategy",
            "Value proposition statement",
        ]),
        ("SWOT Analysis Agent", [
            "Strengths (internal advantages)",
            "Weaknesses (internal gaps)",
            "Opportunities (external positive)",
            "Threats (external risks)",
        ]),
        ("Competitive Advantage Agent", [
            "Defensible moat identification",
            "Key success factors",
            "Barriers to entry for competitors",
            "Long-term sustainability plan",
        ]),
    ],
    "Finance": [
        ("Cost Structure Agent", [
            "One-time setup costs (category-wise)",
            "Monthly recurring costs breakdown",
            "Fixed vs variable cost split",
            "Cost optimization recommendations",
        ]),
        ("Revenue Model Agent", [
            "Revenue streams identified",
            "Pricing strategy per stream",
            "Unit economics (price, COGS, margin)",
            "Revenue growth assumptions",
        ]),
        ("P&L Forecast Agent", [
            "20-period P&L statement",
            "Revenue projections month by month",
            "Operating expenses per period",
            "Gross margin % and Net margin %",
        ]),
        ("Funding & Break-even Agent", [
            "Total funding required",
            "Fund allocation plan",
            "Break-even point (month)",
            "Payback period calculation",
        ]),
    ],
    "Branding": [
        ("Brand Identity Agent", [
            "Brand name suggestions (3-5)",
            "Tagline options",
            "Core brand values (3-5)",
            "Brand personality traits",
        ]),
        ("Brand Voice Agent", [
            "Communication tone (formal/casual/playful)",
            "Vocabulary guidelines",
            "Sample social media post",
            "Do's and Don'ts for messaging",
        ]),
        ("Visual Direction Agent", [
            "Logo style recommendation",
            "Colour palette (primary + accent hex codes)",
            "Typography direction",
            "Visual mood (minimalist/vibrant/rustic)",
        ]),
        ("Brand Story Agent", [
            "Origin narrative",
            "Customer-facing 'why we exist'",
            "Emotional hook",
            "Brand promise statement",
        ]),
    ],
    "Marketing": [
        ("Digital Marketing Agent", [
            "Channel mix (Instagram, Google, WhatsApp, etc.)",
            "Budget % allocation per channel",
            "KPIs per channel",
            "Monthly marketing budget in Rs",
        ]),
        ("Buyer Persona Agent", [
            "2-3 detailed customer profiles",
            "Demographics: age, gender, income, location",
            "Psychographics: values, pain points",
            "Buying triggers and objections",
        ]),
        ("Campaign Plan Agent", [
            "90-day launch campaign timeline",
            "Pre-launch phase activities",
            "Launch week strategy",
            "Post-launch retention plan",
        ]),
        ("SEO & Content Agent", [
            "10-15 target keywords with volume",
            "Content topics for organic traffic",
            "Publishing frequency and formats",
            "Content calendar skeleton",
        ]),
    ],
    "Operations": [
        ("Supply Chain Agent", [
            "Raw material requirements list",
            "Vendor categories (local/wholesale/online)",
            "Inventory approach (JIT/safety stock)",
            "Supply chain risk mitigation",
        ]),
        ("Staffing Plan Agent", [
            "Roles and headcount (Year 1)",
            "Salary ranges at Mumbai market rates",
            "Hiring sequence and timeline",
            "Org chart structure",
        ]),
        ("Technology Stack Agent", [
            "POS system recommendation",
            "Accounting software",
            "Communication tools",
            "Delivery/logistics integrations",
        ]),
        ("Process Flow Agent", [
            "Daily operational workflow (open to close)",
            "Key processes step by step",
            "Quality checkpoints",
            "Inter-process dependencies",
        ]),
    ],
}


def _box(ax, x, y, w, h, color, alpha=1.0, lw=0, ec="none", rad=0.12):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad={rad}",
                       facecolor=color, edgecolor=ec, linewidth=lw, alpha=alpha, zorder=2)
    ax.add_patch(p)


def _circle(ax, cx, cy, r, color):
    ax.add_patch(Circle((cx, cy), r, facecolor=color, edgecolor="none", zorder=4))


def _arrow(ax, x1, y1, x2, y2, color=NAVY):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=2.5), zorder=5)


# ============================================================================
# BUILD THE TALL SINGLE-IMAGE INFOGRAPHIC
# ============================================================================

def make_tall_infographic():
    # Calculate height needed
    # Header: 2, Input: 3, Routing: 2, each dept: ~4.5, Output: 3, Footer: 1
    total_height = 2 + 3.5 + 2.5 + (5 * 5.0) + 3.5 + 1.5
    fig, ax = plt.subplots(figsize=(12, total_height))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, total_height)
    ax.axis("off")
    fig.patch.set_facecolor(OFF_WHITE)

    y = total_height  # draw top-down

    # ===== HEADER =====
    y -= 0.3
    _box(ax, 0.3, y - 1.5, 11.4, 1.5, NAVY, rad=0.1)
    ax.text(6, y - 0.45, "ORION", fontsize=32, fontweight="bold", color=WHITE,
            ha="center", va="center")
    ax.text(6, y - 1.0, "Complete System Flow: Input  ->  Processing  ->  Output",
            fontsize=12, color=SKY, ha="center")
    ax.text(6, y - 1.3, "21 AI Agents  |  5 Departments  |  One Sentence In, Full Business Plan Out",
            fontsize=9, color=MUTED, ha="center")
    y -= 2.0

    # ===== INPUT SECTION =====
    _box(ax, 0.5, y - 3.0, 11.0, 3.0, WHITE, lw=2, ec=LIGHT_BLUE, rad=0.1)

    ax.text(1.0, y - 0.3, "STEP 1: USER INPUT", fontsize=14, fontweight="bold", color=BLUE)
    ax.text(1.0, y - 0.7, "The user types a single natural language sentence. Nothing else required.",
            fontsize=10, color=SLATE)

    # Prompt box
    _box(ax, 1.0, y - 1.5, 10.0, 0.6, LIGHT_GRAY, rad=0.06, lw=1, ec="#cbd5e1")
    ax.text(6, y - 1.2, '"Ice cream shop in Andheri West, budget Rs 15 lakh"',
            fontsize=11.5, color=NAVY, ha="center", fontweight="bold", style="italic")

    # Extraction
    ax.text(1.0, y - 2.0, "System extracts:", fontsize=9, color=MUTED, fontweight="bold")
    fields = [
        "Business Type: Ice Cream Shop",
        "Location: Andheri West, Mumbai",
        "Budget: Rs 15,00,000",
        "Sector: Food & Beverage",
        "Scale: Small (Rs 10L-50L)",
        "Is Physical: Yes -> Operations will run",
    ]
    for i, f in enumerate(fields):
        col = i // 3
        row = i % 3
        ax.text(1.5 + col * 5.5, y - 2.35 - row * 0.25, f, fontsize=9, color=NAVY)

    y -= 3.3
    _arrow(ax, 6, y + 0.1, 6, y - 0.3, BLUE)
    y -= 0.5

    # ===== ROUTING SECTION =====
    _box(ax, 0.5, y - 2.0, 11.0, 2.0, WHITE, lw=2, ec=TEAL, rad=0.1)

    ax.text(1.0, y - 0.3, "STEP 2: SMART ROUTING (< 0.1 seconds)", fontsize=14,
            fontweight="bold", color=TEAL)
    ax.text(1.0, y - 0.7, "The orchestrator decides execution order based on business type:",
            fontsize=10, color=SLATE)

    # DAG visualization
    ax.text(2.0, y - 1.2, "Strategy", fontsize=10, fontweight="bold", color=DEPT_COLORS["Strategy"])
    ax.text(3.8, y - 1.2, "-->", fontsize=10, color=MUTED)
    ax.text(4.5, y - 1.0, "Finance", fontsize=9, color=DEPT_COLORS["Finance"])
    ax.text(4.5, y - 1.25, "Branding", fontsize=9, color=DEPT_COLORS["Branding"])
    ax.text(4.5, y - 1.5, "Marketing", fontsize=9, color=DEPT_COLORS["Marketing"])
    ax.text(6.5, y - 1.2, "-->", fontsize=10, color=MUTED)
    ax.text(7.2, y - 1.2, "Operations", fontsize=10, fontweight="bold", color=DEPT_COLORS["Operations"])
    ax.text(7.2, y - 1.5, "(only if physical business)", fontsize=8, color=MUTED)

    # Parallel note
    ax.text(4.5, y - 1.75, "(these 3 run in PARALLEL)", fontsize=8, color=TEAL, style="italic")

    y -= 2.3
    _arrow(ax, 6, y + 0.1, 6, y - 0.3, NAVY)
    y -= 0.5

    # ===== DEPARTMENT SECTIONS =====
    for dept_name, agents in AGENTS.items():
        dept_color = DEPT_COLORS[dept_name]
        num_agents = len(agents)
        box_height = 0.8 + num_agents * 1.05

        _box(ax, 0.5, y - box_height, 11.0, box_height, WHITE, lw=2, ec=dept_color, rad=0.1)

        # Department header
        _box(ax, 0.8, y - 0.55, 3.5, 0.45, dept_color, rad=0.06)
        ax.text(2.55, y - 0.33, f"{dept_name.upper()} DEPARTMENT", fontsize=11,
                fontweight="bold", color=WHITE, ha="center", va="center")

        # Agent count badge
        ax.text(4.8, y - 0.35, f"{num_agents} agents", fontsize=9, color=dept_color,
                fontweight="bold")

        # Conditional note for Operations
        if dept_name == "Operations":
            ax.text(7.0, y - 0.35, "(runs only for physical businesses)",
                    fontsize=8, color=MUTED, style="italic")

        # Each agent
        for i, (agent_name, outputs) in enumerate(agents):
            ay = y - 0.85 - i * 1.05

            # Agent name
            _circle(ax, 1.2, ay - 0.05, 0.15, dept_color)
            ax.text(1.5, ay - 0.05, agent_name, fontsize=10, fontweight="bold",
                    color=NAVY, va="center")

            # Arrow
            ax.text(5.2, ay - 0.05, "-->", fontsize=9, color=MUTED, va="center")

            # Outputs
            ax.text(5.7, ay + 0.05, "Produces:", fontsize=8, color=MUTED)
            for j, output in enumerate(outputs):
                ox = 5.7
                oy = ay - 0.15 - j * 0.2
                ax.text(ox, oy, f"- {output}", fontsize=8, color=SLATE)

        y -= box_height + 0.3
        _arrow(ax, 6, y + 0.1, 6, y - 0.2, dept_color)
        y -= 0.4

    # ===== OUTPUT SECTION =====
    _box(ax, 0.5, y - 3.2, 11.0, 3.2, WHITE, lw=2, ec=EMERALD, rad=0.1)

    ax.text(1.0, y - 0.3, "STEP 3: OUTPUT ASSEMBLY", fontsize=14,
            fontweight="bold", color=EMERALD)
    ax.text(1.0, y - 0.65, "All agent outputs are assembled into a unified business plan:",
            fontsize=10, color=SLATE)

    # Output formats
    formats = [("Interactive Web Report", "Browser-based, tabbed by department"),
               ("PDF Document", "Branded, cover page, TOC, print-ready"),
               ("JSON Package", "Machine-readable, API accessible")]
    for i, (name, desc) in enumerate(formats):
        fy = y - 1.1 - i * 0.55
        _box(ax, 1.0, fy - 0.15, 3.0, 0.4, EMERALD if i == 0 else VIOLET if i == 1 else TEAL, rad=0.05)
        ax.text(2.5, fy + 0.05, name, fontsize=9, fontweight="bold", color=WHITE, ha="center")
        ax.text(4.3, fy + 0.05, desc, fontsize=9, color=SLATE, va="center")

    # Quality checks
    ax.text(1.0, y - 2.9, "Quality: Pydantic validated | Cross-dept reconciled | Budget-constrained | Sector-benchmarked",
            fontsize=8.5, color=AMBER, fontweight="bold")

    y -= 3.5

    # ===== FOOTER =====
    _box(ax, 0.5, y - 0.8, 11.0, 0.8, NAVY, rad=0.08)
    ax.text(6, y - 0.25, "ONE SENTENCE IN  -->  COMPLETE BUSINESS PLAN OUT  -->  60-90 SECONDS",
            fontsize=11, fontweight="bold", color=WHITE, ha="center")
    ax.text(6, y - 0.55, "Target Users: Entrepreneurs | Students | Consultants | Investors | SME Owners",
            fontsize=9, color=MUTED, ha="center")

    # Save
    png_path = OUT_DIR / "Orion_Full_Infographic.png"
    fig.savefig(str(png_path), dpi=300, bbox_inches="tight", facecolor=OFF_WHITE)
    plt.close(fig)
    print(f"  Full infographic PNG: {png_path}")
    print(f"  Size: {png_path.stat().st_size / 1024:.0f} KB")
    return png_path


# ============================================================================
# BUILD MULTI-PAGE PDF VERSION
# ============================================================================

def make_pdf_version():
    pdf_path = OUT_DIR / "Orion_Full_Infographic.pdf"

    with PdfPages(str(pdf_path)) as pdf:
        # --- PAGE 1: Cover + Input + Routing ---
        fig, ax = plt.subplots(figsize=(11.69, 8.27))  # landscape A4
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 8.5)
        ax.axis("off")
        fig.patch.set_facecolor(OFF_WHITE)

        # Header
        _box(ax, 0.2, 7.3, 11.6, 1.0, NAVY, rad=0.08)
        ax.text(6, 7.95, "ORION — Complete System Flow", fontsize=22,
                fontweight="bold", color=WHITE, ha="center")
        ax.text(6, 7.5, "21 AI Agents | 5 Departments | One Sentence to Full Business Plan",
                fontsize=10, color=SKY, ha="center")

        # Input
        ax.text(0.5, 6.9, "STEP 1: USER INPUT", fontsize=13, fontweight="bold", color=BLUE)
        _box(ax, 0.5, 5.9, 11.0, 0.8, WHITE, lw=1.5, ec=LIGHT_BLUE, rad=0.08)
        ax.text(6, 6.45, 'User types: "Ice cream shop in Andheri West, budget Rs 15 lakh"',
                fontsize=11, ha="center", color=NAVY, fontweight="bold", style="italic")
        ax.text(6, 6.1, "Extracts: Business Type | Location | Budget | Sector | Scale | Physical?",
                fontsize=9, ha="center", color=MUTED)

        # Routing
        ax.text(0.5, 5.5, "STEP 2: SMART ROUTING", fontsize=13, fontweight="bold", color=TEAL)
        _box(ax, 0.5, 4.3, 11.0, 1.0, WHITE, lw=1.5, ec=TEAL, rad=0.08)
        ax.text(1.0, 5.0, "Execution order:  Strategy (first)  -->  Finance + Branding + Marketing (parallel)  -->  Operations (if physical)",
                fontsize=9.5, color=NAVY)
        ax.text(1.0, 4.65, "Digital businesses skip Operations automatically (saves 17.3% tokens, 0% quality loss)",
                fontsize=9, color=TEAL)

        # Department overview
        ax.text(0.5, 3.9, "STEP 3: 21 AGENTS EXECUTE", fontsize=13, fontweight="bold", color=NAVY)
        for i, (dept, color) in enumerate(DEPT_COLORS.items()):
            dx = 0.5 + i * 2.3
            _box(ax, dx, 3.1, 2.1, 0.6, color, rad=0.06)
            ax.text(dx + 1.05, 3.5, dept, fontsize=10, fontweight="bold",
                    color=WHITE, ha="center")
            ax.text(dx + 1.05, 3.25, f"{'5' if dept == 'Strategy' else '4'} agents",
                    fontsize=8, color=WHITE, ha="center", alpha=0.8)

        # Data sources
        _box(ax, 0.5, 2.3, 11.0, 0.6, "#fef3c7", rad=0.06, lw=1, ec=AMBER)
        ax.text(6, 2.6, "REAL DATA SOURCES: Google Maps (competitors) + Serper.dev (market research) + OpenStreetMap",
                fontsize=9, color="#92400e", ha="center", fontweight="bold")

        # Note
        ax.text(6, 1.8, "Following pages show EVERY agent and EVERY output it produces...",
                fontsize=10, color=SLATE, ha="center", style="italic")

        ax.text(6, 0.3, "Orion | B.E. Computer Engineering | University of Mumbai | 2026-27",
                fontsize=8, color=MUTED, ha="center")

        pdf.savefig(fig, dpi=150)
        plt.close(fig)

        # --- PAGES 2-6: One page per department ---
        for dept_name, agents in AGENTS.items():
            dept_color = DEPT_COLORS[dept_name]
            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.set_xlim(0, 12)
            ax.set_ylim(0, 8.5)
            ax.axis("off")
            fig.patch.set_facecolor(OFF_WHITE)

            # Department header
            _box(ax, 0.2, 7.5, 11.6, 0.8, dept_color, rad=0.08)
            ax.text(6, 7.95, f"{dept_name.upper()} DEPARTMENT",
                    fontsize=20, fontweight="bold", color=WHITE, ha="center")
            cond = " (runs only for physical businesses)" if dept_name == "Operations" else ""
            ax.text(6, 7.65, f"{len(agents)} Specialized AI Agents{cond}",
                    fontsize=10, color=WHITE, ha="center", alpha=0.85)

            # Agents
            agent_height = 6.8 / len(agents)
            for i, (agent_name, outputs) in enumerate(agents):
                ay = 7.1 - (i + 1) * agent_height + agent_height * 0.5

                # Agent box
                _box(ax, 0.5, ay - 0.2, 3.8, agent_height - 0.3, LIGHT_GRAY,
                     rad=0.06, lw=1, ec="#e2e8f0")
                _circle(ax, 0.9, ay + agent_height * 0.2, 0.18, dept_color)
                ax.text(0.9, ay + agent_height * 0.2, str(i + 1), fontsize=9,
                        color=WHITE, ha="center", va="center", fontweight="bold")
                ax.text(1.3, ay + agent_height * 0.2, agent_name, fontsize=11,
                        fontweight="bold", color=NAVY, va="center")

                # How it works
                ax.text(1.0, ay - 0.0, "Reads shared state + calls LLM",
                        fontsize=8, color=MUTED, style="italic")

                # Arrow
                ax.text(4.6, ay + agent_height * 0.15, "-->", fontsize=12,
                        color=dept_color, va="center", fontweight="bold")

                # Output box
                _box(ax, 5.0, ay - 0.2, 6.5, agent_height - 0.3, WHITE,
                     rad=0.06, lw=1.5, ec=dept_color)
                ax.text(5.3, ay + agent_height * 0.25, "OUTPUT:",
                        fontsize=8, color=dept_color, fontweight="bold")

                for j, output in enumerate(outputs):
                    oy = ay + agent_height * 0.05 - j * (agent_height - 0.5) / max(len(outputs), 1)
                    ax.text(5.5, oy, f"  {output}", fontsize=9, color=SLATE)

            # Footer
            ax.text(6, 0.3, f"Orion | {dept_name} Department | {len(agents)} agents | All outputs validated by Pydantic schema",
                    fontsize=8, color=MUTED, ha="center")

            pdf.savefig(fig, dpi=150)
            plt.close(fig)

        # --- PAGE 7: Output Assembly ---
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 8.5)
        ax.axis("off")
        fig.patch.set_facecolor(OFF_WHITE)

        _box(ax, 0.2, 7.5, 11.6, 0.8, EMERALD, rad=0.08)
        ax.text(6, 7.95, "FINAL OUTPUT", fontsize=20, fontweight="bold",
                color=WHITE, ha="center")
        ax.text(6, 7.65, "All 21 agent outputs assembled into a unified business plan",
                fontsize=10, color=WHITE, ha="center", alpha=0.85)

        # Three format boxes
        formats_data = [
            ("Web Report", "Interactive browser-based report with:\n- Department tabs\n- Collapsible sections\n- KPI highlights\n- Real-time progress", BLUE),
            ("PDF Document", "Professional branded document with:\n- Cover page with brand colours\n- Table of contents\n- Page numbers\n- Print-optimised layout", VIOLET),
            ("JSON Package", "Machine-readable data with:\n- Complete structured plan\n- Generation metadata\n- API call records\n- Token usage stats", TEAL),
        ]

        for i, (name, desc, color) in enumerate(formats_data):
            fx = 0.7 + i * 3.9
            _box(ax, fx, 4.5, 3.5, 2.7, WHITE, lw=2, ec=color, rad=0.08)
            _box(ax, fx + 0.3, 6.7, 2.9, 0.4, color, rad=0.05)
            ax.text(fx + 1.75, 6.9, name, fontsize=11, fontweight="bold",
                    color=WHITE, ha="center", va="center")
            for j, line in enumerate(desc.split("\n")):
                ax.text(fx + 0.3, 6.3 - j * 0.35, line, fontsize=9, color=SLATE)

        # What's in the plan
        ax.text(0.5, 4.1, "COMPLETE PLAN CONTAINS:", fontsize=12, fontweight="bold", color=NAVY)
        plan_items_left = [
            "Market Sizing (TAM/SAM/SOM in Rs)",
            "Real Competitors (names, ratings, location)",
            "SWOT Analysis",
            "Positioning & Competitive Advantage",
            "Setup + Monthly Cost Breakdown",
            "Revenue Model & Pricing",
        ]
        plan_items_right = [
            "20-Period P&L Forecast",
            "Break-even Analysis",
            "Brand Identity & Colours",
            "90-Day Marketing Campaign",
            "Buyer Personas (2-3 profiles)",
            "Operations & Staffing (if physical)",
        ]
        for i, item in enumerate(plan_items_left):
            ax.text(1.0, 3.7 - i * 0.4, f"  {item}", fontsize=9.5, color=SLATE)
        for i, item in enumerate(plan_items_right):
            ax.text(6.5, 3.7 - i * 0.4, f"  {item}", fontsize=9.5, color=SLATE)

        # Bottom summary
        _box(ax, 0.5, 0.6, 11.0, 0.8, NAVY, rad=0.08)
        ax.text(6, 1.1, "ONE SENTENCE  -->  21 AGENTS  -->  COMPLETE BUSINESS PLAN  -->  60-90 SECONDS",
                fontsize=12, fontweight="bold", color=WHITE, ha="center")
        ax.text(6, 0.78, "Target: Entrepreneurs | Students | Consultants | Investors | SME Owners",
                fontsize=9, color=MUTED, ha="center")

        ax.text(6, 0.3, "Orion | B.E. Computer Engineering | University of Mumbai | 2026-27",
                fontsize=8, color=MUTED, ha="center")

        pdf.savefig(fig, dpi=150)
        plt.close(fig)

    print(f"  Full PDF (7 pages): {pdf_path}")
    return pdf_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("Generating comprehensive Orion infographic...")
    print()
    make_tall_infographic()
    make_pdf_version()
    print("\nDone. Files in docs/orion/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
