"""LLM relationship classification, run only on candidate pairs."""

from __future__ import annotations

import uuid

from .config import CLASSIFICATION_MODEL
from .llm import request_json_object
from .matching import CandidatePair
from .models import Evidence, RelationKind, Relationship, StoredFact

SYSTEM_PROMPT = """You compare two facts extracted from two different documents and decide
how they relate.

Weigh all of these explicitly before deciding: subject identity, predicate meaning, the
values, units and scale, the time period, the scope (consolidated vs standalone, segment vs
total, geography), the methodology, the reporting status (provisional, advance estimate,
revised, final, projection), and how each document worded the claim.

Relations:
- "corroborates": both facts make the same claim about the same subject, predicate, period
  and scope, and the values agree once units and scale are accounted for. Different wording
  is fine.
- "contradicts": the facts are directly comparable (same subject, predicate, period, scope,
  units) but the values genuinely disagree, and no contextual difference explains it.
- "reconciled": the values look different at first, but a concrete contextual difference
  explains it - a different period or vintage, different scope, different units or scale,
  different methodology, or provisional versus revised versus final data. Name the difference.
- "unrelated": they are not really about the same measurement, so comparing values is
  meaningless.

`reasoning` must explain the actual comparison and the actual difference or agreement, with
the numbers involved. Never output a bare label or restate the relation name.

Return JSON only: {"relation": "corroborates"|"contradicts"|"reconciled"|"unrelated",
"reasoning": str, "confidence": number between 0 and 1}"""


def _describe(fact: StoredFact, evidence: Evidence, document_label: str) -> str:
    return (
        f"Document: {document_label}\n"
        f"Page: {evidence.page} | Section: {evidence.section or 'unknown'}\n"
        f"Statement: {fact.statement}\n"
        f"Subject: {fact.subject} | Predicate: {fact.predicate}\n"
        f"Value as printed: {fact.value or 'n/a'} | Unit as printed: {fact.unit or 'n/a'}\n"
        f"Normalized value: {fact.value_normalized} {fact.value_normalized_unit or ''}\n"
        f"Period: {fact.period_label or 'none'} ({fact.period_start or '?'} to {fact.period_end or '?'})\n"
        f"Scope: {fact.scope or 'none'} | Reporting status: {fact.reporting_status or 'unspecified'}\n"
        f"Extraction confidence: {fact.confidence}\n"
        f"Ambiguity flagged at extraction: {fact.ambiguity_note or 'none'}\n"
        f'Verbatim evidence quote: "{evidence.quote}"'
    )


def classify_pair(
    pair: CandidatePair,
    evidence_by_fact: dict[str, Evidence],
    document_labels: dict[str, str],
) -> Relationship:
    user_prompt = (
        "FACT A\n"
        f"{_describe(pair.fact_a, evidence_by_fact[pair.fact_a.fact_id], document_labels[pair.fact_a.document_id])}\n\n"
        "FACT B\n"
        f"{_describe(pair.fact_b, evidence_by_fact[pair.fact_b.fact_id], document_labels[pair.fact_b.document_id])}\n\n"
        "Classify the relationship between fact A and fact B."
    )

    reply = request_json_object(
        model=CLASSIFICATION_MODEL,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_output_tokens=1200,
    )

    relation_text = str(reply.get("relation", "")).strip().lower()
    if relation_text not in RelationKind.__members__:
        raise ValueError(f"classifier returned an unknown relation: {reply!r}")

    reasoning = str(reply.get("reasoning", "")).strip()
    if len(reasoning) < 20:
        raise ValueError(f"classifier returned reasoning that explains nothing: {reply!r}")

    confidence = reply.get("confidence", 0.5)
    try:
        confidence = min(max(float(confidence), 0.0), 1.0)
    except (TypeError, ValueError):
        confidence = 0.5

    return Relationship(
        relationship_id=f"rel_{uuid.uuid4().hex[:12]}",
        fact_a=pair.fact_a.fact_id,
        fact_b=pair.fact_b.fact_id,
        relation=RelationKind(relation_text),
        reasoning=reasoning,
        confidence=confidence,
        candidate_similarity=pair.similarity,
    )
