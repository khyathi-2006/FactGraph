"""Page-aware PDF parsing using PyMuPDF only.

Text is extracted page by page so every downstream fact remains traceable to its
source page. Pages with very little machine-readable text are retained and
flagged instead of being silently discarded.
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from .config import LOW_YIELD_PAGE_CHAR_THRESHOLD
from .models import ParsedDocument, ParsedPage

HEADING_PATTERN = re.compile(
    r"^(?:[A-Z][A-Z0-9 &,\-.'/()]{6,80}|(?:\d+(?:\.\d+)*\s+)[A-Z][\w \-,&/()]{4,80})$"
)


def _guess_section(text: str, previous_section: str | None) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if 8 <= len(stripped) <= 90 and HEADING_PATTERN.match(stripped):
            return stripped.title() if stripped.isupper() else stripped
    return previous_section


def parse_pdf(pdf_path: Path) -> ParsedDocument:
    """Extract a PDF page by page using PyMuPDF only."""

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {pdf_path.name}")

    document = pymupdf.open(pdf_path)
    pages: list[ParsedPage] = []
    current_section: str | None = None

    try:
        for index, page in enumerate(document, start=1):
            raw_text = page.get_text("text").strip()
            current_section = _guess_section(raw_text, current_section)
            char_count = len(raw_text)
            is_low_yield = char_count < LOW_YIELD_PAGE_CHAR_THRESHOLD
            reason = None

            if is_low_yield:
                has_images = bool(page.get_images(full=True))
                if has_images and char_count == 0:
                    reason = "page has images but no machine-readable text (likely image-only)"
                elif has_images:
                    reason = "page has images but very little machine-readable text"
                elif char_count == 0:
                    reason = "page contains no extractable text (blank or scanned page)"
                else:
                    reason = "page contains very little machine-readable text"

            pages.append(
                ParsedPage(
                    page_number=index,
                    text=raw_text,
                    section=current_section,
                    char_count=char_count,
                    table_count=0,
                    is_low_yield=is_low_yield,
                    low_yield_reason=reason,
                )
            )

        metadata_title = (document.metadata or {}).get("title") or None
        page_count = document.page_count
    finally:
        document.close()

    return ParsedDocument(
        filename=pdf_path.name,
        title=metadata_title,
        page_count=page_count,
        pages=pages,
    )
