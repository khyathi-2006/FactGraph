from __future__ import annotations

import uuid
from pathlib import Path

from .classification import classify_pair
from .chunking import chunk_document
from .extraction import extract_facts_from_chunk
from .matching import find_candidate_pairs
from .models import Evidence, StoredFact
from .normalization import normalize_fact
from .pdf_parsing import parse_pdf
from .storage import (
    get_evidence_for_fact,
    initialize_schema,
    insert_document,
    insert_fact_with_evidence,
    insert_pages,
    insert_relationship,
    list_documents,
    list_facts,
    record_issue,
    update_document_status,
)


def ingest_pdf(path: Path, conn):
    """Ingest one PDF and fail visibly when extraction fails for every chunk."""
    path = Path(path)
    parsed = parse_pdf(path)

    if parsed.page_count <= 0:
        raise RuntimeError(f"PDF parsing produced zero pages: {path.name}")

    document_id = "doc_" + uuid.uuid4().hex[:12]
    insert_document(
        conn,
        document_id=document_id,
        filename=path.name,
        title=parsed.title,
        publisher=None,
        page_count=parsed.page_count,
        status="processing",
    )
    insert_pages(conn, document_id, parsed.pages)

    low_yield_pages = [p.page_number for p in parsed.pages if p.is_low_yield]
    stored_facts: list[StoredFact] = []
    evidence_map: dict[str, Evidence] = {}
    extraction_errors: list[str] = []
    chunks_processed = 0

    for chunk in chunk_document(parsed):
        chunks_processed += 1
        try:
            extracted_facts = extract_facts_from_chunk(chunk, path.name)
        except Exception as error:
            message = str(error)
            extraction_errors.append(f"Page {chunk.page_number}: {message}")
            record_issue(
                conn,
                document_id=document_id,
                stage="extraction",
                page=chunk.page_number,
                detail=message,
            )
            continue

        for raw_fact in extracted_facts:
            page = next((p for p in parsed.pages if p.page_number == raw_fact.page), None)
            verified = bool(page and raw_fact.quote.strip() and raw_fact.quote.strip() in page.text)
            if not verified:
                record_issue(
                    conn,
                    document_id=document_id,
                    stage="evidence",
                    page=raw_fact.page,
                    detail="Quote not found verbatim in source page; fact skipped",
                )
                continue

            normalized_data = normalize_fact(raw_fact)
            fact_id = "fact_" + uuid.uuid4().hex[:12]
            evidence_id = "ev_" + uuid.uuid4().hex[:12]
            stored_fact = StoredFact(
                fact_id=fact_id,
                document_id=document_id,
                evidence_id=evidence_id,

                # Original extracted fields required by StoredFact
                statement=raw_fact.statement,
                subject=raw_fact.subject,
                predicate=raw_fact.predicate,
                value=raw_fact.value,
                unit=raw_fact.unit,
                scope=raw_fact.scope,
                confidence=raw_fact.confidence,
                ambiguity_note=raw_fact.ambiguity_note,

                # Normalized fields returned by normalize_fact()
                **normalized_data,
            )
            evidence = Evidence(
                evidence_id=evidence_id,
                document_id=document_id,
                fact_id=fact_id,
                page=raw_fact.page,
                section=raw_fact.section,
                quote=raw_fact.quote,
                quote_verified_in_page_text=True,
            )
            insert_fact_with_evidence(conn, stored_fact, evidence)
            stored_facts.append(stored_fact)
            evidence_map[fact_id] = evidence

    if extraction_errors and not stored_facts:
        detail = (
            "Extraction failed for all chunks. "
            f"First error: {extraction_errors[0]}"
        )
        update_document_status(
            conn,
            document_id,
            "failed",
            detail=detail,
            low_yield_pages=low_yield_pages,
        )
        raise RuntimeError(detail)

    if extraction_errors:
        update_document_status(
            conn,
            document_id,
            "partial",
            detail=(
                f"Extracted {len(stored_facts)} facts; "
                f"{len(extraction_errors)} chunk(s) failed out of {chunks_processed}."
            ),
            low_yield_pages=low_yield_pages,
        )
    else:
        update_document_status(
            conn,
            document_id,
            "completed",
            detail=(
                f"Processed {chunks_processed} chunks and extracted "
                f"{len(stored_facts)} facts."
            ),
            low_yield_pages=low_yield_pages,
        )

    return document_id, stored_facts, evidence_map


def classify_all(conn):
    facts = list_facts(conn)
    if len(facts) < 2:
        return []

    pairs = find_candidate_pairs(facts)
    labels = {d.document_id: d.filename for d in list_documents(conn)}
    evidence_by_fact = {
        fact.fact_id: get_evidence_for_fact(conn, fact.fact_id)
        for fact in facts
    }
    results = []

    for pair in pairs:
        if not evidence_by_fact.get(pair.fact_a.fact_id) or not evidence_by_fact.get(pair.fact_b.fact_id):
            continue
        try:
            relationship = classify_pair(pair, evidence_by_fact, labels)
            insert_relationship(conn, relationship)
            results.append(relationship)
        except Exception as error:
            record_issue(
                conn,
                document_id=None,
                stage="classification",
                detail=str(error),
            )
    return results


def ingest_paths(paths, conn, classify=True):
    initialize_schema(conn)
    document_ids = []
    failures = []

    for path in paths:
        try:
            document_id, _, _ = ingest_pdf(Path(path), conn)
            document_ids.append(document_id)
        except Exception as error:
            failures.append(f"{Path(path).name}: {error}")

    relationships = classify_all(conn) if classify and document_ids else []

    if failures:
        print("\nIngestion failures:")
        for failure in failures:
            print(f"- {failure}")

    return document_ids, relationships
