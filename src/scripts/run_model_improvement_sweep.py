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

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.scripts.run_operational_backtest import (
    _prepare_operational_frame,
    _split_train_val_test,
    _features,
    _labels,
    _score_model,
)

REVIEW_CAPACITIES = [0.05, 0.10, 0.20, 0.35, 0.50]
THRESHOLD_MODES = [
    "maximize_f2",
    "maximize_capture_under_review_capacity",
    "minimize_false_auto_clear_under_review_capacity",
    "utility_score",
]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def _safe_pr_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    y = np.asarray(y).astype(int)
    if len(np.unique(y)) < 2:
        return None
    return float(average_precision_score(y, score))


def _safe_roc_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    y = np.asarray(y).astype(int)
    if len(np.unique(y)) < 2:
        return None
    return float(roc_auc_score(y, score))


def _ece(y: np.ndarray, score: np.ndarray, n_bins: int = 10) -> float:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    value = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (score >= lo) & (score <= hi if hi == 1.0 else score < hi)
        if not np.any(mask):
            continue
        confidence = float(score[mask].mean())
        observed = float(y[mask].mean())
        value += float(mask.mean()) * abs(observed - confidence)
    return float(value)


def _threshold_metrics(y: np.ndarray, score: np.ndarray, threshold: float, review_capacity: float) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    pred = (score >= threshold).astype(int)
    positives = max(1, int(y.sum()))
    tp = int(((pred == 1) & (y == 1)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    return {
        "threshold": float(threshold),
        "rows": int(len(y)),
        "positives": int(y.sum()),
        "positive_rate": float(y.mean()) if len(y) else 0.0,
        "pr_auc": _safe_pr_auc(y, score),
        "roc_auc": _safe_roc_auc(y, score),
        "f2": float(fbeta_score(y, pred, beta=2, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, score)) if len(np.unique(y)) >= 2 else None,
        "ece": _ece(y, score),
        "high_risk_capture": float(tp / positives),
        "false_auto_clear": float(fn / positives),
        "review_burden": float(pred.mean()) if len(pred) else 0.0,
        "review_capacity": float(review_capacity),
    }


def _capacity_metrics(y: np.ndarray, score: np.ndarray, review_capacity: float) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    k = max(1, int(len(score) * review_capacity))
    selected = np.argsort(score)[::-1][:k]
    review_mask = np.zeros(len(score), dtype=bool)
    review_mask[selected] = True
    positives = max(1, int(y.sum()))
    capture = float(y[review_mask].sum() / positives)
    false_auto = float(y[~review_mask].sum() / positives)
    return {
        "rows": int(len(y)),
        "positives": int(y.sum()),
        "positive_rate": float(y.mean()) if len(y) else 0.0,
        "review_capacity": float(review_capacity),
        "pr_auc": _safe_pr_auc(y, score),
        "roc_auc": _safe_roc_auc(y, score),
        "brier": float(brier_score_loss(y, score)) if len(np.unique(y)) >= 2 else None,
        "ece": _ece(y, score),
        "high_risk_capture": capture,
        "false_auto_clear": false_auto,
        "review_burden": float(review_capacity),
        "capture_lift_vs_random": capture / review_capacity if review_capacity > 0 else None,
        "false_auto_clear_reduction_vs_random": ((1.0 - review_capacity) - false_auto) / (1.0 - review_capacity)
        if review_capacity < 1.0
        else None,
    }


def _choose_threshold(y_val: np.ndarray, score_val: np.ndarray, n_thresholds: int, review_capacity: float, mode: str) -> dict[str, Any]:
    candidates = [_threshold_metrics(y_val, score_val, float(t), review_capacity) for t in np.linspace(0.0, 1.0, n_thresholds)]
    if mode == "maximize_f2":
        best = max(candidates, key=lambda r: (r["f2"], r["recall"], -abs(r["review_burden"] - review_capacity)))
    elif mode == "maximize_capture_under_review_capacity":
        feasible = [r for r in candidates if r["review_burden"] <= review_capacity] or candidates
        best = max(feasible, key=lambda r: (r["high_risk_capture"], -r["false_auto_clear"], -r["review_burden"]))
    elif mode == "minimize_false_auto_clear_under_review_capacity":
        feasible = [r for r in candidates if r["review_burden"] <= review_capacity] or candidates
        best = min(feasible, key=lambda r: (r["false_auto_clear"], -r["high_risk_capture"], r["review_burden"]))
    elif mode == "utility_score":
        def utility(r: dict[str, Any]) -> float:
            return 2.0 * r["high_risk_capture"] - r["false_auto_clear"] - 0.25 * r["review_burden"]
        best = max(candidates, key=utility)
        best = dict(best)
        best["utility_score"] = utility(best)
    else:
        raise ValueError(f"Unknown threshold mode: {mode}")
    best = dict(best)
    best["threshold_mode"] = mode
    return best


class SigmoidScoreCalibrator:
    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=1000)

    def fit(self, score: np.ndarray, y: np.ndarray) -> "SigmoidScoreCalibrator":
        eps = 1e-6
        score = np.clip(np.asarray(score, dtype=float), eps, 1.0 - eps)
        logit = np.log(score / (1.0 - score)).reshape(-1, 1)
        self.model.fit(logit, np.asarray(y).astype(int))
        return self

    def predict_score(self, score: np.ndarray) -> np.ndarray:
        eps = 1e-6
        score = np.clip(np.asarray(score, dtype=float), eps, 1.0 - eps)
        logit = np.log(score / (1.0 - score)).reshape(-1, 1)
        return self.model.predict_proba(logit)[:, 1]


def _build_text_numeric_model(numeric_cols: list[str], max_features: int, random_state: int) -> Pipeline:
    transformers: list[tuple[str, Any, Any]] = [
        ("text", TfidfVectorizer(max_features=max_features, ngram_range=(1, 2), min_df=2), "text"),
    ]
    if numeric_cols:
        transformers.append(
            (
                "num",
                Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler(with_mean=False))]),
                numeric_cols,
            )
        )
    return Pipeline(
        [
            ("preprocess", ColumnTransformer(transformers=transformers, remainder="drop")),
            (
                "model",
                LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear", random_state=random_state),
            ),
        ]
    )


def _build_numeric_logreg(numeric_cols: list[str], random_state: int) -> Pipeline:
    return Pipeline(
        [
            (
                "preprocess",
                ColumnTransformer(
                    [
                        (
                            "num",
                            Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
                            numeric_cols,
                        )
                    ],
                    remainder="drop",
                ),
            ),
            (
                "model",
                LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear", random_state=random_state),
            ),
        ]
    )


def _build_numeric_hgb(numeric_cols: list[str], random_state: int) -> Pipeline:
    return Pipeline(
        [
            ("preprocess", ColumnTransformer([("num", SimpleImputer(strategy="median"), numeric_cols)], remainder="drop")),
            (
                "model",
                HistGradientBoostingClassifier(max_iter=120, learning_rate=0.08, l2_regularization=0.01, random_state=random_state),
            ),
        ]
    )


def _fit_predict_model(name: str, model: Any, train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame, model_path: Path) -> dict[str, Any]:
    start = time.perf_counter()
    model.fit(_features(train), _labels(train))
    fit_seconds = time.perf_counter() - start
    joblib.dump(model, model_path)
    return {
        "name": name,
        "val_score": _score_model(model, _features(val)),
        "test_score": _score_model(model, _features(test)),
        "fit_seconds": float(fit_seconds),
    }


def _fit_stacking(
    name: str,
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    base_specs: list[tuple[str, Any]],
    random_state: int,
    calibrate: bool,
    model_path: Path,
) -> dict[str, Any]:
    """Fit score-level stacking without leaking the final test set.

    The earlier version returned validation scores only for val_cal, which is
    half of the validation set. Threshold selection expects y_val and val_score
    to have the same length, so this function now returns scores for the full
    validation frame after fitting the meta model on val_meta and the optional
    calibrator on val_cal.
    """
    y_val = _labels(val)
    stratify = y_val if len(np.unique(y_val)) > 1 else None
    val_meta, val_cal = train_test_split(
        val,
        test_size=0.50,
        random_state=random_state,
        stratify=stratify,
    )

    base_models: dict[str, Any] = {}
    val_meta_scores: list[np.ndarray] = []
    val_cal_scores: list[np.ndarray] = []
    val_full_scores: list[np.ndarray] = []
    test_scores: list[np.ndarray] = []

    start = time.perf_counter()

    for base_name, model in base_specs:
        model.fit(_features(train), _labels(train))
        base_models[base_name] = model
        val_meta_scores.append(_score_model(model, _features(val_meta)))
        val_cal_scores.append(_score_model(model, _features(val_cal)))
        val_full_scores.append(_score_model(model, _features(val)))
        test_scores.append(_score_model(model, _features(test)))

    x_meta = np.vstack(val_meta_scores).T
    x_cal = np.vstack(val_cal_scores).T
    x_val_full = np.vstack(val_full_scores).T
    x_test = np.vstack(test_scores).T

    meta = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        solver="liblinear",
        random_state=random_state,
    )
    meta.fit(x_meta, _labels(val_meta))

    val_cal_score_uncal = meta.predict_proba(x_cal)[:, 1]
    val_full_score_uncal = meta.predict_proba(x_val_full)[:, 1]
    test_score_uncal = meta.predict_proba(x_test)[:, 1]

    calibrator = None
    if calibrate and len(np.unique(_labels(val_cal))) > 1:
        calibrator = SigmoidScoreCalibrator().fit(val_cal_score_uncal, _labels(val_cal))
        val_score = calibrator.predict_score(val_full_score_uncal)
        test_score = calibrator.predict_score(test_score_uncal)
    else:
        val_score = val_full_score_uncal
        test_score = test_score_uncal

    joblib.dump(
        {
            "name": name,
            "base_models": base_models,
            "meta_model": meta,
            "calibrator": calibrator,
            "calibrate": calibrate,
        },
        model_path,
    )

    return {
        "name": name,
        "val_score": val_score,
        "test_score": test_score,
        "fit_seconds": float(time.perf_counter() - start),
    }


def _evaluate_model_scores(name: str, y_val: np.ndarray, val_score: np.ndarray, y_test: np.ndarray, test_score: np.ndarray, review_capacity: float, n_thresholds: int, fit_seconds: float, allowed: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    threshold_rows = []
    best_f2_row = None
    for mode in THRESHOLD_MODES:
        selected = _choose_threshold(y_val, val_score, n_thresholds, review_capacity, mode)
        test_metrics = _threshold_metrics(y_test, test_score, selected["threshold"], review_capacity)
        row = {
            "model": name,
            "threshold_mode": mode,
            "selected_threshold": selected["threshold"],
            "val_f2": selected["f2"],
            "val_high_risk_capture": selected["high_risk_capture"],
            "val_false_auto_clear": selected["false_auto_clear"],
            "val_review_burden": selected["review_burden"],
            "test_f2": test_metrics["f2"],
            "test_precision": test_metrics["precision"],
            "test_recall": test_metrics["recall"],
            "test_high_risk_capture": test_metrics["high_risk_capture"],
            "test_false_auto_clear": test_metrics["false_auto_clear"],
            "test_review_burden": test_metrics["review_burden"],
            "test_pr_auc": test_metrics["pr_auc"],
            "test_roc_auc": test_metrics["roc_auc"],
            "test_brier": test_metrics["brier"],
            "test_ece": test_metrics["ece"],
        }
        threshold_rows.append(row)
        if mode == "maximize_f2":
            best_f2_row = row
    cap = _capacity_metrics(y_test, test_score, review_capacity)
    fixed = _threshold_metrics(y_test, test_score, 0.5, review_capacity)
    summary = {
        "model": name,
        "allowed_champion": bool(allowed),
        "fit_seconds": fit_seconds,
        "pr_auc": cap["pr_auc"],
        "roc_auc": cap["roc_auc"],
        "brier": cap["brier"],
        "ece": cap["ece"],
        "capacity_high_risk_capture": cap["high_risk_capture"],
        "capacity_false_auto_clear": cap["false_auto_clear"],
        "capture_lift_vs_random": cap["capture_lift_vs_random"],
        "false_auto_clear_reduction_vs_random": cap["false_auto_clear_reduction_vs_random"],
        "fixed05_f2": fixed["f2"],
        "fixed05_precision": fixed["precision"],
        "fixed05_recall": fixed["recall"],
        "opt_threshold": best_f2_row["selected_threshold"] if best_f2_row else None,
        "opt_f2": best_f2_row["test_f2"] if best_f2_row else None,
        "opt_precision": best_f2_row["test_precision"] if best_f2_row else None,
        "opt_recall": best_f2_row["test_recall"] if best_f2_row else None,
        "opt_high_risk_capture": best_f2_row["test_high_risk_capture"] if best_f2_row else None,
        "opt_false_auto_clear": best_f2_row["test_false_auto_clear"] if best_f2_row else None,
        "opt_review_burden": best_f2_row["test_review_burden"] if best_f2_row else None,
    }
    frontier_rows = []
    for capacity in REVIEW_CAPACITIES:
        row = _capacity_metrics(y_test, test_score, capacity)
        row["model"] = name
        row["capacity"] = capacity
        frontier_rows.append(row)
    return threshold_rows, frontier_rows, summary


def _source_slice_eval(model_name: str, test: pd.DataFrame, score: np.ndarray, review_capacity: float) -> list[dict[str, Any]]:
    work = test.copy()
    work["_score_eval"] = np.asarray(score, dtype=float)
    amount = pd.to_numeric(work.get("amount", 0.0), errors="coerce").fillna(0.0)
    source = work["source_dataset"].astype(str).str.lower()
    mid_time = work["_event_time"].quantile(0.50)
    slices = {
        "combined_test": work,
        "ibm_aml_only": work[source.str.contains("ibm|aml", regex=True, na=False)],
        "cfpb_only": work[source.str.contains("cfpb", regex=True, na=False)],
        "high_amount_slice": work[amount >= amount.quantile(0.80)],
        "low_amount_slice": work[amount <= amount.quantile(0.50)],
        "late_time_window": work[work["_event_time"] >= mid_time],
        "early_time_window": work[work["_event_time"] < mid_time],
    }
    rows = []
    for slice_name, frame in slices.items():
        if len(frame) == 0:
            rows.append({"model": model_name, "slice": slice_name, "status": "EMPTY", "rows": 0, "positives": 0})
            continue
        y = _labels(frame)
        s = frame["_score_eval"].to_numpy()
        cap = _capacity_metrics(y, s, review_capacity)
        fixed = _threshold_metrics(y, s, 0.5, review_capacity)
        rows.append({
            "model": model_name,
            "slice": slice_name,
            "status": "PASS" if len(np.unique(y)) > 1 else "ONE_CLASS",
            "rows": int(len(frame)),
            "positives": int(y.sum()),
            "positive_rate": float(y.mean()) if len(y) else 0.0,
            "pr_auc": cap["pr_auc"],
            "roc_auc": cap["roc_auc"],
            "brier": cap["brier"],
            "ece": cap["ece"],
            "high_risk_capture": cap["high_risk_capture"],
            "false_auto_clear": cap["false_auto_clear"],
            "f2_at_05": fixed["f2"],
        })
    return rows


def _constrained_champion(summary_rows: list[dict[str, Any]], slice_rows: list[dict[str, Any]], baseline_name: str) -> tuple[str, list[dict[str, Any]]]:
    baseline = next(row for row in summary_rows if row["model"] == baseline_name)

    def source_ok(model_name: str) -> bool:
        relevant = [r for r in slice_rows if r.get("model") == model_name and r.get("slice") in {"ibm_aml_only", "cfpb_only"} and r.get("status") == "PASS" and r.get("positives", 0) >= 20]
        if not relevant:
            return True
        for r in relevant:
            if r.get("pr_auc") is not None and r.get("pr_auc") < r.get("positive_rate", 0.0):
                return False
            if r.get("high_risk_capture") is not None and r.get("high_risk_capture") < 0.35:
                return False
        return True

    decisions = []
    best_name = baseline_name
    best_score = -1e18
    for row in summary_rows:
        name = row["model"]
        if not row.get("allowed_champion", False):
            eligible = False
            failed = ["not_allowed_as_champion_due_to_shortcut_or_ablation_purpose"]
        else:
            checks = {
                "pr_auc": (row["pr_auc"] or 0.0) >= (baseline["pr_auc"] or 0.0) * 0.995,
                "roc_auc": (row["roc_auc"] or 0.0) >= (baseline["roc_auc"] or 0.0) * 0.995,
                "opt_f2": (row["opt_f2"] or 0.0) >= (baseline["opt_f2"] or 0.0) * 0.98,
                "brier": (row["brier"] or 999.0) <= (baseline["brier"] or 999.0),
                "ece": (row["ece"] or 999.0) <= (baseline["ece"] or 999.0),
                "capture": (row["capacity_high_risk_capture"] or 0.0) >= (baseline["capacity_high_risk_capture"] or 0.0),
                "false_auto_clear": (row["capacity_false_auto_clear"] or 999.0) <= (baseline["capacity_false_auto_clear"] or 999.0),
                "source_ok": source_ok(name),
            }
            eligible = all(checks.values())
            failed = [k for k, ok in checks.items() if not ok]
        score = (
            0.25 * (row["pr_auc"] or 0.0)
            + 0.20 * (row["opt_f2"] or 0.0)
            + 0.20 * (row["capacity_high_risk_capture"] or 0.0)
            - 0.20 * (row["capacity_false_auto_clear"] or 1.0)
            - 0.10 * (row["brier"] or 1.0)
            - 0.05 * (row["ece"] or 1.0)
        )
        decisions.append({"model": name, "eligible": bool(eligible), "failed_constraints": ",".join(failed), "selection_score": float(score), "baseline_model": baseline_name})
        if eligible and score > best_score:
            best_score = score
            best_name = name
    return best_name, decisions


def _md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows._"
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        vals = []
        for col in columns:
            value = row.get(col)
            if isinstance(value, float):
                vals.append(f"{value:.4f}")
            elif value is None:
                vals.append("")
            else:
                vals.append(str(value))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", default=os.environ.get("PAYMENTOPS_EXTERNAL_DATA", ""))
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--max-features", type=int, default=10000)
    parser.add_argument("--review-capacity", type=float, default=0.35)
    parser.add_argument("--n-thresholds", type=int, default=101)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    external_root = Path(args.external_root)
    if not external_root.exists():
        raise FileNotFoundError(f"External root not found: {external_root}")
    input_csv = Path(args.input_csv) if args.input_csv else external_root / "validation_outputs" / "external_common_case_schema.csv"
    if not input_csv.exists():
        raise FileNotFoundError(f"Common schema input not found: {input_csv}")

    reports_dir = Path("reports")
    output_dir = external_root / "model_improvement_outputs"
    models_dir = output_dir / "models"
    _ensure_dirs(reports_dir, output_dir, models_dir)

    df = _prepare_operational_frame(input_csv)
    train, val, test = _split_train_val_test(df)
    y_val = _labels(val)
    y_test = _labels(test)
    stamp = _stamp()

    safe_numeric = ["log_amount", "text_length"]
    amount_only = ["log_amount"]
    amount_text_length = ["log_amount", "text_length"]
    source_flags = ["is_cfpb", "is_ibm_aml"]
    event_rank = ["event_rank"]
    all_numeric = ["log_amount", "text_length", "is_cfpb", "is_ibm_aml", "event_rank"]

    specs = [
        ("vanilla_text_only", _build_text_numeric_model([], args.max_features, args.random_state), True),
        ("text_plus_amount", _build_text_numeric_model(amount_only, args.max_features, args.random_state), True),
        ("text_plus_amount_text_length", _build_text_numeric_model(amount_text_length, args.max_features, args.random_state), True),
        ("text_plus_source_flags", _build_text_numeric_model(source_flags, args.max_features, args.random_state), False),
        ("text_plus_event_rank", _build_text_numeric_model(event_rank, args.max_features, args.random_state), False),
        ("text_plus_safe_numeric_without_source_or_event_rank", _build_text_numeric_model(safe_numeric, args.max_features, args.random_state), True),
        ("text_plus_all_numeric", _build_text_numeric_model(all_numeric, args.max_features, args.random_state), False),
        ("numeric_hist_gradient_boosting_safe", _build_numeric_hgb(safe_numeric, args.random_state), True),
    ]

    model_outputs = []
    allowed_map: dict[str, bool] = {}
    for name, model, allowed in specs:
        model_outputs.append(_fit_predict_model(name, model, train, val, test, models_dir / f"{stamp}_{name}.joblib"))
        allowed_map[name] = allowed

    stack_text_amount = _fit_stacking(
        "score_level_stacking_text_amount",
        train,
        val,
        test,
        [("text", _build_text_numeric_model([], args.max_features, args.random_state)), ("amount", _build_numeric_logreg(amount_only, args.random_state))],
        args.random_state,
        False,
        models_dir / f"{stamp}_score_level_stacking_text_amount.joblib",
    )
    model_outputs.append(stack_text_amount)
    allowed_map[stack_text_amount["name"]] = True

    stack_text_safe = _fit_stacking(
        "score_level_stacking_text_safe_numeric",
        train,
        val,
        test,
        [
            ("text", _build_text_numeric_model([], args.max_features, args.random_state)),
            ("safe_numeric", _build_numeric_logreg(safe_numeric, args.random_state)),
            ("hgb_safe_numeric", _build_numeric_hgb(safe_numeric, args.random_state)),
        ],
        args.random_state,
        False,
        models_dir / f"{stamp}_score_level_stacking_text_safe_numeric.joblib",
    )
    model_outputs.append(stack_text_safe)
    allowed_map[stack_text_safe["name"]] = True

    calibrated_stack = _fit_stacking(
        "calibrated_stacking_text_safe_numeric",
        train,
        val,
        test,
        [
            ("text", _build_text_numeric_model([], args.max_features, args.random_state)),
            ("safe_numeric", _build_numeric_logreg(safe_numeric, args.random_state)),
            ("hgb_safe_numeric", _build_numeric_hgb(safe_numeric, args.random_state)),
        ],
        args.random_state,
        True,
        models_dir / f"{stamp}_calibrated_stacking_text_safe_numeric.joblib",
    )
    model_outputs.append(calibrated_stack)
    allowed_map[calibrated_stack["name"]] = True

    summary_rows = []
    threshold_rows = []
    frontier_rows = []
    slice_rows = []
    for output in model_outputs:
        name = output["name"]
        t_rows, f_rows, summary = _evaluate_model_scores(
            name,
            y_val,
            output["val_score"],
            y_test,
            output["test_score"],
            args.review_capacity,
            args.n_thresholds,
            output["fit_seconds"],
            allowed_map.get(name, False),
        )
        threshold_rows.extend(t_rows)
        frontier_rows.extend(f_rows)
        summary_rows.append(summary)
        slice_rows.extend(_source_slice_eval(name, test, output["test_score"], args.review_capacity))

    champion_name, selection_rows = _constrained_champion(summary_rows, slice_rows, "vanilla_text_only")
    baseline = next(r for r in summary_rows if r["model"] == "vanilla_text_only")
    champion = next(r for r in summary_rows if r["model"] == champion_name)

    if champion_name != "vanilla_text_only":
        resume_safe_claims = [
            f"Constrained champion `{champion_name}` satisfied baseline-safety constraints against the vanilla text baseline across ranking, threshold-optimized detection, calibration, and review-capacity metrics."
        ]
    else:
        resume_safe_claims = [
            "Vanilla text baseline remained the strongest constrained model; use workflow-level claims rather than claiming a new hybrid model beat vanilla across all metrics."
        ]
    resume_safe_claims.append(
        f"At {args.review_capacity:.0%} review capacity, the selected constrained workflow captured {champion['capacity_high_risk_capture']:.4f} of high-risk cases with false auto-clear {champion['capacity_false_auto_clear']:.4f}."
    )
    resume_safe_claims.append(
        f"Validation-selected threshold optimization selected threshold {champion['opt_threshold']:.4f} for `{champion_name}`, producing optimized F2 {champion['opt_f2']:.4f} on the future test split."
    )
    claims_not_to_use = [
        "Do not claim hybrid or all-numeric features improved every metric unless the constrained champion is not vanilla and all hard constraints passed.",
        "Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.",
        "Do not claim source-identity features are production-safe; they are ablation-only unless source-separated evaluation supports them.",
    ]

    pd.DataFrame(summary_rows).to_csv(output_dir / "feature_ablation_results.csv", index=False)
    pd.DataFrame(threshold_rows).to_csv(output_dir / "threshold_optimization_results.csv", index=False)
    pd.DataFrame(slice_rows).to_csv(output_dir / "source_slice_results.csv", index=False)
    pd.DataFrame(selection_rows).to_csv(output_dir / "constrained_champion_selection.csv", index=False)
    pd.DataFrame(frontier_rows).to_csv(output_dir / "review_capacity_frontier_improvement.csv", index=False)

    result = {
        "status": "PASS",
        "claim_boundary": "External public-data model-improvement sweep only. No proprietary bank data, production payment logs, real customer account data, or regulatory certification.",
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
        "baseline_model": "vanilla_text_only",
        "constrained_champion": champion_name,
        "baseline_metrics": baseline,
        "champion_metrics": champion,
        "feature_ablation_summary": summary_rows,
        "threshold_optimization_results": threshold_rows,
        "source_slice_results": slice_rows,
        "constrained_champion_selection": selection_rows,
        "resume_safe_claims": resume_safe_claims,
        "claims_not_to_use": claims_not_to_use,
        "external_artifacts": {
            "output_dir": str(output_dir),
            "models_dir": str(models_dir),
            "feature_ablation_results": str(output_dir / "feature_ablation_results.csv"),
            "threshold_optimization_results": str(output_dir / "threshold_optimization_results.csv"),
            "source_slice_results": str(output_dir / "source_slice_results.csv"),
            "constrained_champion_selection": str(output_dir / "constrained_champion_selection.csv"),
        },
    }

    (reports_dir / "model_improvement_sweep_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    summary_cols = [
        "model",
        "allowed_champion",
        "pr_auc",
        "roc_auc",
        "brier",
        "ece",
        "capacity_high_risk_capture",
        "capacity_false_auto_clear",
        "capture_lift_vs_random",
        "opt_threshold",
        "opt_f2",
        "opt_precision",
        "opt_recall",
        "opt_review_burden",
    ]
    md = [
        "# Model Improvement Sweep\n",
        "## Claim boundary\n",
        result["claim_boundary"] + "\n",
        "## Dataset\n",
        f"- Input CSV: `{input_csv}`\n",
        f"- Rows: `{len(df)}`\n",
        f"- Source counts: `{result['source_counts']}`\n",
        f"- Label counts: `{result['label_counts']}`\n",
        "## Temporal split\n",
        "```json\n" + json.dumps(result["temporal_split"], indent=2) + "\n```\n",
        "## Feature ablation and calibrated stacking summary\n",
        _md_table(summary_rows, summary_cols),
        "\n## Constrained champion selection\n",
        _md_table(selection_rows, ["model", "eligible", "failed_constraints", "selection_score", "baseline_model"]),
        "\n## Selected constrained champion\n",
        f"- Champion decision: `{champion_name}`\n",
        "## Baseline metrics\n",
        "```json\n" + json.dumps(baseline, indent=2) + "\n```\n",
        "## Champion metrics\n",
        "```json\n" + json.dumps(champion, indent=2) + "\n```\n",
        "## Source-separated evaluation\n",
        _md_table(slice_rows, ["model", "slice", "status", "rows", "positives", "positive_rate", "pr_auc", "roc_auc", "brier", "ece", "high_risk_capture", "false_auto_clear", "f2_at_05"]),
        "\n## Resume-safe claims\n",
    ]
    md.extend([f"- {claim}" for claim in resume_safe_claims])
    md.append("\n## Claims not to use\n")
    md.extend([f"- {claim}" for claim in claims_not_to_use])
    md.append("\n## External artifacts\n")
    md.extend([f"- {key}: `{value}`" for key, value in result["external_artifacts"].items()])
    (reports_dir / "26_model_improvement_sweep.md").write_text("\n".join(md), encoding="utf-8")

    claims_md = ["# Model Improvement Resume Claims\n", "## Use these claims only if consistent with the latest report\n"]
    claims_md.extend([f"- {claim}" for claim in resume_safe_claims])
    claims_md.append("\n## Do not use\n")
    claims_md.extend([f"- {claim}" for claim in claims_not_to_use])
    (reports_dir / "26_model_improvement_resume_claims.md").write_text("\n".join(claims_md), encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "rows": int(len(df)),
        "test_rows": int(len(test)),
        "baseline_model": "vanilla_text_only",
        "constrained_champion": champion_name,
        "baseline_metrics": baseline,
        "champion_metrics": champion,
        "resume_safe_claims": resume_safe_claims,
        "claims_not_to_use": claims_not_to_use,
        "report": "reports/26_model_improvement_sweep.md",
        "external_output_dir": str(output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
