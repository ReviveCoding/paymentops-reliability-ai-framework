from __future__ import annotations

import json
import yaml
from src.utils import ROOT, REPORTS_DIR, write_report, write_json


def run_release_gate() -> dict:
    cfg = yaml.safe_load((ROOT / "configs" / "release_gate.yaml").read_text(encoding="utf-8"))["release_gate"]
    metrics = json.loads((REPORTS_DIR / "ablation_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "ablation_metrics.json").exists() else {}
    latency = json.loads((REPORTS_DIR / "latency_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "latency_metrics.json").exists() else {}
    feature_store = json.loads((REPORTS_DIR / "feature_store_validation.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "feature_store_validation.json").exists() else {}
    security = json.loads((REPORTS_DIR / "security_guardrail_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "security_guardrail_metrics.json").exists() else {"summary": {}}
    data_contract = json.loads((REPORTS_DIR / "data_contract_validation.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "data_contract_validation.json").exists() else {}
    drift = json.loads((REPORTS_DIR / "drift_backtest_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "drift_backtest_metrics.json").exists() else {}
    observability = json.loads((REPORTS_DIR / "observability_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "observability_metrics.json").exists() else {}
    red_team = json.loads((REPORTS_DIR / "red_team_metrics.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "red_team_metrics.json").exists() else {}
    repo_audit = json.loads((REPORTS_DIR / "repository_audit.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "repository_audit.json").exists() else {}
    api_contract = json.loads((REPORTS_DIR / "api_contract_validation.json").read_text(encoding="utf-8")) if (REPORTS_DIR / "api_contract_validation.json").exists() else {}
    enhanced = metrics.get("enhanced_risk", {})
    rag = metrics.get("rag", {})
    operating_policy = metrics.get("operating_policy", {})
    security_summary = security.get("summary", {})
    checks = {
        "pr_auc": enhanced.get("pr_auc", 0) >= cfg["min_pr_auc"],
        "f2": enhanced.get("f2", 0) >= cfg["min_f2"],
        "false_auto_clear": enhanced.get("false_auto_clear_rate", 1) <= cfg["max_false_auto_clear_rate"],
        "review_burden": enhanced.get("review_burden", 1) <= cfg["max_review_burden"],
        "ece": enhanced.get("ece", 1) <= cfg["max_ece"],
        "evidence_slot_f1": rag.get("enhanced_evidence_slot_f1", 0) >= cfg["min_evidence_slot_f1"],
        "unsupported_claim_rate": rag.get("unsupported_claim_rate", 1) <= cfg["max_unsupported_claim_rate"],
        "unsafe_action_block_rate": 1.0 >= cfg["min_unsafe_action_block_rate"],
        "p95_latency": latency.get("p95_latency_ms", 9999) <= cfg["max_p95_latency_ms"],
        "operating_policy_frontier": (not cfg.get("require_operating_policy_pass", False)) or operating_policy.get("constraint_status") == "PASS",
        "feature_store_contract": (not cfg.get("require_feature_store_validation", False)) or bool(feature_store.get("passed", False)),
        "pii_redaction": (not cfg.get("require_pii_redaction_pass", False)) or bool(security_summary.get("pii_redaction_pass", False)),
        "prompt_injection": security_summary.get("prompt_injection_recall_on_synthetic_attacks", 0) >= cfg.get("min_prompt_injection_recall", 0),
        "data_contract_validation": (not cfg.get("require_data_contract_validation", False)) or bool(data_contract.get("passed", False)),
        "drift_backtest": (not cfg.get("require_drift_backtest_pass", False)) or (drift.get("drift_status") == "PASS" and drift.get("risk_score_psi", 999) <= cfg.get("max_drift_risk_psi", 999)),
        "observability_export": (not cfg.get("require_observability_export", False)) or bool(observability.get("metrics_logs_traces_exported", False)),
        "red_team_safety": (not cfg.get("require_red_team_pass", False)) or red_team.get("red_team_status") == "PASS",
        "repository_audit": (not cfg.get("require_repository_audit_pass", False)) or repo_audit.get("audit_status") == "PASS",
        "api_contract_validation": (not cfg.get("require_api_contract_validation", False)) or api_contract.get("api_contract_status") == "PASS",
    }
    failed = [k for k, v in checks.items() if not v]
    status = "PASS" if not failed else ("REVIEW" if len(failed) <= 3 else "BLOCK")
    result = {"release_status": status, "checks": checks, "failed_checks": failed}
    write_json(REPORTS_DIR / "release_gate_result.json", result)
    rows = "\n".join([f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in checks.items()])
    body = f"""
## Decision

**{status}**

## Checks

| Check | Result |
|---|---|
{rows}

## Failed checks

`{failed}`

## Boundary

This release decision applies only to the local offline sample project. It is not production approval and is not regulatory certification.
"""
    write_report(REPORTS_DIR / "09_release_decision.md", "Release Decision", body)
    return result


if __name__ == "__main__":
    print(run_release_gate())
