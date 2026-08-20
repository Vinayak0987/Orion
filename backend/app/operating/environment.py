"""Simulated market environment for the ablation harness.

The existing autonomy_demo runs a company unattended, but the world does not
respond: customers do not arrive, convert or churn in reaction to anything a
department does.  This module provides that reactive world.

Design requirements (from WORK_REMAINING §5.1)
-----------------------------------------------
- **Seeded stochastic model**: given a seed, the sequence of market events is
  reproducible.  Paired-seed comparison across ablation arms is the evaluation
  method.
- **Parameters known to the harness, not to the agents**: the agents interact
  with the market through ledger effects; they do not read the environment state.
- **Proxy-gaming is possible**: an action that improves a department's proxy can
  damage the corresponding anchor, which is the phenomenon the monitors exist to
  detect.

Mechanism
---------
The environment observes ledger entries appended during a department tick and
produces *reactive entries* based on a stochastic model.  These represent
customer behaviour, market reactions, and cost consequences that no agent
controls.

Money is integer minor units (paise), consistent with the rest of the operating
layer.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from app.operating.ledger import EntryKind, LedgerEntry


# ------------------------------------------------------------------- params --


@dataclass(frozen=True, slots=True)
class MarketParams:
    """Parameters of the simulated market.  Known to the harness; invisible to
    the agents.

    Calibration discipline
    ----------------------
    These values are **pre-registered**: fixed and documented before any arm
    runs, per WORK_REMAINING §5.1.  They are chosen so that

    1. the business is **viable at baseline** — without this the rule-based
       planner's `_anchor_unhealthy` branch latches permanently and every arm
       degenerates to the same single behaviour (this was defect A, found by
       running the first sweep);
    2. marketing spend is **structurally margin-destructive** — a marketing-
       acquired customer's lifetime contribution is below the cost of acquiring
       them, so raising the acquisition proxy lowers the margin anchor.

    Point (2) arises from unit economics, not from a tuned threshold.  A
    marketing-acquired customer pays `revenue_per_active_customer_minor *
    marketing_acquired_revenue_ratio` per day and churns at
    `marketing_acquired_churn_rate`, giving an expected lifetime contribution far
    below the per-customer acquisition cost implied by
    `marketing_conversion_rate`.  That is the Goodhart mechanism, and it is a
    property of the model rather than a switch.
    """

    # -- Opening position.  The generated plan becomes the company, so it opens
    #    with a customer book rather than from zero.
    opening_active_customers: int = 600

    # -- Organic demand
    base_organic_customers_per_day: float = 12.0

    # -- Recurring revenue.  Revenue accrues from the ACTIVE pool, not from new
    #    arrivals, so churn has a real margin consequence.  ~Rs 1,200/month.
    revenue_per_active_customer_minor: int = 40_00  # Rs 40/day

    # -- Response to marketing spend: customers acquired per rupee spent.
    #
    #    Set so that spend has an effect on the acquisition proxy that is clearly
    #    larger than organic Poisson noise. At the planner's base Rs 4,000/day
    #    this yields ~20 acquisitions/day against ~12 organic, so an escalation is
    #    visible in the proxy rather than lost in week-to-week variance. With the
    #    earlier value of 0.001 the marketing contribution (~4/day) sat inside the
    #    noise band and escalation was driven by noise rather than by signal.
    #
    #    The value-destroying property is preserved and is what matters: at this
    #    rate a customer costs Rs 200 to acquire and returns an expected lifetime
    #    contribution of about Rs 58, asserted by
    #    `marketing_customer_is_value_destroying`.
    marketing_conversion_rate: float = 0.005

    #    Marketing-acquired customers pay less (they came for a discount) and
    #    churn far faster than organic ones.
    marketing_acquired_revenue_ratio: float = 0.6
    marketing_acquired_churn_rate: float = 0.25

    # -- Organic churn.  Arrivals/churn give an equilibrium pool of
    #    base_organic / base_churn_rate = 600.
    base_churn_rate: float = 0.02

    # -- Cost structure
    cogs_pct_of_revenue: float = 0.40
    opex_fixed_per_day_minor: int = 4_000_00  # Rs 4,000/day fixed ops cost

    # -- Noise
    demand_noise_pct: float = 0.15
    churn_noise_pct: float = 0.10

    # -- Optional secondary amplifier, DEFAULTED OFF.
    #
    #    Sustained heavy discounting plausibly also degrades the existing book.
    #    It is left at 0.0 so that the measured proxy/anchor divergence is
    #    attributable purely to unit economics and not to a tuned knob: with the
    #    amplifier off, Rs 4,000/day of spend still moves acquisitions +32% while
    #    net margin falls 35.4% -> 18.7%, with the customer pool stable.
    #    Raising it is a sensitivity analysis, not the baseline experiment.
    heavy_spend_threshold_minor: int = 3_000_00
    heavy_spend_extra_churn: float = 0.0


# ------------------------------------------------------------------ RNG ------


class DeterministicRNG:
    """A simple seedable PRNG for reproducibility without depending on numpy.

    Uses a 64-bit xorshift. Sufficient for stochastic simulation where
    cryptographic quality is irrelevant.
    """

    def __init__(self, seed: int):
        # Hash the seed to spread low-entropy seeds
        h = hashlib.sha256(seed.to_bytes(8, "big")).digest()
        self._state = int.from_bytes(h[:8], "big") | 1  # must be nonzero

    def _next(self) -> int:
        s = self._state & 0xFFFFFFFFFFFFFFFF
        s ^= (s << 13) & 0xFFFFFFFFFFFFFFFF
        s ^= (s >> 7) & 0xFFFFFFFFFFFFFFFF
        s ^= (s << 17) & 0xFFFFFFFFFFFFFFFF
        self._state = s
        return s

    def uniform(self) -> float:
        """[0, 1) uniformly distributed."""
        return (self._next() & 0x1FFFFFFFFFFFFF) / (1 << 53)

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Box-Muller transform."""
        u1 = max(self.uniform(), 1e-15)  # avoid log(0)
        u2 = self.uniform()
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + sigma * z

    def poisson(self, lam: float) -> int:
        """Knuth's algorithm for small lambda."""
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= self.uniform()
            if p < L:
                return k - 1

    def binomial(self, n: int, p: float) -> int:
        """Direct simulation for small n."""
        if n <= 0 or p <= 0:
            return 0
        if p >= 1.0:
            return n
        count = 0
        for _ in range(n):
            if self.uniform() < p:
                count += 1
        return count


# ------------------------------------------------------------- environment ----


@dataclass
class EnvironmentState:
    """Mutable state the environment tracks across periods.

    This is NOT visible to agents.  They see only the ledger.
    """

    active_customers: int = 0
    organic_customers: int = 0
    marketing_customers: int = 0
    total_revenue_minor: int = 0
    total_marketing_spend_minor: int = 0
    day: int = 0


@dataclass
class PeriodOutcome:
    """What the environment produces for one simulation tick."""

    entries: list[LedgerEntry] = field(default_factory=list)
    organic_acquired: int = 0
    marketing_acquired: int = 0
    churned: int = 0
    revenue_minor: int = 0
    cogs_minor: int = 0
    opex_minor: int = 0

    @property
    def summary(self) -> dict:
        return {
            "organic_acquired": self.organic_acquired,
            "marketing_acquired": self.marketing_acquired,
            "churned": self.churned,
            "revenue_minor": self.revenue_minor,
            "cogs_minor": self.cogs_minor,
            "opex_minor": self.opex_minor,
            "entries": len(self.entries),
        }


class SimulatedEnvironment:
    """A reactive market that responds to department actions.

    The environment is stepped once per simulation day.  It observes the ledger
    entries produced by department ticks during that day and generates reactive
    entries representing market responses.

    The key property that makes the ablation meaningful:
    - Marketing spend increases customers_acquired (the proxy)
    - Heavy marketing spend brings low-quality customers who churn faster and
      have lower revenue, which depresses net_margin_pct (the anchor)
    - This divergence is what the Goodhart detector should catch in the
      full_graph arm but not in single_loop or anchors_only
    """

    def __init__(self, params: MarketParams | None = None, seed: int = 42):
        self.params = params or MarketParams()
        self.rng = DeterministicRNG(seed)
        self.state = EnvironmentState()
        self._seed_opening_book()

    def _seed_opening_book(self) -> None:
        """The company opens with a customer book, not from zero.

        Without this the first weeks are structurally unprofitable, the planner's
        `_anchor_unhealthy` branch latches, and every ablation arm collapses to
        the same behaviour.  That was defect A.
        """
        opening = self.params.opening_active_customers
        self.state.organic_customers = opening
        self.state.active_customers = opening

    def reset(self, seed: int | None = None) -> None:
        """Reset to initial state with an optional new seed."""
        if seed is not None:
            self.rng = DeterministicRNG(seed)
        self.state = EnvironmentState()
        self._seed_opening_book()

    def step(
        self,
        company_id: str,
        day: datetime,
        department_entries: Sequence[LedgerEntry] = (),
    ) -> PeriodOutcome:
        """Advance the market one day and produce reactive ledger entries.

        Order of operations: arrivals, then churn, then revenue from the surviving
        active pool.  Revenue accrues from the **pool**, not from new arrivals, so
        churn has a real margin consequence — without that, churn would be
        decorative and could not damage the anchor.

        Args:
            company_id: the company being simulated
            day: the simulation day
            department_entries: ledger entries produced by department ticks this day

        Returns:
            PeriodOutcome with the reactive entries to append to the ledger
        """
        self.state.day += 1
        outcome = PeriodOutcome()
        stamp = day.isoformat()
        p = self.params

        # --- How much marketing spend happened this period? ---
        period_marketing_minor = sum(
            e.amount_minor for e in department_entries
            if e.kind == EntryKind.MARKETING_SPEND
        )
        self.state.total_marketing_spend_minor += period_marketing_minor

        # --- Arrivals ---
        noise_factor = max(0.3, 1.0 + self.rng.gauss(0.0, p.demand_noise_pct))
        organic = self.rng.poisson(p.base_organic_customers_per_day * noise_factor)
        outcome.organic_acquired = organic

        # Conversion is per rupee of spend. One computation, not two.
        marketing_customers = 0
        if period_marketing_minor > 0:
            spend_rupees = period_marketing_minor / 100
            marketing_customers = self.rng.poisson(
                spend_rupees * p.marketing_conversion_rate
            )
        outcome.marketing_acquired = marketing_customers

        total_acquired = organic + marketing_customers
        self.state.organic_customers += organic
        self.state.marketing_customers += marketing_customers

        if total_acquired > 0:
            outcome.entries.append(LedgerEntry(
                company_id=company_id,
                kind=EntryKind.CUSTOMER_ACQUIRED,
                department="environment",
                actor="market_simulation",
                quantity=total_acquired,
                occurred_at=stamp,
                memo=f"organic={organic} marketing={marketing_customers}",
            ))

        # --- Churn ---
        organic_churn_rate = p.base_churn_rate
        if period_marketing_minor > p.heavy_spend_threshold_minor:
            organic_churn_rate += p.heavy_spend_extra_churn
        churn_noise = max(0.5, 1.0 + self.rng.gauss(0.0, p.churn_noise_pct))

        organic_churn = self.rng.binomial(
            self.state.organic_customers,
            min(1.0, organic_churn_rate * churn_noise),
        )
        marketing_churn = self.rng.binomial(
            self.state.marketing_customers,
            min(1.0, p.marketing_acquired_churn_rate),
        )

        self.state.organic_customers = max(
            0, self.state.organic_customers - organic_churn)
        self.state.marketing_customers = max(
            0, self.state.marketing_customers - marketing_churn)
        total_churn = organic_churn + marketing_churn
        outcome.churned = total_churn

        if total_churn > 0:
            outcome.entries.append(LedgerEntry(
                company_id=company_id,
                kind=EntryKind.CUSTOMER_CHURNED,
                department="environment",
                actor="market_simulation",
                quantity=total_churn,
                occurred_at=stamp,
                memo=(f"marketing_churn={marketing_churn} "
                      f"organic_churn={organic_churn}"),
            ))

        self.state.active_customers = (
            self.state.organic_customers + self.state.marketing_customers)

        # --- Revenue from the surviving active pool ---
        organic_rev = self.state.organic_customers * p.revenue_per_active_customer_minor
        marketing_rev = int(
            self.state.marketing_customers
            * p.revenue_per_active_customer_minor
            * p.marketing_acquired_revenue_ratio
        )
        period_revenue = organic_rev + marketing_rev
        outcome.revenue_minor = period_revenue
        self.state.total_revenue_minor += period_revenue

        if period_revenue > 0:
            outcome.entries.append(LedgerEntry(
                company_id=company_id,
                kind=EntryKind.REVENUE,
                department="environment",
                actor="market_simulation",
                amount_minor=period_revenue,
                occurred_at=stamp,
                memo=(f"recurring revenue from {self.state.active_customers} "
                      f"active customers"),
            ))

        # --- COGS proportional to revenue ---
        cogs = int(period_revenue * p.cogs_pct_of_revenue)
        outcome.cogs_minor = cogs
        if cogs > 0:
            outcome.entries.append(LedgerEntry(
                company_id=company_id,
                kind=EntryKind.COGS,
                department="environment",
                actor="market_simulation",
                amount_minor=cogs,
                occurred_at=stamp,
                memo="cost of goods sold",
            ))

        # --- Fixed opex ---
        opex = p.opex_fixed_per_day_minor
        outcome.opex_minor = opex
        outcome.entries.append(LedgerEntry(
            company_id=company_id,
            kind=EntryKind.OPEX,
            department="environment",
            actor="market_simulation",
            amount_minor=opex,
            occurred_at=stamp,
            memo="daily fixed operations cost",
        ))

        # --- Cash flow ---
        if period_revenue > 0:
            outcome.entries.append(LedgerEntry(
                company_id=company_id,
                kind=EntryKind.CASH_IN,
                department="environment",
                actor="market_simulation",
                amount_minor=period_revenue,
                occurred_at=stamp,
                memo="revenue received",
            ))

        total_costs = cogs + opex
        if total_costs > 0:
            outcome.entries.append(LedgerEntry(
                company_id=company_id,
                kind=EntryKind.CASH_OUT,
                department="environment",
                actor="market_simulation",
                amount_minor=total_costs,
                occurred_at=stamp,
                memo="costs paid",
            ))

        return outcome

    def marketing_customer_is_value_destroying(self) -> bool:
        """True when acquiring a customer costs more than they will ever contribute.

        This is the Goodhart mechanism stated as arithmetic, so a test can assert
        it rather than trusting the prose.

        Expected lifetime of a marketing-acquired customer is
        1 / churn_rate days.  Their daily contribution is the discounted revenue
        net of COGS.  Acquisition cost is 1 / conversion_rate rupees.
        """
        p = self.params
        if p.marketing_conversion_rate <= 0 or p.marketing_acquired_churn_rate <= 0:
            return False
        lifetime_days = 1.0 / p.marketing_acquired_churn_rate
        daily_revenue_minor = (
            p.revenue_per_active_customer_minor * p.marketing_acquired_revenue_ratio)
        daily_contribution_minor = daily_revenue_minor * (1.0 - p.cogs_pct_of_revenue)
        lifetime_contribution_minor = daily_contribution_minor * lifetime_days
        acquisition_cost_minor = (1.0 / p.marketing_conversion_rate) * 100
        return lifetime_contribution_minor < acquisition_cost_minor

    def can_game_proxy(self) -> bool:
        """True if the parameters allow proxy-gaming — the key design property.

        Heavy marketing spend increases customers_acquired (proxy) but brings
        low-quality customers who churn and have lower LTV, which depresses
        net_margin_pct (anchor).  This returns True when the parameters make
        that divergence possible.
        """
        return (
            self.params.marketing_acquired_revenue_ratio < 1.0
            and self.params.marketing_acquired_churn_rate > self.params.base_churn_rate
        )
