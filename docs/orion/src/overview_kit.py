# Single-page Orion architecture overview.
#
# Deliberately readable at a glance: grouped pastel panels, one card per component,
# line icons, and a legend. Technical enough to be accurate, simple enough that
# someone seeing it for the first time can follow the whole system.
W, H = 1640, 1100

INK = "#1F2733"
MUTED = "#6B7480"
LINE = "#CBD3DE"
WHITE = "#FFFFFF"

# panel palettes: (border, tint, title colour)
P_CLIENT = ("#7C6BC4", "#F4F2FC", "#5B4CA8")
P_API    = ("#4A78C8", "#EEF3FC", "#2F5BA8")
P_GEN    = ("#D9962E", "#FDF7EC", "#B87914")
P_OPS    = ("#2E8B62", "#EDF7F2", "#1E7A50")
P_DATA   = ("#4A78C8", "#EFF4FC", "#2F5BA8")
P_EVAL   = ("#2E8B62", "#EEF8F2", "#1E7A50")
P_GROUND = ("#7C6BC4", "#F5F3FC", "#5B4CA8")
P_LLM    = ("#C2544C", "#FCF0EF", "#A63B33")
P_ANCH   = ("#1E7A50", "#E8F6EE", "#166043")

F = "'Segoe UI',Arial,Helvetica,sans-serif"


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, size=11, colour=INK, anchor="start", weight="400",
        italic=False, spacing=0):
    st = ' font-style="italic"' if italic else ""
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{weight}" fill="{colour}"'
            f'{st}{sp}>{esc(s)}</text>')


def panel(x, y, w, h, title, palette, sub=None):
    border, tint, tc = palette
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{tint}" '
           f'stroke="{border}" stroke-width="1.6"/>']
    out.append(txt(x + w / 2, y + 24, title, 13, tc, "middle", "700", spacing=0.8))
    if sub:
        out.append(txt(x + w / 2, y + 39, sub, 9.5, MUTED, "middle"))
    return "".join(out)


def card(x, y, w, h, label, icon=None, sub=None, border=LINE, lc=INK,
         size=10.5, fill=WHITE):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" '
           f'stroke="{border}" stroke-width="1.3"/>']
    tx = x + 12
    cy = y + h / 2
    if icon:
        out.append(glyph(icon, x + 20, cy, lc))
        tx = x + 38
    lines = label.split("\n")
    start = cy + 3.5 - (len(lines) - 1) * 6
    if sub:
        start -= 5
    for i, ln in enumerate(lines):
        out.append(txt(tx, start + i * 12, ln, size, INK, "start", "600"))
    if sub:
        out.append(txt(tx, start + len(lines) * 12 + 1, sub, 8.6, MUTED))
    return "".join(out)


def chip(x, y, w, h, label, border, tint, tc, size=9.8):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{tint}" '
           f'stroke="{border}" stroke-width="1.2"/>']
    out.append(txt(x + w / 2, y + h / 2 + 3.4, label, size, tc, "middle", "650"))
    return "".join(out)


def dashed_note(x, y, w, items, title=None):
    h = 15 * len(items) + (16 if title else 8)
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" '
           f'stroke="{LINE}" stroke-width="1.1" stroke-dasharray="4,3"/>']
    yy = y + (20 if title else 14)
    if title:
        out.append(txt(x + 10, y + 14, title, 8.8, MUTED, "start", "700"))
        yy = y + 29
    for it in items:
        out.append(txt(x + 10, yy, "\u2022 " + it, 8.8, MUTED))
        yy += 15
    return "".join(out)


def arrow(x1, y1, x2, y2, kind="data", label=None, colour=None, curve=0.0):
    colours = {"data": "#4A5568", "eval": "#4A5568", "read": "#1E7A50",
               "block": "#C2544C"}
    c = colour or colours.get(kind, "#4A5568")
    dash = ' stroke-dasharray="6,4"' if kind in ("eval", "block") else ""
    marker = {"data": "ad", "eval": "ad", "read": "ag", "block": "ar"}[kind]
    if abs(curve) > 1e-6:
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** 0.5 or 1
        mx = (x1 + x2) / 2 - dy / L * L * curve
        my = (y1 + y2) / 2 + dx / L * L * curve
        d = f"M{x1},{y1} Q{mx:.0f},{my:.0f} {x2},{y2}"
        lx, ly = 0.25 * x1 + 0.5 * mx + 0.25 * x2, 0.25 * y1 + 0.5 * my + 0.25 * y2
    else:
        d = f"M{x1},{y1} L{x2},{y2}"
        lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
    out = [f'<path d="{d}" fill="none" stroke="{c}" stroke-width="1.5"{dash} '
           f'marker-end="url(#{marker})"/>']
    if label:
        w = len(label) * 4.9 + 12
        out.append(f'<rect x="{lx-w/2:.0f}" y="{ly-15:.0f}" width="{w:.0f}" '
                   f'height="14" rx="3" fill="{WHITE}" opacity="0.95"/>')
        out.append(txt(lx, ly - 4.5, label, 8.8, c, "middle", "650"))
    return "".join(out)


def glyph(kind, cx, cy, colour):
    s = (f'stroke="{colour}" fill="none" stroke-width="1.35" '
         f'stroke-linecap="round" stroke-linejoin="round"')
    g = []
    if kind == "monitor":
        g += [f'<rect x="{cx-9}" y="{cy-7}" width="18" height="12" rx="1.5" {s}/>',
              f'<path d="M{cx-5},{cy+9} L{cx+5},{cy+9} M{cx},{cy+5} L{cx},{cy+9}" {s}/>']
    elif kind == "api":
        g += [f'<rect x="{cx-9}" y="{cy-6}" width="18" height="12" rx="3" {s}/>',
              f'<path d="M{cx-4},{cy} L{cx+4},{cy} M{cx-1},{cy-3} L{cx-1},{cy+3}" {s}/>']
    elif kind == "socket":
        g += [f'<circle cx="{cx}" cy="{cy+5}" r="2" fill="{colour}" stroke="none"/>',
              f'<path d="M{cx-6},{cy+1} a8,8 0 0,1 12,0" {s}/>',
              f'<path d="M{cx-9},{cy-3} a13,13 0 0,1 18,0" {s}/>']
    elif kind == "terminal":
        g += [f'<rect x="{cx-9}" y="{cy-7}" width="18" height="14" rx="2" {s}/>',
              f'<path d="M{cx-5},{cy-2} L{cx-2},{cy+1} L{cx-5},{cy+4} '
              f'M{cx+0},{cy+4} L{cx+5},{cy+4}" {s}/>']
    elif kind == "brain":
        g += [f'<circle cx="{cx}" cy="{cy}" r="7.5" {s}/>',
              f'<path d="M{cx-7},{cy-2} q3.5,-4 7,0 q3.5,4 7,0" {s}/>']
    elif kind == "route":
        g += [f'<circle cx="{cx-6}" cy="{cy-5}" r="2.4" {s}/>',
              f'<circle cx="{cx+6}" cy="{cy-5}" r="2.4" {s}/>',
              f'<circle cx="{cx}" cy="{cy+6}" r="2.4" {s}/>',
              f'<path d="M{cx-6},{cy-2.6} L{cx-6},{cy+2} L{cx+6},{cy+2} '
              f'L{cx+6},{cy-2.6} M{cx},{cy+2} L{cx},{cy+3.6}" {s}/>']
    elif kind == "doc":
        g += [f'<path d="M{cx-6},{cy-8} h8 l4,4 v12 h-12 z" {s}/>',
              f'<path d="M{cx-3},{cy} h6 M{cx-3},{cy+4} h6" {s}/>']
    elif kind == "chart":
        g += [f'<path d="M{cx-8},{cy+7} L{cx-8},{cy-7} M{cx-8},{cy+7} L{cx+8},{cy+7}" {s}/>',
              f'<path d="M{cx-5},{cy+3} L{cx-1},{cy-3} L{cx+2},{cy} L{cx+7},{cy-6}" {s}/>']
    elif kind == "palette":
        g += [f'<path d="M{cx},{cy-8} a8,8 0 1,0 0,16 q-3,0 -3,-3 t3,-3 a5,5 0 0,0 0,-10 z" {s}/>',
              f'<circle cx="{cx+3}" cy="{cy-3}" r="1.4" fill="{colour}" stroke="none"/>']
    elif kind == "megaphone":
        g += [f'<path d="M{cx-8},{cy-2} L{cx+2},{cy-7} v14 L{cx-8},{cy+2} z" {s}/>',
              f'<path d="M{cx+4},{cy-3} a4,4 0 0,1 0,6" {s}/>']
    elif kind == "gear":
        g += [f'<circle cx="{cx}" cy="{cy}" r="4.2" {s}/>']
        for i in range(6):
            a = i * 60 * 3.14159 / 180
            import math as _m
            g.append(f'<path d="M{cx+5.4*_m.cos(a):.1f},{cy+5.4*_m.sin(a):.1f} '
                     f'L{cx+8.4*_m.cos(a):.1f},{cy+8.4*_m.sin(a):.1f}" {s}/>')
    elif kind == "scale":
        g += [f'<path d="M{cx},{cy-8} L{cx},{cy+7} M{cx-8},{cy-4} L{cx+8},{cy-4} '
              f'M{cx-4},{cy+7} L{cx+4},{cy+7}" {s}/>',
              f'<path d="M{cx-8},{cy-4} l-2.2,4.5 h4.4 z M{cx+8},{cy-4} '
              f'l-2.2,4.5 h4.4 z" {s}/>']
    elif kind == "db":
        for dy in (-5, 0, 5):
            g.append(f'<ellipse cx="{cx}" cy="{cy+dy}" rx="7.5" ry="2.6" {s}/>')
        g.append(f'<path d="M{cx-7.5},{cy-5} v10 M{cx+7.5},{cy-5} v10" {s}/>')
    elif kind == "lockdb":
        for dy in (-6, -1.5):
            g.append(f'<ellipse cx="{cx}" cy="{cy+dy}" rx="7.5" ry="2.5" {s}/>')
        g += [f'<path d="M{cx-7.5},{cy-6} v4.5 M{cx+7.5},{cy-6} v4.5" {s}/>',
              f'<rect x="{cx-4.2}" y="{cy+2.5}" width="8.4" height="6.5" rx="1.2" {s}/>',
              f'<path d="M{cx-2.2},{cy+2.5} v-2.2 a2.2,2.2 0 0,1 4.4,0 v2.2" {s}/>']
    elif kind == "shield":
        g += [f'<path d="M{cx},{cy-8} L{cx+7.5},{cy-4.5} q0,8.5 -7.5,12.5 '
              f'q-7.5,-4 -7.5,-12.5 z" {s}/>',
              f'<path d="M{cx-3.2},{cy-0.5} L{cx-0.6},{cy+2.4} L{cx+3.8},{cy-2.6}" {s}/>']
    elif kind == "bell":
        g += [f'<path d="M{cx-6.5},{cy+3.5} q0,-10 6.5,-10 q6.5,0 6.5,10 z" {s}/>',
              f'<path d="M{cx-8.5},{cy+3.5} h17 M{cx-2},{cy+6.5} q2,2 4,0" {s}/>']
    elif kind == "cycle":
        g += [f'<path d="M{cx-6.5},{cy+1.5} a6.5,6.5 0 1,1 4.6,4.6" {s}/>',
              f'<path d="M{cx-9.5},{cy-1.5} L{cx-6.5},{cy+2} L{cx-3},{cy-1.5}" {s}/>']
    elif kind == "user":
        g += [f'<circle cx="{cx}" cy="{cy-4}" r="3.6" {s}/>',
              f'<path d="M{cx-7},{cy+7.5} q7,-7.5 14,0" {s}/>']
    elif kind == "clock":
        g += [f'<circle cx="{cx}" cy="{cy}" r="8" {s}/>',
              f'<path d="M{cx},{cy-4.5} L{cx},{cy} L{cx+3.5},{cy+2.5}" {s}/>']
    elif kind == "cloud":
        g += [f'<path d="M{cx-7},{cy+3} a4,4 0 0,1 0.6,-7.9 a5.5,5.5 0 0,1 10.6,-1 '
              f'a3.8,3.8 0 0,1 0.5,7.6 z" {s}/>']
    elif kind == "search":
        g += [f'<circle cx="{cx-1.5}" cy="{cy-1.5}" r="5.6" {s}/>',
              f'<path d="M{cx+2.6},{cy+2.6} L{cx+7.5},{cy+7.5}" {s}/>']
    elif kind == "flask":
        g += [f'<path d="M{cx-2.5},{cy-8} v5 L{cx-7},{cy+6} q-1,2.5 1.8,2.5 h10.4 '
              f'q2.8,0 1.8,-2.5 L{cx+2.5},{cy-3} v-5 z" {s}/>',
              f'<path d="M{cx-4},{cy-8} h8" {s}/>']
    elif kind == "check":
        g += [f'<rect x="{cx-7.5}" y="{cy-8}" width="15" height="16" rx="2" {s}/>',
              f'<path d="M{cx-3.5},{cy-2} L{cx-1},{cy+0.8} L{cx+3.8},{cy-4}" {s}/>',
              f'<path d="M{cx-3.5},{cy+4.5} h7" {s}/>']
    elif kind == "target":
        g += [f'<circle cx="{cx}" cy="{cy}" r="8" {s}/>',
              f'<circle cx="{cx}" cy="{cy}" r="4" {s}/>',
              f'<circle cx="{cx}" cy="{cy}" r="1.2" fill="{colour}" stroke="none"/>']
    elif kind == "people":
        g += [f'<circle cx="{cx-4.5}" cy="{cy-3.5}" r="3" {s}/>',
              f'<circle cx="{cx+4.5}" cy="{cy-3.5}" r="3" {s}/>',
              f'<path d="M{cx-9.5},{cy+6.5} q5,-5.5 9.5,0 M{cx},{cy+6.5} '
              f'q4.5,-5.5 9.5,0" {s}/>']
    return "".join(g)


def defs():
    m = []
    for name, c in (("ad", "#4A5568"), ("ag", "#1E7A50"), ("ar", "#C2544C")):
        m.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" '
                 f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                 f'<path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>')
    return "<defs>" + "".join(m) + "</defs>"
