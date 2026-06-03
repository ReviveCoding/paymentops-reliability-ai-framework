from __future__ import annotations


def rerank_by_slot_coverage(query: str, docs: list[dict]) -> list[dict]:
    # Prioritize evidence with more operational slots and original retrieval score.
    return sorted(docs, key=lambda d: (len(d.get("slots", [])), d.get("score", 0.0)), reverse=True)
