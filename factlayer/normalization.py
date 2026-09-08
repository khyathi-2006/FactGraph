"""Normalization of values, units, scales, periods, entities and reporting status.

Original strings are always kept alongside the normalized fields, so a
normalization mistake never destroys what the document actually printed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ExtractedFact

NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")

# Multipliers to a base unit of one (for counts) or one currency unit.
SCALE_MULTIPLIERS: dict[str, float] = {
    "crore": 1e7,
    "crores": 1e7,
    "cr": 1e7,
    "lakh": 1e5,
    "lakhs": 1e5,
    "million": 1e6,
    "mn": 1e6,
    "billion": 1e9,
    "bn": 1e9,
    "trillion": 1e12,
    "thousand": 1e3,
}

CURRENCY_TOKENS: dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
}

PERCENT_TOKENS = {"%", "percent", "per cent", "percentage", "pct"}

STATUS_KEYWORDS: dict[str, str] = {
    "provisional": "provisional",
    "preliminary": "provisional",
    "advance estimate": "advance_estimate",
    "first advance": "advance_estimate",
    "second advance": "advance_estimate",
    "revised": "revised",
    "restated": "revised",
    "projection": "projection",
    "projected": "projection",
    "forecast": "projection",
    "estimate": "estimate",
    "estimated": "estimate",
    "actual": "final",
    "audited": "final",
    "final": "final",
}

BASIS_KEYWORDS: dict[str, str] = {
    "consolidated": "consolidated",
    "standalone": "standalone",
    "segment": "segment",
    "like-for-like": "like_for_like",
}

ENTITY_SUFFIXES = (
    "limited",
    "ltd",
    "ltd.",
    "private",
    "pvt",
    "inc",
    "inc.",
    "plc",
    "corporation",
    "company",
    "the",
)

FISCAL_YEAR_PATTERN = re.compile(
    r"(?:fy\s?|financial year\s?|fiscal year\s?)(\d{2,4})(?:\s?[-/]\s?(\d{2,4}))?", re.I
)
QUARTER_PATTERN = re.compile(r"\bq([1-4])\s?(?:fy)?\s?(\d{2,4})", re.I)
CALENDAR_YEAR_PATTERN = re.compile(r"\b(19|20)(\d{2})\b")


@dataclass
class NormalizedValue:
    numeric: float | None
    kind: str
    normalized_value: float | None
    normalized_unit: str | None
    unit_normalized: str | None


def _parse_number(text: str) -> float | None:
    match = NUMBER_PATTERN.search(text.replace("\u2212", "-"))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _find_scale(text: str) -> tuple[str | None, float]:
    lowered = text.lower()
    for token, multiplier in SCALE_MULTIPLIERS.items():
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            return token, multiplier
    return None, 1.0


def _find_currency(text: str) -> str | None:
    lowered = text.lower()
    for token, code in CURRENCY_TOKENS.items():
        if token in lowered:
            return code
    return None


def normalize_value(value: str | None, unit: str | None) -> NormalizedValue:
    """Convert a printed value into a comparable number plus a canonical unit."""

    combined = " ".join(part for part in (value, unit) if part)
    if not combined.strip():
        return NormalizedValue(None, "non_numeric", None, None, None)

    numeric = _parse_number(combined)
    if numeric is None:
        return NormalizedValue(None, "non_numeric", None, None, (unit or None))

    lowered = combined.lower()
    if any(token in lowered for token in PERCENT_TOKENS):
        return NormalizedValue(numeric, "percentage", numeric, "percent", "percent")

    scale_token, multiplier = _find_scale(combined)
    currency = _find_currency(combined)

    if currency:
        return NormalizedValue(
            numeric,
            "currency",
            numeric * multiplier,
            currency,
            f"{currency} {scale_token}".strip() if scale_token else currency,
        )

    if scale_token:
        return NormalizedValue(
            numeric, "count", numeric * multiplier, "unit", (unit or scale_token)
        )

    return NormalizedValue(numeric, "count", numeric, (unit or "unit"), (unit or None))


def normalize_entity(subject: str) -> str:
    cleaned = re.sub(r"[^\w\s&]", " ", subject.lower())
    tokens = [token for token in cleaned.split() if token and token not in ENTITY_SUFFIXES]
    return " ".join(tokens)


def normalize_period(label: str | None, start: str | None, end: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (canonical label, start, end) using fiscal-year and quarter conventions."""

    text = " ".join(part for part in (label, start, end) if part)
    if not text.strip():
        return None, start, end

    quarter = QUARTER_PATTERN.search(text)
    if quarter:
        year = quarter.group(2)
        year = f"20{year}" if len(year) == 2 else year
        return f"Q{quarter.group(1)} FY{year}", start, end

    fiscal = FISCAL_YEAR_PATTERN.search(text)
    if fiscal:
        first = fiscal.group(1)
        second = fiscal.group(2)
        end_year = second or first
        end_year = f"20{end_year}" if len(end_year) == 2 else end_year
        return f"FY{end_year}", start or f"{int(end_year) - 1}-04-01", end or f"{end_year}-03-31"

    calendar = CALENDAR_YEAR_PATTERN.search(text)
    if calendar:
        year = f"{calendar.group(1)}{calendar.group(2)}"
        return f"CY{year}", start or f"{year}-01-01", end or f"{year}-12-31"

    return label, start, end


def normalize_scope(scope: str | None, statement: str) -> tuple[str | None, str | None]:
    """Return (canonical scope, reporting status) from scope text and the statement."""

    haystack = f"{scope or ''} {statement}".lower()

    basis = next((canonical for keyword, canonical in BASIS_KEYWORDS.items() if keyword in haystack), None)
    status = next((canonical for keyword, canonical in STATUS_KEYWORDS.items() if keyword in haystack), None)

    parts = [part for part in (basis, (scope or "").strip().lower() or None) if part]
    canonical_scope = " | ".join(dict.fromkeys(parts)) or None
    return canonical_scope, status


def normalize_fact(fact: ExtractedFact) -> dict:
    value = normalize_value(fact.value, fact.unit)
    period_label, period_start, period_end = normalize_period(
        fact.period.label, fact.period.start, fact.period.end
    )
    scope_normalized, status = normalize_scope(fact.scope, fact.statement)

    return {
        "subject_normalized": normalize_entity(fact.subject),
        "value_numeric": value.numeric,
        "value_kind": value.kind,
        "value_normalized": value.normalized_value,
        "value_normalized_unit": value.normalized_unit,
        "unit_normalized": value.unit_normalized,
        "period_label": period_label,
        "period_start": period_start,
        "period_end": period_end,
        "scope_normalized": scope_normalized,
        "reporting_status": status,
    }
