from __future__ import annotations


def deflate_unsupported_evidence(docs: list[dict]) -> list[dict]:
    """ABC-inspired deflation: remove duplicate, empty, or weak candidate evidence."""
    out = []
    seen = set()
    for d in docs:
        doc_id = d.get("doc_id")
        content = d.get("content", "")
        if not doc_id or doc_id in seen:
            continue
        if len(content.strip()) < 20:
            continue
        score = float(d.get("score", 1.0))
        if score < 0.0:
            continue
        out.append(d)
        seen.add(doc_id)
    return out


def correct_action(proposed_action: str, risk_score: float, evidence_slots: set[str], source_conflict: bool) -> str:
    """Inflate possible actions, then deflate unsafe or unsupported decisions."""
    required_min = {"policy_rule", "required_action"}
    if source_conflict:
        return "human_review_required"
    if not required_min.issubset(evidence_slots):
        return "human_review_required"
    if proposed_action == "auto_resolve" and risk_score >= 0.50:
        return "analyst_review"
    if proposed_action in {"block_payment", "compliance_escalation"} and risk_score < 0.65:
        return "analyst_review"
    return proposed_action
