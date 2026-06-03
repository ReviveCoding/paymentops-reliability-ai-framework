from __future__ import annotations

from typing import TypedDict, Any
from src.rag.retrieve import retrieve_evidence
from src.rag.rerank import rerank_by_slot_coverage
from src.rag.grounded_summary import make_grounded_summary
from src.reliability.evidence_coverage_expansion import expand_evidence_coverage, slots_from_docs, REQUIRED_SLOTS
from src.reliability.abc_evidence_action_correction import deflate_unsupported_evidence, correct_action
from src.reliability.rule_prior_residual import compute_rule_prior
from src.agents.permission_gates import permission_gate
from src.agents.source_conflict_checker import has_source_conflict
from src.agents.audit_logger import append_audit_log
from src.security.prompt_injection import detect_prompt_injection

try:
    from langgraph.graph import StateGraph  # type: ignore
    USE_LANGGRAPH = True
except Exception:
    StateGraph = None
    USE_LANGGRAPH = False


class AgentState(TypedDict, total=False):
    case: dict
    evidence_docs: list[dict]
    evidence_slots: set[str]
    risk_score: float
    proposed_action: str
    final_action: str
    permission: dict
    source_conflict: bool
    summary: str
    trace: list[dict]


def _score_case(case: dict) -> float:
    # deterministic scoring for runnable agent; model-based scoring is evaluated separately.
    import pandas as pd
    prior = compute_rule_prior(pd.DataFrame([{**case, "text": case.get("text") or case.get("narrative", "")}]))
    return float(prior.iloc[0])


def run_payment_agent(case: dict, policy_docs: list[dict]) -> AgentState:
    state: AgentState = {"case": case, "trace": []}
    query = case.get("text") or case.get("narrative") or ""
    injection = detect_prompt_injection(query)
    state["trace"].append({"node": "prompt_injection_check", **injection})
    if injection["is_suspicious"]:
        state["risk_score"] = 1.0
        state["evidence_docs"] = []
        state["evidence_slots"] = set()
        state["source_conflict"] = False
        state["proposed_action"] = "human_review_required"
        state["final_action"] = "human_review_required"
        state["permission"] = {"allowed": False, "reason": "Prompt-injection pattern detected."}
        state["summary"] = "Case routed to human review because prompt-injection patterns were detected."
        append_audit_log({"case_id": case.get("case_id"), "risk_score": 1.0, "doc_ids": [], "final_action": "human_review_required", "source_conflict": False, "prompt_injection": True})
        return state
    state["risk_score"] = _score_case(case)
    state["trace"].append({"node": "score_case", "risk_score": state["risk_score"]})

    base_docs = retrieve_evidence(query, policy_docs, k=3)
    candidates = retrieve_evidence(query, policy_docs, k=6)
    expanded = expand_evidence_coverage(base_docs[:1], rerank_by_slot_coverage(query, candidates), REQUIRED_SLOTS)
    corrected_docs = deflate_unsupported_evidence(expanded)
    state["evidence_docs"] = corrected_docs
    state["evidence_slots"] = slots_from_docs(corrected_docs)
    state["trace"].append({"node": "retrieve_expand_deflate", "doc_ids": [d["doc_id"] for d in corrected_docs], "slots": sorted(state["evidence_slots"])})

    source_conflict = has_source_conflict(corrected_docs)
    state["source_conflict"] = source_conflict
    proposed = "auto_resolve" if state["risk_score"] < 0.35 else ("compliance_escalation" if state["risk_score"] >= 0.75 else "analyst_review")
    corrected = correct_action(proposed, state["risk_score"], state["evidence_slots"], source_conflict)
    perm = permission_gate(corrected, state["risk_score"], state["evidence_slots"])
    final_action = corrected if perm["allowed"] else "human_review_required"
    state["proposed_action"] = proposed
    state["final_action"] = final_action
    state["permission"] = perm
    state["summary"] = make_grounded_summary(case, corrected_docs, final_action)
    state["trace"].append({"node": "permission_and_route", "proposed": proposed, "final": final_action, "permission": perm})

    append_audit_log({
        "case_id": case.get("case_id"),
        "risk_score": state["risk_score"],
        "doc_ids": [d["doc_id"] for d in corrected_docs],
        "final_action": final_action,
        "source_conflict": source_conflict,
    })
    return state
