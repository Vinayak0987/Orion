"""
Build all four Orion PDFs from HTML via Chromium (Playwright).

    python build_pdfs.py

Writes to the parent directory:
    Orion_Architecture_Explainer.pdf   (full, ~16 pp)
    Orion_Research_Proposal.pdf        (full, ~14 pp)
    Orion_Architecture_Brief.pdf       (2 pp)
    Orion_Research_Proposal_Brief.pdf  (2 pp)
Intermediate HTML is kept alongside for inspection and editing.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.sync_api import sync_playwright

import orion_style as st
import orion_doc1
import orion_doc2
import orion_briefs

SRC = Path(__file__).parent
OUT = SRC.parent


class Brief:
    """Adapter so briefs share the document interface."""

    def __init__(self, fn):
        self.render = fn


DOCS = [
    (orion_doc1, "Orion_Architecture_Explainer", "Architecture Overview", None),
    (orion_doc2, "Orion_Research_Proposal", "Research Proposal", None),
    (Brief(orion_briefs.brief1), "Orion_Architecture_Brief",
     "Architecture Brief", 2),
    (Brief(orion_briefs.brief2), "Orion_Research_Proposal_Brief",
     "Research Proposal Brief", 2),
]


def page_count(path):
    return len(re.findall(rb"/Type\s*/Page[^s]", path.read_bytes()))


def main():
    problems = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for mod, stem, running, expect_pages in DOCS:
            html = mod.render()
            html_path = SRC / f"{stem}.html"
            html_path.write_text(html, encoding="utf-8")

            page.goto(html_path.as_uri(), wait_until="load")
            page.emulate_media(media="print")

            pdf_path = OUT / f"{stem}.pdf"
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template=st.header_template(running),
                footer_template=st.footer_template(),
                margin={"top": "20mm", "bottom": "20mm",
                        "left": "16mm", "right": "16mm"}
                if expect_pages is None else
                {"top": "15mm", "bottom": "14mm",
                 "left": "14mm", "right": "14mm"},
            )
            n = page_count(pdf_path)
            kb = pdf_path.stat().st_size / 1024
            flag = ""
            if expect_pages is not None and n != expect_pages:
                flag = f"  <-- EXPECTED {expect_pages} PAGES"
                problems.append((stem, n, expect_pages))
            print(f"  {pdf_path.name:38s} {n:>3} pp  {kb:>6,.0f} KB{flag}")
        browser.close()

    print("\nOutput directory:", OUT)
    if problems:
        print("\nPAGE-COUNT PROBLEMS:")
        for stem, got, want in problems:
            print(f"  {stem}: got {got}, expected {want}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
