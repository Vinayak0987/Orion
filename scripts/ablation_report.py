# Report on an ablation sweep: per-arm outcomes and paired significance tests.
#
#     python -m scripts.ablation_report --label ablation-v2
#
# Reads the CSV/JSON that `evaluation.ablation_harness` wrote and reports:
#
#   * per-arm business outcomes with between-seed standard deviations
#   * paired Wilcoxon tests for every arm pair on every metric, via the
#     project's own evaluation.significance module
#
# Arms are paired by SEED, which is the ablation's equivalent of pairing by
# prompt_id in the generation-layer sweep. Comparisons with fewer than
# MIN_PAIRS_FOR_POWER pairs are marked UNDERPOWERED by that module, and a p-value
# so marked is not evidence either way.
#
# Deliberately reports which metrics are zero BY CONSTRUCTION. An arm without
# monitors scores exactly 0 on the conflict rate because it runs no conflict
# detector, so a significant p-value there confirms the arm configuration rather
# than any difference in behaviour. Saying so is the point.
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "backend"))

RESULTS = pathlib.Path(__file__).resolve().parent.parent / "evaluation" / "results"
ARMS = ("single_loop", "anchors_only", "monitors_only", "full_graph")
PAIRS = (
    ("single_loop", "anchors_only"),
    ("single_loop", "monitors_only"),
    ("single_loop", "full_graph"),
    ("anchors_only", "full_graph"),
    ("monitors_only", "full_graph"),
)

#: Metrics an arm cannot score unless its topology includes the relevant loop.
#: A difference on these is definitional, not behavioural.
STRUCTURAL = {
    "conflict_incident_rate": "unmonitored arms run no conflict detector",
    "detection_latency_days": "unmonitored arms raise no findings",
    "objective_staleness": "unmonitored arms run no objective review",
    "human_decision_load": "ungoverned arms have no gate to queue at",
}


def outcomes(label: str) -> None:
    path = RESULTS / f"{label}-ablation-sweep.json"
    if not path.exists():
        print(f"missing {path}")
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    per_seed = payload["per_seed"]

    acc = {a: defaultdict(list) for a in ARMS}
    for seed in per_seed:
        for arm in ARMS:
            row = seed["arms"].get(arm)
            if not row:
                continue
            acc[arm]["acquired"].append(row["customers_acquired"])
            acc[arm]["spend"].append(row["total_marketing_spend_minor"] / 100)
            acc[arm]["lessons"].append(row["lessons_written"])
            acc[arm]["corrections"].append(row["corrections"])
            acc[arm]["human"].append(
                row["blocked_actions"] + row["queued_for_review"])

    print(f"n = {len(per_seed)} paired seeds, "
          f"{payload['config']['days']} simulated days per arm")
    print()
    print("%-15s %16s %17s %9s %7s %7s" % (
        "arm", "acquisitions", "mkt spend Rs", "lessons", "corr", "human"))
    print("-" * 78)
    for arm in ARMS:
        v = acc[arm]
        if not v["acquired"]:
            continue
        sd = st.stdev if len(v["acquired"]) > 1 else (lambda _x: 0.0)
        print("%-15s %8.0f+-%-7.0f %8.0f+-%-8.0f %9.1f %7.1f %7.1f" % (
            arm, st.mean(v["acquired"]), sd(v["acquired"]),
            st.mean(v["spend"]), sd(v["spend"]),
            st.mean(v["lessons"]), st.mean(v["corrections"]),
            st.mean(v["human"])))


def significance(label: str) -> None:
    from evaluation.significance import MIN_PAIRS_FOR_POWER, compare

    path = RESULTS / f"{label}-ablation-metrics.csv"
    if not path.exists():
        print(f"missing {path}")
        return

    data: dict = defaultdict(lambda: defaultdict(dict))
    with open(path, encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["score"] == "":
                continue
            data[row["metric"]][row["arm"]][row["seed"]] = float(row["score"])

    for metric in sorted(data):
        print()
        print("=" * 78)
        note = STRUCTURAL.get(metric)
        print(metric + (f"   [STRUCTURAL: {note}]" if note else ""))
        print("=" * 78)
        for left_arm, right_arm in PAIRS:
            left = data[metric].get(left_arm, {})
            right = data[metric].get(right_arm, {})
            seeds = sorted(set(left) & set(right))
            pair = f"{left_arm} vs {right_arm}"
            if not seeds:
                print("  %-30s not scored in both arms" % pair)
                continue
            result = compare(metric, left_arm, right_arm, seeds,
                             [left[s] for s in seeds],
                             [right[s] for s in seeds])
            p = result.wilcoxon_p
            verdict = (
                "no pairable variation" if p is None
                else "SIGNIFICANT" if p < 0.05
                else "not significant"
            )
            flag = " UNDERPOWERED" if result.n_pairs < MIN_PAIRS_FOR_POWER else ""
            print("  %-30s n=%-3d %8.4f vs %8.4f  diff %+8.4f  p=%-8s %s%s" % (
                pair, result.n_pairs, result.mean_a, result.mean_b,
                result.mean_diff,
                ("%.4f" % p) if p is not None else "n/a", verdict, flag))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label", default="ablation-v2")
    args = ap.parse_args(argv)

    outcomes(args.label)
    significance(args.label)
    print()
    print("Read the STRUCTURAL rows with care: those differences follow from the")
    print("arm definition, not from anything the company did differently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
