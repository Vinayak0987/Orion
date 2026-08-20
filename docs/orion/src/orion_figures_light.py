"""
Light-background vector figures.

Document 1: Figures 1, 2, 3, 4, 5, 10, 12, 13
Document 2: conceptual loop graph, anchor boundary, graph invariants,
            ablation design, milestone timeline
"""

import math
from orion_style import (
    ACCENT, ACCENT_SOFT, INK, INK_MUTED, RULE, PANEL_BG, FONT_STACK,
    HUE_ANCHOR, HUE_MONITOR, HUE_HALT, HUE_LEARN, HUE_HUMAN, HUE_EXEC,
)

GREEN = "#1E8A5F"
RED = "#B4433F"
AMBER = "#B07A26"


# ----------------------------------------------------------------- helpers ---

def lc(w, h, content):
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'<defs>'
            f'<marker id="la" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="{ACCENT}"/></marker>'
            f'<marker id="lm" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="{INK_MUTED}"/></marker>'
            f'<marker id="lr" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="{RED}"/></marker>'
            f'<marker id="lg" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="{GREEN}"/></marker>'
            f'</defs>{content}</svg>')


def txt(x, y, s, size=9, colour=None, anchor="start", weight="400",
        italic=False, spacing=0):
    st = f' font-style="italic"' if italic else ''
    sp = f' letter-spacing="{spacing}"' if spacing else ''
    return (f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" '
            f'font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
            f'fill="{colour or INK}"{st}{sp}>{s}</text>')


def box(x, y, w, h, label=None, sub=None, fill=PANEL_BG, stroke=RULE,
        r=5, label_size=9.4, colour=None, sw=1.0, dash=False):
    d = ' stroke-dasharray="4,4"' if dash else ''
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
           f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>']
    if label and sub:
        out.append(txt(x + w / 2, y + h / 2 - 2, label, label_size,
                       colour or INK, "middle", "650"))
        out.append(txt(x + w / 2, y + h / 2 + 10, sub, 7.6, INK_MUTED,
                       "middle"))
    elif label:
        out.append(txt(x + w / 2, y + h / 2 + 3.2, label, label_size,
                       colour or INK, "middle", "650"))
    return "".join(out)


def arrow(x1, y1, x2, y2, dashed=False, label=None, marker="la",
          colour=None, curve=0.0, width=1.2, label_dy=-5):
    c = colour or ACCENT
    d = ' stroke-dasharray="5,4"' if dashed else ''
    if abs(curve) > 1e-6:
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1
        px, py = -dy / L, dx / L
        mx, my = (x1 + x2) / 2 + px * L * curve, (y1 + y2) / 2 + py * L * curve
        p = f'M{x1},{y1} Q{mx:.1f},{my:.1f} {x2},{y2}'
        lx, ly = 0.25 * x1 + 0.5 * mx + 0.25 * x2, 0.25 * y1 + 0.5 * my + 0.25 * y2
    else:
        p = f'M{x1},{y1} L{x2},{y2}'
        lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
    out = [f'<path d="{p}" fill="none" stroke="{c}" stroke-width="{width}"{d} '
           f'marker-end="url(#{marker})"/>']
    if label:
        w = len(label) * 4.4 + 8
        out.append(f'<rect x="{lx - w/2:.1f}" y="{ly + label_dy - 8:.1f}" '
                   f'width="{w:.1f}" height="12" fill="#FFFFFF" opacity="0.94"/>')
        out.append(txt(lx, ly + label_dy + 1, label, 7.4, INK_MUTED, "middle",
                       "600"))
    return "".join(out)


def caption_tag(x, y, s, colour=None):
    return txt(x, y, s.upper(), 8.2, colour or INK_MUTED, "start", "700",
               spacing=1.4)


# --------------------------------------- Figure 1: pipeline vs closed cycle --

def fig1_pipeline_vs_cycle():
    W, H = 1000, 330
    c = [box(20, 20, 455, 292, None, None, "#FFFFFF", RULE, 6),
         box(525, 20, 455, 292, None, None, "#FCFCFE", ACCENT + "30", 6, sw=1.2),
         caption_tag(38, 46, "A one-shot pipeline", INK_MUTED),
         caption_tag(543, 46, "Orion — a cycle that does not end", ACCENT)]

    steps = ["Prompt", "Agents", "Report", "Finish"]
    for i, s in enumerate(steps):
        y = 78 + i * 54
        last = i == len(steps) - 1
        c.append(box(112, y, 270, 38, s, None,
                     "#F4F4F7" if not last else "#FBEDED",
                     RULE if not last else RED + "50", 5,
                     colour=INK if not last else RED))
        if not last:
            c.append(arrow(247, y + 38, 247, y + 54, marker="lm",
                           colour=INK_MUTED))
    c.append(txt(247, 300, "The output is a document. Nothing continues.",
                 8.2, INK_MUTED, "middle", italic=True))

    # right: ring of stages
    cx, cy, r = 752, 176, 104
    labels = ["Business", "Departments", "Projects", "Tasks", "Workers",
              "Decisions", "Execution", "Memory", "Reflection"]
    n = len(labels)
    c.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
             f'stroke="{ACCENT}" stroke-width="1.1" opacity="0.3"/>')
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n
        a2 = -math.pi / 2 + (i + 0.72) * 2 * math.pi / n
        x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        c.append(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 0,1 {x2:.1f},{y2:.1f}" '
                 f'fill="none" stroke="{ACCENT}" stroke-width="1.6" '
                 f'opacity="0.75" marker-end="url(#la)"/>')
        lx, ly = cx + (r + 26) * math.cos(a), cy + (r + 26) * math.sin(a)
        an = "middle"
        if math.cos(a) > 0.35:
            an = "start"
        elif math.cos(a) < -0.35:
            an = "end"
        c.append(txt(lx, ly + 3, labels[i], 8.3, INK, an, "600"))
        c.append(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="3.6" fill="{ACCENT}"/>')
    c.append(txt(cx, cy - 6, "Continuous", 10.4, ACCENT, "middle", "700"))
    c.append(txt(cx, cy + 8, "Operation", 10.4, ACCENT, "middle", "700"))
    return lc(W, H, "".join(c))


# ----------------------------------------- Figure 2: layered architecture ----

def fig2_layers():
    W, H = 1000, 510
    c = []
    L = [
        (20, "Interface Layer", "Business View · Work View · Activity View",
         "#F2F4FD", ACCENT),
        (100, "Business Operating Core", "Intent Classifier · Orchestrator · "
         "Scheduler · Governance · Loop Registry", "#EDF0FC", ACCENT),
    ]
    for y, t, s, fill, col in L:
        c.append(box(20, y, 960, 62, None, None, fill, col + "40", 6, sw=1.2))
        c.append(txt(38, y + 25, t, 10.6, col, "start", "700"))
        c.append(txt(38, y + 43, s, 8.4, INK_MUTED))

    depts = [("Strategy", "5 agents"), ("Finance", "4 agents"),
             ("Branding", "4 agents"), ("Marketing", "4 agents"),
             ("Operations", "4 agents")]
    c.append(box(20, 188, 960, 96, None, None, "#FFFFFF", RULE, 6))
    c.append(txt(38, 208, "FIVE DEPARTMENTS · 21 SPECIALISED AGENTS", 8.2,
                 INK_MUTED, "start", "700", spacing=1.4))
    for i, (d, n) in enumerate(depts):
        x = 36 + i * 187
        c.append(box(x, 220, 174, 52, None, None, PANEL_BG,
                     HUE_EXEC + "45", 5))
        c.append(txt(x + 87, 240, d, 9.6, INK, "middle", "650"))
        c.append(txt(x + 87, 254, n, 7.6, INK_MUTED, "middle"))
        c.append(txt(x + 87, 266, "manager · planner · workers", 6.8,
                     INK_MUTED, "middle"))

    c.append(box(20, 300, 470, 60, None, None, "#F0FBF7", HUE_ANCHOR + "55",
                 6, sw=1.2))
    c.append(txt(38, 322, "Departmental Memory", 10.2, GREEN, "start", "700"))
    c.append(txt(38, 340, "one isolated store per department · four memory types",
                 8.2, INK_MUTED))

    c.append(box(510, 300, 470, 60, None, None, "#F0FBF7", HUE_ANCHOR + "55",
                 6, sw=1.2))
    c.append(txt(528, 322, "Knowledge Base", 10.2, GREEN, "start", "700"))
    c.append(txt(528, 340, "lessons · templates · reusable plans · playbooks",
                 8.2, INK_MUTED))

    c.append(box(20, 376, 960, 76, None, None, "#FAFAFC", RULE, 6, sw=1.2))
    c.append(txt(38, 398, "Shared State — append-only contract", 10.6, ACCENT,
                 "start", "700"))
    c.append(txt(38, 416, "company · departments · projects · tasks · customers · "
                 "products · documents · decisions · audit trail", 8.4, INK_MUTED))
    c.append(txt(38, 434, "An agent may write only its own department's section; a "
                 "cross-department write raises a contract violation.", 8.4,
                 INK_MUTED))

    c.append(box(20, 464, 960, 34, None, None, "#F0FBF7", HUE_ANCHOR + "70",
                 6, sw=1.4))
    c.append(txt(38, 486, "Anchor layer — every anchor metric is derived from the "
                 "append-only record by code. No agent writes one.", 8.8, GREEN,
                 "start", "650"))

    for y in (82, 162, 284, 360, 452):
        c.append(arrow(500, y, 500, y + 14, marker="lm", colour=INK_MUTED,
                       width=1.1))
    return lc(W, H, "".join(c))


def fig_two_layers():
    """Generation layer and operating layer as one system."""
    W, H = 1000, 300
    c = [caption_tag(20, 26, "One system, two layers", ACCENT)]

    c.append(box(24, 46, 452, 214, None, None, "#FFFFFF", HUE_EXEC + "55", 6,
                 sw=1.3))
    c.append(f'<rect x="24" y="46" width="452" height="30" rx="6" '
             f'fill="{HUE_EXEC}" opacity="0.1"/>')
    c.append(txt(40, 66, "GENERATION LAYER", 8.6, HUE_EXEC, "start", "700",
                 spacing=1.2))
    c.append(txt(250, 100, "Produces the opening state", 10.4, INK, "middle",
                 "700"))
    for i, s in enumerate([
            "21 agents across five departments",
            "routing orchestrator over a shared state object",
            "derived quantities override asserted ones",
            "external grounding for competitors and market data"]):
        c.append(txt(46, 128 + i * 20, "·", 9, HUE_EXEC, "start", "700"))
        c.append(txt(58, 128 + i * 20, s, 8.4, INK_MUTED))
    c.append(txt(250, 236, "runs once per company", 7.8, INK_MUTED, "middle",
                 italic=True))

    c.append(box(524, 46, 452, 214, None, None, "#FCFCFE", ACCENT + "40", 6,
                 sw=1.3))
    c.append(f'<rect x="524" y="46" width="452" height="30" rx="6" '
             f'fill="{ACCENT}" opacity="0.08"/>')
    c.append(txt(540, 66, "OPERATING LAYER", 8.6, ACCENT, "start", "700",
                 spacing=1.2))
    c.append(txt(750, 100, "Operates that state onward", 10.4, INK, "middle",
                 "700"))
    for i, s in enumerate([
            "the same five departments, now on cadences",
            "anchors computed from an append-only record",
            "constraints enforced in code, not in prompts",
            "monitor loops and human governance"]):
        c.append(txt(546, 128 + i * 20, "·", 9, ACCENT, "start", "700"))
        c.append(txt(558, 128 + i * 20, s, 8.4, INK_MUTED))
    c.append(txt(750, 236, "runs indefinitely", 7.8, INK_MUTED, "middle",
                 italic=True))

    c.append(arrow(476, 152, 524, 152, marker="la", colour=ACCENT, width=1.6))
    c.append(txt(500, 138, "plan becomes", 7.2, ACCENT, "middle", "650"))
    c.append(txt(500, 176, "state", 7.2, ACCENT, "middle", "650"))

    c.append(txt(20, 284, "The generation layer's two operative findings — derived "
                 "figures override asserted ones, and cross-agent constraints hold "
                 "only when enforced in code — are the principles the operating "
                 "layer generalises.", 8.2, INK_MUTED))
    return lc(W, H, "".join(c))


# ------------------------------------- Figure 3: anatomy of one department ----

def fig3_department_anatomy():
    W, H = 1000, 480
    cx, cy = 500, 240
    RX, RY = 235, 165
    BW, BH = 142, 38
    c = [f'<circle cx="{cx}" cy="{cy}" r="66" fill="#F2F4FD" '
         f'stroke="{ACCENT}" stroke-width="1.4"/>',
         txt(cx, cy - 6, "Department", 10.6, ACCENT, "middle", "700"),
         txt(cx, cy + 9, "persistent identity", 7.8, INK_MUTED, "middle",
             italic=True),
         caption_tag(20, 28, "One department, nine constituent parts", ACCENT)]

    parts = [
        ("Manager", "owns outcomes", HUE_EXEC),
        ("Planner", "decomposes goals", HUE_EXEC),
        ("Workers", "execute tasks", HUE_EXEC),
        ("Memory", "four typed stores", HUE_ANCHOR),
        ("Knowledge", "playbooks, templates", HUE_ANCHOR),
        ("Tools", "registry with health checks", HUE_LEARN),
        ("Objectives", "what it is pursuing", HUE_HUMAN),
        ("Queue", "prioritised work", HUE_MONITOR),
        ("KPIs & State", "health, cadence, throughput", HUE_MONITOR),
    ]
    n = len(parts)
    for i, (t, s, col) in enumerate(parts):
        a = -math.pi / 2 + i * 2 * math.pi / n
        px, py = cx + RX * math.cos(a), cy + RY * math.sin(a)
        ex, ey = cx + 68 * math.cos(a), cy + 68 * math.sin(a)
        # stop the connector at the box edge nearest the centre
        tx = px - (BW / 2 + 4) * math.cos(a) * 0.9
        ty = py - (BH / 2 + 4) * math.sin(a) * 0.9
        c.append(arrow(ex, ey, tx, ty, marker="lm", colour=INK_MUTED,
                       width=1.0))
        c.append(box(px - BW / 2, py - BH / 2, BW, BH, t, s, "#FFFFFF",
                     col + "60", 5, 9.0))
    return lc(W, H, "".join(c))


# ------------------------------- Figure 4: shared context vs scoped memory ----

def fig4_memory_scoping():
    W, H = 1000, 340
    c = [box(20, 20, 455, 300, None, None, "#FFFFFF", RULE, 6),
         box(525, 20, 455, 300, None, None, "#FCFCFE", HUE_ANCHOR + "40", 6, sw=1.2),
         caption_tag(38, 46, "One shared context", INK_MUTED),
         caption_tag(543, 46, "One store per department", GREEN)]

    # left: everything into one pool
    c.append(box(150, 210, 196, 66, None, None, "#FBEDED", RED + "50", 5))
    c.append(txt(248, 236, "Shared context", 9.4, RED, "middle", "650"))
    c.append(txt(248, 250, "every department's history", 7.6, INK_MUTED, "middle"))
    c.append(txt(248, 264, "in one window", 7.6, INK_MUTED, "middle"))
    src = ["Strategy", "Finance", "Branding", "Marketing", "Operations"]
    for i, s in enumerate(src):
        x = 46 + i * 82
        c.append(box(x, 76, 74, 30, s, None, PANEL_BG, RULE, 4, 7.2))
        c.append(arrow(x + 37, 106, 248, 210, marker="lr", colour=RED,
                       width=0.85))
    c.append(txt(248, 296, "A Marketing query retrieves Strategy's risk register.",
                 8.2, RED, "middle", "600"))
    c.append(txt(248, 309, "Precision falls as the company accumulates history.",
                 8.0, INK_MUTED, "middle"))

    # right: isolated stores
    for i, s in enumerate(src):
        x = 546 + i * 86
        c.append(box(x, 76, 78, 30, s, None, PANEL_BG, RULE, 4, 7.2))
        c.append(arrow(x + 39, 106, x + 39, 158, marker="lg", colour=GREEN,
                       width=0.9))
        c.append(box(x, 158, 78, 74, None, None, "#F0FBF7", HUE_ANCHOR + "55", 4))
        for j, ty in enumerate(["episodic", "semantic", "procedural",
                                "reflective"]):
            c.append(txt(x + 39, 174 + j * 15, ty, 6.4, GREEN, "middle", "600"))
    c.append(txt(752, 262, "Retrieval is scoped to the department that owns it.",
                 8.2, GREEN, "middle", "600"))
    c.append(txt(752, 278, "Context stays bounded as the company grows, and each",
                 8.0, INK_MUTED, "middle"))
    c.append(txt(752, 291, "department's learning can be measured on its own.",
                 8.0, INK_MUTED, "middle"))
    return lc(W, H, "".join(c))


# ----------------------------------------- Figure 5: governance gate chain ----

def fig5_gate_chain():
    W, H = 1000, 300
    c = [caption_tag(20, 28, "Every consequential action passes the same chain",
                     ACCENT)]
    stages = [
        ("Decision", "proposed by a department", ACCENT),
        ("Review Queue", "classified by risk", HUE_MONITOR),
        ("Approval Gate", "policy rules evaluated", HUE_HUMAN),
        ("Execution Gate", "Constitution enforced in code", HUE_HALT),
        ("Audit Trail", "immutable, append-only", HUE_ANCHOR),
    ]
    bw, gap = 172, 24
    for i, (t, s, col) in enumerate(stages):
        x = 20 + i * (bw + gap)
        c.append(box(x, 96, bw, 62, None, None, "#FFFFFF", col + "60", 5, sw=1.3))
        c.append(txt(x + bw / 2, 122, t, 9.8, col, "middle", "700"))
        c.append(txt(x + bw / 2, 138, s, 7.4, INK_MUTED, "middle"))
        if i < len(stages) - 1:
            c.append(arrow(x + bw, 127, x + bw + gap, 127, marker="la",
                           colour=ACCENT, width=1.3))
        if i in (1, 2, 3):
            c.append(arrow(x + bw / 2, 158, x + bw / 2, 198, marker="lr",
                           colour=RED, width=1.1, dashed=True))
            halt = {1: "returned for revision", 2: "rejected",
                    3: "blocked by hard constraint"}[i]
            c.append(box(x + 6, 198, bw - 12, 32, halt, None, "#FBEDED",
                         RED + "40", 4, 7.6, colour=RED))
    c.append(txt(20, 268, "A decision can stop at three points. Nothing "
                 "irreversible executes without passing all five.",
                 8.4, INK_MUTED))
    c.append(txt(20, 284, "Subjective questions — brand voice, ethics, "
                 "strategy — are routed to a human by classification, not by "
                 "the agent's discretion.", 8.4, INK_MUTED))
    return lc(W, H, "".join(c))


# ------------------------------------ Figure 10: Kaapi divergence (illustr.) --

def fig10_variance_measured():
    """Real measured data: five repeated runs of prompt p01 per arm."""
    W, H = 1000, 330
    x0, y0, x1, y1 = 300, 52, 700, 250
    c = [caption_tag(20, 26,
                     "Measured — identical prompt, repeated runs", ACCENT)]

    multi = [290.9, 129.1, 239.2, 96.8, 38.4]
    base = [51.7, 87.5, 50.0]
    hi = 320.0

    c.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" '
             f'fill="#FFFFFF" stroke="{RULE}" stroke-width="1"/>')
    for v in (0, 100, 200, 300):
        gy = y1 - v / hi * (y1 - y0)
        c.append(f'<path d="M{x0},{gy:.1f} L{x1},{gy:.1f}" stroke="{RULE}" '
                 f'stroke-width="0.6" stroke-dasharray="3,3"/>')
        c.append(txt(x0 - 7, gy + 3, str(v), 7.2, INK_MUTED, "end"))
    c.append(txt(x0 - 7, y0 - 6, "MAPE %", 7.2, INK_MUTED, "end"))

    def band(vals, cx, colour, label, mean, sd, side=1):
        out = []
        lo, up = min(vals), max(vals)
        ylo = y1 - lo / hi * (y1 - y0)
        yup = y1 - up / hi * (y1 - y0)
        ym = y1 - mean / hi * (y1 - y0)
        out.append(f'<rect x="{cx-26}" y="{yup:.1f}" width="52" '
                   f'height="{ylo-yup:.1f}" fill="{colour}" opacity="0.1"/>')
        out.append(f'<path d="M{cx-30},{ym:.1f} L{cx+30},{ym:.1f}" '
                   f'stroke="{colour}" stroke-width="2"/>')
        for v in vals:
            vy = y1 - v / hi * (y1 - y0)
            out.append(f'<circle cx="{cx}" cy="{vy:.1f}" r="3.6" '
                       f'fill="#FFFFFF" stroke="{colour}" stroke-width="1.6"/>')
            lx = cx + side * 10
            out.append(txt(lx, vy + 3, f"{v}", 6.8, INK_MUTED,
                           "start" if side > 0 else "end"))
        out.append(txt(cx, y1 + 16, label, 8.4, colour, "middle", "700"))
        out.append(txt(cx, y1 + 29, f"mean {mean}  ·  sd {sd}", 7.4,
                       INK_MUTED, "middle"))
        return "".join(out)

    c.append(band(base, 400, GREEN, "baseline", 63.1, 21.2, side=-1))
    c.append(band(multi, 600, RED, "multi-agent", 158.9, 103.8, side=1))

    c.append(txt(20, 74, "Same prompt, five times.", 10.2, INK, "start", "700"))
    c.append(txt(20, 92, "p01 — ice cream shop,", 8.6, INK_MUTED))
    c.append(txt(20, 106, "Andheri West, ₹15 L.", 8.6, INK_MUTED))
    c.append(txt(20, 128, "All spread is run-to-run", 8.6, INK_MUTED))
    c.append(txt(20, 142, "variance, not input variance.", 8.6, INK_MUTED))

    c.append(txt(20, 176, "The pipeline's best run", 8.6, INK, "start", "650"))
    c.append(txt(20, 190, "(38.4) beats the baseline's", 8.6, INK, "start",
                 "650"))
    c.append(txt(20, 204, "best (50.0). It does not", 8.6, INK, "start", "650"))
    c.append(txt(20, 218, "reliably produce it.", 8.6, INK, "start", "650"))

    c.append(txt(20, 244, "sd 4.9× the baseline's", 8.2, RED, "start", "700"))
    c.append(txt(20, 258, "spread 7.6× vs 1.8×", 8.2, RED, "start", "700"))

    c.append(txt(760, 90, "Unreliably better,", 9.6, INK, "start", "700"))
    c.append(txt(760, 105, "not reliably worse.", 9.6, INK, "start", "700"))
    c.append(txt(760, 128, "This is the signature of", 8.2, INK_MUTED))
    c.append(txt(760, 141, "variance compounding along", 8.2, INK_MUTED))
    c.append(txt(760, 154, "a dependency chain: each", 8.2, INK_MUTED))
    c.append(txt(760, 167, "estimation step carries", 8.2, INK_MUTED))
    c.append(txt(760, 180, "error and the errors", 8.2, INK_MUTED))
    c.append(txt(760, 193, "compose.", 8.2, INK_MUTED))

    c.append(txt(20, 296, "Measured data, n=5 (multi-agent) and n=3 (baseline). "
                 "Financial accuracy is scored against sector benchmarks that are "
                 "not yet sourced, so absolute", 7.8, INK_MUTED))
    c.append(txt(20, 308, "values are PROVISIONAL; the between-arm comparison is "
                 "less affected since both arms use the same benchmark. Not a "
                 "settled finding until the full sweep is run.", 7.8, INK_MUTED))
    return lc(W, H, "".join(c))


def fig_goodhart_prospective():
    """Prospective divergence pattern - explicitly not measured."""
    W, H = 420, 300
    x0, y0, x1, y1 = 52, 40, 386, 226
    c = [caption_tag(6, 20, "Prospective — proxy up, anchor down", INK_MUTED)]
    c.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" '
             f'fill="#FFFFFF" stroke="{RULE}" stroke-width="1"/>')
    for i in range(1, 4):
        gy = y0 + (y1 - y0) * i / 4
        c.append(f'<path d="M{x0},{gy} L{x1},{gy}" stroke="{RULE}" '
                 f'stroke-width="0.6" stroke-dasharray="3,3"/>')

    weeks = 12
    proxy = [0, 6, 13, 19, 26, 33, 41, 48, 56, 63, 71, 78]
    anchor = [0, -1, -2, -3, -5, -6, -8, -9, -11, -12, -14, -15]

    def px(i):
        return x0 + (x1 - x0) * i / (weeks - 1)

    def py(v, lo=-24, hi=88):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    area = " ".join(f"{px(i):.1f},{py(proxy[i]):.1f}" for i in range(weeks))
    area += " " + " ".join(f"{px(i):.1f},{py(anchor[i]):.1f}"
                           for i in reversed(range(weeks)))
    c.append(f'<polygon points="{area}" fill="{AMBER}" opacity="0.1"/>')

    pl = " ".join(f"{px(i):.1f},{py(proxy[i]):.1f}" for i in range(weeks))
    al = " ".join(f"{px(i):.1f},{py(anchor[i]):.1f}" for i in range(weeks))
    c.append(f'<polyline points="{pl}" fill="none" stroke="{GREEN}" '
             f'stroke-width="2"/>')
    c.append(f'<polyline points="{al}" fill="none" stroke="{RED}" '
             f'stroke-width="2"/>')
    c.append(f'<path d="M{x0},{py(0)} L{x1},{py(0)}" stroke="{INK_MUTED}" '
             f'stroke-width="0.9"/>')

    c.append(txt(px(11) - 4, py(proxy[-1]) - 8, "proxy metric", 7.6,
                 GREEN, "end", "650"))
    c.append(txt(px(11) - 4, py(anchor[-1]) + 14, "anchor metric",
                 7.6, RED, "end", "650"))
    c.append(txt(x0 - 6, py(0) + 3, "0", 7.2, INK_MUTED, "end"))
    for i in (0, 5, 11):
        c.append(txt(px(i), y1 + 13, f"wk {i+1}", 7.0, INK_MUTED, "middle"))

    c.append(txt(6, 256, "The pattern the operating layer is", 8.4, INK,
                 "start", "650"))
    c.append(txt(6, 270, "designed to make detectable.", 8.4, INK, "start",
                 "650"))
    c.append(txt(6, 288, "Not measured — this is the hypothesis, not a result.",
                 7.6, INK_MUTED, "start", "400", italic=True))
    return lc(W, H, "".join(c))


# --------------------------------- Figure 12: living object version history --

def fig12_living_object():
    W, H = 1000, 250
    c = [caption_tag(20, 28, "A marketing plan is a living object, not an export",
                     ACCENT)]
    y = 96
    c.append(f'<path d="M62,{y} L946,{y}" stroke="{RULE}" stroke-width="2"/>')
    versions = [
        ("v1", "launch plan", "opening state"),
        ("v2", "channel mix cut", "CAC +18%"),
        ("v3", "discount pulled", "margin −11%"),
        ("v4", "retention priority", "churn −9%"),
        ("v5", "current", "margin +6%"),
    ]
    step = 884 / (len(versions) - 1)
    for i, (v, what, why) in enumerate(versions):
        x = 62 + i * step
        cur = i == len(versions) - 1
        col = ACCENT if cur else ACCENT_SOFT
        c.append(f'<circle cx="{x:.1f}" cy="{y}" r="{9 if cur else 7}" '
                 f'fill="{"#FFFFFF"}" stroke="{col}" stroke-width="2"/>')
        if cur:
            c.append(f'<circle cx="{x:.1f}" cy="{y}" r="3.4" fill="{col}"/>')
        c.append(txt(x, y - 22, v, 10.2, col, "middle", "700"))
        c.append(txt(x, y + 30, what, 8.4, INK, "middle", "650"))
        c.append(txt(x, y + 44, why, 7.6, INK_MUTED, "middle"))
        if i:
            c.append(txt(x - step / 2, y - 8, "revised by", 7.0, INK_MUTED,
                         "middle", italic=True))
    c.append(box(20, 164, 960, 62, None, None, PANEL_BG, RULE, 5))
    c.append(txt(38, 186, "Every revision cites the anchor movement that "
                 "caused it.", 9.2, ACCENT, "start", "650"))
    c.append(txt(38, 204, "Nothing is regenerated from scratch and no version "
                 "is discarded, so the reasoning behind the current plan "
                 "remains inspectable.", 8.4, INK_MUTED))
    c.append(txt(38, 218, "The same holds for the business strategy, financial "
                 "model, product roadmap, sales pipeline and customer database.",
                 8.4, INK_MUTED))
    return lc(W, H, "".join(c))


# ------------------------------------------- Figure 13: tick sequence chart --

def fig13_sequence():
    W, H = 1000, 470
    lanes = [("Scheduler", ACCENT), ("Dept Manager", HUE_EXEC),
             ("Memory", HUE_ANCHOR), ("Planner", HUE_EXEC),
             ("Governance", HUE_HUMAN), ("Human", HUE_HUMAN),
             ("Worker", HUE_EXEC), ("Ledger", HUE_ANCHOR),
             ("Monitors", HUE_MONITOR)]
    c = [caption_tag(20, 26, "One tick, end to end", ACCENT)]
    n = len(lanes)
    x0, gap = 76, (930 - 76) / (n - 1)
    xs = [x0 + i * gap for i in range(n)]
    for (nm, col), x in zip(lanes, xs):
        c.append(txt(x, 52, nm, 7.8, col, "middle", "700"))
        c.append(f'<path d="M{x:.1f},62 L{x:.1f},404" stroke="{col}" '
                 f'stroke-width="0.9" stroke-dasharray="3,4" opacity="0.55"/>')

    msgs = [
        (0, 1, "tick fires", False),
        (1, 2, "retrieve context", False),
        (2, 1, "memories & lessons", True),
        (1, 3, "plan work", False),
        (3, 4, "submit decisions", False),
        (4, 5, "escalate high-risk", False),
        (5, 4, "approve", True),
        (4, 6, "execute approved only", False),
        (6, 7, "record outcome", False),
        (6, 2, "write memory", False),
        (7, 8, "recompute anchors", False),
        (8, 5, "flag divergence", True),
    ]
    y = 80
    for a, b, lbl, dashed in msgs:
        xa, xb = xs[a], xs[b]
        c.append(arrow(xa, y, xb, y, dashed=dashed, marker="lm",
                       colour=INK_MUTED, width=1.1))
        mid = (xa + xb) / 2
        c.append(txt(mid, y - 5, lbl, 7.4, INK, "middle", "600"))
        y += 24

    c.append(f'<rect x="{xs[1]-30:.1f}" y="374" width="{xs[8]-xs[1]+60:.1f}" '
             f'height="30" rx="4" fill="{PANEL_BG}" stroke="{RULE}"/>')
    c.append(txt((xs[1] + xs[8]) / 2, 393,
                 "every N ticks the department reflects — on measured anchor "
                 "deltas, never on its own report", 7.8, INK_MUTED, "middle",
                 "600"))
    c.append(txt(20, 436, "Solid arrows carry work. Dashed arrows return "
                 "evaluation. The worker never writes an anchor; the ledger "
                 "does, and the anchors are recomputed from it.",
                 8.2, INK_MUTED))
    return lc(W, H, "".join(c))


# ============================ DOCUMENT 2 FIGURES ============================

def d2_fig1_loop_graph():
    """Conceptual loop graph, academic styling."""
    W, H = 1000, 400
    c = [caption_tag(20, 26, "The proposed control topology under study", ACCENT)]
    c.append(box(28, 44, 300, 300, None, None, "#FFFFFF", HUE_EXEC + "55", 6,
                 sw=1.2))
    c.append(txt(44, 66, "EXECUTION LOOPS", 8.0, HUE_EXEC, "start", "700",
                 spacing=1.3))
    depts = ["Strategy", "Finance", "Branding", "Marketing", "Operations"]
    for i, d in enumerate(depts):
        c.append(box(44, 82 + i * 50, 268, 40, d, None, PANEL_BG,
                     HUE_EXEC + "40", 4, 8.8))

    c.append(box(672, 44, 300, 300, None, None, "#FFFFFF", HUE_MONITOR + "55",
                 6, sw=1.2))
    c.append(txt(688, 66, "MONITOR LOOPS", 8.0, HUE_MONITOR, "start", "700",
                 spacing=1.3))
    mons = [("Goodhart Detector", "claim vs ledger"),
            ("Conflict Detector", "cross-department"),
            ("Drift & Decay Monitor", "freshness"),
            ("Objective Review", "should this goal exist?")]
    for i, (m, s) in enumerate(mons):
        c.append(box(688, 84 + i * 62, 268, 50, m, s, PANEL_BG,
                     HUE_MONITOR + "40", 4, 8.8))

    c.append(box(374, 62, 252, 76, None, None, "#F0FBF7", HUE_ANCHOR + "70", 6,
                 sw=1.5))
    c.append(txt(500, 88, "Anchors", 10.6, GREEN, "middle", "700"))
    c.append(txt(500, 104, "computed by code from an", 7.8, INK_MUTED, "middle"))
    c.append(txt(500, 117, "append-only ledger", 7.8, INK_MUTED, "middle"))
    c.append(txt(500, 131, "agent-immutable", 7.6, GREEN, "middle", "650"))

    c.append(box(374, 168, 252, 60, None, None, "#FDF3F5", HUE_HALT + "60", 6,
                 sw=1.3))
    c.append(txt(500, 192, "Constitution", 10.2, RED, "middle", "700"))
    c.append(txt(500, 208, "hard constraints enforced in code", 7.8, INK_MUTED,
                 "middle"))
    c.append(txt(500, 220, "not in prompts", 7.6, RED, "middle", "650"))

    c.append(box(374, 258, 252, 60, None, None, "#F7F2FD", HUE_HUMAN + "70", 6,
                 sw=1.3))
    c.append(txt(500, 282, "Human Judgement", 10.2, "#6B3FA0", "middle", "700"))
    c.append(txt(500, 298, "subjective questions, arbitration,", 7.8, INK_MUTED,
                 "middle"))
    c.append(txt(500, 310, "ratification", 7.8, INK_MUTED, "middle"))

    c.append(arrow(328, 150, 374, 110, marker="lg", colour=GREEN, width=1.2,
                   label="writes"))
    c.append(arrow(626, 100, 672, 140, marker="lg", colour=GREEN, width=1.2,
                   label="reads"))
    c.append(arrow(672, 250, 626, 200, marker="lr", colour=RED, width=1.2,
                   dashed=True))
    c.append(arrow(374, 200, 328, 240, marker="lr", colour=RED, width=1.2,
                   dashed=True, label="blocks"))
    c.append(arrow(672, 300, 626, 288, marker="lm", colour=INK_MUTED,
                   width=1.2, dashed=True, label="escalate"))
    c.append(arrow(374, 288, 328, 300, marker="lm", colour=INK_MUTED,
                   width=1.2, dashed=True, label="ratify"))
    c.append(txt(20, 376, "Monitors read anchors but are not evaluated by the "
                 "loops they audit. Every cycle terminates at an anchor or at a "
                 "human.", 8.2, INK_MUTED))
    return lc(W, H, "".join(c))


def d2_fig2_anchor_boundary():
    W, H = 1000, 300
    c = [caption_tag(20, 26, "The anchor boundary", ACCENT)]
    c.append(box(28, 46, 380, 216, None, None, "#FFFFFF", RULE, 6))
    c.append(txt(44, 68, "AGENT RUNTIME", 8.0, INK_MUTED, "start", "700",
                 spacing=1.3))
    for i, t in enumerate(["Planners", "Workers", "Reflection", "Managers"]):
        c.append(box(44, 82 + i * 44, 348, 36, t, None, PANEL_BG, RULE, 4, 8.8))

    c.append(f'<path d="M448,52 L448,258" stroke="{RED}" stroke-width="2.2" '
             f'stroke-dasharray="7,5"/>')
    c.append(txt(448, 42, "no write path exists", 8.0, RED, "middle", "700"))

    c.append(box(492, 46, 480, 216, None, None, "#F0FBF7", HUE_ANCHOR + "60", 6,
                 sw=1.4))
    c.append(txt(508, 68, "ANCHOR LAYER", 8.0, GREEN, "start", "700",
                 spacing=1.3))
    c.append(box(508, 82, 448, 50, "Append-only ledger",
                 "immutable, timestamped, source-attributed", "#FFFFFF",
                 HUE_ANCHOR + "50", 4, 9.2))
    c.append(arrow(732, 132, 732, 150, marker="lg", colour=GREEN, width=1.2))
    c.append(box(508, 150, 448, 50, "Anchor metrics",
                 "recomputed deterministically by code", "#FFFFFF",
                 HUE_ANCHOR + "50", 4, 9.2))
    c.append(box(508, 212, 448, 34, "read-only to every agent", None,
                 "#FFFFFF", HUE_ANCHOR + "50", 4, 8.8, colour=GREEN))

    for i in range(4):
        c.append(arrow(392, 100 + i * 44, 442, 130 + i * 20, marker="lr",
                       colour=RED, width=0.9, dashed=True))
    c.append(txt(20, 288, "We propose that this asymmetry — readable, never "
                 "writable — is what allows an anchor to remain a measure "
                 "rather than becoming a target.", 8.2, INK_MUTED))
    return lc(W, H, "".join(c))


def d2_fig3_invariants():
    W, H = 1000, 300
    c = [caption_tag(20, 26, "Two invariants checked when a loop registers",
                     ACCENT)]
    c.append(box(28, 48, 452, 212, None, None, "#FFFFFF", RULE, 6))
    c.append(txt(48, 74, "I1 — Termination", 10.4, ACCENT, "start", "700"))
    c.append(txt(48, 92, "Every cycle in the loop graph contains at least one",
                 8.4, INK_MUTED))
    c.append(txt(48, 105, "node that is a code-computed anchor or a human",
                 8.4, INK_MUTED))
    c.append(txt(48, 118, "decision.", 8.4, INK_MUTED))
    c.append(box(48, 132, 190, 34, "A → B → C → A", None, "#FBEDED",
                 RED + "45", 4, 8.6, colour=RED))
    c.append(txt(143, 180, "rejected", 8.0, RED, "middle", "700"))
    c.append(box(270, 132, 190, 34, "A → B → anchor → A", None, "#F0FBF7",
                 HUE_ANCHOR + "55", 4, 8.6, colour=GREEN))
    c.append(txt(365, 180, "accepted", 8.0, GREEN, "middle", "700"))
    c.append(txt(48, 210, "Rationale: a cycle with no external referent can", 8.2,
                 INK_MUTED))
    c.append(txt(48, 223, "converge on agreement without converging on truth.",
                 8.2, INK_MUTED))

    c.append(box(520, 48, 452, 212, None, None, "#FFFFFF", RULE, 6))
    c.append(txt(540, 74, "I2 — Independence", 10.4, ACCENT, "start", "700"))
    c.append(txt(540, 92, "A monitor loop is not evaluated by, and shares no",
                 8.4, INK_MUTED))
    c.append(txt(540, 105, "reward signal with, the loop it monitors.", 8.4,
                 INK_MUTED))
    c.append(box(540, 132, 190, 34, "shared signal", None, "#FBEDED",
                 RED + "45", 4, 8.6, colour=RED))
    c.append(txt(635, 180, "rejected", 8.0, RED, "middle", "700"))
    c.append(box(762, 132, 190, 34, "disjoint signals", None, "#F0FBF7",
                 HUE_ANCHOR + "55", 4, 8.6, colour=GREEN))
    c.append(txt(857, 180, "accepted", 8.0, GREEN, "middle", "700"))
    c.append(txt(540, 210, "Rationale: an auditor rewarded by the metric it", 8.2,
                 INK_MUTED))
    c.append(txt(540, 223, "audits has no incentive to report capture.", 8.2,
                 INK_MUTED))
    c.append(txt(20, 288, "Whether these conditions are necessary, or merely "
                 "sufficient, is among the questions this work proposes to "
                 "examine.", 8.2, INK_MUTED, italic=True))
    return lc(W, H, "".join(c))


def d2_fig4_ablation():
    W, H = 1000, 390
    c = [caption_tag(20, 26,
                     "Existing arms retained · proposed arms added", ACCENT)]

    existing = [
        ("multi_agent", "full pipeline", "treatment", GREEN),
        ("baseline", "one LLM call, same rubric", "RQ1 control", AMBER),
        ("all_departments", "routing disabled", "RQ2 control", AMBER),
        ("no_grounding", "retrieval disabled", "RQ3 control", AMBER),
    ]
    proposed = [
        ("single_loop", "proxy metrics, no anchors,\nno monitors, no gates",
         "RQ5 control", RED),
        ("anchors_only", "anchor metrics,\nno monitors", "isolates anchoring",
         AMBER),
        ("monitors_only", "proxy metrics,\nfour monitors", "isolates monitoring",
         AMBER),
        ("full_graph", "anchors, monitors,\nconstitution, gates",
         "RQ5–RQ7 treatment", GREEN),
    ]

    c.append(box(20, 46, 470, 320, None, None, "#FFFFFF", RULE, 6))
    c.append(txt(38, 68, "IMPLEMENTED AND MEASURED", 8.2, INK_MUTED, "start",
                 "700", spacing=1.3))
    for i, (n, m, s, col) in enumerate(existing):
        y = 84 + i * 68
        c.append(box(38, y, 434, 56, None, None, PANEL_BG, col + "50", 5))
        c.append(txt(52, y + 22, n, 9.4, INK, "start", "700"))
        c.append(txt(52, y + 38, m, 8.0, INK_MUTED))
        c.append(txt(458, y + 22, s, 7.6, col, "end", "650"))

    c.append(box(510, 46, 470, 320, None, None, "#FCFCFE", ACCENT + "35", 6,
                 sw=1.2))
    c.append(txt(528, 68, "PROPOSED FOR THE OPERATING LAYER", 8.2, ACCENT,
                 "start", "700", spacing=1.3))
    for i, (n, m, s, col) in enumerate(proposed):
        y = 84 + i * 68
        c.append(box(528, y, 434, 56, None, None, "#FFFFFF", col + "50", 5))
        c.append(txt(542, y + 20, n, 9.4, INK, "start", "700"))
        for j, ln in enumerate(m.split("\n")):
            c.append(txt(542, y + 34 + j * 11, ln, 7.6, INK_MUTED))
        c.append(txt(948, y + 20, s, 7.6, col, "end", "650"))

    c.append(txt(20, 384, "All arms share the seed, the model, the prompt set and "
                 "the starting state. Only the manipulation named in each arm "
                 "differs. The four existing arms are unchanged, so results "
                 "already obtained remain valid.", 8.0, INK_MUTED))
    return lc(W, H, "".join(c))


def d2_fig5_timeline():
    W, H = 1000, 250
    c = [caption_tag(20, 26, "Milestones and decision gates", ACCENT)]
    y = 108
    c.append(f'<path d="M60,{y} L950,{y}" stroke="{RULE}" stroke-width="2"/>')
    ms = [
        ("W1–2", "Substrate", "state, ledger,\nanchors, Constitution"),
        ("W3–4", "Operation", "departments, work,\nmemory, governance"),
        ("W5", "Continuity", "scheduler, events —\nthe business runs"),
        ("W6", "Loop graph", "registry, validator,\nfour monitors"),
        ("W7", "Experiment", "ablation harness,\nseeded runs"),
        ("W8", "Write-up", "analysis, artifact,\nthesis draft"),
    ]
    step = 890 / (len(ms) - 1)
    for i, (wk, name, detail) in enumerate(ms):
        x = 60 + i * step
        gate = i in (2, 4)
        col = ACCENT if not gate else GREEN
        c.append(f'<circle cx="{x:.1f}" cy="{y}" r="{9 if gate else 7}" '
                 f'fill="#FFFFFF" stroke="{col}" stroke-width="2"/>')
        if gate:
            c.append(f'<circle cx="{x:.1f}" cy="{y}" r="3.4" fill="{col}"/>')
        c.append(txt(x, y - 40, wk, 8.2, INK_MUTED, "middle", "650"))
        c.append(txt(x, y - 24, name, 9.6, col, "middle", "700"))
        for j, ln in enumerate(detail.split("\n")):
            c.append(txt(x, y + 26 + j * 12, ln, 7.4, INK_MUTED, "middle"))
        if gate:
            c.append(txt(x, y + 62, "decision gate", 7.2, GREEN, "middle",
                         "700", italic=True))
    c.append(txt(20, 212, "At each decision gate the work either proceeds or "
                 "the scope narrows. The two gates protect the experiment: if "
                 "continuous operation is not stable by week 5,", 8.2, INK_MUTED))
    c.append(txt(20, 228, "the ablation cannot be run, and the study would be "
                 "re-scoped to a narrower claim rather than reported on an "
                 "unstable substrate.", 8.2, INK_MUTED))
    return lc(W, H, "".join(c))
