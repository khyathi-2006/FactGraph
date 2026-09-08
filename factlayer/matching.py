"""Cheap candidate matching, run before any LLM relationship call.

Only cross-document pairs are considered: the assignment's cases are all about
agreement or disagreement between documents, and same-document pairs are
overwhelmingly restatements that would dominate the LLM budget.
"""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import MAX_CANDIDATE_PAIRS_PER_FACT, MIN_CANDIDATE_SIMILARITY
from .models import StoredFact


@dataclass
class CandidatePair:
    fact_a: StoredFact
    fact_b: StoredFact
    similarity: float
    reason: str


def _comparison_text(fact: StoredFact) -> str:
    parts = [
        fact.predicate.replace("_", " "),
        fact.subject_normalized,
        fact.statement,
        fact.unit_normalized or "",
        fact.period_label or "",
        fact.scope_normalized or "",
    ]
    return " ".join(part for part in parts if part)


def _value_kinds_comparable(a: StoredFact, b: StoredFact) -> bool:
    if a.value_kind == b.value_kind:
        return True
    return {a.value_kind, b.value_kind} <= {"count", "currency"}


def _periods_overlap(a: StoredFact, b: StoredFact) -> bool:
    if not (a.period_label or b.period_label):
        return True
    if a.period_label == b.period_label:
        return True
    if not (a.period_start and a.period_end and b.period_start and b.period_end):
        return True
    return a.period_start <= b.period_end and b.period_start <= a.period_end


def find_candidate_pairs(
    facts: list[StoredFact],
    min_similarity: float = MIN_CANDIDATE_SIMILARITY,
    max_pairs_per_fact: int = MAX_CANDIDATE_PAIRS_PER_FACT,
) -> list[CandidatePair]:
    """Filter the O(n^2) space down with predicate/unit/period gates plus TF-IDF similarity."""

    if len(facts) < 2:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform([_comparison_text(fact) for fact in facts])
    similarity_matrix = cosine_similarity(matrix)

    pairs: dict[tuple[str, str], CandidatePair] = {}
    for index, fact in enumerate(facts):
        scored: list[tuple[float, int, str]] = []
        for other_index, other in enumerate(facts):
            if other_index == index or other.document_id == fact.document_id:
                continue
            if not _value_kinds_comparable(fact, other):
                continue
            if not _periods_overlap(fact, other):
                continue

            similarity = float(similarity_matrix[index, other_index])
            reason = "text similarity"
            if fact.predicate == other.predicate:
                similarity = max(similarity, 0.6)
                reason = "identical predicate"
            elif fact.subject_normalized == other.subject_normalized and similarity > 0.2:
                reason = "same subject, similar wording"

            if similarity >= min_similarity:
                scored.append((similarity, other_index, reason))

        scored.sort(reverse=True)
        for similarity, other_index, reason in scored[:max_pairs_per_fact]:
            other = facts[other_index]
            key = tuple(sorted((fact.fact_id, other.fact_id)))
            existing = pairs.get(key)
            if existing is None or similarity > existing.similarity:
                first, second = (fact, other) if fact.fact_id == key[0] else (other, fact)
                pairs[key] = CandidatePair(first, second, round(similarity, 4), reason)

    return sorted(pairs.values(), key=lambda pair: pair.similarity, reverse=True)
