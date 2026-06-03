from __future__ import annotations


def has_source_conflict(docs: list[dict]) -> bool:
    text = " ".join(d.get("content", "").lower() for d in docs)
    # Simple deterministic conflict proxy for testability.
    return "auto-clear" in text and "must not be auto-cleared" in text
