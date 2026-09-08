"""Chunking that never crosses a page boundary, so every fact keeps a real page number."""

from __future__ import annotations

from .config import CHUNK_OVERLAP_CHARS, MAX_CHUNK_CHARS
from .models import Chunk, ParsedDocument


def _split_page_text(text: str, max_chars: int, overlap: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            newline = text.rfind("\n", start + max_chars // 2, end)
            if newline != -1:
                end = newline
        pieces.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return pieces


def chunk_document(
    document: ParsedDocument,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in document.pages:
        if page.is_low_yield:
            continue
        for piece in _split_page_text(page.text, max_chars, overlap):
            if not piece.strip():
                continue
            chunks.append(
                Chunk(
                    chunk_index=len(chunks),
                    page_number=page.page_number,
                    section=page.section,
                    text=piece,
                )
            )
    return chunks
