import pandas as pd
from src.reliability.case_health_timestep import add_case_health_timestep
from src.reliability.rule_prior_residual import compute_rule_prior
from src.reliability.evidence_coverage_expansion import expand_evidence_coverage, slots_from_docs, REQUIRED_SLOTS
from src.reliability.abc_evidence_action_correction import correct_action


def test_case_health_timestep_and_prior():
    df = pd.DataFrame([{"amount": 30000, "payment_status": "RJCT", "exception_type": "amount_limit", "text": "customer impact rejected"}])
    out = add_case_health_timestep(df)
    assert out["case_health_timestep"].iloc[0] > 0
    assert compute_rule_prior(out).iloc[0] > 0.5


def test_evidence_expansion_and_action_correction():
    docs = [
        {"doc_id": "a", "slots": ["payment_status"], "content": "valid evidence for status"},
        {"doc_id": "b", "slots": ["policy_rule", "required_action", "risk_reason", "customer_impact"], "content": "valid evidence for policy and action"},
    ]
    selected = expand_evidence_coverage([docs[0]], docs, REQUIRED_SLOTS)
    assert REQUIRED_SLOTS.issubset(slots_from_docs(selected))
    assert correct_action("auto_resolve", 0.8, slots_from_docs(selected), False) == "analyst_review"
