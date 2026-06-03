from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, TypedDict


class PaymentOpsState(TypedDict, total=False):
    case_id: str
    source: str
    text: str
    amount: float
    evidence: list[str]
    risk_score: float
    risk_reason: str
    route: str
    decision: dict[str, Any]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def intake_node(state: PaymentOpsState) -> PaymentOpsState:
    return {
        "case_id": state.get("case_id", "unknown_case"),
        "text": state.get("text", "").strip(),
        "amount": float(state.get("amount", 0.0)),
        "source": state.get("source", "unknown_source"),
    }


def evidence_node(state: PaymentOpsState) -> PaymentOpsState:
    text = state.get("text", "").lower()
    evidence = []
    if "fraud" in text or "suspicious" in text or "wire" in text:
        evidence.append("risk_keyword_match")
    if float(state.get("amount", 0.0)) >= 10000:
        evidence.append("high_amount_review_signal")
    if "aml" in state.get("source", "").lower():
        evidence.append("aml_source_signal")
    if not evidence:
        evidence.append("routine_case_no_high_risk_signal")
    return {"evidence": evidence}


def triage_node(state: PaymentOpsState) -> PaymentOpsState:
    evidence = state.get("evidence", [])
    score = 0.10
    if "risk_keyword_match" in evidence:
        score += 0.35
    if "high_amount_review_signal" in evidence:
        score += 0.30
    if "aml_source_signal" in evidence:
        score += 0.15
    score = min(score, 0.99)
    return {"risk_score": score, "risk_reason": " + ".join(evidence)}


def compliance_gate_node(state: PaymentOpsState) -> PaymentOpsState:
    score = float(state.get("risk_score", 0.0))
    route = "human_review" if score >= 0.65 else "auto_clear_candidate"
    return {"route": route}


def reviewer_decision_node(state: PaymentOpsState) -> PaymentOpsState:
    route = state.get("route", "human_review")
    decision = {
        "case_id": state.get("case_id", "unknown_case"),
        "route": route,
        "risk_score": state.get("risk_score", 0.0),
        "risk_reason": state.get("risk_reason", ""),
        "requires_human_review": route == "human_review",
        "claim_boundary": "LangGraph local wrapper only. No automated production payment decision.",
    }
    return {"decision": decision}


def build_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(PaymentOpsState)
    graph.add_node("intake", intake_node)
    graph.add_node("evidence_retrieval", evidence_node)
    graph.add_node("risk_triage", triage_node)
    graph.add_node("compliance_gate", compliance_gate_node)
    graph.add_node("reviewer_decision", reviewer_decision_node)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "evidence_retrieval")
    graph.add_edge("evidence_retrieval", "risk_triage")
    graph.add_edge("risk_triage", "compliance_gate")
    graph.add_edge("compliance_gate", "reviewer_decision")
    graph.add_edge("reviewer_decision", END)
    return graph.compile()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local LangGraph PaymentOps review-routing wrapper.")
    parser.add_argument("--sample-cases", type=int, default=5)
    args = parser.parse_args()

    app = build_graph()
    cases = [
        {"case_id": "case_001", "source": "ibm_aml_style", "text": "urgent suspicious wire transfer", "amount": 25000.0},
        {"case_id": "case_002", "source": "cfpb_complaint", "text": "customer asks about payment status", "amount": 120.0},
        {"case_id": "case_003", "source": "ibm_aml_style", "text": "routine payment", "amount": 50000.0},
        {"case_id": "case_004", "source": "cfpb_complaint", "text": "fraud claim and unauthorized transfer", "amount": 800.0},
        {"case_id": "case_005", "source": "paymentops_sample", "text": "normal service inquiry", "amount": 50.0},
    ][: args.sample_cases]

    outputs = []
    for case in cases:
        result = app.invoke(case)
        outputs.append(result["decision"])

    out_dir = Path("reports") / "langgraph_paymentops_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "langgraph_decisions.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in outputs:
            f.write(json.dumps(row) + "\n")

    human_review_count = sum(1 for row in outputs if row["requires_human_review"])
    summary = {
        "status": "PASS",
        "cases": len(outputs),
        "human_review_count": human_review_count,
        "auto_clear_candidate_count": len(outputs) - human_review_count,
        "jsonl_output": str(jsonl_path),
        "claim_boundary": "Local LangGraph wrapper for PaymentOps review routing. No production payment decisions.",
    }

    metrics_path = Path("reports") / "langgraph_paymentops_wrapper_metrics.json"
    report_path = Path("reports") / "31_langgraph_paymentops_wrapper.md"
    write_text(metrics_path, json.dumps(summary, indent=2))
    write_text(
        report_path,
        "# LangGraph PaymentOps Agentic Review Wrapper\n\n"
        "## Claim boundary\n\n"
        "Local LangGraph wrapper for PaymentOps-style review routing only. No production payment decisioning, proprietary bank data, or JPMC systems.\n\n"
        "## Graph nodes\n\n"
        "1. intake\n2. evidence_retrieval\n3. risk_triage\n4. compliance_gate\n5. reviewer_decision\n\n"
        "## Outputs\n\n"
        f"- Cases: `{summary['cases']}`\n"
        f"- Human review count: `{summary['human_review_count']}`\n"
        f"- Auto-clear candidate count: `{summary['auto_clear_candidate_count']}`\n"
        f"- JSONL decisions: `{summary['jsonl_output']}`\n\n"
        "## Resume-safe wording\n\n"
        "Added a LangGraph-based local agentic review wrapper with intake, evidence retrieval, risk triage, compliance gating, and human-review routing under non-production claim boundaries.\n",
    )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
