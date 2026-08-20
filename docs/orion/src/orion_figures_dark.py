"""
Dark loop-graph figures for Document 1.

Figure 6  reference case: the ML production loop graph
Figure 7  the Orion loop graph, derived node-for-node
Figure 8  anchor immutability - the crossed "never written" edge
Figure 9  a rejected AI-only cycle beside a valid anchor-terminated cycle
Figure 11 the Kaapi quarter under the loop graph: detection and escalation
"""

from orion_graph import (
    node, edge, legend, dark_canvas, title, note, band, HUES,
)
from orion_style import GRAPH_BG, GRAPH_TEXT, GRAPH_MUTED, HUE_HALT, \
    HUE_ANCHOR, HUE_MONITOR, HUE_LEARN, HUE_HUMAN, FONT_STACK

R = 52


def _step(x, y, n, colour=None):
    """A small numbered step badge."""
    c = colour or GRAPH_TEXT
    return (f'<circle cx="{x}" cy="{y}" r="9.5" fill="{GRAPH_BG}" '
            f'stroke="{c}" stroke-width="1.3"/>'
            f'<text x="{x}" y="{y + 3.4}" text-anchor="middle" '
            f'font-family="{FONT_STACK}" font-size="8.6" font-weight="700" '
            f'fill="{c}">{n}</text>')


# ------------------------------------------------- Figure 6: reference case --

def fig6_ml_reference():
    W, H = 1000, 620
    P = {
        "chal": (248, 132), "inc": (668, 132), "eval": (884, 316),
        "drift": (116, 316), "live": (452, 316), "alert": (140, 494),
        "roll": (438, 494), "train": (708, 486),
    }
    c = [title(30, 34, "Reference case — a machine-learning system in production")]

    E = [
        # work / data flow
        ("live", "chal", "exec", False, -0.18, None, False),
        ("live", "inc", "exec", False, 0.18, None, False),
        ("live", "drift", "exec", False, 0.0, None, False),
        ("live", "roll", "exec", False, 0.0, None, False),
        ("live", "train", "learn", False, -0.12, None, False),
        ("drift", "chal", "monitor", False, -0.16, None, False),
        ("drift", "alert", "monitor", False, 0.0, None, False),
        ("train", "inc", "learn", False, -0.2, "retrain", False),
        # control / evaluation signals
        ("chal", "inc", "muted", True, 0.0, "Head-to-Head Evaluation", False),
        ("chal", "eval", "monitor", True, -0.16, None, False),
        ("inc", "eval", "monitor", True, -0.1, None, False),
        ("alert", "roll", "halt", True, 0.0, None, False),
        ("roll", "chal", "halt", True, 0.14, None, False),
        ("roll", "inc", "halt", True, -0.3, None, False),
        # the forbidden path
        ("train", "eval", "muted", True, 0.14, "Never Seen", True),
    ]
    for a, b, hue, dash, cur, lbl, cross in E:
        (x1, y1), (x2, y2) = P[a], P[b]
        r2 = 62 if b == "eval" else R
        c.append(edge(x1, y1, x2, y2, hue=hue, dashed=dash, curve=cur,
                      label=lbl, crossed=cross, r1=R, r2=r2))

    c += [
        node(*P["chal"], "Challenger Model", "brain", "exec"),
        node(*P["inc"], "Incumbent Model", "brain", "exec"),
        node(*P["live"], "Live Traffic", "people", "exec"),
        node(*P["drift"], "Drift Monitor", "chart", "monitor"),
        node(*P["alert"], "Alert Threshold", "bell", "monitor"),
        node(*P["roll"], "Automatic Rollback", "rollback", "halt"),
        node(*P["train"], "Training Loop", "cycle", "learn"),
        node(*P["eval"], "Held-Out Eval Set", "lockdb", "anchor", r=62,
             locked=True, sub="never trained on", wrap=13),
    ]

    c.append(note(884, 404, "The measure stays a measure", HUE_ANCHOR,
                  8.0, "middle", "700"))
    c.append(note(884, 417, "only because the learner", GRAPH_MUTED, 7.6, "middle"))
    c.append(note(884, 429, "cannot reach it.", GRAPH_MUTED, 7.6, "middle"))

    c.append(legend(30, 578, [
        ("solid", "exec", "Work / data flow"),
        ("dashed", "monitor", "Control / evaluation"),
        ("node", "anchor", "Locked anchor"),
        ("cross", "halt", "Forbidden path"),
    ], cols=4, gap=228))
    return dark_canvas(W, H, "".join(c))


# ------------------------------------------------ Figure 7: derived mapping --

def fig7_orion_loop_graph():
    W, H = 1000, 640
    P = {
        "prop": (246, 128), "play": (652, 128), "anch": (884, 298),
        "drift": (114, 312), "ops": (446, 316), "const": (136, 492),
        "gate": (400, 500), "refl": (646, 458), "human": (886, 552),
    }
    c = [title(30, 34, "The Orion loop graph — the same shape, "
                       "in a business")]

    E = [
        ("ops", "prop", "exec", False, -0.18, None, False),
        ("ops", "play", "exec", False, 0.16, None, False),
        ("ops", "drift", "exec", False, 0.0, None, False),
        ("ops", "gate", "exec", False, 0.0, None, False),
        ("ops", "refl", "learn", False, -0.12, None, False),
        ("ops", "anch", "anchor", False, 0.15, "ledger writes", False),
        ("drift", "prop", "monitor", False, -0.16, None, False),
        ("drift", "const", "monitor", False, 0.0, None, False),
        ("refl", "play", "learn", False, -0.2, "playbook update", False),
        ("prop", "play", "muted", True, 0.0, "Compared against anchors", False),
        ("prop", "anch", "monitor", True, -0.14, None, False),
        ("play", "anch", "monitor", True, -0.1, None, False),
        ("const", "gate", "halt", True, 0.0, None, False),
        ("gate", "prop", "halt", True, 0.14, None, False),
        ("gate", "human", "human", True, 0.16, "escalate", False),
        ("human", "play", "human", True, -0.12, "ratify", False),
        ("refl", "anch", "muted", True, 0.16, "Never optimised against", True),
    ]
    for a, b, hue, dash, cur, lbl, cross in E:
        (x1, y1), (x2, y2) = P[a], P[b]
        r1 = 62 if a == "anch" else R
        r2 = 62 if b == "anch" else R
        c.append(edge(x1, y1, x2, y2, hue=hue, dashed=dash, curve=cur,
                      label=lbl, crossed=cross, r1=r1, r2=r2))

    c += [
        node(*P["prop"], "Proposed Plan", "doc", "exec", sub="planner output"),
        node(*P["play"], "Active Playbook", "target", "exec", sub="in force"),
        node(*P["ops"], "Business Operations", "people", "exec", wrap=13),
        node(*P["drift"], "Drift & Decay Monitor", "chart", "monitor", wrap=12),
        node(*P["const"], "Constitution Thresholds", "shield", "monitor", wrap=12),
        node(*P["gate"], "Execution Gate & Rollback", "rollback", "halt", wrap=12),
        node(*P["refl"], "Reflection & Knowledge", "cycle", "learn", wrap=12),
        node(*P["human"], "Human Ratification", "user", "human", wrap=12),
        node(*P["anch"], "Anchor Metrics", "lockdb", "anchor", r=62,
             locked=True, sub="append-only ledger", wrap=13),
    ]

    c.append(legend(30, 604, [
        ("solid", "exec", "Work / data flow"),
        ("dashed", "monitor", "Control / evaluation"),
        ("node", "anchor", "Locked anchor"),
        ("node", "human", "Human judgement"),
        ("cross", "halt", "Forbidden path"),
    ], cols=5, gap=186))
    return dark_canvas(W, H, "".join(c))


# ------------------------------------------- Figure 8: anchor immutability ---

def fig8_anchor_immutability():
    W, H = 1000, 560
    c = [title(30, 32, "Anchor immutability — the boundary no agent crosses")]

    c.append(band(58, 58, 250, 456, "exec", "Agent runtime"))
    c.append(band(692, 58, 250, 456, "monitor", "Read-only consumers"))

    L = {"plan": (183, 148), "work": (183, 292), "refl": (183, 436)}
    Rt = {"good": (817, 148), "drift": (817, 292), "health": (817, 436)}
    A = (500, 286)

    for k, lbl in (("plan", "never written"), ("work", "never written"),
                   ("refl", "never optimised against")):
        x, y = L[k]
        c.append(edge(x, y, A[0], A[1], hue="muted", dashed=True,
                      curve=0.0, label=lbl, crossed=True, r1=46, r2=88))
    for k in Rt:
        x, y = Rt[k]
        c.append(edge(A[0], A[1], x, y, hue="anchor", dashed=False,
                      curve=0.0, label="read-only", r1=88, r2=46))

    c += [
        node(*L["plan"], "Department Planner", "doc", "exec", r=46, wrap=12),
        node(*L["work"], "Workers", "gear", "exec", r=46),
        node(*L["refl"], "Reflection Loop", "cycle", "learn", r=46, wrap=12),
        node(*Rt["good"], "Goodhart Detector", "search", "monitor", r=46, wrap=12),
        node(*Rt["drift"], "Drift & Decay Monitor", "chart", "monitor", r=46, wrap=12),
        node(*Rt["health"], "Business Health", "chart", "monitor", r=46, wrap=12),
        node(A[0], A[1], "Anchor Metrics", "lockdb", "anchor", r=88,
             locked=True, sub="computed from an append-only ledger", wrap=16),
    ]

    c.append(note(500, 424, "Revenue · Contribution margin · Retention · Churn",
                  HUE_ANCHOR, 8.2, "middle", "600"))
    c.append(note(500, 438, "CAC · LTV · Cash · SLA breaches",
                  GRAPH_MUTED, 8.0, "middle"))
    c.append(note(500, 480,
                  "Anchors are computed, never reported.",
                  GRAPH_TEXT, 9.4, "middle", "700"))
    c.append(note(500, 496,
                  "There is no write path from the agent runtime to an anchor.",
                  GRAPH_MUTED, 8.2, "middle"))

    c.append(legend(30, 534, [
        ("cross", "halt", "Write path absent by construction"),
        ("solid", "anchor", "Read-only access"),
        ("node", "anchor", "Locked anchor"),
    ], cols=3, gap=305))
    return dark_canvas(W, H, "".join(c))


# ---------------------------------------- Figure 9: cycle validity contrast --

def fig9_cycle_validity():
    W, H = 1000, 500
    c = [title(30, 32, "Two cycles — one is rejected before it ever runs")]

    c.append(band(34, 54, 452, 392, "halt", None, dash=False))
    c.append(band(514, 54, 452, 392, "anchor", None, dash=False))

    c.append(note(260, 84, "REJECTED AT REGISTRATION", HUE_HALT, 9.4,
                  "middle", "700"))
    c.append(note(740, 84, "VALID TOPOLOGY", HUE_ANCHOR, 9.4, "middle", "700"))

    # left: AI checks AI checks AI
    LA, LB, LC = (156, 190), (364, 190), (260, 348)
    c.append(edge(*LA, *LB, hue="muted", dashed=True, curve=-0.16, r1=44, r2=44))
    c.append(edge(*LB, *LC, hue="muted", dashed=True, curve=-0.16, r1=44, r2=44))
    c.append(edge(*LC, *LA, hue="muted", dashed=True, curve=-0.16, r1=44, r2=44))
    c += [
        node(*LA, "Agent A", "brain", "exec", r=44),
        node(*LB, "Agent B", "brain", "exec", r=44),
        node(*LC, "Agent C", "brain", "exec", r=44),
    ]
    c.append(note(260, 420, "Every node approves the next. Nothing touches",
                  GRAPH_MUTED, 8.2, "middle"))
    c.append(note(260, 433, "reality. This is one larger loop wearing a",
                  GRAPH_MUTED, 8.2, "middle"))
    c.append(note(260, 446, "disguise.", GRAPH_MUTED, 8.2, "middle"))

    # right: cycle terminating at an anchor
    RA, RB, RC = (636, 190), (844, 190), (740, 348)
    c.append(edge(*RA, *RB, hue="monitor", dashed=True, curve=-0.16, r1=44, r2=44))
    c.append(edge(*RB, *RC, hue="monitor", dashed=True, curve=-0.16, r1=44, r2=52))
    c.append(edge(*RC, *RA, hue="anchor", dashed=False, curve=-0.16, r1=52, r2=44))
    c += [
        node(*RA, "Department Loop", "gear", "exec", r=44, wrap=11),
        node(*RB, "Monitor Loop", "search", "monitor", r=44, wrap=11),
        node(*RC, "Anchor", "lockdb", "anchor", r=52, locked=True,
             sub="code-computed"),
    ]
    c.append(note(740, 428, "The cycle passes through a value no agent",
                  GRAPH_MUTED, 8.2, "middle"))
    c.append(note(740, 441, "can author. A human node satisfies the rule",
                  GRAPH_MUTED, 8.2, "middle"))
    c.append(note(740, 454, "equally well.", GRAPH_MUTED, 8.2, "middle"))

    c.append(legend(34, 478, [
        ("dashed", "monitor", "Evaluation signal"),
        ("solid", "anchor", "Anchor-grounded return path"),
        ("node", "anchor", "Locked anchor"),
    ], cols=3, gap=305))
    return dark_canvas(W, H, "".join(c))


# ------------------------------------- Figure 11: Kaapi under the loop graph --

def fig11_kaapi_caught():
    W, H = 1000, 660
    c = [title(30, 32, "p01 under continuous operation — a prospective "
                       "detection path")]

    P = {
        "mkt": (110, 160), "claim": (340, 110), "anch": (340, 320),
        "sf": (110, 430), "good": (600, 150), "conf": (600, 350),
        "human": (840, 250), "obj": (840, 480),
    }
    RA = 58  # anchor node radius

    c.append(edge(*P["obj"], *P["mkt"], hue="learn", dashed=False,
                  curve=-0.30, label="new objective", r1=R, r2=R))
    c.append(edge(*P["mkt"], *P["claim"], hue="exec", dashed=False,
                  curve=0.0, label="claims success", r1=R, r2=R))
    c.append(edge(*P["mkt"], *P["anch"], hue="anchor", dashed=False,
                  curve=0.0, label="ledger writes", r1=R, r2=RA))
    c.append(edge(*P["claim"], *P["good"], hue="monitor", dashed=True,
                  curve=0.0, r1=R, r2=R))
    c.append(edge(*P["anch"], *P["good"], hue="anchor", dashed=False,
                  curve=0.0, r1=RA, r2=R))
    c.append(edge(*P["sf"], *P["conf"], hue="exec", dashed=False,
                  curve=0.0, r1=R, r2=R))
    c.append(edge(*P["anch"], *P["conf"], hue="anchor", dashed=False,
                  curve=0.0, r1=RA, r2=R))
    c.append(edge(*P["good"], *P["human"], hue="human", dashed=True,
                  curve=0.0, label="escalate", r1=R, r2=R))
    c.append(edge(*P["conf"], *P["human"], hue="human", dashed=True,
                  curve=0.0, label="arbitrate", r1=R, r2=R))
    c.append(edge(*P["human"], *P["obj"], hue="human", dashed=True,
                  curve=0.0, label="ratified change", r1=R, r2=R))

    c += [
        node(*P["mkt"], "Marketing Loop", "flag", "exec", wrap=12),
        node(*P["claim"], "Proxy: footfall up", "chart", "exec",
             sub="promotions run", wrap=13),
        node(*P["sf"], "Finance & Ops actions", "people", "exec", wrap=12),
        node(*P["good"], "Goodhart Detector", "search", "monitor", wrap=12),
        node(*P["conf"], "Conflict Detector", "scale", "monitor", wrap=12),
        node(*P["human"], "Human Arbitration", "user", "human", wrap=12),
        node(*P["obj"], "Revised Objective", "target", "learn", wrap=12),
        node(*P["anch"], "Anchor: net margin", "lockdb", "anchor", r=RA,
             locked=True, sub="falling", wrap=14),
    ]

    for x, y, n in ((228, 118, "1"), (208, 255, "2"), (474, 116, "3"),
                    (356, 396, "4"), (774, 164, "5"), (840, 372, "6")):
        c.append(_step(x, y, n))

    c.append(note(30, 618,
                  "1  Marketing reports a win.    2  The record shows what "
                  "actually happened.    3  The detector finds a claim with no "
                  "matching anchor movement.",
                  GRAPH_MUTED, 8.0))
    c.append(note(30, 634,
                  "4  The conflict detector surfaces the Finance–Operations "
                  "collision.    5  Both escalate to a human.    6  A ratified "
                  "objective replaces the captured proxy.",
                  GRAPH_MUTED, 8.0))
    return dark_canvas(W, H, "".join(c))
