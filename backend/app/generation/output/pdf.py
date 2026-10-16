"""F44 - PDF export.

Two free backends, tried in order of output quality:

    weasyprint   Best CSS support. Needs native Pango/Cairo libraries, which are
                 installed in the backend Docker image but are awkward on a bare
                 Windows host (the import fails outright).
    xhtml2pdf    Pure Python, Apache 2.0, zero native dependencies. Supports a
                 CSS2 subset, which is why the report template avoids flexbox,
                 grid and web fonts - one template renders correctly in both.

If neither import succeeds, `PdfUnavailable` is raised and the caller falls back
to the HTML report, which prints to PDF from any browser. Nothing here costs
money and nothing requires a service account.
"""

from __future__ import annotations

import io
from typing import Callable

import structlog

log = structlog.get_logger(__name__)


class PdfUnavailable(RuntimeError):
    """No PDF backend could be loaded."""


def _render_with_weasyprint(html: str) -> bytes:
    from weasyprint import HTML  # noqa: PLC0415 - optional dependency

    return HTML(string=html).write_pdf()


def _render_with_xhtml2pdf(html: str) -> bytes:
    from xhtml2pdf import pisa  # noqa: PLC0415 - optional dependency

    buffer = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf reported {result.err} error(s)")
    return buffer.getvalue()


BACKENDS: tuple[tuple[str, Callable[[str], bytes]], ...] = (
    ("weasyprint", _render_with_weasyprint),
    ("xhtml2pdf", _render_with_xhtml2pdf),
)


def available_backend() -> str | None:
    """Name of the backend that would be used, or None."""
    for name, _ in BACKENDS:
        try:
            __import__(name)
        except Exception:  # noqa: BLE001 - a broken optional dep is just unavailable
            continue
        return name
    return None


def render_pdf(html: str) -> tuple[bytes, str]:
    """Convert a rendered HTML report to PDF bytes.

    Returns:
        (pdf_bytes, backend_name)

    Raises:
        PdfUnavailable: when no backend is importable or all of them fail.
    """
    failures: dict[str, str] = {}

    for name, renderer in BACKENDS:
        try:
            __import__(name)
        except Exception as exc:  # noqa: BLE001
            failures[name] = f"not importable: {str(exc)[:120]}"
            continue

        try:
            pdf = renderer(html)
        except Exception as exc:  # noqa: BLE001 - try the next backend
            failures[name] = f"render failed: {str(exc)[:160]}"
            log.warning("pdf.backend_failed", backend=name, error=str(exc)[:200])
            continue

        if not pdf.startswith(b"%PDF"):
            failures[name] = "output was not a PDF"
            continue

        log.info("pdf.rendered", backend=name, bytes=len(pdf))
        return pdf, name

    detail = "; ".join(f"{k}: {v}" for k, v in failures.items()) or "no backends registered"
    raise PdfUnavailable(
        f"No PDF backend available ({detail}). "
        f"Use the HTML report and print to PDF from a browser, or run the backend "
        f"in Docker where WeasyPrint's native libraries are installed."
    )


def pdf_health() -> dict:
    """Surfaced on /health so a missing backend is visible before a user tries it."""
    backend = available_backend()
    return {
        "available": backend is not None,
        "backend": backend,
        "fallback": "HTML report, print to PDF from browser",
    }
