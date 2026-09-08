"""LLM fact extraction with structured output, one call per chunk."""

from __future__ import annotations

import json

from .config import EXTRACTION_MODEL
from .llm import request_json_object
from .models import Chunk, ExtractedFact, Period

SYSTEM_PROMPT = """You extract checkable facts from one page of a PDF document.

Rules:
- State each fact exactly as the page supports it. Do not infer anything the page does not say.
- Do not merge two separate facts into one, and do not split one fact into parts.
- Do not convert units, currencies, scales or dates. Copy the value as printed.
- `quote` must be a verbatim span copied character-for-character from the page text given
  to you. Never paraphrase, never reflow numbers, never invent a quote.
- Extract numeric facts (amounts, growth rates, counts, ratios) and also non-numeric ones
  (dates, statuses, appointments, names, events, policy decisions) when they are specific.
- Skip boilerplate, page furniture, disclaimers, navigation text and generic marketing claims.
- `predicate` is a normalized snake_case fact type reused across documents, for example
  revenue_from_services, real_gdp_growth_rate, director_appointment_date, employee_count.
- `scope` records qualifiers that change what the number measures: consolidated, standalone,
  segment name, provisional, revised, estimate, projection, geography, methodology.
- If a value is ambiguous (unclear column, unlabelled table, unclear period, chart with no
  reliable label-to-value link), still report it but set confidence below 0.5 and explain in
  `ambiguity_note`.
- If the page contains no extractable fact, return an empty list.

Return JSON only: {"facts": [{"statement": str, "subject": str, "predicate": str,
"value": str|null, "unit": str|null, "scope": str|null,
"period": {"label": str|null, "start": str|null, "end": str|null},
"quote": str, "confidence": number between 0 and 1, "ambiguity_note": str|null}]}"""


def _build_user_prompt(chunk: Chunk, document_label: str) -> str:
    section = chunk.section or "unknown"
    return (
        f"Document: {document_label}\n"
        f"Page number: {chunk.page_number}\n"
        f"Section (best guess from headings): {section}\n\n"
        "Page text:\n"
        "-----\n"
        f"{chunk.text}\n"
        "-----\n\n"
        "Extract the facts this page supports, following the rules exactly."
    )


def _coerce_fact(raw: dict, chunk: Chunk) -> ExtractedFact | None:
    quote = (raw.get("quote") or "").strip()
    statement = (raw.get("statement") or "").strip()
    subject = (raw.get("subject") or "").strip()
    predicate = (raw.get("predicate") or "").strip()
    if not (quote and statement and subject and predicate):
        return None

    period_raw = raw.get("period") or {}
    if not isinstance(period_raw, dict):
        period_raw = {}

    confidence = raw.get("confidence", 0.5)
    try:
        confidence = min(max(float(confidence), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.5

    return ExtractedFact(
        statement=statement,
        subject=subject,
        predicate=predicate.lower().replace(" ", "_"),
        value=(str(raw["value"]).strip() if raw.get("value") is not None else None),
        unit=(str(raw["unit"]).strip() if raw.get("unit") else None),
        scope=(str(raw["scope"]).strip() if raw.get("scope") else None),
        period=Period(
            label=period_raw.get("label"),
            start=period_raw.get("start"),
            end=period_raw.get("end"),
        ),
        quote=quote,
        page=chunk.page_number,
        section=chunk.section,
        confidence=confidence,
        ambiguity_note=(raw.get("ambiguity_note") or None),
    )


def extract_facts_from_chunk(chunk: Chunk, document_label: str) -> list[ExtractedFact]:
    reply = request_json_object(
        model=EXTRACTION_MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(chunk, document_label),
    )
    raw_facts = reply.get("facts")
    if not isinstance(raw_facts, list):
        raise ValueError(f"extraction reply had no facts list: {json.dumps(reply)[:300]}")

    facts: list[ExtractedFact] = []
    for raw in raw_facts:
        if isinstance(raw, dict):
            fact = _coerce_fact(raw, chunk)
            if fact is not None:
                facts.append(fact)
    return facts
