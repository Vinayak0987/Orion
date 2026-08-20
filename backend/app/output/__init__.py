"""F42-F46 - output layer: JSON package, HTML report, PDF, section access."""

from app.output.html import render_html, render_state_to_html
from app.output.package import (
    BusinessPackage,
    GenerationMetadata,
    build_metadata,
    build_package,
    business_name_for,
)
from app.output.pdf import PdfUnavailable, available_backend, pdf_health, render_pdf
from app.output.sections import (
    SECTION_ORDER,
    SECTIONS,
    SECTIONS_BY_KEY,
    SectionSpec,
    describe_sections,
    section_payload,
    sections_for,
)

__all__ = [
    "SECTIONS",
    "SECTIONS_BY_KEY",
    "SECTION_ORDER",
    "BusinessPackage",
    "GenerationMetadata",
    "PdfUnavailable",
    "SectionSpec",
    "available_backend",
    "build_metadata",
    "build_package",
    "business_name_for",
    "describe_sections",
    "pdf_health",
    "render_html",
    "render_pdf",
    "render_state_to_html",
    "section_payload",
    "sections_for",
]
