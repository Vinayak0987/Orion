"""Programmatic figure checks: box overlap and department naming."""

import math
import re
import orion_figures_light as fl

FAIL = 0


def rects(svg):
    out = []
    for m in re.finditer(r'<rect x="([-\d.]+)" y="([-\d.]+)" '
                         r'width="([\d.]+)" height="([\d.]+)"', svg):
        x, y, w, h = (float(m.group(i)) for i in range(1, 5))
        out.append((x, y, w, h))
    return out


def overlap(a, b, tol=1.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = min(ax + aw, bx + bw) - max(ax, bx)
    iy = min(ay + ah, by + bh) - max(ay, by)
    return ix > tol and iy > tol


print("=" * 70)
print("FIG: department anatomy — box overlap check")
print("=" * 70)
svg = fl.fig3_department_anatomy()
# the nine part boxes are the 142x38 ones
boxes = [r for r in rects(svg) if abs(r[2] - 142) < 0.5 and abs(r[3] - 38) < 0.5]
print(f"  part boxes found: {len(boxes)} (expected 9)")
if len(boxes) != 9:
    FAIL += 1
bad = 0
for i in range(len(boxes)):
    for j in range(i + 1, len(boxes)):
        if overlap(boxes[i], boxes[j]):
            print(f"  OVERLAP: box{i} {boxes[i]} vs box{j} {boxes[j]}")
            bad += 1
print(f"  overlapping pairs: {bad} (expected 0)")
if bad:
    FAIL += 1

# also confirm boxes stay inside the canvas
vb = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
W, H = int(vb.group(1)), int(vb.group(2))
oob = [b for b in boxes
       if b[0] < 0 or b[1] < 0 or b[0] + b[2] > W or b[1] + b[3] > H]
print(f"  boxes outside {W}x{H} canvas: {len(oob)} (expected 0)")
if oob:
    for b in oob:
        print("   ", b)
    FAIL += 1

print()
print("=" * 70)
print("DEPARTMENT NAMING — must be the five implemented departments")
print("=" * 70)
REAL = {"Strategy", "Finance", "Branding", "Marketing", "Operations"}
STALE = {"Sales", "HR", "Legal", "Ops"}

for name, fn in (("fig2_layers", fl.fig2_layers),
                 ("fig4_memory_scoping", fl.fig4_memory_scoping),
                 ("fig_two_layers", fl.fig_two_layers),
                 ("d2_fig1_loop_graph", fl.d2_fig1_loop_graph)):
    s = fn()
    txts = set(re.findall(r'>([A-Za-z& ]{2,20})</text>', s))
    found = {t.strip() for t in txts} & REAL
    stale = {t.strip() for t in txts} & STALE
    status = "OK" if not stale else "STALE NAMES PRESENT"
    print(f"  {name:22s} real={sorted(found)}")
    print(f"  {'':22s} stale={sorted(stale) if stale else 'none'}  -> {status}")
    if stale:
        FAIL += 1

print()
print("=" * 70)
print("MEASURED DATA — variance figure must carry the real observations")
print("=" * 70)
s = fl.fig10_variance_measured()
expect = ["290.9", "129.1", "239.2", "96.8", "38.4", "158.9", "103.8",
          "63.1", "21.2"]
missing = [v for v in expect if v not in s]
print(f"  expected values present: {len(expect) - len(missing)}/{len(expect)}")
if missing:
    print("  MISSING:", missing)
    FAIL += 1
for token in ("PROVISIONAL", "n=5", "n=3"):
    ok = token in s
    print(f"  caveat '{token}': {'present' if ok else 'ABSENT'}")
    if not ok:
        FAIL += 1

print()
print("=" * 70)
print("RESULT:", "ALL CHECKS PASSED" if FAIL == 0 else f"{FAIL} CHECK(S) FAILED")
print("=" * 70)
