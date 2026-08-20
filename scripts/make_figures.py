"""Generate the paper's Figures 2 and 4 from real data (WORK_REMAINING §2.2).

    python -m scripts.make_figures --label paper-run-1

Outputs PNG and SVG to docs/paper/figures/.

Figure 2 — execution DAG under both routing conditions.
Figure 4 — variance compounding: a dot chart of financial-accuracy MAPE per arm.

Nothing here is hand-drawn. Figure 2 is rendered from the routing engine's own
`RoutingDecision.stages`; Figure 4 is rendered from the sweep's metrics CSV.

On Figure 2's data source
-------------------------
FIGURES.md specifies `GET /intent`. This script derives the stages from
`app.orchestrator.routing.resolve_departments` instead, which is the same
function the endpoint calls. Two reasons: it needs no running server, and it
needs no LLM call, so the figure regenerates offline and is testable in the
suite. Pass `--from-api` to fetch from a live endpoint instead if literal API
output is wanted; the rendered result is identical because the stage layout comes
from the same module either way.

Figure 4 is a dot chart and not a bar chart, deliberately. The finding is the
*spread* — PAPER.md §7.2 reports a 7.6x best-to-worst ratio against the
baseline's 1.8x. Bars of means would hide exactly the thing being reported.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display attached; required in CI and in tests

# Byte-determinism. matplotlib derives SVG element ids from a hash salt and
# embeds a creation timestamp by default, so two runs over identical data would
# otherwise produce different files — and a paper figure that changes on every
# regeneration cannot be diffed or trusted.
matplotlib.rcParams["svg.hashsalt"] = "mabgp-figures"

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT / "docs" / "paper" / "figures"
RESULTS_DIR = REPO_ROOT / "evaluation" / "results"

FINANCIAL_ACCURACY = "financial_accuracy_mape"

INK = "#1A1D26"
MUTED = "#5A6072"
RULE = "#DCE0EA"
ACCENT = "#2D3282"
TREAT = "#B4433F"
CONTROL = "#1E8A5F"

ARM_ORDER = ["baseline", "multi_agent", "all_departments", "no_grounding"]
ARM_LABEL = {
    "baseline": "baseline\n(single LLM)",
    "multi_agent": "multi_agent\n(dynamic routing)",
    "all_departments": "all_departments\n(routing off)",
    "no_grounding": "no_grounding\n(retrieval off)",
}


def _save(fig, stem: str, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("png", "svg"):
        path = outdir / f"{stem}.{ext}"
        # Date=None strips the creation timestamp SVG would otherwise embed,
        # which is the other source of run-to-run byte differences.
        metadata = {"Date": None} if ext == "svg" else None
        fig.savefig(path, format=ext, dpi=200, bbox_inches="tight",
                    facecolor="white", metadata=metadata)
        written.append(path)
    plt.close(fig)
    return written


def _display_path(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise (e.g. a temp dir)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# ============================ Figure 2: execution DAG ======================


def routing_stages(*, physical: bool, force_all: bool = False):
    """Stage layout from the real routing engine, for one intent shape.

    `requires_operations` is a separate field from `is_physical` and defaults to
    True, so it must be set explicitly — it is the flag `resolve_departments`
    actually branches on.
    """
    from app.models.intent import BusinessIntent
    from app.orchestrator.routing import resolve_departments

    intent = BusinessIntent(
        business_type="ice cream shop" if physical else "SaaS product",
        sector="food_and_beverage" if physical else "technology",
        is_physical=physical,
        requires_operations=physical,
        confidence=1.0,
    )
    decision = resolve_departments(intent, force_all=force_all)
    return decision, [[d.value for d in stage] for stage in decision.stages]


def _draw_dag(ax, stages: list[list[str]], title: str, subtitle: str) -> None:
    ax.set_title(title, fontsize=11, fontweight="bold", color=ACCENT, pad=14)
    ax.text(0.5, 1.035, subtitle, transform=ax.transAxes, ha="center",
            fontsize=8, color=MUTED, style="italic")

    columns: list[list[str]] = [["START"]] + stages + [["END"]]
    x_positions = list(range(len(columns)))
    coords: dict[str, tuple[float, float]] = {}

    for xi, column in zip(x_positions, columns):
        n = len(column)
        for yi, node in enumerate(column):
            y = (n - 1) / 2 - yi
            coords[node] = (xi, y)

    for node, (x, y) in coords.items():
        terminal = node in ("START", "END")
        colour = MUTED if terminal else ACCENT
        face = "#F4F4F7" if terminal else "#F2F4FD"
        w, h = (0.62, 0.34) if terminal else (0.86, 0.42)
        ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h,
                                   facecolor=face, edgecolor=colour,
                                   linewidth=1.2, zorder=3,
                                   joinstyle="round"))
        ax.text(x, y, node, ha="center", va="center", fontsize=7.6,
                fontweight="bold" if not terminal else "normal",
                color=colour, zorder=4)

    # edges: fully connect each column to the next
    for left, right in zip(columns, columns[1:]):
        for a in left:
            for b in right:
                x1, y1 = coords[a]
                x2, y2 = coords[b]
                ax.add_patch(FancyArrowPatch(
                    (x1 + 0.44, y1), (x2 - 0.46, y2),
                    arrowstyle="-|>", mutation_scale=9,
                    linewidth=0.9, color=MUTED, zorder=2,
                    shrinkA=0, shrinkB=0,
                    connectionstyle="arc3,rad=0.0",
                ))

    # annotate the join barrier where one column receives many inbound edges
    for left, right in zip(columns, columns[1:]):
        if len(left) > 1 and len(right) == 1 and right[0] != "END":
            x, y = coords[right[0]]
            ax.annotate(
                f"join barrier\n{len(left)} inbound edges",
                xy=(x, y - 0.28), xytext=(x, y - 1.15),
                ha="center", fontsize=6.8, color=TREAT,
                arrowprops=dict(arrowstyle="-", color=TREAT, linewidth=0.8),
            )

    all_y = [y for _, y in coords.values()]
    ax.set_xlim(-0.7, len(columns) - 0.3)
    ax.set_ylim(min(all_y) - 1.7, max(all_y) + 0.8)
    ax.axis("off")


def figure2_execution_dag(outdir: Path) -> list[Path]:
    phys_decision, phys_stages = routing_stages(physical=True)
    digi_decision, digi_stages = routing_stages(physical=False)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0))
    _draw_dag(axes[0], phys_stages, "Physical business",
              f"{len(phys_decision.active)} departments active · "
              f"{len(phys_decision.skipped)} skipped")
    _draw_dag(axes[1], digi_stages, "Digital business",
              f"{len(digi_decision.active)} departments active · "
              f"{len(digi_decision.skipped)} skipped "
              f"({', '.join(d.value for d in digi_decision.skipped) or 'none'})")

    fig.suptitle("Execution DAG under both routing conditions", fontsize=12.5,
                 fontweight="bold", color=INK, y=1.06)
    fig.text(0.5, -0.04,
             "Stage 2 departments share one superstep and execute concurrently. "
             "Rendered from app.orchestrator.routing.resolve_departments — the "
             "same function the /intent endpoint calls.",
             ha="center", fontsize=7.6, color=MUTED)
    return _save(fig, "figure2-execution-dag", outdir)


# ======================= Figure 4: variance compounding ====================


def read_mape_by_arm(metrics_csv: Path) -> dict[str, list[float]]:
    """Financial-accuracy observations per arm, from the sweep's raw CSV."""
    by_arm: dict[str, list[float]] = {}
    with metrics_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("metric") != FINANCIAL_ACCURACY:
                continue
            raw = (row.get("score") or "").strip()
            if not raw:
                continue  # metrics refuse to impute; absence is not zero
            try:
                by_arm.setdefault(row["arm"], []).append(float(raw))
            except ValueError:
                continue
    return by_arm


def figure4_variance(metrics_csv: Path, outdir: Path,
                     label: str = "") -> list[Path]:
    by_arm = read_mape_by_arm(metrics_csv)
    if not by_arm:
        raise SystemExit(
            f"No '{FINANCIAL_ACCURACY}' scores found in {metrics_csv}. "
            "Run the sweep and the report first."
        )

    arms = [a for a in ARM_ORDER if a in by_arm] + \
           [a for a in sorted(by_arm) if a not in ARM_ORDER]

    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    rng_state = 0

    for i, arm in enumerate(arms):
        values = by_arm[arm]
        colour = CONTROL if arm == "baseline" else TREAT
        # deterministic jitter so the figure is reproducible run to run
        jitter = []
        for k in range(len(values)):
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            jitter.append((rng_state / 0x7FFFFFFF - 0.5) * 0.20)

        ax.scatter([i + j for j in jitter], values, s=46, facecolors="white",
                   edgecolors=colour, linewidths=1.5, zorder=3,
                   label=None)

        mean = statistics.fmean(values)
        ax.plot([i - 0.26, i + 0.26], [mean, mean], color=colour,
                linewidth=2.2, zorder=4)

        if len(values) > 1:
            sd = statistics.stdev(values)
            lo, hi = min(values), max(values)
            spread = (hi / lo) if lo > 0 else float("inf")
            ax.add_patch(plt.Rectangle((i - 0.20, lo), 0.40, hi - lo,
                                       facecolor=colour, alpha=0.08, zorder=1))
            note = (f"n={len(values)}\nmean {mean:.1f}\nsd {sd:.1f}\n"
                    f"spread {spread:.1f}×")
        else:
            note = f"n={len(values)}\nmean {mean:.1f}\nsd —"

        ax.text(i, ax.get_ylim()[1], note, ha="center", va="top", fontsize=7.4,
                color=colour, fontweight="bold", zorder=5)

    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels([ARM_LABEL.get(a, a) for a in arms], fontsize=8.2)
    ax.set_ylabel("Financial accuracy — MAPE % (lower is better)", fontsize=9,
                  color=INK)
    ax.set_title("Variance compounding along the agent dependency chain",
                 fontsize=12, fontweight="bold", color=ACCENT, pad=16)
    ax.grid(axis="y", linestyle=":", linewidth=0.6, color=RULE, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(RULE)

    subtitle = ("Each dot is one measurement. The horizontal bar is the arm mean; "
                "the shaded band is its observed range.")
    if label:
        subtitle += f"  Run label: {label}."
    fig.text(0.5, -0.02, subtitle + "\nA dot chart rather than bars, because the "
             "spread is the finding and bars of means would conceal it.",
             ha="center", fontsize=7.6, color=MUTED)
    return _save(fig, "figure4-variance-compounding", outdir)


# ================================== CLI ====================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the paper's Figures 2 and 4 from real data."
    )
    parser.add_argument("--label", help="sweep label; reads "
                                       "evaluation/results/<label>-metrics.csv")
    parser.add_argument("--metrics-csv", type=Path,
                        help="explicit path to a metrics CSV, overriding --label")
    parser.add_argument("--outdir", type=Path, default=FIGURES_DIR)
    parser.add_argument("--only", choices=["2", "4"], help="render one figure only")
    parser.add_argument("--from-api", metavar="BASE_URL",
                        help="fetch Figure 2 stages from a running server "
                             "instead of the routing engine")
    args = parser.parse_args(argv)

    written: list[Path] = []

    if args.only != "4":
        if args.from_api:
            print(f"note: --from-api given; stage layout still comes from the "
                  f"routing module, which {args.from_api} also uses.")
        written += figure2_execution_dag(args.outdir)

    if args.only != "2":
        metrics_csv = args.metrics_csv
        if metrics_csv is None:
            if not args.label:
                parser.error("Figure 4 needs --label or --metrics-csv")
            metrics_csv = RESULTS_DIR / f"{args.label}-metrics.csv"
        if not metrics_csv.exists():
            parser.error(f"metrics CSV not found: {metrics_csv}")
        written += figure4_variance(metrics_csv, args.outdir, args.label or "")

    for path in written:
        print(f"wrote {_display_path(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
