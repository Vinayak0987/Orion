"""
Shared design system for the Orion document set.

Both documents are rendered from HTML via Chromium (Playwright) print-to-PDF.
This module holds the single source of truth for typography, colour and
page layout so the two PDFs share one visual identity.
"""

# ---------------------------------------------------------------- palette ----

ACCENT = "#2D3282"          # deep indigo, the single accent colour
ACCENT_SOFT = "#5A60B8"
INK = "#1A1D26"             # body text
INK_MUTED = "#5A6072"
RULE = "#DCE0EA"
PAGE_BG = "#FFFFFF"
PANEL_BG = "#F6F7FB"

# Dark graph canvas (Document 1 loop-graph figures)
GRAPH_BG = "#1B2A4A"
GRAPH_TEXT = "#D8E4F5"
GRAPH_MUTED = "#8098BE"

# Hue coding for graph nodes
HUE_EXEC = "#4FA8E8"        # execution / work flow      – blue
HUE_MONITOR = "#3FD0D4"     # monitor loops              – cyan
HUE_HALT = "#F0688A"        # halt / rollback            – rose
HUE_LEARN = "#E8C46A"       # learning / reflection      – gold
HUE_ANCHOR = "#2FD9A8"      # anchors (locked)           – teal
HUE_HUMAN = "#C89BF0"       # human judgement            – violet

FONT_STACK = ("'Inter','Segoe UI',Calibri,'Helvetica Neue',Helvetica,Arial,"
              "sans-serif")
FONT_MONO = "'Cascadia Mono','Consolas','SF Mono',Menlo,monospace"


def stylesheet() -> str:
    """Return the full CSS used by both documents."""
    return f"""
@page {{
  size: A4;
  margin: 20mm 18mm 20mm 18mm;
}}

* {{ box-sizing: border-box; }}

html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}

body {{
  font-family: {FONT_STACK};
  font-size: 9.6pt;
  line-height: 1.44;
  color: {INK};
  background: {PAGE_BG};
  margin: 0;
  hyphens: none;
}}

/* ------------------------------------------------------------- title page */

.title-page {{
  height: 246mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  page-break-after: always;
}}

.title-rule {{
  height: 5px;
  width: 74px;
  background: {ACCENT};
  margin-bottom: 30mm;
}}

.title-page h1 {{
  font-size: 33pt;
  line-height: 1.1;
  letter-spacing: -0.9px;
  color: {ACCENT};
  margin: 0 0 12px 0;
  font-weight: 700;
}}

.title-page .subtitle {{
  font-size: 14.5pt;
  color: {INK};
  font-weight: 400;
  line-height: 1.42;
  margin: 0 0 20px 0;
  max-width: 132mm;
}}

.title-page .kicker {{
  font-size: 9pt;
  letter-spacing: 2.4px;
  text-transform: uppercase;
  color: {INK_MUTED};
  margin-bottom: 14px;
  font-weight: 600;
}}

.title-meta {{
  font-size: 10pt;
  color: {INK_MUTED};
  line-height: 1.9;
  border-top: 1px solid {RULE};
  padding-top: 14px;
}}
.title-meta strong {{ color: {INK}; font-weight: 600; }}

.spec-note {{
  font-size: 8.8pt;
  color: {INK_MUTED};
  font-style: italic;
  margin-top: 10px;
}}

/* ---------------------------------------------------------------- content */

h2 {{
  font-size: 14.6pt;
  color: {ACCENT};
  margin: 17px 0 7px 0;
  padding-bottom: 4px;
  border-bottom: 1.5px solid {RULE};
  font-weight: 700;
  letter-spacing: -0.35px;
  page-break-after: avoid;
}}
h2 .num {{ color: {INK_MUTED}; font-weight: 600; margin-right: 9px; }}

h3 {{
  font-size: 11pt;
  color: {INK};
  margin: 12px 0 4px 0;
  font-weight: 700;
  page-break-after: avoid;
}}

h4 {{
  font-size: 10pt;
  color: {ACCENT};
  margin: 10px 0 3px 0;
  font-weight: 700;
  page-break-after: avoid;
}}

p {{ margin: 0 0 7px 0; text-align: left; }}

.lead {{
  font-size: 11pt;
  line-height: 1.48;
  color: {INK};
}}

ul, ol {{ margin: 0 0 8px 0; padding-left: 19px; }}
li {{ margin-bottom: 4px; }}

strong {{ font-weight: 650; }}
em {{ font-style: italic; }}

code {{
  font-family: {FONT_MONO};
  font-size: 8.9pt;
  background: {PANEL_BG};
  padding: 1px 4px;
  border-radius: 3px;
  color: {ACCENT};
}}

.page-break {{ page-break-before: always; }}
.no-break {{ page-break-inside: avoid; }}

/* ----------------------------------------------------------------- tables */

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 8.8pt;
  margin: 8px 0 10px 0;
  page-break-inside: avoid;
}}

th {{
  text-align: left;
  font-weight: 650;
  color: {ACCENT};
  border-bottom: 1.5px solid {ACCENT};
  padding: 5px 8px 5px 0;
  font-size: 8.4pt;
  letter-spacing: 0.25px;
  text-transform: uppercase;
  vertical-align: bottom;
}}

td {{
  padding: 4.5px 8px 4.5px 0;
  border-bottom: 1px solid {RULE};
  vertical-align: top;
  line-height: 1.4;
}}

table.compact td, table.compact th {{ font-size: 8.1pt; padding: 4px 6px 4px 0; }}
td.yes {{ color: #1E8A5F; font-weight: 700; }}
td.no  {{ color: #B4433F; font-weight: 600; }}
td.part {{ color: #B07A26; font-weight: 600; }}

/* ---------------------------------------------------------------- figures */

figure {{
  margin: 10px 0 11px 0;
  page-break-inside: avoid;
}}

figure svg {{ display: block; width: 100%; height: auto; }}

figcaption {{
  font-size: 8.3pt;
  color: {INK_MUTED};
  margin-top: 4px;
  line-height: 1.4;
  padding-left: 2px;
}}
figcaption b {{ color: {ACCENT}; font-weight: 650; }}

/* ------------------------------------------------------------- callouts */

.callout {{
  background: {PANEL_BG};
  border-left: 3px solid {ACCENT};
  padding: 8px 12px;
  margin: 9px 0;
  font-size: 9.4pt;
  page-break-inside: avoid;
}}
.callout .label {{
  font-size: 8pt;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: {ACCENT};
  font-weight: 700;
  display: block;
  margin-bottom: 4px;
}}
.callout p:last-child {{ margin-bottom: 0; }}

.invariant {{
  background: #10233A;
  color: {GRAPH_TEXT};
  padding: 10px 14px;
  margin: 9px 0;
  border-left: 3px solid {HUE_ANCHOR};
  font-size: 9.7pt;
  page-break-inside: avoid;
}}
.invariant .label {{
  font-size: 8pt;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: {HUE_ANCHOR};
  font-weight: 700;
  display: block;
  margin-bottom: 4px;
}}
.invariant p {{ margin: 0; }}
.invariant em {{ color: #FFFFFF; font-style: normal; font-weight: 650; }}

/* ------------------------------------------------------- problem blocks */

.problem {{
  margin: 0 0 9px 0;
  padding-left: 12px;
  border-left: 2px solid {RULE};
  page-break-inside: avoid;
}}
.problem .pname {{
  font-weight: 700;
  color: {ACCENT};
  font-size: 10.1pt;
  display: block;
  margin-bottom: 2px;
}}
.problem .row {{ font-size: 9.2pt; margin-bottom: 2px; line-height: 1.42; }}
.problem .row span.k {{
  display: inline-block;
  min-width: 74px;
  font-size: 8pt;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  color: {INK_MUTED};
  font-weight: 650;
}}

/* ------------------------------------------------------------------- misc */

.hierarchy {{
  font-family: {FONT_MONO};
  font-size: 9.2pt;
  background: {PANEL_BG};
  padding: 11px 14px;
  margin: 11px 0;
  line-height: 1.75;
  color: {ACCENT};
  page-break-inside: avoid;
}}

.rq {{
  margin: 0 0 11px 0;
  page-break-inside: avoid;
}}
.rq .tag {{
  display: inline-block;
  background: {ACCENT};
  color: #fff;
  font-size: 8pt;
  font-weight: 700;
  padding: 1.5px 7px;
  border-radius: 3px;
  margin-right: 7px;
  letter-spacing: 0.6px;
}}
.rq .falsify {{
  font-size: 9.2pt;
  color: {INK_MUTED};
  margin-top: 3px;
  padding-left: 12px;
  border-left: 2px solid {HUE_HALT};
}}
.rq .falsify b {{ color: #B4433F; font-weight: 650; }}

.refs {{ font-size: 8.8pt; line-height: 1.55; }}
.refs li {{ margin-bottom: 7px; }}

.two-col {{ column-count: 2; column-gap: 16px; }}
.two-col p {{ margin-bottom: 7px; }}
"""


def header_template(doc_title: str) -> str:
    """Chromium running header."""
    return f"""
<div style="font-family:{FONT_STACK}; font-size:7pt; color:{INK_MUTED};
            width:100%; padding:0 18mm; margin-top:8mm;
            display:flex; justify-content:space-between;
            border-bottom:0.5px solid {RULE}; padding-bottom:3px;">
  <span style="letter-spacing:1px; text-transform:uppercase;">Orion</span>
  <span>{doc_title}</span>
</div>"""


def footer_template() -> str:
    """Chromium running footer with page numbers."""
    return f"""
<div style="font-family:{FONT_STACK}; font-size:7pt; color:{INK_MUTED};
            width:100%; padding:0 18mm; margin-bottom:8mm;
            display:flex; justify-content:space-between;">
  <span>Vinayak Maurya</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>"""


def html_document(title: str, body: str) -> str:
    """Wrap rendered body content in a complete HTML document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{stylesheet()}</style>
</head>
<body>
{body}
</body>
</html>"""
