from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, fbeta_score, precision_score, recall_score, roc_auc_score

from src.scripts.run_source_specific_aml_behavior_experiment import (
    BehaviorFeatureMapper,
    _best_threshold,
    _build_behavior_hgb,
    _build_text_model,
    _combined_features,
    _constant_score,
    _ensure_dirs,
    _eval_scores,
    _find_ibm_file,
    _fit_if_two_classes,
    _load_ibm_raw_sample,
    _model_score,
    _prepare_cfpb,
    _split_df,
    _standardize_ibm_raw,
    _text_features,
    _write_md_table,
    _behavior_features,
)


REVIEW_CAPACITIES = [0.05, 0.10, 0.20, 0.35, 0.50]


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_pr_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    if len(np.unique(y)) < 2:
        return None
    return float(average_precision_score(y, score))


def _safe_roc_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    if len(np.unique(y)) < 2:
        return None
    return float(roc_auc_score(y, score))


def _ece(y: np.ndarray, score: np.ndarray, n_bins: int = 10) -> float:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    total = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        if hi == 1.0:
            mask = (score >= lo) & (score <= hi)
        else:
            mask = (score >= lo) & (score < hi)
        if np.any(mask):
            total += float(mask.mean()) * abs(float(y[mask].mean()) - float(score[mask].mean()))
    return float(total)


def _metrics_at_threshold(y: np.ndarray, score: np.ndarray, review_capacity: float, threshold: float) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    pred = (score >= threshold).astype(int)

    k = max(1, int(len(score) * review_capacity))
    top_idx = np.argsort(score)[::-1][:k]
    review = np.zeros(len(score), dtype=bool)
    review[top_idx] = True
    positives = max(1, int(y.sum()))

    return {
        "rows": int(len(y)),
        "positives": int(y.sum()),
        "positive_rate": float(y.mean()) if len(y) else 0.0,
        "threshold": float(threshold),
        "pr_auc": _safe_pr_auc(y, score),
        "roc_auc": _safe_roc_auc(y, score),
        "f2": float(fbeta_score(y, pred, beta=2, zero_division=0)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "brier": float(brier_score_loss(y, score)) if len(np.unique(y)) > 1 else None,
        "ece": _ece(y, score),
        "high_risk_capture": float(y[review].sum() / positives),
        "false_auto_clear": float(y[~review].sum() / positives),
        "review_capacity": float(review_capacity),
        "capture_lift_vs_random": float(y[review].sum() / positives / review_capacity) if review_capacity > 0 else None,
        "false_auto_clear_reduction_vs_random": ((1.0 - review_capacity) - float(y[~review].sum() / positives)) / (1.0 - review_capacity)
        if review_capacity < 1.0
        else None,
    }


def _objective(m: dict[str, Any]) -> float:
    return (
        0.30 * (m.get("pr_auc") or 0.0)
        + 0.25 * (m.get("f2") or 0.0)
        + 0.20 * (m.get("high_risk_capture") or 0.0)
        - 0.15 * (m.get("false_auto_clear") or 1.0)
        - 0.10 * (m.get("brier") or 1.0)
    )


def _pct_change(new: float | None, old: float | None, lower_is_better: bool = False) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return float((old - new) / old if lower_is_better else (new - old) / old)


class SourceMinMaxAligner:
    def __init__(self) -> None:
        self.params: dict[str, tuple[float, float]] = {}

    def fit(self, sources: pd.Series, score: np.ndarray) -> "SourceMinMaxAligner":
        score = np.asarray(score, dtype=float)
        for source in sorted(pd.Series(sources).astype(str).unique()):
            mask = pd.Series(sources).astype(str).to_numpy() == source
            vals = score[mask]
            if len(vals) == 0:
                self.params[source] = (0.0, 1.0)
            else:
                self.params[source] = (float(np.nanmin(vals)), float(np.nanmax(vals)))
        return self

    def transform(self, sources: pd.Series, score: np.ndarray) -> np.ndarray:
        out = np.zeros(len(score), dtype=float)
        src_values = pd.Series(sources).astype(str).to_numpy()
        score = np.asarray(score, dtype=float)
        for source in np.unique(src_values):
            mask = src_values == source
            lo, hi = self.params.get(str(source), (float(np.nanmin(score)), float(np.nanmax(score))))
            if hi <= lo:
                out[mask] = 0.5
            else:
                out[mask] = (score[mask] - lo) / (hi - lo)
        return np.clip(out, 0.0, 1.0)


class SourcePercentileAligner:
    def __init__(self) -> None:
        self.sorted_scores: dict[str, np.ndarray] = {}

    def fit(self, sources: pd.Series, score: np.ndarray) -> "SourcePercentileAligner":
        src_values = pd.Series(sources).astype(str).to_numpy()
        score = np.asarray(score, dtype=float)
        for source in np.unique(src_values):
            vals = np.sort(score[src_values == source])
            self.sorted_scores[str(source)] = vals if len(vals) else np.array([0.5])
        return self

    def transform(self, sources: pd.Series, score: np.ndarray) -> np.ndarray:
        src_values = pd.Series(sources).astype(str).to_numpy()
        score = np.asarray(score, dtype=float)
        out = np.zeros(len(score), dtype=float)
        for source in np.unique(src_values):
            mask = src_values == source
            ref = self.sorted_scores.get(str(source))
            if ref is None or len(ref) == 0:
                out[mask] = 0.5
            else:
                out[mask] = np.searchsorted(ref, score[mask], side="right") / max(1, len(ref))
        return np.clip(out, 0.0, 1.0)


class SigmoidScoreCalibrator:
    def __init__(self) -> None:
        self.model = LogisticRegression(max_iter=1000)
        self.fitted = False
        self.constant: float | None = None

    def fit(self, score: np.ndarray, y: np.ndarray) -> "SigmoidScoreCalibrator":
        y = np.asarray(y).astype(int)
        if len(np.unique(y)) < 2:
            self.constant = float(y.mean()) if len(y) else 0.0
            self.fitted = False
            return self
        eps = 1e-6
        s = np.clip(np.asarray(score, dtype=float), eps, 1.0 - eps)
        x = np.log(s / (1.0 - s)).reshape(-1, 1)
        self.model.fit(x, y)
        self.fitted = True
        return self

    def transform(self, score: np.ndarray) -> np.ndarray:
        if not self.fitted:
            return np.full(len(score), 0.0 if self.constant is None else self.constant, dtype=float)
        eps = 1e-6
        s = np.clip(np.asarray(score, dtype=float), eps, 1.0 - eps)
        x = np.log(s / (1.0 - s)).reshape(-1, 1)
        return self.model.predict_proba(x)[:, 1]


class SourceCalibrator:
    def __init__(self, method: str) -> None:
        self.method = method
        self.models: dict[str, Any] = {}
        self.constants: dict[str, float] = {}

    def fit(self, sources: pd.Series, score: np.ndarray, y: np.ndarray) -> "SourceCalibrator":
        src_values = pd.Series(sources).astype(str).to_numpy()
        score = np.asarray(score, dtype=float)
        y = np.asarray(y).astype(int)
        for source in np.unique(src_values):
            mask = src_values == source
            ys = y[mask]
            ss = np.clip(score[mask], 0.0, 1.0)
            if len(np.unique(ys)) < 2:
                self.constants[str(source)] = float(ys.mean()) if len(ys) else 0.0
                continue
            if self.method == "sigmoid":
                model = SigmoidScoreCalibrator().fit(ss, ys)
            elif self.method == "isotonic":
                model = IsotonicRegression(out_of_bounds="clip")
                model.fit(ss, ys)
            else:
                raise ValueError(f"Unknown calibration method: {self.method}")
            self.models[str(source)] = model
        return self

    def transform(self, sources: pd.Series, score: np.ndarray) -> np.ndarray:
        src_values = pd.Series(sources).astype(str).to_numpy()
        score = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
        out = np.zeros(len(score), dtype=float)
        for source in np.unique(src_values):
            mask = src_values == source
            key = str(source)
            if key in self.models:
                model = self.models[key]
                if isinstance(model, SigmoidScoreCalibrator):
                    out[mask] = model.transform(score[mask])
                else:
                    out[mask] = model.predict(score[mask])
            else:
                out[mask] = self.constants.get(key, 0.0)
        return np.clip(out, 0.0, 1.0)


def _source_group(df: pd.DataFrame) -> pd.Series:
    source = df["source_dataset"].astype(str).str.lower()
    return pd.Series(np.where(source.str.contains("ibm|aml", regex=True, na=False), "ibm_aml", "cfpb"), index=df.index)


def _fit_cfpb_text_model(cfpb_train: pd.DataFrame, max_features: int, random_state: int) -> Any | None:
    if len(cfpb_train) == 0:
        return None
    return _fit_if_two_classes(_build_text_model(max_features, random_state), cfpb_train, _text_features)


def _score_cfpb(model: Any | None, train: pd.DataFrame, df: pd.DataFrame) -> np.ndarray:
    if len(df) == 0:
        return np.array([], dtype=float)
    if model is None:
        return _constant_score(train, len(df))
    return _model_score(model, _text_features(df))


def _make_source_router_scores(
    df: pd.DataFrame,
    ibm_behavior_hgb: Any,
    cfpb_model: Any | None,
    cfpb_train: pd.DataFrame,
) -> np.ndarray:
    score = np.zeros(len(df), dtype=float)
    source = df["source_dataset"].astype(str).str.lower()
    is_ibm = source.str.contains("ibm|aml", regex=True, na=False).to_numpy()
    is_cfpb = source.str.contains("cfpb", regex=True, na=False).to_numpy()
    if is_ibm.any():
        score[is_ibm] = _model_score(ibm_behavior_hgb, _behavior_features(df.loc[is_ibm]))
    if is_cfpb.any():
        score[is_cfpb] = _score_cfpb(cfpb_model, cfpb_train, df.loc[is_cfpb])
    return np.clip(score, 0.0, 1.0)


def _select_threshold_by_validation(y_val: np.ndarray, val_score: np.ndarray, n_thresholds: int) -> float:
    return float(_best_threshold(y_val, np.clip(val_score, 0.0, 1.0), n_thresholds))


def _candidate_eval(
    name: str,
    y_val: np.ndarray,
    val_score: np.ndarray,
    y_test: np.ndarray,
    test_score: np.ndarray,
    review_capacity: float,
    n_thresholds: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    threshold = _select_threshold_by_validation(y_val, val_score, n_thresholds)
    row = _metrics_at_threshold(y_test, test_score, review_capacity, threshold)
    row.update({"model": name, "selected_threshold": threshold})
    if extra:
        row.update(extra)
    return row


def _val_eval_for_selection(
    name: str,
    y_val: np.ndarray,
    val_score: np.ndarray,
    review_capacity: float,
    n_thresholds: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    threshold = _select_threshold_by_validation(y_val, val_score, n_thresholds)
    row = _metrics_at_threshold(y_val, val_score, review_capacity, threshold)
    row.update({"model": name, "selected_threshold": threshold, "selection_objective": _objective(row)})
    if extra:
        row.update(extra)
    return row


def _passes_constraints(candidate: dict[str, Any], baseline: dict[str, Any]) -> tuple[bool, list[str]]:
    checks = {
        "pr_auc": (candidate.get("pr_auc") or 0.0) >= (baseline.get("pr_auc") or 0.0),
        "f2": (candidate.get("f2") or 0.0) >= (baseline.get("f2") or 0.0) * 0.98,
        "brier": (candidate.get("brier") or 999.0) <= (baseline.get("brier") or 999.0),
        "high_risk_capture": (candidate.get("high_risk_capture") or 0.0) >= (baseline.get("high_risk_capture") or 0.0),
        "false_auto_clear": (candidate.get("false_auto_clear") or 999.0) <= (baseline.get("false_auto_clear") or 999.0),
    }
    failed = [k for k, ok in checks.items() if not ok]
    return all(checks.values()), failed


def _source_slice_eval(model_name: str, df: pd.DataFrame, score: np.ndarray, review_capacity: float, threshold: float) -> list[dict[str, Any]]:
    temp = df.copy()
    temp["_score"] = np.clip(np.asarray(score, dtype=float), 0.0, 1.0)
    source = temp["source_dataset"].astype(str).str.lower()
    slices = {
        "combined_test": temp,
        "ibm_aml_only": temp[source.str.contains("ibm|aml", regex=True, na=False)],
        "cfpb_only": temp[source.str.contains("cfpb", regex=True, na=False)],
    }
    rows: list[dict[str, Any]] = []
    for slice_name, frame in slices.items():
        if len(frame) == 0:
            continue
        row = _metrics_at_threshold(frame["risk_label"].astype(int).to_numpy(), frame["_score"].to_numpy(), review_capacity, threshold)
        row.update({"model": model_name, "slice": slice_name})
        rows.append(row)
    return rows


def _claim_summary(best_test: dict[str, Any], baseline_test: dict[str, Any]) -> dict[str, Any]:
    return {
        "best_aligned_vs_combined_text_baseline": {
            "pr_auc_pct_change": _pct_change(best_test.get("pr_auc"), baseline_test.get("pr_auc")),
            "roc_auc_pct_change": _pct_change(best_test.get("roc_auc"), baseline_test.get("roc_auc")),
            "f2_pct_change": _pct_change(best_test.get("f2"), baseline_test.get("f2")),
            "brier_pct_reduction": _pct_change(best_test.get("brier"), baseline_test.get("brier"), lower_is_better=True),
            "ece_pct_reduction": _pct_change(best_test.get("ece"), baseline_test.get("ece"), lower_is_better=True),
            "high_risk_capture_point_change": (best_test.get("high_risk_capture") or 0.0) - (baseline_test.get("high_risk_capture") or 0.0),
            "false_auto_clear_pct_reduction": _pct_change(best_test.get("false_auto_clear"), baseline_test.get("false_auto_clear"), lower_is_better=True),
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", default=os.environ.get("PAYMENTOPS_EXTERNAL_DATA", ""))
    parser.add_argument("--common-csv", default=None)
    parser.add_argument("--max-ibm-rows", type=int, default=500000)
    parser.add_argument("--chunk-size", type=int, default=100000)
    parser.add_argument("--max-chunks", type=int, default=80)
    parser.add_argument("--max-features", type=int, default=10000)
    parser.add_argument("--review-capacity", type=float, default=0.35)
    parser.add_argument("--n-thresholds", type=int, default=101)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    external_root = Path(args.external_root)
    if not external_root.exists():
        raise FileNotFoundError(f"External root not found: {external_root}")

    common_csv = Path(args.common_csv) if args.common_csv else external_root / "validation_outputs" / "external_common_case_schema.csv"
    if not common_csv.exists():
        raise FileNotFoundError(f"Common schema CSV not found: {common_csv}")

    reports_dir = Path("reports")
    output_dir = external_root / "score_alignment_blend_outputs"
    models_dir = output_dir / "models"
    _ensure_dirs(reports_dir, output_dir, models_dir)
    stamp = _now_stamp()

    # Build the same raw IBM + CFPB temporal split used by the source-specific experiment.
    ibm_path = _find_ibm_file(external_root)
    raw_ibm = _load_ibm_raw_sample(ibm_path, args.max_ibm_rows, args.chunk_size, args.max_chunks, args.random_state)
    ibm_df = _standardize_ibm_raw(raw_ibm)
    ibm_train_raw, ibm_val_raw, ibm_test_raw = _split_df(ibm_df)

    mapper = BehaviorFeatureMapper().fit(ibm_train_raw)
    ibm_train = mapper.transform(ibm_train_raw)
    ibm_val = mapper.transform(ibm_val_raw)
    ibm_test = mapper.transform(ibm_test_raw)

    cfpb_df = _prepare_cfpb(common_csv)
    if len(cfpb_df) > 0:
        cfpb_train, cfpb_val, cfpb_test = _split_df(cfpb_df)
    else:
        cfpb_train = cfpb_val = cfpb_test = pd.DataFrame()

    combined_train = pd.concat([cfpb_train, ibm_train], ignore_index=True).sort_values(["_event_time", "case_id"]).reset_index(drop=True)
    combined_val = pd.concat([cfpb_val, ibm_val], ignore_index=True).sort_values(["_event_time", "case_id"]).reset_index(drop=True)
    combined_test = pd.concat([cfpb_test, ibm_test], ignore_index=True).sort_values(["_event_time", "case_id"]).reset_index(drop=True)

    y_val = combined_val["risk_label"].astype(int).to_numpy()
    y_test = combined_test["risk_label"].astype(int).to_numpy()
    source_val = _source_group(combined_val)
    source_test = _source_group(combined_test)

    # Strong combined text baseline.
    combined_text = _build_text_model(args.max_features, args.random_state)
    combined_text.fit(_text_features(combined_train), combined_train["risk_label"].astype(int))
    baseline_val_score = _model_score(combined_text, _text_features(combined_val))
    baseline_test_score = _model_score(combined_text, _text_features(combined_test))
    joblib.dump(combined_text, models_dir / f"{stamp}_combined_text_logreg_baseline.joblib")

    # Source models.
    ibm_behavior_hgb = _build_behavior_hgb(args.random_state)
    ibm_behavior_hgb.fit(_behavior_features(ibm_train), ibm_train["risk_label"].astype(int))
    joblib.dump(ibm_behavior_hgb, models_dir / f"{stamp}_ibm_behavior_hgb.joblib")

    cfpb_model = _fit_cfpb_text_model(cfpb_train, args.max_features, args.random_state)
    if cfpb_model is not None:
        joblib.dump(cfpb_model, models_dir / f"{stamp}_cfpb_text_logreg.joblib")

    raw_router_val_score = _make_source_router_scores(combined_val, ibm_behavior_hgb, cfpb_model, cfpb_train)
    raw_router_test_score = _make_source_router_scores(combined_test, ibm_behavior_hgb, cfpb_model, cfpb_train)

    # Source-wise score alignment variants. Fit all transforms on validation only, then apply to test.
    minmax = SourceMinMaxAligner().fit(source_val, raw_router_val_score)
    minmax_val_score = minmax.transform(source_val, raw_router_val_score)
    minmax_test_score = minmax.transform(source_test, raw_router_test_score)

    percentile = SourcePercentileAligner().fit(source_val, raw_router_val_score)
    percentile_val_score = percentile.transform(source_val, raw_router_val_score)
    percentile_test_score = percentile.transform(source_test, raw_router_test_score)

    sigmoid = SourceCalibrator("sigmoid").fit(source_val, raw_router_val_score, y_val)
    sigmoid_val_score = sigmoid.transform(source_val, raw_router_val_score)
    sigmoid_test_score = sigmoid.transform(source_test, raw_router_test_score)

    isotonic = SourceCalibrator("isotonic").fit(source_val, raw_router_val_score, y_val)
    isotonic_val_score = isotonic.transform(source_val, raw_router_val_score)
    isotonic_test_score = isotonic.transform(source_test, raw_router_test_score)

    base_candidates = {
        "combined_text_logreg_baseline": (baseline_val_score, baseline_test_score),
        "raw_source_router": (raw_router_val_score, raw_router_test_score),
        "source_minmax_router": (minmax_val_score, minmax_test_score),
        "source_percentile_router": (percentile_val_score, percentile_test_score),
        "source_sigmoid_calibrated_router": (sigmoid_val_score, sigmoid_test_score),
        "source_isotonic_calibrated_router": (isotonic_val_score, isotonic_test_score),
    }

    validation_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []

    baseline_val_row = _val_eval_for_selection(
        "combined_text_logreg_baseline",
        y_val,
        baseline_val_score,
        args.review_capacity,
        args.n_thresholds,
        extra={"family": "baseline", "alpha_baseline": 1.0, "source_variant": "none"},
    )
    baseline_test_row = _candidate_eval(
        "combined_text_logreg_baseline",
        y_val,
        baseline_val_score,
        y_test,
        baseline_test_score,
        args.review_capacity,
        args.n_thresholds,
        extra={"family": "baseline", "alpha_baseline": 1.0, "source_variant": "none"},
    )

    for name, (val_score, test_score) in base_candidates.items():
        extra = {"family": "base_candidate", "alpha_baseline": None, "source_variant": name}
        validation_rows.append(_val_eval_for_selection(name, y_val, val_score, args.review_capacity, args.n_thresholds, extra=extra))
        test_rows.append(_candidate_eval(name, y_val, val_score, y_test, test_score, args.review_capacity, args.n_thresholds, extra=extra))

    blend_source_variants = {
        "raw_source_router": (raw_router_val_score, raw_router_test_score),
        "source_minmax_router": (minmax_val_score, minmax_test_score),
        "source_percentile_router": (percentile_val_score, percentile_test_score),
        "source_sigmoid_calibrated_router": (sigmoid_val_score, sigmoid_test_score),
        "source_isotonic_calibrated_router": (isotonic_val_score, isotonic_test_score),
    }

    blend_validation_rows: list[dict[str, Any]] = []
    blend_test_rows_by_name: dict[str, dict[str, Any]] = {}
    blend_scores_by_name: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    for source_name, (src_val, src_test) in blend_source_variants.items():
        for alpha in np.linspace(0.0, 1.0, 21):
            alpha = float(alpha)
            name = f"blend_baseline_{alpha:.2f}_plus_{source_name}_{1-alpha:.2f}"
            val_score = np.clip(alpha * baseline_val_score + (1.0 - alpha) * src_val, 0.0, 1.0)
            test_score = np.clip(alpha * baseline_test_score + (1.0 - alpha) * src_test, 0.0, 1.0)
            extra = {"family": "blend", "alpha_baseline": alpha, "source_variant": source_name}
            val_row = _val_eval_for_selection(name, y_val, val_score, args.review_capacity, args.n_thresholds, extra=extra)
            is_eligible, failed = _passes_constraints(val_row, baseline_val_row)
            val_row["eligible_on_validation"] = bool(is_eligible)
            val_row["failed_validation_constraints"] = ",".join(failed)
            blend_validation_rows.append(val_row)
            blend_scores_by_name[name] = (val_score, test_score)

            test_row = _candidate_eval(name, y_val, val_score, y_test, test_score, args.review_capacity, args.n_thresholds, extra=extra)
            blend_test_rows_by_name[name] = test_row

    eligible = [r for r in blend_validation_rows if r.get("eligible_on_validation")]
    if eligible:
        selected_val_row = max(eligible, key=_objective)
        selection_status = "PASS_ELIGIBLE_BLEND_FOUND"
    else:
        selected_val_row = max(blend_validation_rows, key=_objective)
        selection_status = "NO_BLEND_MET_ALL_VALIDATION_CONSTRAINTS_USE_BEST_OBJECTIVE_FOR_DIAGNOSTICS"

    selected_name = selected_val_row["model"]
    selected_val_score, selected_test_score = blend_scores_by_name[selected_name]
    selected_test_row = blend_test_rows_by_name[selected_name]
    selected_test_constraints_pass, selected_test_failed = _passes_constraints(selected_test_row, baseline_test_row)
    selected_test_row["test_constraints_pass"] = bool(selected_test_constraints_pass)
    selected_test_row["failed_test_constraints"] = ",".join(selected_test_failed)
    selected_test_row["selection_status"] = selection_status

    validation_rows.extend(blend_validation_rows)
    test_rows.extend(blend_test_rows_by_name.values())

    pd.DataFrame(validation_rows).to_csv(output_dir / "score_alignment_validation_results.csv", index=False)
    pd.DataFrame(test_rows).to_csv(output_dir / "score_alignment_test_results.csv", index=False)

    selected_threshold = float(selected_test_row["selected_threshold"])
    slice_rows = []
    slice_rows.extend(_source_slice_eval("combined_text_logreg_baseline", combined_test, baseline_test_score, args.review_capacity, baseline_test_row["selected_threshold"]))
    slice_rows.extend(_source_slice_eval(selected_name, combined_test, selected_test_score, args.review_capacity, selected_threshold))
    pd.DataFrame(slice_rows).to_csv(output_dir / "score_alignment_source_slice_results.csv", index=False)

    claim_summary = _claim_summary(selected_test_row, baseline_test_row)

    resume_safe_claims: list[str] = [
        "Added source-wise score normalization, percentile alignment, calibration, and validation-tuned blending to diagnose and reduce score-scale mismatch between CFPB text and IBM AML behavior models.",
    ]
    claims_not_to_use: list[str] = [
        "Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.",
        "Do not claim the aligned router beat the combined baseline unless test_constraints_pass is true and PR-AUC/F2 are not degraded.",
        "Do not claim normalization alone solved the issue; use the selected validation-tuned blend result.",
    ]

    if selected_test_constraints_pass:
        resume_safe_claims.append(
            "Selected a validation-constrained blended router that preserved or improved combined-baseline PR-AUC/F2 while reducing calibration error and false auto-clear on the future test split."
        )
    else:
        resume_safe_claims.append(
            "Validation-tuned blending improved score-alignment diagnostics, but final test constraints did not all pass; use as model-risk analysis rather than a full baseline-outperformance claim."
        )

    result = {
        "status": "PASS",
        "claim_boundary": "External public-data score-alignment and source-blending experiment only. No proprietary bank data, production payment logs, real customer account data, or regulatory certification.",
        "ibm_raw_path": str(ibm_path),
        "common_csv": str(common_csv),
        "rows": {
            "ibm_total": int(len(ibm_df)),
            "cfpb_total": int(len(cfpb_df)),
            "combined_train": int(len(combined_train)),
            "combined_val": int(len(combined_val)),
            "combined_test": int(len(combined_test)),
        },
        "baseline_test": baseline_test_row,
        "selected_validation_row": selected_val_row,
        "selected_test_row": selected_test_row,
        "selection_status": selection_status,
        "claim_summary": claim_summary,
        "validation_results": validation_rows,
        "test_results": test_rows,
        "source_slice_results": slice_rows,
        "resume_safe_claims": resume_safe_claims,
        "claims_not_to_use": claims_not_to_use,
        "external_artifacts": {
            "output_dir": str(output_dir),
            "models_dir": str(models_dir),
            "score_alignment_validation_results": str(output_dir / "score_alignment_validation_results.csv"),
            "score_alignment_test_results": str(output_dir / "score_alignment_test_results.csv"),
            "score_alignment_source_slice_results": str(output_dir / "score_alignment_source_slice_results.csv"),
        },
    }

    (reports_dir / "score_alignment_blend_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    columns = [
        "model",
        "family",
        "source_variant",
        "alpha_baseline",
        "rows",
        "positives",
        "pr_auc",
        "roc_auc",
        "f2",
        "brier",
        "ece",
        "high_risk_capture",
        "false_auto_clear",
        "capture_lift_vs_random",
        "selected_threshold",
        "test_constraints_pass",
    ]
    top_test_rows = sorted(test_rows, key=_objective, reverse=True)[:20]

    md = []
    md.append("# Score Alignment and Blended Router Experiment\n")
    md.append("## Claim boundary\n")
    md.append(result["claim_boundary"] + "\n")
    md.append("## Why this experiment was added\n")
    md.append(
        "The previous source-specific router improved calibration and false auto-clear but degraded global PR-AUC/F2, suggesting source score-scale mismatch. This experiment fits source-wise MinMax, percentile, sigmoid, isotonic, and validation-tuned baseline-plus-source blends.\n"
    )
    md.append("## Data\n")
    md.append("```json\n" + json.dumps(result["rows"], indent=2) + "\n```\n")
    md.append("## Baseline test metrics\n")
    md.append("```json\n" + json.dumps(baseline_test_row, indent=2) + "\n```\n")
    md.append("## Selected blend on validation\n")
    md.append("```json\n" + json.dumps(selected_val_row, indent=2) + "\n```\n")
    md.append("## Selected blend on final test\n")
    md.append("```json\n" + json.dumps(selected_test_row, indent=2) + "\n```\n")
    md.append("## Top test candidates by objective\n")
    md.append(_write_md_table(top_test_rows, columns))
    md.append("\n## Source-slice comparison\n")
    slice_cols = ["model", "slice", "rows", "positives", "pr_auc", "roc_auc", "f2", "brier", "ece", "high_risk_capture", "false_auto_clear"]
    md.append(_write_md_table(slice_rows, slice_cols))
    md.append("\n## Claim summary\n")
    md.append("```json\n" + json.dumps(claim_summary, indent=2) + "\n```\n")
    md.append("## Resume-safe claims\n")
    for claim in resume_safe_claims:
        md.append(f"- {claim}")
    md.append("\n## Claims not to use\n")
    for claim in claims_not_to_use:
        md.append(f"- {claim}")
    md.append("\n## External artifacts\n")
    for key, value in result["external_artifacts"].items():
        md.append(f"- {key}: `{value}`")

    (reports_dir / "28_score_alignment_blend_experiment.md").write_text("\n".join(md), encoding="utf-8")

    claims_md = ["# Score Alignment Blend Resume Claims\n", "## Use only if consistent with latest metrics\n"]
    for claim in resume_safe_claims:
        claims_md.append(f"- {claim}")
    claims_md.append("\n## Do not use\n")
    for claim in claims_not_to_use:
        claims_md.append(f"- {claim}")
    (reports_dir / "28_score_alignment_blend_resume_claims.md").write_text("\n".join(claims_md), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "PASS",
                "rows": result["rows"],
                "selection_status": selection_status,
                "baseline_test": baseline_test_row,
                "selected_validation_row": selected_val_row,
                "selected_test_row": selected_test_row,
                "claim_summary": claim_summary,
                "report": "reports/28_score_alignment_blend_experiment.md",
                "external_output_dir": str(output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
