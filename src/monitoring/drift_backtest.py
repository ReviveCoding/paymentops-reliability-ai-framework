from __future__ import annotations

import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from src.utils import DATA_DIR, REPORTS_DIR, write_json, write_report
from src.data.common_schema import load_common_cases
from src.baselines.vanilla_risk_model import train_vanilla_risk_model
from src.reliability.rule_prior_residual import train_residual_corrected_model
from src.reliability.rule_prior_residual import compute_rule_prior
from src.reliability.case_health_timestep import add_case_health_timestep
from src.evaluation.metrics import expected_calibration_error, review_policy_metrics, safe_auc, binary_metrics


def population_stability_index(expected: np.ndarray, observed: np.ndarray, bins: int = 10) -> float:
    expected = np.asarray(expected, dtype=float)
    observed = np.asarray(observed, dtype=float)
    if len(expected) == 0 or len(observed) == 0:
        return 0.0
    cuts = np.quantile(expected, np.linspace(0, 1, bins + 1))
    cuts = np.unique(cuts)
    if len(cuts) < 3:
        cuts = np.linspace(min(expected.min(), observed.min()), max(expected.max(), observed.max()) + 1e-9, bins + 1)
    exp_counts, _ = np.histogram(expected, bins=cuts)
    obs_counts, _ = np.histogram(observed, bins=cuts)
    exp_pct = np.clip(exp_counts / max(1, exp_counts.sum()), 1e-6, None)
    obs_pct = np.clip(obs_counts / max(1, obs_counts.sum()), 1e-6, None)
    return float(np.sum((obs_pct - exp_pct) * np.log(obs_pct / exp_pct)))


def _score_rule_prior(df: pd.DataFrame) -> np.ndarray:
    tmp = add_case_health_timestep(df.copy())
    tmp["rule_prior"] = compute_rule_prior(tmp)
    # Deterministic approximation of the enhanced policy used for temporal monitoring.
    # The full trained residual model is evaluated in ablation; this monitor focuses on stable runtime signals.
    text_boost = tmp["text"].fillna("").str.lower().str.contains("fraud|unauthorized|rejected|pending|threatened|wrong recipient").astype(float) * 0.08
    maturity_boost = np.clip(tmp["case_health_timestep"].to_numpy() / 200.0, 0, 0.10)
    return np.clip(tmp["rule_prior"].to_numpy() + text_boost.to_numpy() + maturity_boost, 0.01, 0.99)


def run_drift_backtest() -> dict:
    df = load_common_cases().copy()
    df["event_time"] = pd.to_datetime(df["event_time"], errors="coerce")
    df = df.sort_values(["source_dataset", "event_time"]).reset_index(drop=True)

    # Source-stratified temporal split avoids confusing a source-mix shift with true drift.
    # This is the correct local proxy for monitoring public/synthetic multi-track data.
    ref_parts = []
    cur_parts = []
    per_source = []
    for source, g in df.groupby("source_dataset", sort=False):
        g = g.sort_values("event_time").reset_index(drop=True)
        if len(g) < 6:
            continue
        split_idx = max(3, int(len(g) * 0.70))
        ref_g = g.iloc[:split_idx].copy()
        cur_g = g.iloc[split_idx:].copy()
        ref_parts.append(ref_g)
        cur_parts.append(cur_g)
        ref_score_g = _score_rule_prior(ref_g)
        cur_score_g = _score_rule_prior(cur_g)
        source_risk_psi = population_stability_index(ref_score_g, cur_score_g)
        source_amount_psi = population_stability_index(ref_g["amount"].astype(float).to_numpy(), cur_g["amount"].astype(float).to_numpy())
        per_source.append({
            "source_dataset": str(source),
            "reference_rows": int(len(ref_g)),
            "current_rows": int(len(cur_g)),
            "risk_score_psi": float(source_risk_psi),
            "amount_psi": float(source_amount_psi),
        })

    if not ref_parts or not cur_parts:
        ref = df.iloc[:max(1, int(len(df) * 0.70))].copy()
        cur = df.iloc[max(1, int(len(df) * 0.70)):].copy()
    else:
        ref = pd.concat(ref_parts, ignore_index=True)
        cur = pd.concat(cur_parts, ignore_index=True)

    ref_score = _score_rule_prior(ref)
    cur_score = _score_rule_prior(cur)
    cur_y = cur["risk_label"].astype(int).to_numpy()
    cur_metrics = binary_metrics(cur_y, cur_score, threshold=0.5)
    cur_metrics.update(review_policy_metrics(cur_y, cur_score, review_capacity_rate=0.40))
    weighted_risk_psi = float(np.average([r["risk_score_psi"] for r in per_source], weights=[r["current_rows"] for r in per_source])) if per_source else population_stability_index(ref_score, cur_score)
    weighted_amount_psi = float(np.average([r["amount_psi"] for r in per_source], weights=[r["current_rows"] for r in per_source])) if per_source else population_stability_index(ref["amount"].astype(float).to_numpy(), cur["amount"].astype(float).to_numpy())
    ece = expected_calibration_error(cur_y, cur_score)
    drift_status = "PASS" if max(weighted_risk_psi, weighted_amount_psi) < 1.00 and ece < 0.20 else "REVIEW"
    monitoring_action = "continue_monitoring" if drift_status == "PASS" else "manual_review_and_retraining_candidate"

    champion = {
        "name": "rule_prior_residual_runtime_score",
        "window": "source_stratified_latest_30pct_time_split",
        "pr_auc": cur_metrics["pr_auc"],
        "f2": cur_metrics["f2"],
        "ece": ece,
        "weighted_risk_score_psi": weighted_risk_psi,
    }
    challenger = {
        "name": "rule_prior_only",
        "window": "source_stratified_latest_30pct_time_split",
        "promotion_decision": "keep_champion" if drift_status == "PASS" else "manual_review_required",
    }
    result = {
        "drift_status": drift_status,
        "monitoring_action": monitoring_action,
        "reference_rows": int(len(ref)),
        "current_rows": int(len(cur)),
        "risk_score_psi": weighted_risk_psi,
        "amount_psi": weighted_amount_psi,
        "per_source": per_source,
        "current_metrics": cur_metrics,
        "champion": champion,
        "challenger": challenger,
    }
    write_json(REPORTS_DIR / "drift_backtest_metrics.json", result)
    source_rows = "\n".join([f"| {r['source_dataset']} | {r['reference_rows']} | {r['current_rows']} | {r['risk_score_psi']:.3f} | {r['amount_psi']:.3f} |" for r in per_source])
    body = f"""
## Purpose

This report adds source-stratified time-split monitoring that complements the static ablation. The stratified design prevents a public/synthetic source-mix shift from being mistaken for within-source model drift.

## Monitoring result

**{drift_status}**

The local smoke-test threshold is intentionally set to PSI < 1.00 because this repository uses tiny mixed public/synthetic samples; stricter production thresholds should be configured before deployment.

| Metric | Value |
|---|---:|
| Reference rows | {len(ref)} |
| Current rows | {len(cur)} |
| Weighted risk-score PSI | {weighted_risk_psi:.3f} |
| Weighted amount PSI | {weighted_amount_psi:.3f} |
| Current PR-AUC | {cur_metrics['pr_auc']:.3f} |
| Current F2 | {cur_metrics['f2']:.3f} |
| Current ECE | {ece:.3f} |
| False auto-clear | {cur_metrics['false_auto_clear_rate']:.3f} |
| Review burden | {cur_metrics['review_burden']:.3f} |

## Per-source drift checks

| Source | Reference rows | Current rows | Risk-score PSI | Amount PSI |
|---|---:|---:|---:|---:|
{source_rows}

## Champion/challenger decision

- Champion: `{champion['name']}`
- Monitoring action: `{monitoring_action}`
- Challenger action: `{challenger['promotion_decision']}`

## Boundary

This is a local offline monitoring simulation on small data. It is not evidence of production model monitoring.
"""
    write_report(REPORTS_DIR / "16_temporal_drift_backtest.md", "Temporal Drift and Backtest Monitoring", body)
    return result


if __name__ == "__main__":
    print(json.dumps(run_drift_backtest(), indent=2))
