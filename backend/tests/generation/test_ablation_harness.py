"""Tests for evaluation.ablation_harness — the experiment runner.

Verifies:
  - Sweep produces results for all arms and seeds
  - Output CSV files are well-formed
  - Sweep JSON is valid and complete
  - Metrics are compatible with significance.py
  - CLI entrypoint works
  - End-to-end: short simulation produces all expected output
"""

import csv
import json
import tempfile
from pathlib import Path

import pytest

from app.generation.db import sqlite as sq
from app.generation.operating import init_all
from evaluation.ablation_harness import (
    SweepConfig,
    SeedResult,
    run_sweep,
    write_metrics_csv,
    write_summary_csv,
    write_sweep_json,
    run_and_save,
    main,
)
from evaluation.operating_metrics import ALL_OPERATING_METRICS
from app.generation.operating.ablation import AblationArm


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    """Each test gets a temp db directory."""
    db_file = tmp_path / "harness-test.db"
    monkeypatch.setattr(sq.settings.__class__, "sqlite_file",
                        property(lambda _self: db_file))
    init_all()
    yield


@pytest.fixture
def short_config(tmp_path):
    """A minimal config for fast tests: 2 seeds, 7 days, 2 arms."""
    return SweepConfig(
        label="test-short",
        seeds=[1, 2],
        days=7,
        arms=[AblationArm.SINGLE_LOOP, AblationArm.FULL_GRAPH],
        onset_day=3,
    )


@pytest.fixture
def short_results(short_config):
    """Cached sweep results for reuse across write tests."""
    return run_sweep(short_config)


class TestRunSweep:
    def test_returns_one_result_per_seed(self, short_config):
        results = run_sweep(short_config)
        assert len(results) == 2  # 2 seeds

    def test_each_seed_has_all_arms(self, short_config):
        results = run_sweep(short_config)
        for sr in results:
            assert len(sr.arm_results) == 2
            assert "single_loop" in sr.arm_results
            assert "full_graph" in sr.arm_results

    def test_each_arm_has_metrics(self, short_config):
        results = run_sweep(short_config)
        for sr in results:
            for arm_name, metrics in sr.metrics.items():
                assert len(metrics) == 5  # F59-F63

    def test_duration_recorded(self, short_config):
        results = run_sweep(short_config)
        for sr in results:
            assert sr.duration_s > 0

    def test_single_arm_sweep(self):
        config = SweepConfig(
            label="single-arm",
            seeds=[42],
            days=7,
            arms=[AblationArm.MONITORS_ONLY],
        )
        results = run_sweep(config)
        assert len(results) == 1
        assert "monitors_only" in results[0].arm_results


class TestWriteMetricsCSV:
    def test_produces_valid_csv(self, short_config, short_results, tmp_path):
        # Redirect output to tmp
        import evaluation.ablation_harness as mod
        orig = mod.RESULTS_DIR
        mod.RESULTS_DIR = tmp_path
        try:
            path = write_metrics_csv(short_config, short_results)
            assert path.exists()
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            # 2 seeds × 2 arms × 5 metrics = 20 rows
            assert len(rows) == 20
            assert "seed" in rows[0]
            assert "arm" in rows[0]
            assert "metric" in rows[0]
            assert "score" in rows[0]
        finally:
            mod.RESULTS_DIR = orig

    def test_all_metrics_present(self, short_config, short_results, tmp_path):
        import evaluation.ablation_harness as mod
        orig = mod.RESULTS_DIR
        mod.RESULTS_DIR = tmp_path
        try:
            path = write_metrics_csv(short_config, short_results)
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                metrics_seen = {row["metric"] for row in reader}
            for m in ALL_OPERATING_METRICS:
                assert m in metrics_seen
        finally:
            mod.RESULTS_DIR = orig


class TestWriteSummaryCSV:
    def test_produces_valid_summary(self, short_config, short_results, tmp_path):
        import evaluation.ablation_harness as mod
        orig = mod.RESULTS_DIR
        mod.RESULTS_DIR = tmp_path
        try:
            path = write_summary_csv(short_config, short_results)
            assert path.exists()
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            # 2 arms × 5 metrics = 10 rows
            assert len(rows) == 10
            assert "arm" in rows[0]
            assert "mean" in rows[0]
            assert "sd" in rows[0]
        finally:
            mod.RESULTS_DIR = orig


class TestWriteSweepJSON:
    def test_produces_valid_json(self, short_config, short_results, tmp_path):
        import evaluation.ablation_harness as mod
        orig = mod.RESULTS_DIR
        mod.RESULTS_DIR = tmp_path
        try:
            path = write_sweep_json(short_config, short_results)
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["label"] == "test-short"
            assert data["config"]["days"] == 7
            assert len(data["per_seed"]) == 2
        finally:
            mod.RESULTS_DIR = orig


class TestRunAndSave:
    def test_end_to_end(self, tmp_path):
        import evaluation.ablation_harness as mod
        orig = mod.RESULTS_DIR
        mod.RESULTS_DIR = tmp_path
        try:
            config = SweepConfig(
                label="e2e",
                seeds=[1],
                days=7,
                arms=[AblationArm.SINGLE_LOOP, AblationArm.MONITORS_ONLY],
            )
            results, files = run_and_save(config)
            assert len(results) == 1
            assert files["metrics"].exists()
            assert files["summary"].exists()
            assert files["sweep"].exists()
        finally:
            mod.RESULTS_DIR = orig


class TestCLI:
    def test_main_runs_short_sweep(self, tmp_path, capsys):
        import evaluation.ablation_harness as mod
        orig = mod.RESULTS_DIR
        mod.RESULTS_DIR = tmp_path
        try:
            exit_code = main([
                "--seeds", "1",
                "--days", "7",
                "--label", "cli-test",
                "--arms", "single_loop", "full_graph",
            ])
            assert exit_code == 0
            captured = capsys.readouterr()
            assert "Completed" in captured.out
            assert "cli-test" in captured.out
        finally:
            mod.RESULTS_DIR = orig
