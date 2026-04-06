"""PDF parser for Phase A source gathering.

Uses pdfplumber to extract text and tables from digital-native PDFs
(FAO/IITA guides). No OCR needed. Each page becomes a PageSection.
Tables are extracted separately and attached to the section.
"""

from __future__ import annotations

import io
from pathlib import Path

import pdfplumber

from app.agent_farm.models import PageSection
from app.logger import Step, pipeline_logger as log

_MIN_PAGE_TEXT_LENGTH = 100  # skip cover pages, blank pages, etc.


def parse_pdf_bytes(
    pdf_bytes: bytes,
    source_url: str,
    source_name: str,
) -> list[PageSection]:
    """Extract PageSections from PDF bytes (one section per page)."""
    sections: list[PageSection] = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            log.log_step(Step.SYSTEM, "parse_pdf", details={
                "source": source_name, "pages": len(pdf.pages),
            })

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()

                if len(text) < _MIN_PAGE_TEXT_LENGTH:
                    continue

                # Extract tables on this page
                tables: list[list[list[str]]] = []
                try:
                    raw_tables = page.extract_tables() or []
                    for table in raw_tables:
                        cleaned = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in table
                        ]
                        tables.append(cleaned)
                except Exception:
                    pass  # table extraction can fail on complex layouts

                sections.append(PageSection(
                    source_url=source_url,
                    source_name=source_name,
                    heading=f"page_{page_num}",
                    content=text,
                    tables=tables,
                ))

    except Exception as exc:
        log.log_step(Step.SYSTEM, "parse_pdf_error", level="ERROR",
                     details={"source": source_name, "error": str(exc)})

    return sections


def parse_pdf_file(
    pdf_path: Path,
    source_name: str,
) -> list[PageSection]:
    """Extract PageSections from a local PDF file."""
    return parse_pdf_bytes(
        pdf_bytes=pdf_path.read_bytes(),
        source_url=str(pdf_path),
        source_name=source_name,
    )
