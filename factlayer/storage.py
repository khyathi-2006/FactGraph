"""SQLite storage for documents, facts, evidence and relationships."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import DATABASE_PATH
from .models import DocumentRecord, Evidence, RelationKind, Relationship, StoredFact

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    title TEXT,
    publisher TEXT,
    page_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    status_detail TEXT,
    low_yield_pages TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
    document_id TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    section TEXT,
    char_count INTEGER NOT NULL,
    table_count INTEGER NOT NULL,
    is_low_yield INTEGER NOT NULL,
    low_yield_reason TEXT,
    text TEXT NOT NULL,
    PRIMARY KEY (document_id, page_number),
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    subject TEXT NOT NULL,
    subject_normalized TEXT NOT NULL,
    predicate TEXT NOT NULL,
    value TEXT,
    value_numeric REAL,
    unit TEXT,
    unit_normalized TEXT,
    value_normalized REAL,
    value_normalized_unit TEXT,
    value_kind TEXT NOT NULL,
    scope TEXT,
    scope_normalized TEXT,
    period_label TEXT,
    period_start TEXT,
    period_end TEXT,
    reporting_status TEXT,
    confidence REAL NOT NULL,
    ambiguity_note TEXT,
    evidence_id TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    fact_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    section TEXT,
    quote TEXT NOT NULL,
    bbox TEXT,
    quote_verified_in_page_text INTEGER NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    fact_a TEXT NOT NULL,
    fact_b TEXT NOT NULL,
    relation TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    confidence REAL NOT NULL,
    candidate_similarity REAL NOT NULL,
    UNIQUE (fact_a, fact_b)
);

CREATE TABLE IF NOT EXISTS pipeline_issues (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT,
    stage TEXT NOT NULL,
    page INTEGER,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_facts_document ON facts(document_id);
CREATE INDEX IF NOT EXISTS idx_facts_predicate ON facts(predicate);
CREATE INDEX IF NOT EXISTS idx_evidence_fact ON evidence(fact_id);
CREATE INDEX IF NOT EXISTS idx_relationships_relation ON relationships(relation);
"""


def connect(database_path: Path | None = None) -> sqlite3.Connection:
    path = Path(database_path or DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def insert_document(
    connection: sqlite3.Connection,
    *,
    document_id: str,
    filename: str,
    title: str | None,
    publisher: str | None,
    page_count: int,
    status: str,
) -> None:
    connection.execute(
        "INSERT INTO documents (document_id, filename, title, publisher, page_count, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (document_id, filename, title, publisher, page_count, status, _now()),
    )
    connection.commit()


def update_document_status(
    connection: sqlite3.Connection,
    document_id: str,
    status: str,
    detail: str | None = None,
    low_yield_pages: list[int] | None = None,
) -> None:
    if low_yield_pages is None:
        connection.execute(
            "UPDATE documents SET status = ?, status_detail = ? WHERE document_id = ?",
            (status, detail, document_id),
        )
    else:
        connection.execute(
            "UPDATE documents SET status = ?, status_detail = ?, low_yield_pages = ? WHERE document_id = ?",
            (status, detail, json.dumps(low_yield_pages), document_id),
        )
    connection.commit()


def insert_pages(connection: sqlite3.Connection, document_id: str, pages) -> None:
    connection.executemany(
        "INSERT OR REPLACE INTO pages (document_id, page_number, section, char_count, table_count,"
        " is_low_yield, low_yield_reason, text) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                document_id,
                page.page_number,
                page.section,
                page.char_count,
                page.table_count,
                int(page.is_low_yield),
                page.low_yield_reason,
                page.text,
            )
            for page in pages
        ],
    )
    connection.commit()


def insert_fact_with_evidence(
    connection: sqlite3.Connection, fact: StoredFact, evidence: Evidence
) -> None:
    connection.execute(
        "INSERT INTO facts (fact_id, document_id, statement, subject, subject_normalized, predicate,"
        " value, value_numeric, unit, unit_normalized, value_normalized, value_normalized_unit,"
        " value_kind, scope, scope_normalized, period_label, period_start, period_end,"
        " reporting_status, confidence, ambiguity_note, evidence_id)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            fact.fact_id,
            fact.document_id,
            fact.statement,
            fact.subject,
            fact.subject_normalized,
            fact.predicate,
            fact.value,
            fact.value_numeric,
            fact.unit,
            fact.unit_normalized,
            fact.value_normalized,
            fact.value_normalized_unit,
            fact.value_kind,
            fact.scope,
            fact.scope_normalized,
            fact.period_label,
            fact.period_start,
            fact.period_end,
            fact.reporting_status,
            fact.confidence,
            fact.ambiguity_note,
            fact.evidence_id,
        ),
    )
    connection.execute(
        "INSERT INTO evidence (evidence_id, document_id, fact_id, page, section, quote, bbox,"
        " quote_verified_in_page_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            evidence.evidence_id,
            evidence.document_id,
            evidence.fact_id,
            evidence.page,
            evidence.section,
            evidence.quote,
            json.dumps(evidence.bbox) if evidence.bbox else None,
            int(evidence.quote_verified_in_page_text),
        ),
    )
    connection.commit()


def insert_relationship(connection: sqlite3.Connection, relationship: Relationship) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO relationships (relationship_id, fact_a, fact_b, relation, reasoning,"
        " confidence, candidate_similarity) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            relationship.relationship_id,
            relationship.fact_a,
            relationship.fact_b,
            relationship.relation.value,
            relationship.reasoning,
            relationship.confidence,
            relationship.candidate_similarity,
        ),
    )
    connection.commit()


def record_issue(
    connection: sqlite3.Connection,
    *,
    document_id: str | None,
    stage: str,
    detail: str,
    page: int | None = None,
) -> None:
    connection.execute(
        "INSERT INTO pipeline_issues (document_id, stage, page, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (document_id, stage, page, detail, _now()),
    )
    connection.commit()


def _row_to_stored_fact(row: sqlite3.Row) -> StoredFact:
    return StoredFact(**{key: row[key] for key in row.keys() if key in StoredFact.model_fields})


def list_documents(connection: sqlite3.Connection) -> list[DocumentRecord]:
    rows = connection.execute(
        "SELECT d.*, (SELECT COUNT(*) FROM facts f WHERE f.document_id = d.document_id) AS fact_count"
        " FROM documents d ORDER BY d.created_at"
    ).fetchall()
    return [
        DocumentRecord(
            document_id=row["document_id"],
            filename=row["filename"],
            title=row["title"],
            publisher=row["publisher"],
            page_count=row["page_count"],
            status=row["status"],
            status_detail=row["status_detail"],
            fact_count=row["fact_count"],
            low_yield_pages=json.loads(row["low_yield_pages"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def list_facts(
    connection: sqlite3.Connection,
    document_id: str | None = None,
    predicate: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[StoredFact]:
    query = "SELECT * FROM facts"
    clauses: list[str] = []
    params: list[object] = []
    if document_id:
        clauses.append("document_id = ?")
        params.append(document_id)
    if predicate:
        clauses.append("predicate = ?")
        params.append(predicate)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY document_id, fact_id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return [_row_to_stored_fact(row) for row in connection.execute(query, params).fetchall()]


def get_fact(connection: sqlite3.Connection, fact_id: str) -> StoredFact | None:
    row = connection.execute("SELECT * FROM facts WHERE fact_id = ?", (fact_id,)).fetchone()
    return _row_to_stored_fact(row) if row else None


def get_evidence_for_fact(connection: sqlite3.Connection, fact_id: str) -> Evidence | None:
    row = connection.execute("SELECT * FROM evidence WHERE fact_id = ?", (fact_id,)).fetchone()
    if not row:
        return None
    return Evidence(
        evidence_id=row["evidence_id"],
        document_id=row["document_id"],
        fact_id=row["fact_id"],
        page=row["page"],
        section=row["section"],
        quote=row["quote"],
        bbox=json.loads(row["bbox"]) if row["bbox"] else None,
        quote_verified_in_page_text=bool(row["quote_verified_in_page_text"]),
    )


def list_relationships(
    connection: sqlite3.Connection,
    relation: RelationKind | None = None,
    include_unrelated: bool = False,
    limit: int = 500,
) -> list[Relationship]:
    query = "SELECT * FROM relationships"
    params: list[object] = []
    if relation:
        query += " WHERE relation = ?"
        params.append(relation.value)
    elif not include_unrelated:
        query += " WHERE relation != 'unrelated'"
    query += " ORDER BY confidence DESC LIMIT ?"
    params.append(limit)
    return [
        Relationship(
            relationship_id=row["relationship_id"],
            fact_a=row["fact_a"],
            fact_b=row["fact_b"],
            relation=RelationKind(row["relation"]),
            reasoning=row["reasoning"],
            confidence=row["confidence"],
            candidate_similarity=row["candidate_similarity"],
        )
        for row in connection.execute(query, params).fetchall()
    ]


def list_issues(connection: sqlite3.Connection, document_id: str | None = None) -> list[dict]:
    query = "SELECT * FROM pipeline_issues"
    params: list[object] = []
    if document_id:
        query += " WHERE document_id = ?"
        params.append(document_id)
    query += " ORDER BY issue_id DESC LIMIT 500"
    return [dict(row) for row in connection.execute(query, params).fetchall()]


def list_low_yield_pages(connection: sqlite3.Connection, document_id: str) -> list[dict]:
    rows = connection.execute(
        "SELECT page_number, low_yield_reason, char_count FROM pages"
        " WHERE document_id = ? AND is_low_yield = 1 ORDER BY page_number",
        (document_id,),
    ).fetchall()
    return [dict(row) for row in rows]
