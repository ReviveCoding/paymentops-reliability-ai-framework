from __future__ import annotations

import json
import numpy as np
import pandas as pd
from src.utils import REPORTS_DIR, write_json, write_report
from src.reliability.rule_prior_residual import train_residual_corrected_model, compute_rule_prior
from src.reliability.case_health_timestep import add_case_health_timestep
from src.evaluation.metrics import review_policy_metrics, expected_calibration_error, binary_metrics
from src.data.common_schema import load_common_cases


def _amount_bucket(x: float) -> str:
    if x <= 0:
        return "no_amount"
    if x < 5000:
        return "low_amount"
    if x < 25000:
        return "medium_amount"
    return "high_amount"


def _slice_metrics(x_test: pd.DataFrame, y_test, prob, group_col: str) -> list[dict]:
    rows = []
    tmp = x_test.copy()
    tmp["_y"] = np.asarray(y_test)
    tmp["_prob"] = np.asarray(prob)
    for name, g in tmp.groupby(group_col):
        if len(g) < 3:
            continue
        m = binary_metrics(g["_y"], g["_prob"], threshold=0.5)
        m.update(review_policy_metrics(g["_y"], g["_prob"], review_capacity_rate=0.45))
        rows.append({"slice_type": group_col, "slice": str(name), "n": int(len(g)), **m})
    return rows


def _population_stability_index(expected, actual, bins: int = 10) -> float:
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    if len(expected) == 0 or len(actual) == 0:
        return 0.0
    quantiles = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if len(quantiles) < 3:
        return 0.0
    exp_counts, _ = np.histogram(expected, bins=quantiles)
    act_counts, _ = np.histogram(actual, bins=quantiles)
    exp_pct = np.maximum(exp_counts / max(1, exp_counts.sum()), 1e-6)
    act_pct = np.maximum(act_counts / max(1, act_counts.sum()), 1e-6)
    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def run_robustness() -> dict:
    common = load_common_cases()
    result = train_residual_corrected_model(common)
    x = result["X_test"].copy()
    y = result["y_test"]
    prob = result["prob"]
    x["amount_bucket"] = x["amount"].astype(float).map(_amount_bucket)
    slice_rows = []
    for col in ["case_type", "payment_status", "exception_type", "amount_bucket"]:
        slice_rows.extend(_slice_metrics(x, y, prob, col))
    worst_by_false_auto_clear = sorted(slice_rows, key=lambda r: r.get("false_auto_clear_rate", 0), reverse=True)[:8]
    worst_by_ece = sorted(slice_rows, key=lambda r: r.get("ece", 0), reverse=True)[:8]

    # Synthetic stress scenarios: amount shock and status-risk shock.
    stressed = add_case_health_timestep(common.copy())
    stressed["rule_prior_base"] = compute_rule_prior(stressed)
    stressed_amount = stressed.copy()
    stressed_amount["amount"] = stressed_amount["amount"].astype(float) * 3.0
    stressed_amount["rule_prior_stress"] = compute_rule_prior(stressed_amount)
    stressed_status = stressed.copy()
    pay_mask = stressed_status["case_type"].str.contains("payment|fraud", case=False, na=False)
    stressed_status.loc[pay_mask, "payment_status"] = "PDNG"
    stressed_status.loc[pay_mask, "exception_type"] = "status_mismatch"
    stressed_status["rule_prior_stress"] = compute_rule_prior(stressed_status)

    psi_amount = _population_stability_index(stressed["amount"].astype(float), stressed_amount["amount"].astype(float))
    prior_shift_amount = float((stressed_amount["rule_prior_stress"] - stressed["rule_prior_base"]).mean())
    prior_shift_status = float((stressed_status["rule_prior_stress"] - stressed["rule_prior_base"]).mean())

    output = {
        "slice_count": len(slice_rows),
        "worst_false_auto_clear_slices": worst_by_false_auto_clear,
        "worst_calibration_slices": worst_by_ece,
        "stress_tests": {
            "amount_3x_psi": psi_amount,
            "amount_3x_mean_prior_shift": prior_shift_amount,
            "payment_status_to_pending_mean_prior_shift": prior_shift_status,
        },
    }
    write_json(REPORTS_DIR / "robustness_metrics.json", output)
    fa_rows = "\n".join([f"| {r['slice_type']} | {r['slice']} | {r['n']} | {r['false_auto_clear_rate']:.3f} | {r['review_burden']:.3f} | {r['ece']:.3f} |" for r in worst_by_false_auto_clear])
    ece_rows = "\n".join([f"| {r['slice_type']} | {r['slice']} | {r['n']} | {r['ece']:.3f} | {r['false_auto_clear_rate']:.3f} | {r['review_burden']:.3f} |" for r in worst_by_ece])
    body = f"""
## Purpose

This report closes a remaining weakness from the first enhanced version: aggregate metrics alone can hide weak slices. The project now reports worst-slice false auto-clear, calibration, and simple stress tests on local sample data.

## Worst false-auto-clear slices

| Slice type | Slice | n | False auto-clear | Review burden | ECE |
|---|---|---:|---:|---:|---:|
{fa_rows}

## Worst calibration slices

| Slice type | Slice | n | ECE | False auto-clear | Review burden |
|---|---|---:|---:|---:|---:|
{ece_rows}

## Stress tests

| Stress test | Value |
|---|---:|
| Amount 3x PSI | {psi_amount:.3f} |
| Amount 3x mean rule-prior shift | {prior_shift_amount:.3f} |
| Payment-status pending/status-mismatch mean rule-prior shift | {prior_shift_status:.3f} |

## Interpretation

The project now surfaces whether the release gate is driven by a few fragile slices. This is still a local/sample-data stress test, not evidence of production robustness.
"""
    write_report(REPORTS_DIR / "11_worst_slice_and_stress_report.md", "Worst-Slice and Stress Robustness Report", body)
    return output


if __name__ == "__main__":
    print(json.dumps(run_robustness(), indent=2))
