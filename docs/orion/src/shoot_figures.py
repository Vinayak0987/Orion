"""Screenshot individual figures so they can be inspected visually."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from playwright.sync_api import sync_playwright

SRC = Path(__file__).parent
SHOTS = SRC / "_shots"
SHOTS.mkdir(exist_ok=True)

TARGETS = {
    "Orion_Architecture_Explainer.html": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                          11, 12, 13],
    "Orion_Research_Proposal.html": [1, 2, 3, 4, 5],
}


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1400, "height": 1000},
                          device_scale_factor=2)
        for html, idxs in TARGETS.items():
            page.goto((SRC / html).as_uri(), wait_until="load")
            figs = page.locator("figure")
            total = figs.count()
            print(f"{html}: {total} figures")
            tag = "d1" if "Explainer" in html else "d2"
            for i in idxs:
                if i - 1 >= total:
                    print(f"  fig {i}: MISSING")
                    continue
                out = SHOTS / f"{tag}_fig{i:02d}.png"
                figs.nth(i - 1).screenshot(path=str(out))
                print(f"  fig {i:>2} -> {out.name}")
        b.close()


if __name__ == "__main__":
    main()
