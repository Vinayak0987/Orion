"""
Verification pass over the two generated documents.

Checks:
  1. Document 1 contains no migration / prior-draft / implementation-plan language
  2. Document 2 makes no claim that a problem is solved; framing stays investigative
  3. Figures are all present and numbered
  4. Reports page counts
"""

import re
from pathlib import Path

SRC = Path(__file__).parent
OUT = SRC.parent


def text_of(html_name):
    h = (SRC / html_name).read_text(encoding="utf-8")
    t = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", t)


def ctx(t, m, w=95):
    return "..." + t[max(0, m.start() - w):m.end() + w].strip() + "..."


print("=" * 78)
print("DOC 1 — forbidden framing audit")
print("=" * 78)
t1 = text_of("Orion_Architecture_Explainer.html")
forbidden = [
    "current design", "proposed design", "migration", "migrate",
    "prior draft", "earlier draft", "existing draft",
    "phase 1", "phase 2", "we will change", "upgrade plan",
    "task 1", "roadmap of changes",
    "what we are changing", "evolution from",
]
# Note: "mabgp" is no longer forbidden. Under the merged framing it is the
# legitimate identifier of the generation layer and of the code artefacts, and
# Doc 1 carries a deliberate implementation note explaining it.
issues = 0
for b in forbidden:
    for m in re.finditer(re.escape(b), t1, re.I):
        print(f"  FLAG [{b}]: {ctx(t1, m)}")
        issues += 1
print(f"  -> {issues} issue(s)")

print("\n  Standalone risk words (context shown):")
for w in (r"\bdraft\w*", r"\bphase\w*", r"\bmigrat\w*"):
    for m in re.finditer(w, t1, re.I):
        print(f"    {m.group(0)}: {ctx(t1, m, 70)}")

print()
print("=" * 78)
print("DOC 2 — investigative language audit")
print("=" * 78)
t2 = text_of("Orion_Research_Proposal.html")
claims = [
    "solves the problem", "orion solves", "will solve", "eliminates",
    "this prevents", "guarantees", "proves that", "we prove",
    "is solved", "resolves the", "ensures that", "clearly shows",
]
issues2 = 0
for b in claims:
    for m in re.finditer(re.escape(b), t2, re.I):
        print(f"  FLAG [{b}]: {ctx(t2, m)}")
        issues2 += 1
print(f"  -> {issues2} issue(s)")

print("\n  Investigative markers present:")
for w in ("we propose", "we hypothes", "would be refuted", "we do not",
          "null result", "we suggest", "we argue", "we regard",
          "we commit", "open question", "we acknowledge", "threat"):
    print(f"    {w:22s} {len(re.findall(re.escape(w), t2, re.I)):>3}")

print()
print("=" * 78)
print("FIGURES")
print("=" * 78)
for name, t in (("Doc 1", t1), ("Doc 2", t2)):
    figs = re.findall(r"Figure (\d+) —", t)
    print(f"  {name}: {len(figs)} captioned figures -> {figs}")
    svg = (SRC / ("Orion_Architecture_Explainer.html" if name == "Doc 1"
                  else "Orion_Research_Proposal.html")
           ).read_text(encoding="utf-8").count("<svg")
    print(f"          {svg} inline SVG elements")
    legends = t.count("Work / data flow") + t.count("Evaluation signal") \
        + t.count("Read-only access") + t.count("Anchor-grounded")
    if name == "Doc 1":
        print(f"          {legends} graph-figure legend blocks")

print()
print("=" * 78)
print("PAGE COUNTS")
print("=" * 78)
for f in ("Orion_Architecture_Explainer.pdf", "Orion_Research_Proposal.pdf"):
    p = OUT / f
    d = p.read_bytes()
    n = len(re.findall(rb"/Type\s*/Page[^s]", d))
    print(f"  {f:44s} {n:>3} pages   {p.stat().st_size/1024:,.0f} KB")
