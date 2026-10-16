"""F43 - HTML report rendering.

Jinja2 with autoescaping. The template is self-contained: inline CSS, no external
stylesheets and no web fonts, so a saved report opens correctly offline and the
PDF engine needs no network access either.

The report is styled in the palette the Branding department recommended (F27),
which is why brand colours are resolved here rather than hard-coded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.generation.models.state import Department, SharedBusinessState
from app.generation.output.package import BusinessPackage, build_package
from app.generation.output.sections import SECTIONS_BY_KEY

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "report.html.j2"

# Fallbacks when the branding agent produced no palette.
DEFAULT_PRIMARY = "#1F3A5F"
DEFAULT_ACCENT = "#C2703D"


def _inr(value: object) -> str:
    """Indian-grouped currency, or an em dash when absent."""
    if value is None or value == "":
        return "—"
    try:
        amount = int(round(float(value)))
    except (TypeError, ValueError):
        return str(value)

    negative = amount < 0
    digits = str(abs(amount))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        formatted = ",".join(groups) + "," + tail
    else:
        formatted = digits
    return ("-" if negative else "") + formatted


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["inr"] = _inr
    return env


def _duration_display(milliseconds: int | None) -> str:
    if not milliseconds:
        return "—"
    seconds = milliseconds / 1000.0
    return f"{seconds:.1f} s" if seconds < 60 else f"{seconds / 60:.1f} min"


def _brand_colours(package: BusinessPackage) -> tuple[str, str]:
    palette = (package.sections.get("brand") or {}).get("color_palette") or {}
    primary = palette.get("primary_hex") or DEFAULT_PRIMARY
    accent = palette.get("accent_hex") or palette.get("secondary_hex") or DEFAULT_ACCENT
    return primary, accent


def _kpis(package: BusinessPackage) -> list[dict[str, str]]:
    """The four headline numbers, shown on the cover."""
    costs = package.sections.get("costs") or {}
    projections = package.sections.get("projections") or {}
    revenue = package.sections.get("revenue") or {}

    entries: list[dict[str, str]] = []
    if costs.get("total_setup_cost_inr") is not None:
        entries.append({"label": "Setup cost", "value": f"₹{_inr(costs['total_setup_cost_inr'])}"})
    if revenue.get("projected_revenue_y1_inr") is not None:
        entries.append(
            {"label": "Year-1 revenue", "value": f"₹{_inr(revenue['projected_revenue_y1_inr'])}"}
        )
    if projections.get("net_margin_pct") is not None:
        entries.append({"label": "Net margin", "value": f"{projections['net_margin_pct']}%"})
    if projections.get("break_even_month"):
        entries.append({"label": "Break-even", "value": f"Month {projections['break_even_month']}"})
    return entries[:4]


def render_html(
    package: BusinessPackage,
    contradictions: list[str] | None = None,
) -> str:
    """Render a business package to a standalone HTML document."""
    primary, accent = _brand_colours(package)
    brand = package.sections.get("brand_voice") or {}
    taglines = brand.get("taglines") or []
    intent = package.intent or {}
    location = (intent.get("location") or {}).get("area") or ""
    city = (intent.get("location") or {}).get("city") or ""
    location_display = ", ".join(p for p in (location, city) if p and p != "unspecified") or city

    budget = intent.get("budget") or {}
    budget_display = ""
    if budget.get("specified") and budget.get("amount"):
        budget_display = f"₹{_inr(budget['amount'])}"

    generated = package.metadata.generated_at
    try:
        generated_on = datetime.fromisoformat(generated).strftime("%d %B %Y, %H:%M UTC")
    except (TypeError, ValueError):
        generated_on = datetime.now(UTC).strftime("%d %B %Y")

    template = _environment().get_template(TEMPLATE_NAME)
    return template.render(
        package=package,
        meta=package.metadata,
        intent=intent,
        location=location_display,
        budget_display=budget_display,
        tagline=taglines[0] if taglines else "",
        primary=primary,
        accent=accent,
        kpis=_kpis(package),
        contradictions=[
            w for w in (contradictions or package.metadata.validation_warnings)
            if not w.startswith("missing:")
        ],
        competitor_source=package.metadata.grounding.get("competitor_source", "llm_inferred"),
        present_sections=[SECTIONS_BY_KEY[key] for key in package.present_sections],
        generated_on=generated_on,
        duration_display=_duration_display(package.metadata.total_duration_ms),
    )


def render_state_to_html(state: SharedBusinessState) -> str:
    """Convenience path: state -> package -> HTML."""
    from app.generation.orchestrator.completeness import detect_contradictions

    package = build_package(state)
    return render_html(package, detect_contradictions(state, state.get("intent")))


def department_of(section_key: str) -> Department | None:
    spec = SECTIONS_BY_KEY.get(section_key)
    return spec.department if spec else None
