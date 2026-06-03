from __future__ import annotations

from src.utils import ARTIFACTS_DIR, write_json

TOOLS = [
    {"name": "get_case_profile", "description": "Return normalized case fields from common case schema.", "input_schema": {"case_id": "string"}},
    {"name": "score_payment_risk", "description": "Return rule-prior, model, and residual-corrected risk scores.", "input_schema": {"case_id": "string"}},
    {"name": "retrieve_policy_evidence", "description": "Retrieve policy evidence for payment investigation.", "input_schema": {"query": "string", "top_k": "integer"}},
    {"name": "check_source_conflict", "description": "Detect conflicting evidence documents.", "input_schema": {"doc_ids": "array"}},
    {"name": "create_human_review_ticket", "description": "Create a review ticket when risk, weak evidence, or permission gate requires review.", "input_schema": {"case_id": "string", "reason": "string"}},
    {"name": "write_audit_log", "description": "Write auditable decision trace.", "input_schema": {"case_id": "string", "decision": "string"}},
]

RESOURCES = [
    {"name": "policy_docs", "description": "Synthetic payment policy evidence documents."},
    {"name": "risk_taxonomy", "description": "Risk taxonomy for payment exception and complaint triage."},
    {"name": "model_card", "description": "Generated model card artifact."},
    {"name": "release_gate_config", "description": "PASS/REVIEW/BLOCK release gate thresholds."},
]

PROMPTS = [
    {"name": "payment_investigation_summary", "description": "Grounded summary template for payment investigation."},
    {"name": "compliance_review_note", "description": "Human-review note template for compliance review."},
    {"name": "evidence_sufficiency_check", "description": "Template for checking missing evidence slots."},
]


def export_mcp_artifacts() -> None:
    base = ARTIFACTS_DIR / "mcp"
    write_json(base / "tools.json", TOOLS)
    write_json(base / "resources.json", RESOURCES)
    write_json(base / "prompts.json", PROMPTS)


if __name__ == "__main__":
    export_mcp_artifacts()
