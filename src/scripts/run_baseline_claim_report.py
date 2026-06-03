from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    fbeta_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from src.scripts.run_operational_backtest import (
    _prepare_operational_frame,
    _split_train_val_test,
    _build_model,
    _features,
    _labels,
    _score_model,
    _metrics_for_scores,
)


REVIEW_CAPACITIES = [0.05, 0.10, 0.20, 0.35, 0.50]


def _ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(x: Any) -> float | None:
    try:
        if x is None or pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def _ece(y_true: np.ndarray, score: np.ndarray, n_bins: int = 10) -> float:
    y_true = np.asarray(y_true).astype(int)
    score = np.asarray(score).astype(float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(score)
    for lo, hi in zip(bins[:-1], bins[1:]):
        if hi == 1.0:
            mask = (score >= lo) & (score <= hi)
        else:
            mask = (score >= lo) & (score < hi)
        if not np.any(mask):
            continue
        conf = float(score[mask].mean())
        acc = float(y_true[mask].mean())
        ece += float(mask.mean()) * abs(acc - conf)
    return float(ece)


def _calibration_slope_intercept(y_true: np.ndarray, score: np.ndarray) -> dict[str, float | None]:
    y_true = np.asarray(y_true).astype(int)
    score = np.asarray(score).astype(float)
    if len(np.unique(y_true)) < 2:
        return {"calibration_intercept": None, "calibration_slope": None}
    eps = 1e-6
    logit = np.log(np.clip(score, eps, 1 - eps) / (1 - np.clip(score, eps, 1 - eps))).reshape(-1, 1)
    cal = LogisticRegression(max_iter=1000)
    cal.fit(logit, y_true)
    return {
        "calibration_intercept": float(cal.intercept_[0]),
        "calibration_slope": float(cal.coef_[0][0]),
    }


class SigmoidScoreCalibrator:
    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=1000)

    def fit(self, score: np.ndarray, y: np.ndarray) -> "SigmoidScoreCalibrator":
        eps = 1e-6
        score = np.asarray(score, dtype=float)
        x = np.log(np.clip(score, eps, 1 - eps) / (1 - np.clip(score, eps, 1 - eps))).reshape(-1, 1)
        self.model.fit(x, np.asarray(y).astype(int))
        return self

    def predict_score(self, score: np.ndarray) -> np.ndarray:
        eps = 1e-6
        score = np.asarray(score, dtype=float)
        x = np.log(np.clip(score, eps, 1 - eps) / (1 - np.clip(score, eps, 1 - eps))).reshape(-1, 1)
        return self.model.predict_proba(x)[:, 1]


def _evaluate_score_vector(
    name: str,
    y: np.ndarray,
    score: np.ndarray,
    review_capacity: float,
    reference_random: bool = True,
) -> dict[str, Any]:
    metrics = _metrics_for_scores(y, score, review_capacity=review_capacity)
    metrics["model"] = name
    metrics["ece"] = _ece(y, score)
    metrics.update(_calibration_slope_intercept(y, score))

    if reference_random:
        expected_random_capture = review_capacity
        expected_random_false_auto_clear = 1.0 - review_capacity
        metrics["random_expected_high_risk_capture"] = expected_random_capture
        metrics["random_expected_false_auto_clear"] = expected_random_false_auto_clear
        metrics["capture_lift_vs_random"] = (
            metrics["high_risk_capture"] / expected_random_capture
            if metrics.get("high_risk_capture") is not None and expected_random_capture > 0
            else None
        )
        metrics["false_auto_clear_reduction_vs_random"] = (
            (expected_random_false_auto_clear - metrics["false_auto_clear"]) / expected_random_false_auto_clear
            if metrics.get("false_auto_clear") is not None and expected_random_false_auto_clear > 0
            else None
        )
    return metrics


def _amount_rule_score(df: pd.DataFrame) -> np.ndarray:
    amount = pd.to_numeric(df.get("amount", 0.0), errors="coerce").fillna(0.0).to_numpy()
    log_amount = np.log1p(np.clip(amount, 0, None))
    if np.nanmax(log_amount) <= np.nanmin(log_amount):
        return np.full(len(df), 0.5)
    return (log_amount - np.nanmin(log_amount)) / (np.nanmax(log_amount) - np.nanmin(log_amount))


def _source_rule_score(df: pd.DataFrame) -> np.ndarray:
    src = df["source_dataset"].astype(str).str.lower()
    text = df["text"].astype(str).str.lower()
    amount = pd.to_numeric(df.get("amount", 0.0), errors="coerce").fillna(0.0)
    score = np.full(len(df), 0.10)
    score += src.str.contains("ibm|aml", regex=True).astype(float).to_numpy() * 0.15
    score += text.str.contains("laundering|fraud|dispute|unauthorized|late|untimely", regex=True).astype(float).to_numpy() * 0.35
    score += (amount > amount.quantile(0.90)).astype(float).to_numpy() * 0.20
    return np.clip(score, 0.0, 1.0)


def _md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for r in rows:
        vals = []
        for c in columns:
            v = r.get(c)
            if isinstance(v, float):
                vals.append(f"{v:.4f}")
            elif v is None:
                vals.append("")
            else:
                vals.append(str(v))
        body.append("| " + " | ".join(vals) + " |")
    return "\n".join([header, sep] + body)


def _pct_change(new: float | None, old: float | None, lower_is_better: bool = False) -> float | None:
    if new is None or old is None or old == 0:
        return None
    if lower_is_better:
        return (old - new) / old
    return (new - old) / old


def _point_change(new: float | None, old: float | None) -> float | None:
    if new is None or old is None:
        return None
    return new - old


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", default=os.environ.get("PAYMENTOPS_EXTERNAL_DATA", ""))
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--max-features", type=int, default=10000)
    parser.add_argument("--review-capacity", type=float, default=0.35)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    external_root = Path(args.external_root)
    if not external_root.exists():
        raise FileNotFoundError(f"External root not found: {external_root}")

    input_csv = Path(args.input_csv) if args.input_csv else external_root / "validation_outputs" / "external_common_case_schema.csv"
    if not input_csv.exists():
        raise FileNotFoundError(f"Common schema input not found: {input_csv}")

    reports_dir = Path("reports")
    registry_dir = Path("artifacts/model_registry")
    out_dir = external_root / "baseline_claim_outputs"
    models_dir = out_dir / "models"
    _ensure_dirs(reports_dir, registry_dir, out_dir, models_dir)

    df = _prepare_operational_frame(input_csv)
    train, val, test = _split_train_val_test(df)
    y_test = _labels(test)

    # Baseline score vectors
    rng = np.random.default_rng(args.random_state)
    random_score = rng.random(len(test))
    amount_score = _amount_rule_score(test)
    source_rule_score = _source_rule_score(test)

    rows: list[dict[str, Any]] = []

    # Expected random-review baseline for direct reviewer-capacity lift.
    rows.append({
        "model": "random_review_expected",
        "rows": int(len(test)),
        "positives": int(y_test.sum()),
        "positive_rate": float(y_test.mean()),
        "review_capacity": args.review_capacity,
        "status": "REFERENCE",
        "roc_auc": None,
        "pr_auc": float(y_test.mean()),
        "f2": None,
        "brier": None,
        "ece": None,
        "high_risk_capture": args.review_capacity,
        "false_auto_clear": 1.0 - args.review_capacity,
        "review_burden": args.review_capacity,
        "capture_lift_vs_random": 1.0,
        "false_auto_clear_reduction_vs_random": 0.0,
    })

    for name, score in [
        ("random_score_baseline", random_score),
        ("amount_rule_baseline", amount_score),
        ("source_rule_baseline", source_rule_score),
    ]:
        rows.append(_evaluate_score_vector(name, y_test, score, review_capacity=args.review_capacity))

    # Train fair final-test baseline and proposed method on the same temporal training split.
    model_specs = {
        "vanilla_text_logreg": _build_model("vanilla_text_logreg", args.max_features, args.random_state),
        "hybrid_text_numeric_logreg": _build_model("hybrid_text_numeric_logreg", args.max_features, args.random_state),
    }

    trained_models: dict[str, Any] = {}
    stamp = _now_stamp()

    for name, model in model_specs.items():
        t0 = time.perf_counter()
        model.fit(_features(train), _labels(train))
        fit_seconds = time.perf_counter() - t0
        score = _score_model(model, _features(test))
        metrics = _evaluate_score_vector(name, y_test, score, review_capacity=args.review_capacity)
        metrics["fit_seconds"] = float(fit_seconds)
        rows.append(metrics)
        trained_models[name] = model
        joblib.dump(model, models_dir / f"{stamp}_{name}.joblib")

    # Calibration: fit sigmoid score calibrator on validation scores, evaluate on final future test.
    hybrid_model = trained_models["hybrid_text_numeric_logreg"]
    val_score = _score_model(hybrid_model, _features(val))
    calibrator = SigmoidScoreCalibrator().fit(val_score, _labels(val))
    test_hybrid_score = _score_model(hybrid_model, _features(test))
    calibrated_score = calibrator.predict_score(test_hybrid_score)

    calibrated_metrics = _evaluate_score_vector(
        "hybrid_text_numeric_logreg_sigmoid_calibrated",
        y_test,
        calibrated_score,
        review_capacity=args.review_capacity,
    )
    calibrated_metrics["fit_seconds"] = None
    rows.append(calibrated_metrics)

    joblib.dump(
        {"base_model": hybrid_model, "sigmoid_score_calibrator": calibrator},
        models_dir / f"{stamp}_hybrid_sigmoid_calibrated_bundle.joblib",
    )

    # Review capacity frontier for the important models.
    frontier_rows: list[dict[str, Any]] = []
    score_map = {
        "random_score_baseline": random_score,
        "vanilla_text_logreg": _score_model(trained_models["vanilla_text_logreg"], _features(test)),
        "hybrid_text_numeric_logreg": test_hybrid_score,
        "hybrid_text_numeric_logreg_sigmoid_calibrated": calibrated_score,
    }

    for model_name, score in score_map.items():
        for cap in REVIEW_CAPACITIES:
            m = _evaluate_score_vector(model_name, y_test, score, review_capacity=cap)
            m["capacity"] = cap
            frontier_rows.append(m)

    # Claim comparison summaries.
    def get_row(name: str) -> dict[str, Any]:
        for r in rows:
            if r["model"] == name:
                return r
        raise KeyError(name)

    vanilla = get_row("vanilla_text_logreg")
    hybrid = get_row("hybrid_text_numeric_logreg")
    calibrated = get_row("hybrid_text_numeric_logreg_sigmoid_calibrated")
    random_expected = get_row("random_review_expected")

    claim_summary = {
        "hybrid_vs_vanilla": {
            "pr_auc_pct_change": _pct_change(hybrid.get("pr_auc"), vanilla.get("pr_auc")),
            "roc_auc_pct_change": _pct_change(hybrid.get("roc_auc"), vanilla.get("roc_auc")),
            "f2_pct_change": _pct_change(hybrid.get("f2"), vanilla.get("f2")),
            "brier_pct_reduction": _pct_change(hybrid.get("brier"), vanilla.get("brier"), lower_is_better=True),
            "ece_pct_reduction": _pct_change(hybrid.get("ece"), vanilla.get("ece"), lower_is_better=True),
            "high_risk_capture_point_change": _point_change(hybrid.get("high_risk_capture"), vanilla.get("high_risk_capture")),
            "false_auto_clear_pct_reduction": _pct_change(hybrid.get("false_auto_clear"), vanilla.get("false_auto_clear"), lower_is_better=True),
        },
        "calibrated_hybrid_vs_uncalibrated_hybrid": {
            "brier_pct_reduction": _pct_change(calibrated.get("brier"), hybrid.get("brier"), lower_is_better=True),
            "ece_pct_reduction": _pct_change(calibrated.get("ece"), hybrid.get("ece"), lower_is_better=True),
            "high_risk_capture_point_change": _point_change(calibrated.get("high_risk_capture"), hybrid.get("high_risk_capture")),
            "false_auto_clear_pct_reduction": _pct_change(calibrated.get("false_auto_clear"), hybrid.get("false_auto_clear"), lower_is_better=True),
        },
        "hybrid_vs_random_review": {
            "capture_lift_vs_random": hybrid.get("capture_lift_vs_random"),
            "false_auto_clear_reduction_vs_random": hybrid.get("false_auto_clear_reduction_vs_random"),
            "random_expected_high_risk_capture": random_expected.get("high_risk_capture"),
            "hybrid_high_risk_capture": hybrid.get("high_risk_capture"),
            "random_expected_false_auto_clear": random_expected.get("false_auto_clear"),
            "hybrid_false_auto_clear": hybrid.get("false_auto_clear"),
        },
        "calibrated_hybrid_vs_random_review": {
            "capture_lift_vs_random": calibrated.get("capture_lift_vs_random"),
            "false_auto_clear_reduction_vs_random": calibrated.get("false_auto_clear_reduction_vs_random"),
            "random_expected_high_risk_capture": random_expected.get("high_risk_capture"),
            "calibrated_high_risk_capture": calibrated.get("high_risk_capture"),
            "random_expected_false_auto_clear": random_expected.get("false_auto_clear"),
            "calibrated_false_auto_clear": calibrated.get("false_auto_clear"),
        },
    }

    comparison_df = pd.DataFrame(rows)
    frontier_df = pd.DataFrame(frontier_rows)
    comparison_csv = out_dir / "final_test_baseline_vs_method_comparison.csv"
    frontier_csv = out_dir / "review_capacity_lift_frontier.csv"
    comparison_df.to_csv(comparison_csv, index=False)
    frontier_df.to_csv(frontier_csv, index=False)

    result = {
        "status": "PASS",
        "claim_boundary": "External public-data final-test comparison only. No proprietary bank data, production payment logs, or regulatory certification.",
        "input_csv": str(input_csv),
        "rows": int(len(df)),
        "source_counts": {str(k): int(v) for k, v in df["source_dataset"].value_counts().to_dict().items()},
        "label_counts": {str(k): int(v) for k, v in df["risk_label"].value_counts().to_dict().items()},
        "temporal_split": {
            "train_rows": int(len(train)),
            "validation_rows": int(len(val)),
            "test_rows": int(len(test)),
            "test_positives": int(y_test.sum()),
            "test_positive_rate": float(y_test.mean()),
        },
        "final_test_comparison": rows,
        "review_capacity_frontier": frontier_rows,
        "claim_summary": claim_summary,
        "external_artifacts": {
            "output_dir": str(out_dir),
            "models_dir": str(models_dir),
            "comparison_csv": str(comparison_csv),
            "frontier_csv": str(frontier_csv),
        },
    }

    (reports_dir / "baseline_vs_method_claim_metrics.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    (registry_dir / "baseline_claim_model_versions.json").write_text(
        json.dumps({
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": result["claim_boundary"],
            "external_output_dir": str(out_dir),
            "models_dir": str(models_dir),
            "comparison_csv": str(comparison_csv),
            "frontier_csv": str(frontier_csv),
        }, indent=2),
        encoding="utf-8",
    )

    display_cols = [
        "model", "pr_auc", "roc_auc", "f2", "brier", "ece",
        "high_risk_capture", "false_auto_clear", "capture_lift_vs_random",
        "false_auto_clear_reduction_vs_random"
    ]
    frontier_cols = [
        "model", "capacity", "pr_auc", "roc_auc", "brier", "ece",
        "high_risk_capture", "false_auto_clear", "capture_lift_vs_random"
    ]

    md = []
    md.append("# Baseline vs Method Claim Report\n")
    md.append("## Claim boundary\n")
    md.append("This report compares final-test baselines and reliability-enhanced methods using local external public-data samples only. It does not use proprietary bank data, production payment logs, real customer account data, or regulatory certification.\n")
    md.append("## Dataset\n")
    md.append(f"- Input common schema: `{input_csv}`\n")
    md.append(f"- Rows: `{len(df)}`\n")
    md.append(f"- Source counts: `{result['source_counts']}`\n")
    md.append(f"- Label counts: `{result['label_counts']}`\n")
    md.append("## Temporal split\n")
    md.append("```json\n" + json.dumps(result["temporal_split"], indent=2) + "\n```\n")
    md.append("## Final-test baseline vs method comparison\n")
    md.append(_md_table(rows, display_cols))
    md.append("\n## Reviewer-capacity lift frontier\n")
    md.append(_md_table(frontier_rows, frontier_cols))
    md.append("\n## Claim summary\n")
    md.append("```json\n" + json.dumps(claim_summary, indent=2) + "\n```\n")
    md.append("## How to use in resume\n")
    md.append("- Use only claims supported by this report.\n")
    md.append("- Prefer `external public-data final-test comparison` or `external public-data operational backtest` wording.\n")
    md.append("- Do not claim proprietary bank data, production deployment, JPMC data, or regulatory certification.\n")
    md.append("## External artifacts\n")
    md.append(f"- Comparison CSV: `{comparison_csv}`\n")
    md.append(f"- Review-capacity frontier CSV: `{frontier_csv}`\n")
    md.append(f"- Model artifacts: `{models_dir}`\n")

    (reports_dir / "25_baseline_vs_method_claim_report.md").write_text(
        "\n".join(md),
        encoding="utf-8",
    )

    print(json.dumps({
        "status": "PASS",
        "rows": int(len(df)),
        "test_rows": int(len(test)),
        "test_positives": int(y_test.sum()),
        "report": "reports/25_baseline_vs_method_claim_report.md",
        "claim_summary": claim_summary,
        "external_output_dir": str(out_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
