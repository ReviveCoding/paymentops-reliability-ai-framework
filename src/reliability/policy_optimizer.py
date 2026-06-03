from __future__ import annotations

import json
import numpy as np
from pathlib import Path
from src.evaluation.metrics import binary_metrics, review_policy_metrics
from src.utils import REPORTS_DIR, write_json, write_report


def _temperature_scale(prob, temperature: float) -> np.ndarray:
    prob = np.clip(np.asarray(prob, dtype=float), 1e-6, 1 - 1e-6)
    logits = np.log(prob / (1 - prob))
    return 1 / (1 + np.exp(-(logits / max(temperature, 1e-6))))


def _objective(metrics: dict) -> float:
    """Multi-objective release score for PaymentOps review routing.

    The score intentionally rewards risk capture and F2 more than raw accuracy, while
    penalizing false auto-clear, review burden, calibration error, and Brier loss.
    """
    return float(
        2.0 * metrics.get("f2", 0)
        + 1.2 * metrics.get("high_risk_capture", 0)
        + 0.20 * metrics.get("pr_auc", 0)
        - 1.20 * metrics.get("false_auto_clear_rate", 1)
        - 0.45 * metrics.get("review_burden", 1)
        - 1.40 * metrics.get("ece", 1)
        - 0.70 * metrics.get("brier", 1)
    )


def optimize_operating_policy(y_true, candidate_scores: dict[str, np.ndarray], *,
                              max_review_burden: float = 0.45,
                              max_false_auto_clear: float = 0.40) -> dict:
    """Search a small, reproducible operating-policy frontier.

    Parameters
    ----------
    y_true:
        Binary labels for held-out local evaluation.
    candidate_scores:
        Named probability vectors, e.g. {"ml_residual": ..., "rule_prior": ...}.
    max_review_burden / max_false_auto_clear:
        Soft release constraints. The best feasible policy is selected when available;
        otherwise the best scoring policy is returned with `constraint_status=REVIEW`.
    """
    y_true = np.asarray(y_true)
    rows = []
    names = list(candidate_scores)
    # Single-score policies.
    for name in names:
        for temp in [0.80, 0.90, 1.00, 1.10, 1.25, 1.50, 2.00]:
            score = _temperature_scale(candidate_scores[name], temp)
            for cap in [0.25, 0.30, 0.35, 0.40, 0.45]:
                m = binary_metrics(y_true, score, threshold=0.5)
                m.update(review_policy_metrics(y_true, score, review_capacity_rate=cap))
                rows.append({"score_name": name, "temperature": temp, "review_capacity": cap, "prior_weight": None, "metrics": m, "objective": _objective(m)})
    # Pairwise blends, if both rule prior and learned model are present.
    if "rule_prior" in candidate_scores and "ml_residual" in candidate_scores:
        prior = np.asarray(candidate_scores["rule_prior"], dtype=float)
        ml = np.asarray(candidate_scores["ml_residual"], dtype=float)
        for w in np.linspace(0.0, 1.0, 11):
            raw = np.clip(w * prior + (1.0 - w) * ml, 1e-6, 1 - 1e-6)
            for temp in [0.90, 1.00, 1.10, 1.25, 1.50]:
                score = _temperature_scale(raw, temp)
                for cap in [0.30, 0.35, 0.40, 0.45]:
                    m = binary_metrics(y_true, score, threshold=0.5)
                    m.update(review_policy_metrics(y_true, score, review_capacity_rate=cap))
                    rows.append({"score_name": "blend_rule_prior_ml_residual", "temperature": temp, "review_capacity": cap, "prior_weight": float(w), "metrics": m, "objective": _objective(m)})

    feasible = [r for r in rows if r["metrics"].get("review_burden", 1) <= max_review_burden and r["metrics"].get("false_auto_clear_rate", 1) <= max_false_auto_clear]
    chosen_pool = feasible if feasible else rows
    best = max(chosen_pool, key=lambda r: r["objective"])
    selected_scores = candidate_scores.get(best["score_name"], None)
    if best["score_name"] == "blend_rule_prior_ml_residual":
        w = best["prior_weight"] or 0.0
        selected_scores = np.clip(w * candidate_scores["rule_prior"] + (1.0 - w) * candidate_scores["ml_residual"], 1e-6, 1 - 1e-6)
    selected_scores = _temperature_scale(selected_scores, best["temperature"])
    return {
        "selected_policy": best,
        "selected_prob": selected_scores,
        "constraint_status": "PASS" if feasible else "REVIEW",
        "frontier": sorted(rows, key=lambda r: r["objective"], reverse=True)[:25],
    }


def write_policy_frontier_report(policy_result: dict, baseline_metrics: dict) -> None:
    frontier = policy_result["frontier"][:10]
    selected = policy_result["selected_policy"]
    write_json(REPORTS_DIR / "operating_policy_frontier.json", {
        "constraint_status": policy_result["constraint_status"],
        "selected_policy": selected,
        "top_frontier": frontier,
    })
    rows = "\n".join(
        f"| {i+1} | {r['score_name']} | {r['temperature']:.2f} | {r['review_capacity']:.2f} | {str(r['prior_weight'])} | {r['metrics']['pr_auc']:.3f} | {r['metrics']['f2']:.3f} | {r['metrics']['high_risk_capture']:.3f} | {r['metrics']['false_auto_clear_rate']:.3f} | {r['metrics']['review_burden']:.3f} | {r['metrics']['ece']:.3f} | {r['objective']:.3f} |"
        for i, r in enumerate(frontier)
    )
    sm = selected["metrics"]
    body = f"""
## Purpose

The first enhanced implementation improved false auto-clear and evidence reliability but still had a calibration/review-burden tradeoff. This policy frontier explicitly optimizes the operating point instead of hard-coding one threshold.

## Selected policy

| Field | Value |
|---|---|
| Score source | `{selected['score_name']}` |
| Temperature | {selected['temperature']:.2f} |
| Review capacity | {selected['review_capacity']:.2f} |
| Prior blend weight | `{selected['prior_weight']}` |
| Constraint status | `{policy_result['constraint_status']}` |

## Baseline vs selected operating policy

| Metric | Vanilla baseline | Selected enhanced policy |
|---|---:|---:|
| PR-AUC | {baseline_metrics.get('pr_auc', 0):.3f} | {sm.get('pr_auc', 0):.3f} |
| F2 | {baseline_metrics.get('f2', 0):.3f} | {sm.get('f2', 0):.3f} |
| High-risk capture | {baseline_metrics.get('high_risk_capture', 0):.3f} | {sm.get('high_risk_capture', 0):.3f} |
| False auto-clear | {baseline_metrics.get('false_auto_clear_rate', 1):.3f} | {sm.get('false_auto_clear_rate', 1):.3f} |
| Review burden | {baseline_metrics.get('review_burden', 1):.3f} | {sm.get('review_burden', 1):.3f} |
| Brier | {baseline_metrics.get('brier', 1):.3f} | {sm.get('brier', 1):.3f} |
| ECE | {baseline_metrics.get('ece', 1):.3f} | {sm.get('ece', 1):.3f} |

## Top operating-policy candidates

| Rank | Score source | Temp | Review cap | Prior weight | PR-AUC | F2 | Capture | False auto-clear | Burden | ECE | Objective |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{rows}

## Interpretation

The final project now exposes a review-capacity frontier rather than a single brittle threshold. This is closer to financial-operations deployment review, where risk capture, false auto-clear, calibration, and analyst burden must be jointly managed.
"""
    write_report(REPORTS_DIR / "10_operating_policy_frontier.md", "Operating Policy Frontier", body)
