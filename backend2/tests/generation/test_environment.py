"""Tests for app.generation.operating.environment — the simulated market.

Key properties tested:
  - Deterministic with a fixed seed
  - Proxy-gaming is possible: heavy marketing spend increases acquisition (proxy)
    but depresses net margin (anchor)
  - Environment produces valid ledger entries
  - Parameters are respected
  - Offline, no LLM calls, no network
"""

import pytest
from datetime import UTC, datetime

from app.generation.operating.environment import (
    DeterministicRNG,
    EnvironmentState,
    MarketParams,
    PeriodOutcome,
    SimulatedEnvironment,
)
from app.generation.operating.ledger import EntryKind, LedgerEntry


# -------------------------------------------------------------------- RNG -----


class TestDeterministicRNG:
    def test_same_seed_same_sequence(self):
        r1 = DeterministicRNG(42)
        r2 = DeterministicRNG(42)
        for _ in range(100):
            assert r1.uniform() == r2.uniform()

    def test_different_seed_different_sequence(self):
        r1 = DeterministicRNG(42)
        r2 = DeterministicRNG(99)
        vals1 = [r1.uniform() for _ in range(20)]
        vals2 = [r2.uniform() for _ in range(20)]
        assert vals1 != vals2

    def test_uniform_in_range(self):
        rng = DeterministicRNG(7)
        for _ in range(1000):
            v = rng.uniform()
            assert 0.0 <= v < 1.0

    def test_gauss_produces_reasonable_values(self):
        rng = DeterministicRNG(1)
        values = [rng.gauss(0, 1) for _ in range(500)]
        mean = sum(values) / len(values)
        assert abs(mean) < 0.3  # should be close to 0

    def test_poisson_non_negative(self):
        rng = DeterministicRNG(5)
        for _ in range(200):
            assert rng.poisson(3.0) >= 0

    def test_poisson_zero_lambda(self):
        rng = DeterministicRNG(5)
        assert rng.poisson(0.0) == 0
        assert rng.poisson(-1.0) == 0

    def test_binomial_in_range(self):
        rng = DeterministicRNG(5)
        for _ in range(200):
            v = rng.binomial(10, 0.3)
            assert 0 <= v <= 10

    def test_binomial_edge_cases(self):
        rng = DeterministicRNG(5)
        assert rng.binomial(0, 0.5) == 0
        assert rng.binomial(10, 0.0) == 0
        assert rng.binomial(10, 1.0) == 10


# ------------------------------------------------------------- environment ----


class TestSimulatedEnvironment:
    @pytest.fixture
    def env(self):
        return SimulatedEnvironment(seed=42)

    @pytest.fixture
    def day(self):
        return datetime(2026, 7, 1, 9, 0, tzinfo=UTC)

    def test_deterministic_with_same_seed(self, day):
        """Same seed produces identical outcomes."""
        env1 = SimulatedEnvironment(seed=100)
        env2 = SimulatedEnvironment(seed=100)
        for i in range(30):
            d = datetime(2026, 7, 1 + i, 9, 0, tzinfo=UTC)
            o1 = env1.step("co1", d)
            o2 = env2.step("co2", d)
            assert o1.organic_acquired == o2.organic_acquired
            assert o1.churned == o2.churned
            assert o1.revenue_minor == o2.revenue_minor

    def test_different_seed_produces_different_outcomes(self, day):
        env1 = SimulatedEnvironment(seed=1)
        env2 = SimulatedEnvironment(seed=2)
        outcomes1 = [env1.step("co", day).organic_acquired for _ in range(20)]
        outcomes2 = [env2.step("co", day).organic_acquired for _ in range(20)]
        # With different seeds, at least some outcomes should differ
        assert outcomes1 != outcomes2

    def test_organic_customers_arrive_without_marketing(self, env, day):
        """Even with no marketing spend, organic customers appear."""
        outcome = env.step("co", day, department_entries=[])
        assert outcome.organic_acquired >= 0
        # Over 30 days, we should get some organic customers
        total = sum(
            env.step("co", datetime(2026, 7, d, 9, 0, tzinfo=UTC)).organic_acquired
            for d in range(2, 31)
        )
        assert total > 0

    def test_marketing_spend_increases_acquisition(self, day):
        """Marketing spend produces additional acquired customers."""
        env_no_spend = SimulatedEnvironment(seed=50)
        env_spend = SimulatedEnvironment(seed=50)

        # Run 30 days with no marketing
        no_marketing_acquired = 0
        for d in range(30):
            dt = datetime(2026, 7, 1 + d, 9, 0, tzinfo=UTC)
            o = env_no_spend.step("co", dt)
            no_marketing_acquired += o.organic_acquired + o.marketing_acquired

        # Run 30 days with heavy marketing
        env_spend.reset(seed=50)
        marketing_acquired = 0
        for d in range(30):
            dt = datetime(2026, 7, 1 + d, 9, 0, tzinfo=UTC)
            spend_entries = [LedgerEntry(
                company_id="co", kind=EntryKind.MARKETING_SPEND,
                department="marketing", actor="marketing_worker",
                amount_minor=10_000_00, occurred_at=dt.isoformat(),
            )]
            o = env_spend.step("co", dt, spend_entries)
            marketing_acquired += o.organic_acquired + o.marketing_acquired

        assert marketing_acquired > no_marketing_acquired

    def test_proxy_gaming_possible(self, day):
        """Heavy marketing increases acquisitions (proxy) but causes more churn
        and lower revenue per customer, depressing margin (anchor).

        This is THE key property the ablation harness needs.
        """
        from datetime import timedelta

        # Run two simulations: one with moderate spend, one with heavy spend
        env_moderate = SimulatedEnvironment(seed=77)
        env_heavy = SimulatedEnvironment(seed=77)

        moderate_acquired = 0
        moderate_revenue = 0
        moderate_churn = 0
        heavy_acquired = 0
        heavy_revenue = 0
        heavy_churn = 0

        base = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        for d in range(60):
            dt = base + timedelta(days=d)

            # Moderate: ₹1000/day
            mod_entries = [LedgerEntry(
                company_id="co", kind=EntryKind.MARKETING_SPEND,
                department="marketing", actor="w",
                amount_minor=1_000_00, occurred_at=dt.isoformat(),
            )]
            om = env_moderate.step("co", dt, mod_entries)
            moderate_acquired += om.organic_acquired + om.marketing_acquired
            moderate_revenue += om.revenue_minor
            moderate_churn += om.churned

            # Heavy: ₹10000/day (above heavy_spend_threshold)
            heavy_entries = [LedgerEntry(
                company_id="co", kind=EntryKind.MARKETING_SPEND,
                department="marketing", actor="w",
                amount_minor=10_000_00, occurred_at=dt.isoformat(),
            )]
            oh = env_heavy.step("co", dt, heavy_entries)
            heavy_acquired += oh.organic_acquired + oh.marketing_acquired
            heavy_revenue += oh.revenue_minor
            heavy_churn += oh.churned

        # Heavy spend should get more customers (proxy improved)
        assert heavy_acquired > moderate_acquired
        # But higher churn (anchor damaged)
        assert heavy_churn > moderate_churn

    def test_can_game_proxy_default_params(self):
        env = SimulatedEnvironment()
        assert env.can_game_proxy() is True

    def test_can_game_proxy_false_when_no_discount(self):
        params = MarketParams(
            marketing_acquired_revenue_ratio=1.0,
            marketing_acquired_churn_rate=0.05,
        )
        env = SimulatedEnvironment(params=params)
        assert env.can_game_proxy() is False

    def test_entries_are_valid_ledger_entries(self, env, day):
        """All produced entries should be valid LedgerEntry instances."""
        spend = [LedgerEntry(
            company_id="co", kind=EntryKind.MARKETING_SPEND,
            department="marketing", actor="w",
            amount_minor=5_000_00, occurred_at=day.isoformat(),
        )]
        outcome = env.step("co", day, spend)
        for entry in outcome.entries:
            assert isinstance(entry, LedgerEntry)
            assert entry.company_id == "co"
            assert entry.department == "environment"
            assert entry.actor == "market_simulation"
            # Monetary entries have non-negative amount
            if entry.kind in (EntryKind.REVENUE, EntryKind.COGS, EntryKind.OPEX,
                              EntryKind.CASH_IN, EntryKind.CASH_OUT):
                assert entry.amount_minor >= 0
            # Count entries have non-negative quantity
            if entry.kind in (EntryKind.CUSTOMER_ACQUIRED, EntryKind.CUSTOMER_CHURNED):
                assert entry.quantity >= 0

    def test_reset_restores_initial_state(self, env, day):
        env.step("co", day)
        env.step("co", day)
        assert env.state.day == 2
        env.reset(seed=42)
        assert env.state.day == 0
        # Reset restores the OPENING BOOK, not an empty company: the generated
        # plan becomes the company, so it starts with customers.
        assert env.state.active_customers == env.params.opening_active_customers

    def test_opens_with_a_customer_book(self):
        """The company must open viable, or the planner's unhealthy-anchor branch
        latches permanently and every ablation arm collapses to one behaviour.
        This was defect A, found by running the first sweep."""
        env = SimulatedEnvironment(seed=1)
        assert env.state.active_customers == env.params.opening_active_customers
        assert env.state.organic_customers == env.params.opening_active_customers

    def test_revenue_accrues_from_the_active_pool_not_from_arrivals(self):
        """Revenue must come from the pool, otherwise churn cannot damage margin
        and the anchor could never move against the proxy."""
        env = SimulatedEnvironment(seed=3)
        day = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        outcome = env.step("co", day)
        # Revenue is far larger than a few arrivals could explain
        expected_floor = 500 * env.params.revenue_per_active_customer_minor
        assert outcome.revenue_minor > expected_floor
        assert outcome.organic_acquired < 100  # only a handful arrived

    def test_marketing_acquisition_is_value_destroying(self):
        """The Goodhart mechanism stated as arithmetic.

        A marketing-acquired customer's expected lifetime contribution is below
        the cost of acquiring them, so raising the acquisition proxy lowers the
        margin anchor. This is a property of the unit economics, not a tuned
        threshold - the churn amplifier is defaulted to 0.0.
        """
        env = SimulatedEnvironment()
        assert env.params.heavy_spend_extra_churn == 0.0, (
            "the baseline experiment must not rely on the churn amplifier"
        )
        assert env.marketing_customer_is_value_destroying()

    def test_goodhart_holds_without_the_churn_amplifier(self):
        """Proxy up, anchor down, from unit economics alone.

        With the amplifier off the customer pool is stable, so the margin damage
        is attributable purely to spending more on acquisition than the acquired
        customers contribute.
        """
        from datetime import timedelta

        def run(spend_minor):
            env = SimulatedEnvironment(seed=1)
            rev = cogs = opex = mkt = acquired = 0
            base = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
            for d in range(90):
                dt = base + timedelta(days=d)
                entries = []
                if spend_minor:
                    entries.append(LedgerEntry(
                        company_id="c", kind=EntryKind.MARKETING_SPEND,
                        department="marketing", actor="w",
                        amount_minor=spend_minor, occurred_at=dt.isoformat()))
                o = env.step("c", dt, entries)
                rev += o.revenue_minor
                cogs += o.cogs_minor
                opex += o.opex_minor
                mkt += spend_minor
                acquired += o.organic_acquired + o.marketing_acquired
            net = rev - cogs - opex - mkt
            return acquired, (net / rev * 100.0), env.state.active_customers

        quiet_acq, quiet_margin, quiet_pool = run(0)
        spend_acq, spend_margin, spend_pool = run(4_000_00)

        # The proxy improves
        assert spend_acq > quiet_acq
        # while the anchor it is supposed to serve declines
        assert spend_margin < quiet_margin
        # and the decline is material, not noise
        assert quiet_margin - spend_margin > 5.0
        # The pool is stable, so this is unit economics and not a churn collapse
        assert abs(spend_pool - quiet_pool) < 0.25 * quiet_pool

    def test_opex_always_produced(self, env, day):
        """Fixed opex is always incurred."""
        outcome = env.step("co", day)
        opex_entries = [e for e in outcome.entries if e.kind == EntryKind.OPEX]
        assert len(opex_entries) == 1
        assert opex_entries[0].amount_minor == env.params.opex_fixed_per_day_minor

    def test_cogs_proportional_to_revenue(self, env, day):
        outcome = env.step("co", day)
        if outcome.revenue_minor > 0:
            expected_cogs = int(outcome.revenue_minor * env.params.cogs_pct_of_revenue)
            assert outcome.cogs_minor == expected_cogs

    def test_cash_flow_entries_balance(self, env, day):
        """Cash in = revenue; cash out = cogs + opex."""
        spend = [LedgerEntry(
            company_id="co", kind=EntryKind.MARKETING_SPEND,
            department="marketing", actor="w",
            amount_minor=3_000_00, occurred_at=day.isoformat(),
        )]
        outcome = env.step("co", day, spend)
        cash_in = sum(
            e.amount_minor for e in outcome.entries if e.kind == EntryKind.CASH_IN
        )
        cash_out = sum(
            e.amount_minor for e in outcome.entries if e.kind == EntryKind.CASH_OUT
        )
        assert cash_in == outcome.revenue_minor
        assert cash_out == outcome.cogs_minor + outcome.opex_minor

    def test_active_customers_never_negative(self):
        """Churn cannot exceed active customers."""
        from datetime import timedelta
        env = SimulatedEnvironment(seed=999)
        base = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        for d in range(100):
            dt = base + timedelta(days=d)
            env.step("co", dt)
            assert env.state.active_customers >= 0

    def test_summary_dict(self, env, day):
        outcome = env.step("co", day)
        s = outcome.summary
        assert "organic_acquired" in s
        assert "marketing_acquired" in s
        assert "churned" in s
        assert "entries" in s
        assert isinstance(s["entries"], int)
