from __future__ import annotations

from src.security.pii_redaction import redact_pii


def make_grounded_summary(case: dict, evidence_docs: list[dict], final_action: str) -> str:
    cites = ", ".join([d.get("doc_id", "UNKNOWN") for d in evidence_docs[:4]])
    status = case.get("payment_status", "NA")
    exception = case.get("exception_type", "NA")
    return (
        f"Case {case.get('case_id')} has payment status {status} and exception type {exception}. "
        f"Based on evidence documents {cites}, the recommended route is {final_action}. "
        "If required evidence slots are missing or source conflict is detected, human review is required."
    )
