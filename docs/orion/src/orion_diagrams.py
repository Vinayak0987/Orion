# Academic diagrams for the project review deck.
# Aspect ratios match the template picture frames exactly so nothing is letterboxed.
import math
from orion_figures_light import lc, txt, box, arrow, caption_tag
from orion_style import ACCENT, INK, INK_MUTED, RULE, PANEL_BG, FONT_STACK

GREEN = "#1E8A5F"
RED = "#B4433F"
AMBER = "#B07A26"
TEAL = "#0097A7"
BLUE = "#4285F4"

# ------------------------------------------------------------ DFD primitives --

def entity(x, y, w, h, label):
    # External entity: plain rectangle
    return box(x, y, w, h, label, None, "#FFFFFF", INK_MUTED, 2, 9.0)

def process(x, y, w, h, num, label):
    out = [box(x, y, w, h, None, None, "#F2F4FD", ACCENT, 8, sw=1.3)]
    out.append(txt(x + w / 2, y + 15, num, 8.2, ACCENT, "middle", "700"))
    lines = label.split("\n")
    start = y + h / 2 + (2 if len(lines) == 1 else -3)
    for i, ln in enumerate(lines):
        out.append(txt(x + w / 2, start + i * 11, ln, 8.6, INK, "middle", "650"))
    return "".join(out)

def datastore(x, y, w, h, tag, label):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#F0FBF7" '
           f'stroke="none"/>']
    out.append(f'<path d="M{x},{y} L{x+w},{y} M{x},{y+h} L{x+w},{y+h}" '
               f'stroke="{GREEN}" stroke-width="1.4"/>')
    out.append(f'<path d="M{x+26},{y} L{x+26},{y+h}" stroke="{GREEN}" '
               f'stroke-width="1.1"/>')
    out.append(txt(x + 13, y + h / 2 + 3, tag, 8.4, GREEN, "middle", "700"))
    out.append(txt(x + 26 + (w - 26) / 2, y + h / 2 + 3, label, 8.4, INK,
                   "middle", "600"))
    return "".join(out)

def flow(x1, y1, x2, y2, label=None, curve=0.0, colour=None, dashed=False):
    return arrow(x1, y1, x2, y2, dashed=dashed, label=label,
                 marker="lm" if not colour else "la",
                 colour=colour or INK_MUTED, curve=curve, width=1.15)

# ================================================= 1. ARCHITECTURE (1.40) ====

def architecture():
    W, H = 700, 500
    c = [caption_tag(16, 20, "Orion ? system architecture", ACCENT)]
    rows = [
        (44, "Natural-language prompt", "one sentence from the founder", "#FFFFFF", INK_MUTED),
        (96, "Intent Classifier", "LLM semantics + deterministic budget/location parsing", "#F2F4FD", ACCENT),
        (148, "Business Orchestrator", "routing rules -> active departments -> execution DAG", "#F2F4FD", ACCENT),
    ]
    for y, t, s, fill, col in rows:
        c.append(box(28, y, 644, 44, None, None, fill, col, 6, sw=1.2))
        c.append(txt(350, y + 19, t, 10.2, col if col != INK_MUTED else INK, "middle", "700"))
        c.append(txt(350, y + 33, s, 7.6, INK_MUTED, "middle"))

    c.append(box(28, 204, 644, 74, None, None, "#FFFFFF", RULE, 6))
    c.append(txt(40, 220, "DEPARTMENT LAYER ? 5 nested graphs, 21 agents", 7.6,
                 INK_MUTED, "start", "700", spacing=1.2))
    depts = [("Strategy", 5), ("Finance", 4), ("Branding", 4),
             ("Marketing", 4), ("Operations", 4)]
    for i, (d, n) in enumerate(depts):
        x = 40 + i * 125
        c.append(box(x, 230, 116, 38, None, None, PANEL_BG, BLUE, 5))
        c.append(txt(x + 58, 246, d, 8.6, INK, "middle", "650"))
        c.append(txt(x + 58, 258, "%d agents" % n, 7.2, INK_MUTED, "middle"))

    c.append(box(28, 292, 644, 40, None, None, "#FAFAFC", RULE, 6, sw=1.2))
    c.append(txt(350, 308, "SharedBusinessState ? append-only contract", 9.6,
                 ACCENT, "middle", "700"))
    c.append(txt(350, 322, "an agent may write only its own department's section",
                 7.4, INK_MUTED, "middle"))

    c.append(box(28, 346, 644, 86, None, None, "#F0FBF7", GREEN, 6, sw=1.3))
    c.append(txt(40, 362, "OPERATING LAYER", 7.6, GREEN, "start", "700", spacing=1.2))
    ops = [("Ledger", "append-only"), ("Anchors", "computed, never written"),
           ("Constitution", "code-enforced"), ("Governance", "gate chain"),
           ("Monitors", "4 loops"), ("Scheduler", "cadences")]
    for i, (t, s) in enumerate(ops):
        x = 40 + (i % 3) * 213
        y = 372 + (i // 3) * 30
        c.append(box(x, y, 202, 26, None, None, "#FFFFFF", GREEN, 4))
        c.append(txt(x + 101, y + 12, t, 8.2, INK, "middle", "650"))
        c.append(txt(x + 101, y + 22, s, 6.8, INK_MUTED, "middle"))

    c.append(box(28, 444, 644, 36, None, None, "#FFFFFF", INK_MUTED, 6))
    c.append(txt(350, 466, "Output layer ? JSON package, HTML report, PDF",
                 9.4, INK, "middle", "650"))

    for y in (88, 140, 192, 284, 338, 436):
        c.append(arrow(350, y, 350, y + 12, marker="lm", colour=INK_MUTED, width=1.1))
    return lc(W, H, "".join(c))

# ================================================== 2. DFD LEVEL 0 (1.55) ====

def dfd0():
    W, H = 680, 440
    c = [caption_tag(16, 22, "DFD Level 0 ? context diagram", ACCENT)]
    c.append(entity(24, 60, 130, 52, "Founder"))
    c.append(entity(24, 300, 130, 52, "Human Supervisor"))
    c.append(entity(526, 60, 130, 52, "External Data Sources"))
    c.append(txt(591, 122, "OpenStreetMap ? Serper", 7.0, INK_MUTED, "middle"))
    c.append(entity(526, 300, 130, 52, "Report Consumer"))

    c.append(process(255, 175, 170, 90, "0", "Orion\nAI Business\nOperating System"))

    c.append(flow(154, 78, 255, 196, "business idea + budget"))
    c.append(flow(255, 244, 154, 320, "plan, report, PDF", curve=0.06))
    c.append(flow(425, 196, 526, 82, "place + market queries"))
    c.append(flow(526, 96, 425, 214, "competitors, statistics", curve=0.06))
    c.append(flow(425, 232, 526, 318, "living business objects"))
    c.append(flow(154, 330, 255, 250, "approve / reject decision"))
    c.append(flow(255, 226, 154, 306, "pending decisions, findings", curve=-0.06))

    c.append(txt(16, 418, "One process, four external entities. No data stores are "
                 "shown at level 0 by convention.", 7.6, INK_MUTED))
    return lc(W, H, "".join(c))

# ================================================== 3. DFD LEVEL 1 (1.90) ====

def dfd1():
    W, H = 865, 455
    c = [caption_tag(16, 20, "DFD Level 1 ? major processes", ACCENT)]
    c.append(entity(14, 54, 104, 44, "Founder"))
    c.append(entity(14, 250, 104, 44, "Supervisor"))
    c.append(entity(748, 54, 104, 44, "External APIs"))

    c.append(process(150, 44, 132, 62, "1.0", "Intent\nExtraction"))
    c.append(process(150, 150, 132, 62, "2.0", "Routing &\nOrchestration"))
    c.append(process(330, 96, 150, 70, "3.0", "Department\nExecution"))
    c.append(process(548, 44, 140, 62, "4.0", "Output\nGeneration"))
    c.append(process(548, 150, 140, 62, "5.0", "Cadence\nScheduler"))
    c.append(process(330, 236, 150, 70, "6.0", "Monitoring &\nGovernance"))

    c.append(datastore(120, 348, 200, 30, "D1", "SharedBusinessState"))
    c.append(datastore(348, 348, 150, 30, "D2", "Ledger"))
    c.append(datastore(524, 348, 176, 30, "D3", "Department Memory"))
    c.append(datastore(348, 396, 200, 30, "D4", "Decisions + Audit Trail"))

    c.append(flow(118, 68, 150, 70, "prompt"))
    c.append(flow(216, 106, 216, 150, "intent"))
    c.append(flow(282, 178, 330, 140, "routing decision"))
    c.append(flow(480, 124, 548, 74, "plan"))
    c.append(flow(548, 62, 118, 62, None, curve=0.0, colour=INK_MUTED) if False else "")
    c.append(flow(618, 44, 118, 54, "report", curve=-0.10))
    c.append(flow(480, 110, 748, 72, "queries"))
    c.append(flow(748, 88, 480, 118, "grounded data", curve=0.08))
    c.append(flow(405, 166, 405, 236, "outcomes"))
    c.append(flow(548, 180, 480, 260, "tick"))
    c.append(flow(405, 306, 118, 272, "findings, pending decisions", curve=0.06))
    c.append(flow(118, 262, 330, 268, "approve / reject", curve=-0.05))

    c.append(flow(370, 166, 240, 348, None, curve=0.05))
    c.append(flow(240, 348, 370, 176, None, curve=0.05))
    c.append(flow(420, 306, 420, 348, None))
    c.append(flow(470, 306, 570, 348, None))
    c.append(flow(455, 306, 455, 396, None, curve=-0.12))

    c.append(txt(16, 440, "D1 carries the generation state; D2 is the append-only "
                 "ledger every anchor is derived from; D4 records every decision "
                 "and its outcome, including halts.", 7.4, INK_MUTED))
    return lc(W, H, "".join(c))

# ================================================== 4. DFD LEVEL 2 (1.78) ====

def dfd2():
    W, H = 770, 433
    c = [caption_tag(16, 20, "DFD Level 2 ? process 3.0 Department Execution",
                     ACCENT)]
    c.append(entity(14, 40, 96, 40, "2.0 Routing"))
    c.append(datastore(430, 386, 200, 28, "D1", "SharedBusinessState"))
    c.append(datastore(60, 386, 176, 28, "D3", "Department Memory"))

    c.append(process(140, 34, 132, 54, "3.1", "Strategy\n(stage 1 + 2)"))
    c.append(process(310, 34, 132, 54, "3.2", "Finance"))
    c.append(process(480, 34, 132, 54, "3.3", "Branding"))
    c.append(process(310, 116, 132, 54, "3.4", "Marketing"))
    c.append(process(480, 116, 132, 54, "3.5", "Operations"))
    c.append(process(258, 214, 236, 66, "3.6",
                     "Deterministic Reconciliation\nderived overrides asserted"))
    c.append(process(258, 306, 236, 54, "3.7", "Completeness & Consistency Check"))

    c.append(flow(110, 58, 140, 58, "intent"))
    c.append(flow(272, 52, 310, 52, None))
    c.append(flow(442, 52, 480, 52, None))
    c.append(flow(206, 88, 340, 116, "competitor set", curve=0.06))
    c.append(flow(376, 88, 376, 116, None))
    c.append(flow(546, 88, 546, 116, None))
    c.append(flow(376, 170, 376, 214, "asserted figures"))
    c.append(flow(546, 170, 470, 220, "cost base", curve=0.05))
    c.append(flow(376, 280, 376, 306, "reconciled"))
    c.append(flow(494, 240, 530, 386, "write section", curve=0.12))
    c.append(flow(258, 250, 148, 386, "read / write lessons", curve=-0.10))

    c.append(txt(16, 424, "3.6 is the mechanism the paper reports: where two agents "
                 "assert the same quantity, the derived figure wins. Prompt-level "
                 "bounds were insufficient.", 7.4, INK_MUTED))
    return lc(W, H, "".join(c))

# =================================================== 5. USE CASE (1.45) ======

def usecase():
    W, H = 637, 439
    c = [caption_tag(16, 20, "Use case diagram", ACCENT)]

    def actor(x, y, label):
        out = [f'<circle cx="{x}" cy="{y}" r="9" fill="none" stroke="{INK}" '
               f'stroke-width="1.3"/>']
        out.append(f'<path d="M{x},{y+9} L{x},{y+30} M{x-12},{y+17} L{x+12},{y+17} '
                   f'M{x},{y+30} L{x-10},{y+48} M{x},{y+30} L{x+10},{y+48}" '
                   f'stroke="{INK}" stroke-width="1.3" fill="none"/>')
        out.append(txt(x, y + 64, label, 8.4, INK, "middle", "650"))
        return "".join(out)

    def uc(x, y, w, label, colour=ACCENT):
        out = [f'<ellipse cx="{x+w/2}" cy="{y}" rx="{w/2}" ry="19" '
               f'fill="#F2F4FD" stroke="{colour}" stroke-width="1.2"/>']
        lines = label.split("\n")
        for i, ln in enumerate(lines):
            out.append(txt(x + w / 2, y + 3 + (i - (len(lines) - 1) / 2) * 10,
                           ln, 7.6, INK, "middle", "600"))
        return "".join(out)

    c.append(f'<rect x="150" y="42" width="330" height="356" rx="8" fill="none" '
             f'stroke="{RULE}" stroke-width="1.2"/>')
    c.append(txt(315, 60, "ORION", 8.0, INK_MUTED, "middle", "700", spacing=1.5))

    c.append(actor(58, 96, "Founder"))
    c.append(actor(58, 250, "Supervisor"))
    c.append(actor(578, 120, "Scheduler"))
    c.append(actor(578, 276, "External\nData API"))

    cases = [
        (170, 96, 290, "Generate business plan from one sentence"),
        (170, 142, 290, "View plan, report and PDF export"),
        (170, 188, 290, "Review pending decision"),
        (170, 234, 290, "Approve, reject or return a decision"),
        (170, 280, 290, "Inspect audit trail"),
        (170, 326, 290, "Run department cadence"),
        (170, 372, 290, "Detect proxy divergence"),
    ]
    for x, y, w, label in cases:
        c.append(uc(x, y, w, label))

    for ay, ucy in ((110, 96), (110, 142), (110, 188)):
        c.append(arrow(78, ay, 170, ucy, marker="lm", colour=INK_MUTED, width=1.0))
    for ucy in (188, 234, 280):
        c.append(arrow(78, 264, 170, ucy, marker="lm", colour=INK_MUTED, width=1.0))
    for ucy in (326, 372):
        c.append(arrow(560, 134, 460, ucy, marker="lm", colour=INK_MUTED, width=1.0))
    c.append(arrow(560, 290, 460, 96, marker="lm", colour=INK_MUTED, width=1.0))

    c.append(txt(16, 424, "The supervisor's cases are the governance boundary: "
                 "departments draft, humans ratify.", 7.4, INK_MUTED))
    return lc(W, H, "".join(c))

# =================================================== 6. ACTIVITY (1.10) ======

def activity():
    W, H = 564, 512
    c = [caption_tag(14, 18, "Activity diagram ? one department tick", ACCENT)]
    CX = 250

    def node(y, label, w=210, h=30, fill="#F2F4FD", col=ACCENT, size=8.4):
        out = [box(CX - w / 2, y, w, h, None, None, fill, col, 6)]
        out.append(txt(CX, y + h / 2 + 3, label, size, INK, "middle", "600"))
        return "".join(out)

    def diamond(y, label, w=130, h=44, col=AMBER):
        pts = f"{CX},{y} {CX+w/2},{y+h/2} {CX},{y+h} {CX-w/2},{y+h/2}"
        out = [f'<polygon points="{pts}" fill="#FDF6E8" stroke="{col}" '
               f'stroke-width="1.2"/>']
        out.append(txt(CX, y + h / 2 + 3, label, 7.6, INK, "middle", "650"))
        return "".join(out)

    def down(y1, y2, label=None):
        return arrow(CX, y1, CX, y2, marker="lm", colour=INK_MUTED, width=1.15,
                     label=label)

    c.append(f'<circle cx="{CX}" cy="38" r="9" fill="{INK}"/>')
    c.append(down(47, 56))
    c.append(node(56, "Cadence due for this department"))
    c.append(down(86, 96))
    c.append(node(96, "Read anchors from the ledger", fill="#F0FBF7", col=GREEN))
    c.append(down(126, 136))
    c.append(node(136, "Retrieve own departmental memory", fill="#F0FBF7", col=GREEN))
    c.append(down(166, 176))
    c.append(node(176, "Plan candidate tasks"))
    c.append(down(206, 216))
    c.append(node(216, "Submit decision to governance"))
    c.append(down(246, 254))
    c.append(diamond(254, "Needs human\nreview?"))
    c.append(down(298, 310, "no"))
    c.append(node(310, "Approval gate"))

    c.append(box(392, 258, 150, 36, None, None, "#F7F2FD", "#6B3FA0", 6))
    c.append(txt(467, 280, "Human reviews", 8.2, INK, "middle", "600"))
    c.append(arrow(CX + 66, 276, 392, 276, marker="lm", colour=INK_MUTED,
                   width=1.1, label="yes"))
    c.append(arrow(467, 294, 360, 322, marker="lm", colour=INK_MUTED, width=1.1))

    c.append(down(340, 350))
    c.append(diamond(350, "Constitution\nsatisfied?", col=RED))
    c.append(box(16, 354, 130, 36, None, None, "#FBEDED", RED, 6))
    c.append(txt(81, 376, "Blocked, audited", 8.2, INK, "middle", "600"))
    c.append(arrow(CX - 66, 372, 146, 372, marker="lm", colour=RED, width=1.1,
                   label="no"))

    c.append(down(394, 404, "yes"))
    c.append(node(404, "Execute and append to the ledger",
                  fill="#F0FBF7", col=GREEN))
    c.append(down(434, 444))
    c.append(node(444, "Write episodic memory; recompute anchors",
                  fill="#F0FBF7", col=GREEN, size=8.0))
    c.append(down(474, 484))
    c.append(f'<circle cx="{CX}" cy="493" r="10" fill="none" stroke="{INK}" '
             f'stroke-width="1.4"/>')
    c.append(f'<circle cx="{CX}" cy="493" r="5.5" fill="{INK}"/>')
    return lc(W, H, "".join(c))

# ================================================== 7. TECH STACK (1.00) =====

def techstack():
    W, H = 500, 500
    c = [caption_tag(14, 20, "Technology stack", ACCENT)]
    layers = [
        ("Frontend", "React 18 + Vite  ?  inline SVG only", BLUE),
        ("Backend", "FastAPI  ?  WebSocket  ?  Python 3.13", BLUE),
        ("Orchestration", "LangGraph  ?  stateful multi-agent graphs", ACCENT),
        ("LLM layer", "Groq -> Gemini -> Ollama fallback chain", ACCENT),
        ("Operating layer", "ledger ? anchors ? constitution ? monitors", GREEN),
        ("Persistence", "SQLite (WAL)  ?  ChromaDB", GREEN),
        ("Evaluation", "scipy ? matplotlib ? 5 metrics, 8 arms", TEAL),
        ("Testing", "pytest ? 828 tests, fully offline", TEAL),
    ]
    y = 46
    for name, detail, col in layers:
        c.append(box(24, y, 452, 48, None, None, "#FFFFFF", col, 6, sw=1.3))
        c.append(txt(40, y + 20, name, 9.6, col, "start", "700"))
        c.append(txt(40, y + 36, detail, 8.0, INK_MUTED))
        y += 55
    c.append(txt(14, 486, "Every layer is free tier or local. No paid dependency "
                 "anywhere in the code path.", 7.6, INK_MUTED))
    return lc(W, H, "".join(c))

ALL = {
    "architecture": architecture,
    "dfd0": dfd0,
    "dfd1": dfd1,
    "dfd2": dfd2,
    "usecase": usecase,
    "activity": activity,
    "techstack": techstack,
}
