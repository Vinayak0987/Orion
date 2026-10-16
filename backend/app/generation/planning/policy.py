"""Execution policy - one frozen, fail-closed limits object.

Adapted from AgentArea's `EffectivePolicy`, collapsed to Orion's single scope
(no workspace/agent/user merge - there is one operator). The discipline that is
worth keeping is the important part: the policy is resolved once, immutable, and
`runtime_contract()` FAILS CLOSED - a missing limit is rejected, never silently
defaulted. This mirrors the planning layer's existing "no silent fallbacks"
stance (`service._blockers`).

Free-tier reality: there is no dollar budget. The run budget is expressed as a
token ceiling (a proxy for the Gemini daily limit) plus a per-node upper bound
the report already computed. Defaults are offline-appropriate, not AgentArea's
production ceilings.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from app.generation.config import settings


class PolicyError(RuntimeError):
    """A policy was used with a missing or invalid limit."""


@dataclass(frozen=True)
class ExecutionPolicy:
    """Immutable run limits. Every field must be present and positive."""

    max_tokens: int  # run-wide completion-token ceiling (upper bound)
    max_repair_rounds: int  # hard cap on any per-node validate-repair loop
    node_timeout_s: float  # per-node wall-clock budget

    def runtime_contract(self) -> "ExecutionPolicy":
        """Return self iff every limit is present and > 0, else fail closed.

        Named after AgentArea's contract check: runtime code has no numeric
        fallback, so an incomplete policy stops the run rather than guessing.
        """
        missing = [f.name for f in fields(self) if getattr(self, f.name) is None]
        if missing:
            raise PolicyError(f"execution policy missing limit(s): {sorted(missing)}")
        nonpositive = [
            f.name for f in fields(self) if (value := getattr(self, f.name)) <= 0
        ]
        if nonpositive:
            raise PolicyError(
                f"execution policy limit(s) must be positive: {sorted(nonpositive)}"
            )
        return self

    def within_token_budget(self, tokens_used: int) -> bool:
        """True while spend is under the ceiling (deny at 100%)."""
        return tokens_used < self.max_tokens

    def token_warn_threshold(self) -> int:
        """80% of the ceiling - the warn line (AgentArea's guard pattern)."""
        return int(self.max_tokens * 0.8)


def default_policy() -> ExecutionPolicy:
    """The policy a run uses when the caller supplies none.

    The token ceiling tracks the configured Gemini daily limit so the planner
    never plans a run larger than the provider will serve; the other limits are
    conservative offline defaults. `runtime_contract()` is asserted here so a
    misconfigured settings object fails at construction, not mid-run.
    """
    return ExecutionPolicy(
        max_tokens=int(settings.gemini_daily_token_limit),
        max_repair_rounds=1,
        node_timeout_s=float(settings.generation_timeout_seconds),
    ).runtime_contract()
