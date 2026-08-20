"""
Vector node-graph engine for the Orion loop-graph figures.

Produces standalone inline SVG in the dark "production loop graph" visual
language: circular nodes with thin luminous strokes and line glyphs, solid
edges for work/data flow, dashed edges for control/evaluation signals, and
crossed-out edges for forbidden paths.
"""

import math
from orion_style import (
    GRAPH_BG, GRAPH_TEXT, GRAPH_MUTED,
    HUE_EXEC, HUE_MONITOR, HUE_HALT, HUE_LEARN, HUE_ANCHOR, HUE_HUMAN,
    FONT_STACK,
)

HUES = {
    "exec": HUE_EXEC,
    "monitor": HUE_MONITOR,
    "halt": HUE_HALT,
    "learn": HUE_LEARN,
    "anchor": HUE_ANCHOR,
    "human": HUE_HUMAN,
    "muted": GRAPH_MUTED,
}


# ------------------------------------------------------------------ glyphs ---

def _glyph(kind: str, cx: float, cy: float, colour: str) -> str:
    """Return a small line-art glyph centred on (cx, cy)."""
    s = f'stroke="{colour}" fill="none" stroke-width="1.25" ' \
        f'stroke-linecap="round" stroke-linejoin="round"'
    g = []

    if kind == "brain":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="8" {s}/>')
        g.append(f'<path d="M{cx-8},{cy-2} q4,-5 8,0 q4,5 8,0" {s}/>')
        g.append(f'<path d="M{cx},{cy-8} L{cx},{cy+8}" {s} opacity="0.55"/>')
    elif kind == "chart":
        g.append(f'<path d="M{cx-9},{cy+7} L{cx-9},{cy-8}" {s} opacity="0.5"/>')
        g.append(f'<path d="M{cx-9},{cy+7} L{cx+9},{cy+7}" {s} opacity="0.5"/>')
        g.append(f'<path d="M{cx-7},{cy+3} L{cx-2},{cy-3} '
                 f'L{cx+2},{cy+1} L{cx+8},{cy-6}" {s}/>')
    elif kind == "bell":
        g.append(f'<path d="M{cx-7},{cy+4} q0,-11 7,-11 q7,0 7,11 z" {s}/>')
        g.append(f'<path d="M{cx-9},{cy+4} L{cx+9},{cy+4}" {s}/>')
        g.append(f'<path d="M{cx-2},{cy+7} q2,2 4,0" {s}/>')
    elif kind == "rollback":
        g.append(f'<path d="M{cx+8},{cy} a8,8 0 1,1 -3.5,-6.6" {s}/>')
        g.append(f'<path d="M{cx+1},{cy-9} L{cx+4.5},{cy-6.6} L{cx+1},{cy-3.5}" {s}/>')
    elif kind == "people":
        g.append(f'<circle cx="{cx-5}" cy="{cy-4}" r="3.2" {s}/>')
        g.append(f'<circle cx="{cx+5}" cy="{cy-4}" r="3.2" {s}/>')
        g.append(f'<path d="M{cx-10},{cy+7} q5,-6 10,0" {s}/>')
        g.append(f'<path d="M{cx},{cy+7} q5,-6 10,0" {s}/>')
    elif kind == "gear":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="5" {s}/>')
        for i in range(6):
            a = math.radians(i * 60)
            g.append(f'<path d="M{cx+6*math.cos(a):.1f},{cy+6*math.sin(a):.1f} '
                     f'L{cx+9*math.cos(a):.1f},{cy+9*math.sin(a):.1f}" {s}/>')
    elif kind == "cycle":
        g.append(f'<path d="M{cx-7},{cy+2} a7,7 0 1,1 5,5" {s}/>')
        g.append(f'<path d="M{cx-10},{cy-1} L{cx-7},{cy+2.5} L{cx-3.5},{cy-1}" {s}/>')
    elif kind == "db":
        for dy in (-5, 0, 5):
            g.append(f'<ellipse cx="{cx}" cy="{cy+dy}" rx="8" ry="2.8" {s}/>')
        g.append(f'<path d="M{cx-8},{cy-5} L{cx-8},{cy+5}" {s}/>')
        g.append(f'<path d="M{cx+8},{cy-5} L{cx+8},{cy+5}" {s}/>')
    elif kind == "lockdb":
        for dy in (-6, -1):
            g.append(f'<ellipse cx="{cx}" cy="{cy+dy}" rx="8" ry="2.6" {s}/>')
        g.append(f'<path d="M{cx-8},{cy-6} L{cx-8},{cy-1}" {s}/>')
        g.append(f'<path d="M{cx+8},{cy-6} L{cx+8},{cy-1}" {s}/>')
        g.append(f'<rect x="{cx-4.5}" y="{cy+3}" width="9" height="7" rx="1.4" {s}/>')
        g.append(f'<path d="M{cx-2.4},{cy+3} v-2.4 a2.4,2.4 0 0,1 4.8,0 v2.4" {s}/>')
    elif kind == "lock":
        g.append(f'<rect x="{cx-6}" y="{cy-1}" width="12" height="9.5" rx="1.8" {s}/>')
        g.append(f'<path d="M{cx-3.4},{cy-1} v-3.2 a3.4,3.4 0 0,1 6.8,0 v3.2" {s}/>')
    elif kind == "shield":
        g.append(f'<path d="M{cx},{cy-9} L{cx+8},{cy-5} '
                 f'q0,9 -8,14 q-8,-5 -8,-14 z" {s}/>')
        g.append(f'<path d="M{cx-3.4},{cy} L{cx-0.6},{cy+3} L{cx+4},{cy-2.6}" {s}/>')
    elif kind == "scale":
        g.append(f'<path d="M{cx},{cy-9} L{cx},{cy+8}" {s}/>')
        g.append(f'<path d="M{cx-8},{cy-5} L{cx+8},{cy-5}" {s}/>')
        g.append(f'<path d="M{cx-8},{cy-5} l-2.4,5 h4.8 z" {s}/>')
        g.append(f'<path d="M{cx+8},{cy-5} l-2.4,5 h4.8 z" {s}/>')
        g.append(f'<path d="M{cx-4},{cy+8} L{cx+4},{cy+8}" {s}/>')
    elif kind == "doc":
        g.append(f'<path d="M{cx-6},{cy-9} h8 l4,4 v14 h-12 z" {s}/>')
        for dy in (-1, 2.5, 6):
            g.append(f'<path d="M{cx-3.4},{cy+dy} L{cx+3.4},{cy+dy}" {s} opacity="0.65"/>')
    elif kind == "user":
        g.append(f'<circle cx="{cx}" cy="{cy-4}" r="4" {s}/>')
        g.append(f'<path d="M{cx-7.5},{cy+8} q7.5,-8 15,0" {s}/>')
    elif kind == "target":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="8.5" {s}/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" {s}/>')
        g.append(f'<circle cx="{cx}" cy="{cy}" r="1.2" fill="{colour}" stroke="none"/>')
    elif kind == "flag":
        g.append(f'<path d="M{cx-5},{cy+9} L{cx-5},{cy-9}" {s}/>')
        g.append(f'<path d="M{cx-5},{cy-9} L{cx+7},{cy-5.5} L{cx-5},{cy-2} z" {s}/>')
    elif kind == "search":
        g.append(f'<circle cx="{cx-1.5}" cy="{cy-1.5}" r="6" {s}/>')
        g.append(f'<path d="M{cx+3},{cy+3} L{cx+8},{cy+8}" {s}/>')
    elif kind == "globe":
        g.append(f'<circle cx="{cx}" cy="{cy}" r="8.5" {s}/>')
        g.append(f'<ellipse cx="{cx}" cy="{cy}" rx="3.6" ry="8.5" {s} opacity="0.7"/>')
        g.append(f'<path d="M{cx-8.5},{cy} L{cx+8.5},{cy}" {s} opacity="0.7"/>')
    elif kind == "queue":
        for i, dy in enumerate((-7, -1.5, 4)):
            g.append(f'<rect x="{cx-8}" y="{cy+dy}" width="16" height="4" '
                     f'rx="1.2" {s} opacity="{1 - i * 0.22:.2f}"/>')
    return "".join(g)


# ------------------------------------------------------------------- nodes ---

def _wrap(label: str, width: int = 15):
    words, lines, cur = label.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def node(cx, cy, label, glyph="gear", hue="exec", r=52, locked=False,
         sub=None, wrap=15):
    """A circular graph node with a line glyph and an internal label."""
    c = HUES.get(hue, hue)
    lines = _wrap(label, wrap)
    out = [
        f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="{c}" opacity="0.05"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#16233D" '
        f'stroke="{c}" stroke-width="1.5" opacity="0.98"/>',
    ]
    gy = cy - (16 if len(lines) > 1 else 13)
    out.append(_glyph(glyph, cx, gy, c))
    start = cy + (6 if len(lines) > 1 else 12)
    for i, ln in enumerate(lines):
        out.append(
            f'<text x="{cx}" y="{start + i * 11.4}" text-anchor="middle" '
            f'font-family="{FONT_STACK}" font-size="9.1" font-weight="600" '
            f'fill="{GRAPH_TEXT}">{ln}</text>')
    if sub:
        out.append(
            f'<text x="{cx}" y="{start + len(lines) * 11.4 + 1}" '
            f'text-anchor="middle" font-family="{FONT_STACK}" font-size="7.4" '
            f'fill="{c}" opacity="0.9" font-style="italic">{sub}</text>')
    if locked:
        out.append(_glyph("lock", cx + r - 6, cy - r + 8, c))
        out.append(f'<circle cx="{cx + r - 6}" cy="{cy - r + 8}" r="11" '
                   f'fill="{GRAPH_BG}" stroke="{c}" stroke-width="1.1"/>')
        out.append(_glyph("lock", cx + r - 6, cy - r + 8, c))
    return "".join(out)


# ------------------------------------------------------------------- edges ---

def _trim(x1, y1, x2, y2, r1, r2):
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy) or 1
    ux, uy = dx / d, dy / d
    return x1 + ux * r1, y1 + uy * r1, x2 - ux * r2, y2 - uy * r2


def edge(x1, y1, x2, y2, hue="exec", dashed=False, curve=0.0,
         label=None, crossed=False, r1=52, r2=52, label_dy=-6, width=1.5):
    """
    An edge between two nodes.

    dashed  -> control / evaluation / feedback signal
    curve   -> perpendicular bow, as a fraction of edge length
    crossed -> forbidden path, drawn with an X and a label
    """
    c = HUES.get(hue, hue)
    sx, sy, ex, ey = _trim(x1, y1, x2, y2, r1, r2)
    mx, my = (sx + ex) / 2, (sy + ey) / 2

    if abs(curve) > 1e-6:
        dx, dy = ex - sx, ey - sy
        d = math.hypot(dx, dy) or 1
        px, py = -dy / d, dx / d
        cxp, cyp = mx + px * d * curve, my + py * d * curve
        path = f'M{sx:.1f},{sy:.1f} Q{cxp:.1f},{cyp:.1f} {ex:.1f},{ey:.1f}'
        mx, my = 0.25 * sx + 0.5 * cxp + 0.25 * ex, 0.25 * sy + 0.5 * cyp + 0.25 * ey
    else:
        path = f'M{sx:.1f},{sy:.1f} L{ex:.1f},{ey:.1f}'

    mid = f"arrow-{hue}"
    dash = ' stroke-dasharray="6,5"' if dashed else ''
    op = "0.5" if crossed else "0.88"
    out = [f'<path d="{path}" fill="none" stroke="{c}" stroke-width="{width}" '
           f'{dash} opacity="{op}" marker-end="url(#{mid})"/>']

    if crossed:
        k = 7.5
        out.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="12" '
                   f'fill="{GRAPH_BG}" opacity="0.95"/>')
        out.append(f'<path d="M{mx-k:.1f},{my-k:.1f} L{mx+k:.1f},{my+k:.1f} '
                   f'M{mx+k:.1f},{my-k:.1f} L{mx-k:.1f},{my+k:.1f}" '
                   f'stroke="{HUE_HALT}" stroke-width="2.4" '
                   f'stroke-linecap="round" fill="none"/>')

    if label:
        ly = my + label_dy - (14 if crossed else 0)
        w = len(label) * 4.55 + 12
        out.append(f'<rect x="{mx - w/2:.1f}" y="{ly - 8.5:.1f}" width="{w:.1f}" '
                   f'height="13" rx="2.5" fill="{GRAPH_BG}" opacity="0.92"/>')
        out.append(f'<text x="{mx:.1f}" y="{ly + 1.5:.1f}" text-anchor="middle" '
                   f'font-family="{FONT_STACK}" font-size="7.6" '
                   f'font-weight="600" '
                   f'fill="{HUE_HALT if crossed else GRAPH_MUTED}">{label}</text>')
    return "".join(out)


# ------------------------------------------------------------------ canvas ---

def _defs():
    m = []
    for name, c in HUES.items():
        m.append(
            f'<marker id="arrow-{name}" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    return "<defs>" + "".join(m) + "</defs>"


def legend(x, y, items, cols=4, gap=150):
    """Legend rows: (kind, colour_key, text) where kind is solid|dashed|node|cross."""
    out = []
    for i, (kind, hue, text) in enumerate(items):
        c = HUES.get(hue, hue)
        cx = x + (i % cols) * gap
        cy = y + (i // cols) * 17
        if kind == "solid":
            out.append(f'<path d="M{cx},{cy} L{cx+22},{cy}" stroke="{c}" '
                       f'stroke-width="1.8" marker-end="url(#arrow-{hue})"/>')
        elif kind == "dashed":
            out.append(f'<path d="M{cx},{cy} L{cx+22},{cy}" stroke="{c}" '
                       f'stroke-width="1.8" stroke-dasharray="5,4" '
                       f'marker-end="url(#arrow-{hue})"/>')
        elif kind == "node":
            out.append(f'<circle cx="{cx+9}" cy="{cy}" r="7" fill="#16233D" '
                       f'stroke="{c}" stroke-width="1.5"/>')
        elif kind == "cross":
            out.append(f'<path d="M{cx+3},{cy-5} L{cx+15},{cy+5} '
                       f'M{cx+15},{cy-5} L{cx+3},{cy+5}" stroke="{HUE_HALT}" '
                       f'stroke-width="2.1" stroke-linecap="round"/>')
        out.append(f'<text x="{cx+29}" y="{cy+3.4}" font-family="{FONT_STACK}" '
                   f'font-size="7.8" fill="{GRAPH_MUTED}">{text}</text>')
    return "".join(out)


def title(x, y, text, colour=None):
    return (f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" font-size="9.6" '
            f'font-weight="700" letter-spacing="1.5" '
            f'fill="{colour or GRAPH_MUTED}">{text.upper()}</text>')


def note(x, y, text, colour=None, size=8.2, anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT_STACK}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'fill="{colour or GRAPH_MUTED}">{text}</text>')


def band(x, y, w, h, colour, label=None, dash=True):
    """A translucent grouping band behind a cluster of nodes."""
    c = HUES.get(colour, colour)
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
           f'fill="{c}" opacity="0.045"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" '
           f'stroke="{c}" stroke-width="1" opacity="0.3"'
           + (' stroke-dasharray="5,5"' if dash else '') + '/>']
    if label:
        out.append(f'<text x="{x+13}" y="{y+17}" font-family="{FONT_STACK}" '
                   f'font-size="8" font-weight="700" letter-spacing="1.2" '
                   f'fill="{c}" opacity="0.95">{label.upper()}</text>')
    return "".join(out)


def dark_canvas(w, h, content):
    """Wrap content in a dark-navy SVG canvas."""
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'{_defs()}'
            f'<rect width="{w}" height="{h}" rx="6" fill="{GRAPH_BG}"/>'
            f'{content}</svg>')
