"""Sector margin benchmarks - the "expected" side of Financial Accuracy (F54).

Single source of truth: the P&L agent records the benchmark it was measured
against, and the evaluation harness scores MAPE against the same table, so the
number in the paper and the number in the API can never disagree.

PROVENANCE IS TRACKED DELIBERATELY
----------------------------------
F54 divides by these values. If they are wrong, the headline metric is wrong, and
a reader cannot tell. So every entry carries a `source`, and entries that are not
yet backed by a citation are marked `sourced=False`. The evaluation report refuses
to present an unqualified MAPE while any benchmark in use is unsourced - it labels
the result provisional instead.

The shipped defaults are planning midpoints drawn from general industry knowledge,
NOT published constants. They are good enough to exercise the metric and to sanity
check agent output, and not good enough to publish.

TO MAKE F54 PUBLISHABLE
-----------------------
Fill `evaluation/benchmarks.csv` with cited figures and the harness will load them
automatically:

    sector,gross_margin_pct,net_margin_pct,source
    food_and_beverage,62.0,9.5,"MSME Annual Report 2023-24, Table 4.2, p.61"
    retail,28.0,6.0,"RBI Statistical Tables Relating to Banks 2024, sector aggregate"

Candidate sources worth checking: the MSME Ministry Annual Report sector notes,
RBI's "Performance of Private Corporate Business Sector" quarterly releases,
CMIE Prowess sector aggregates (paid), and NSSO unincorporated-enterprise surveys.
Cite the exact table and year in the paper's methodology section.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import structlog

from app.models.intent import Sector

log = structlog.get_logger(__name__)

UNSOURCED = "unsourced planning estimate - replace before publication"


@dataclass(frozen=True, slots=True)
class MarginBenchmark:
    sector: Sector
    gross_margin_pct: float
    net_margin_pct: float
    source: str = UNSOURCED

    @property
    def sourced(self) -> bool:
        return self.source != UNSOURCED and bool(self.source.strip())


# Shipped defaults. Every entry is explicitly unsourced.
_DEFAULTS: tuple[MarginBenchmark, ...] = (
    MarginBenchmark(Sector.FOOD_AND_BEVERAGE, 60.0, 12.0),
    MarginBenchmark(Sector.RETAIL, 30.0, 8.0),
    MarginBenchmark(Sector.SERVICES, 55.0, 18.0),
    MarginBenchmark(Sector.TECHNOLOGY, 75.0, 20.0),
    MarginBenchmark(Sector.EDUCATION, 65.0, 22.0),
    MarginBenchmark(Sector.HEALTHCARE, 55.0, 20.0),
    MarginBenchmark(Sector.MANUFACTURING, 25.0, 9.0),
    MarginBenchmark(Sector.CREATIVE, 60.0, 18.0),
    MarginBenchmark(Sector.UNSPECIFIED, 45.0, 12.0),
)

BENCHMARKS: dict[Sector, MarginBenchmark] = {b.sector: b for b in _DEFAULTS}

# Backwards-compatible view used by existing callers and tests.
SECTOR_MARGIN_BENCHMARKS: dict[Sector, tuple[float, float]] = {
    sector: (b.gross_margin_pct, b.net_margin_pct) for sector, b in BENCHMARKS.items()
}


def benchmark_for(sector: Sector) -> MarginBenchmark:
    return BENCHMARKS.get(sector, BENCHMARKS[Sector.UNSPECIFIED])


def gross_margin_benchmark(sector: Sector) -> float:
    return benchmark_for(sector).gross_margin_pct


def net_margin_benchmark(sector: Sector) -> float:
    return benchmark_for(sector).net_margin_pct


def all_sourced() -> bool:
    """True only when every benchmark carries a citation.

    The evaluation report keys off this to decide whether F54 may be presented as
    a final result or must be labelled provisional.
    """
    return all(b.sourced for b in BENCHMARKS.values())


def unsourced_sectors() -> list[str]:
    return [s.value for s, b in BENCHMARKS.items() if not b.sourced]


def load_benchmarks_csv(path: str | Path) -> int:
    """Override defaults from a CSV of cited figures. Returns rows applied.

    Expected header: sector,gross_margin_pct,net_margin_pct,source
    Unknown sectors and malformed rows are skipped with a warning rather than
    failing the run, so a partially filled file still improves the metric.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        log.info("benchmarks.csv_absent", path=str(csv_path))
        return 0

    applied = 0
    with csv_path.open(encoding="utf-8", newline="") as handle:
        # Strip comment lines first: csv.DictReader would otherwise take the
        # leading "#" block as the header row and silently apply nothing.
        rows = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]

    for row in csv.DictReader(rows):
        name = (row.get("sector") or "").strip().lower()
        try:
            sector = Sector(name)
        except ValueError:
            log.warning("benchmarks.unknown_sector", sector=name)
            continue

        try:
            gross = float(row["gross_margin_pct"])
            net = float(row["net_margin_pct"])
        except (KeyError, TypeError, ValueError):
            log.warning("benchmarks.bad_row", sector=name)
            continue

        source = (row.get("source") or "").strip() or UNSOURCED
        BENCHMARKS[sector] = MarginBenchmark(sector, gross, net, source)
        SECTOR_MARGIN_BENCHMARKS[sector] = (gross, net)
        applied += 1

    log.info(
        "benchmarks.loaded",
        path=str(csv_path),
        applied=applied,
        all_sourced=all_sourced(),
    )
    return applied
