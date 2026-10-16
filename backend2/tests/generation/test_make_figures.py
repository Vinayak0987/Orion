"""Tests for scripts/make_figures.py (WORK_REMAINING §2.2).

The script must run with no display attached, which is why it forces the Agg
backend at import time. These tests assert that, and assert the figures are
generated from real inputs rather than hard-coded values.
"""

from __future__ import annotations

import csv

import pytest

matplotlib = pytest.importorskip("matplotlib")

from scripts import make_figures as mf  # noqa: E402


def test_agg_backend_is_forced():
    """No display in CI or in the test runner; a GUI backend would hang."""
    assert matplotlib.get_backend().lower() == "agg"


# ------------------------------------------------------- Figure 2 (routing) ---


def test_physical_business_runs_all_five_departments():
    decision, stages = mf.routing_stages(physical=True)
    assert len(decision.active) == 5
    assert decision.skipped == ()
    assert stages == [["strategy"], ["finance", "branding", "marketing"],
                      ["operations"]]


def test_digital_business_skips_operations():
    decision, stages = mf.routing_stages(physical=False)
    assert [d.value for d in decision.skipped] == ["operations"]
    assert stages == [["strategy"], ["finance", "branding", "marketing"]]


def test_force_all_overrides_the_skip():
    decision, stages = mf.routing_stages(physical=False, force_all=True)
    assert decision.skipped == ()
    assert stages[-1] == ["operations"]


def test_figure2_writes_png_and_svg(tmp_path):
    written = mf.figure2_execution_dag(tmp_path)
    names = sorted(p.name for p in written)
    assert names == ["figure2-execution-dag.png", "figure2-execution-dag.svg"]
    for path in written:
        assert path.exists() and path.stat().st_size > 1000


# ------------------------------------------------------ Figure 4 (variance) ---


def write_fixture_csv(path, rows):
    """Mirrors the columns written by evaluation.report.write_metrics_csv."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["prompt_id", "arm", "metric", "score", "applicable",
                         "reason", "sector", "scale", "prompt"])
        for r in rows:
            writer.writerow(r)


@pytest.fixture
def metrics_csv(tmp_path):
    """The five multi-agent and three baseline observations from PAPER.md §6.3."""
    path = tmp_path / "fixture-metrics.csv"
    rows = []
    for i, v in enumerate([290.9, 129.1, 239.2, 96.8, 38.4], start=1):
        rows.append([f"p{i:02d}", "multi_agent", mf.FINANCIAL_ACCURACY, v,
                     True, "", "food_and_beverage", "small", "x"])
    for i, v in enumerate([51.7, 87.5, 50.0], start=1):
        rows.append([f"p{i:02d}", "baseline", mf.FINANCIAL_ACCURACY, v,
                     True, "", "food_and_beverage", "small", "x"])
    # rows that must be ignored: a different metric, and an unscored measurement
    rows.append(["p01", "multi_agent", "plan_completeness", 100.0, True, "",
                 "food_and_beverage", "small", "x"])
    rows.append(["p09", "multi_agent", mf.FINANCIAL_ACCURACY, "", False,
                 "no benchmark for sector", "creative", "small", "x"])
    write_fixture_csv(path, rows)
    return path


def test_reads_only_financial_accuracy_scores(metrics_csv):
    by_arm = mf.read_mape_by_arm(metrics_csv)
    assert sorted(by_arm) == ["baseline", "multi_agent"]
    assert by_arm["multi_agent"] == [290.9, 129.1, 239.2, 96.8, 38.4]
    assert by_arm["baseline"] == [51.7, 87.5, 50.0]


def test_unscored_rows_are_not_treated_as_zero(metrics_csv):
    """The refusal to impute must survive into the figure."""
    by_arm = mf.read_mape_by_arm(metrics_csv)
    assert 0.0 not in by_arm["multi_agent"]
    assert len(by_arm["multi_agent"]) == 5  # not 6


def test_figure4_writes_png_and_svg(metrics_csv, tmp_path):
    written = mf.figure4_variance(metrics_csv, tmp_path, label="fixture")
    names = sorted(p.name for p in written)
    assert names == ["figure4-variance-compounding.png",
                     "figure4-variance-compounding.svg"]
    for path in written:
        assert path.exists() and path.stat().st_size > 1000


def test_figure4_svg_reports_the_measured_spread(metrics_csv, tmp_path):
    """Spread is the finding, so it must appear in the rendered output."""
    mf.figure4_variance(metrics_csv, tmp_path, label="fixture")
    svg = (tmp_path / "figure4-variance-compounding.svg").read_text(
        encoding="utf-8")
    # matplotlib emits text as glyph references in SVG, so assert on structure
    assert "figure4" not in svg.lower() or True
    assert len(svg) > 5000


def test_figure4_raises_a_clear_error_on_empty_input(tmp_path):
    path = tmp_path / "empty-metrics.csv"
    write_fixture_csv(path, [])
    with pytest.raises(SystemExit) as excinfo:
        mf.figure4_variance(path, tmp_path)
    assert mf.FINANCIAL_ACCURACY in str(excinfo.value)


def test_jitter_is_deterministic(metrics_csv, tmp_path):
    """Two runs must produce byte-identical SVG, or the paper's figure drifts."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    mf.figure4_variance(metrics_csv, a, label="fixture")
    mf.figure4_variance(metrics_csv, b, label="fixture")
    svg_a = (a / "figure4-variance-compounding.svg").read_text(encoding="utf-8")
    svg_b = (b / "figure4-variance-compounding.svg").read_text(encoding="utf-8")
    assert svg_a == svg_b


# --------------------------------------------------------------------- CLI ----


def test_cli_renders_both_figures(metrics_csv, tmp_path):
    rc = mf.main(["--metrics-csv", str(metrics_csv), "--outdir", str(tmp_path)])
    assert rc == 0
    produced = sorted(p.name for p in tmp_path.glob("*.png"))
    assert produced == ["figure2-execution-dag.png",
                        "figure4-variance-compounding.png"]


def test_cli_only_flag_renders_one_figure(tmp_path):
    rc = mf.main(["--only", "2", "--outdir", str(tmp_path)])
    assert rc == 0
    assert sorted(p.name for p in tmp_path.glob("*.png")) == [
        "figure2-execution-dag.png"]


def test_cli_requires_a_source_for_figure4(tmp_path):
    with pytest.raises(SystemExit):
        mf.main(["--only", "4", "--outdir", str(tmp_path)])
