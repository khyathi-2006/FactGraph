"""Explicit data models for documents, facts, evidence and relationships."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Period(BaseModel):
    """Time span a fact refers to. All parts are optional: many facts have none."""

    label: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class ParsedPage(BaseModel):
    page_number: int
    text: str
    section: Optional[str] = None
    char_count: int
    table_count: int = 0
    is_low_yield: bool = False
    low_yield_reason: Optional[str] = None


class ParsedDocument(BaseModel):
    filename: str
    title: Optional[str] = None
    page_count: int
    pages: list[ParsedPage]


class Chunk(BaseModel):
    chunk_index: int
    page_number: int
    section: Optional[str]
    text: str


class ExtractedFact(BaseModel):
    """A single fact as returned by the extraction model, before normalization."""

    statement: str
    subject: str
    predicate: str
    value: Optional[str] = None
    unit: Optional[str] = None
    scope: Optional[str] = None
    period: Period = Field(default_factory=Period)
    quote: str
    page: int
    section: Optional[str] = None
    confidence: float = 0.5
    ambiguity_note: Optional[str] = None


class StoredFact(BaseModel):
    fact_id: str
    document_id: str
    statement: str
    subject: str
    subject_normalized: str
    predicate: str
    value: Optional[str]
    value_numeric: Optional[float]
    unit: Optional[str]
    unit_normalized: Optional[str]
    value_normalized: Optional[float]
    value_normalized_unit: Optional[str]
    value_kind: str
    scope: Optional[str]
    scope_normalized: Optional[str]
    period_label: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    reporting_status: Optional[str]
    confidence: float
    ambiguity_note: Optional[str]
    evidence_id: str


class Evidence(BaseModel):
    evidence_id: str
    document_id: str
    fact_id: str
    page: int
    section: Optional[str]
    quote: str
    bbox: Optional[list[float]] = None
    quote_verified_in_page_text: bool = False


class RelationKind(str, Enum):
    corroborates = "corroborates"
    contradicts = "contradicts"
    reconciled = "reconciled"
    unrelated = "unrelated"


class Relationship(BaseModel):
    relationship_id: str
    fact_a: str
    fact_b: str
    relation: RelationKind
    reasoning: str
    confidence: float
    candidate_similarity: float


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    title: Optional[str]
    publisher: Optional[str]
    page_count: int
    status: str
    status_detail: Optional[str] = None
    fact_count: int = 0
    low_yield_pages: list[int] = Field(default_factory=list)
    created_at: str
