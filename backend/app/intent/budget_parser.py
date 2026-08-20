"""F4 - Budget parsing and normalization.

Deterministic, LLM-free. Indian numbering conventions ("15L", "1.5 crore",
"15,00,000") are parsed by regex rather than handed to a model.

Why deterministic: the Financial Accuracy metric (F54) compares projected margins
against MSME benchmarks, and every projection is anchored to this number. If the
budget wobbled between providers or between runs, MAPE variance would no longer
be attributable to the agents - it would be intent-extraction noise. Regex makes
the number identical on every run, on every provider, forever.
"""

from __future__ import annotations

import re

from app.models.intent import Budget

# Indian lakh/crore notation plus international k/m. Ordered longest-first so
# "crore" wins over a bare "cr", and "lakhs" over "l".
_UNIT_ALTERNATION = (
    r"crores?|cr|lakhs?|lacs?|l|thousands?|k|millions?|mn|m"
)

# "₹15L", "Rs 1.5 crore", "15 lakhs", "INR 50k"
_AMOUNT_WITH_UNIT = re.compile(
    r"(?:₹|rs\.?|inr)?\s*"
    r"(\d+(?:,\d{2,3})*(?:\.\d+)?)\s*"
    rf"({_UNIT_ALTERNATION})\b",
    re.IGNORECASE,
)

# Currency-prefixed plain number: "₹50,000", "Rs 1500000"
_AMOUNT_CURRENCY_PREFIXED = re.compile(
    r"(?:₹|rs\.?|inr)\s*(\d+(?:,\d{2,3})*)",
    re.IGNORECASE,
)

# Budget-keyword context: "budget of 500000", "capital 250000"
_AMOUNT_IN_BUDGET_CONTEXT = re.compile(
    r"(?:budget|capital|investment|invest|funds?|funding)"
    r"[^\d]{0,20}(\d{4,}(?:,\d{2,3})*)",
    re.IGNORECASE,
)


def _unit_multiplier(unit: str) -> int:
    u = unit.lower().rstrip(".")
    if u.startswith("cr"):
        return 10_000_000
    if u.startswith("lakh") or u.startswith("lac") or u == "l":
        return 100_000
    if u.startswith("million") or u in ("m", "mn"):
        return 1_000_000
    if u == "k" or u.startswith("thousand"):
        return 1_000
    return 1


def _to_int(number_text: str) -> int:
    return int(round(float(number_text.replace(",", ""))))


def _scaled(number_text: str, multiplier: int) -> int:
    """Multiply BEFORE rounding.

    Rounding first would turn "1.5 crore" into 2 crore and "12.5 lakh" into
    13 lakh - a 33% and 4% error respectively, straight into the budget that
    every financial projection is anchored to.
    """
    return int(round(float(number_text.replace(",", "")) * multiplier))


def parse_budget(text: str) -> Budget:
    """Extract an INR budget from free text.

    Returns an unspecified Budget (amount 0, specified False) when no budget is
    present, so downstream agents can distinguish "no budget given" from
    "budget of zero".
    """
    if not text or not text.strip():
        return Budget()

    match = _AMOUNT_WITH_UNIT.search(text)
    if match:
        amount = _scaled(match.group(1), _unit_multiplier(match.group(2)))
        return Budget(amount=amount, specified=True, raw=match.group(0).strip())

    match = _AMOUNT_CURRENCY_PREFIXED.search(text)
    if match:
        return Budget(
            amount=_to_int(match.group(1)), specified=True, raw=match.group(0).strip()
        )

    match = _AMOUNT_IN_BUDGET_CONTEXT.search(text)
    if match:
        return Budget(
            amount=_to_int(match.group(1)), specified=True, raw=match.group(0).strip()
        )

    return Budget()
