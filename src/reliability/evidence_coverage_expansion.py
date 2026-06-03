from __future__ import annotations

REQUIRED_SLOTS = {"payment_status", "policy_rule", "customer_impact", "risk_reason", "required_action"}


def slots_from_docs(docs: list[dict]) -> set[str]:
    slots = set()
    for d in docs:
        slots.update(d.get("slots", []))
    return slots


def expand_evidence_coverage(initial_docs: list[dict], candidate_docs: list[dict], required_slots: set[str] | None = None) -> list[dict]:
    required_slots = required_slots or REQUIRED_SLOTS
    selected = list(initial_docs)
    covered = slots_from_docs(selected)
    seen = {d["doc_id"] for d in selected}
    for doc in candidate_docs:
        if doc["doc_id"] in seen:
            continue
        new_slots = set(doc.get("slots", [])) - covered
        if new_slots:
            selected.append(doc)
            covered.update(new_slots)
            seen.add(doc["doc_id"])
        if required_slots.issubset(covered):
            break
    return selected
