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
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data.adapters.cfpb_full_adapter import standardize_cfpb
from src.scripts.run_external_validation import _find_ibm_transaction_file, _standardize_ibm_chunked


REVIEW_CAPACITIES = [0.05, 0.10, 0.20, 0.35, 0.50]


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(x: Any) -> float | None:
    try:
        if pd.isna(x):
            return None
        return float(x)
    except Exception:
        return None


def _ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def _find_or_build_external_common_schema(
    external_root: Path,
    cfpb_rows: int,
    ibm_rows: int,
    ibm_chunk_size: int,
    ibm_max_chunks: int,
    force_rebuild: bool,
) -> Path:
    validation_dir = external_root / "validation_outputs"
    validation_dir.mkdir(parents=True, exist_ok=True)
    common_path = validation_dir / "external_common_case_schema.csv"

    if common_path.exists() and not force_rebuild:
        return common_path

    frames: list[pd.DataFrame] = []

    cfpb_path = external_root / "cfpb" / "complaints.csv"
    if cfpb_path.exists():
        cfpb = standardize_cfpb(cfpb_path, max_rows=cfpb_rows)
        frames.append(cfpb)

    ibm_path = _find_ibm_transaction_file(external_root)
    if ibm_path:
        ibm = _standardize_ibm_chunked(
            ibm_path,
            max_rows=ibm_rows,
            chunk_size=ibm_chunk_size,
            max_chunks=ibm_max_chunks,
        )
        if len(ibm) > 0:
            frames.append(ibm)

    if not frames:
        raise FileNotFoundError(
            "No external rows loaded. Set PAYMENTOPS_EXTERNAL_DATA to a folder containing cfpb/complaints.csv and/or ibm_aml/*_Trans.csv."
        )

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(common_path, index=False)
    return common_path


def _prepare_operational_frame(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["case_id", "source_dataset", "event_time", "case_type", "text", "risk_label", "route_label"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Input common schema missing required columns: {missing}")

    work = df.copy()
    work["case_id"] = work["case_id"].astype(str)
    work = work.drop_duplicates(subset=["case_id"]).copy()

    work["text"] = work["text"].fillna("").astype(str)
    work["risk_label"] = pd.to_numeric(work["risk_label"], errors="coerce").fillna(0).astype(int).clip(0, 1)
    work["amount"] = pd.to_numeric(work.get("amount", 0.0), errors="coerce").fillna(0.0)
    work["source_dataset"] = work["source_dataset"].fillna("unknown").astype(str)
    work["case_type"] = work["case_type"].fillna("unknown").astype(str)
    work["exception_type"] = work.get("exception_type", "unknown")
    work["exception_type"] = work["exception_type"].fillna("unknown").astype(str)

    parsed_time = pd.to_datetime(work["event_time"], errors="coerce", utc=True)
    if parsed_time.notna().sum() < max(10, int(0.5 * len(work))):
        parsed_time = pd.Series(
            pd.date_range("2023-01-01", periods=len(work), freq="min", tz="UTC"),
            index=work.index,
        )
    else:
        fallback = pd.Series(
            pd.date_range("2023-01-01", periods=len(work), freq="min", tz="UTC"),
            index=work.index,
        )
        parsed_time = parsed_time.fillna(fallback)

    work["_event_time"] = parsed_time
    work = work.sort_values(["_event_time", "case_id"]).reset_index(drop=True)
    work["_pos"] = np.arange(len(work))

    work["text_length"] = work["text"].str.len().clip(0, 5000)
    work["log_amount"] = np.log1p(work["amount"].clip(lower=0))
    work["is_cfpb"] = work["source_dataset"].str.contains("cfpb", case=False, na=False).astype(int)
    work["is_ibm_aml"] = work["source_dataset"].str.contains("ibm|aml", case=False, regex=True, na=False).astype(int)
    work["event_rank"] = work["_pos"] / max(1, len(work) - 1)

    class_counts = work["risk_label"].value_counts().to_dict()
    if len(class_counts) < 2:
        raise ValueError(f"Need at least two classes for backtest. class_counts={class_counts}")

    return work


def _features(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["text", "log_amount", "text_length", "is_cfpb", "is_ibm_aml", "event_rank"]
    return df[cols].copy()


def _labels(df: pd.DataFrame) -> np.ndarray:
    return df["risk_label"].astype(int).to_numpy()


def _build_model(model_name: str, max_features: int, random_state: int) -> Pipeline:
    numeric_cols = ["log_amount", "text_length", "is_cfpb", "is_ibm_aml", "event_rank"]

    if model_name == "vanilla_text_logreg":
        pre = ColumnTransformer(
            transformers=[
                ("text", TfidfVectorizer(max_features=max_features, ngram_range=(1, 2), min_df=2), "text"),
            ],
            remainder="drop",
        )
        return Pipeline([
            ("preprocess", pre),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear")),
        ])

    if model_name == "hybrid_text_numeric_logreg":
        pre = ColumnTransformer(
            transformers=[
                ("text", TfidfVectorizer(max_features=max_features, ngram_range=(1, 2), min_df=2), "text"),
                ("num", Pipeline([
                    ("impute", SimpleImputer(strategy="median")),
                    ("scale", StandardScaler(with_mean=False)),
                ]), numeric_cols),
            ],
            remainder="drop",
        )
        return Pipeline([
            ("preprocess", pre),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear")),
        ])

    if model_name == "numeric_hist_gradient_boosting":
        pre = ColumnTransformer(
            transformers=[
                ("num", SimpleImputer(strategy="median"), numeric_cols),
            ],
            remainder="drop",
        )
        return Pipeline([
            ("preprocess", pre),
            ("model", HistGradientBoostingClassifier(
                max_iter=120,
                learning_rate=0.08,
                l2_regularization=0.01,
                random_state=random_state,
            )),
        ])

    raise ValueError(f"Unknown model_name={model_name}")


def _score_model(model: Pipeline, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    raw = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-raw))


def _metrics_for_scores(y: np.ndarray, score: np.ndarray, review_capacity: float = 0.35) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    score = np.asarray(score).astype(float)
    pred = (score >= 0.5).astype(int)

    result: dict[str, Any] = {
        "rows": int(len(y)),
        "positives": int(y.sum()),
        "positive_rate": float(y.mean()) if len(y) else 0.0,
        "review_capacity": float(review_capacity),
    }

    if len(np.unique(y)) < 2:
        result.update({
            "status": "SKIPPED_ONE_CLASS",
            "roc_auc": None,
            "pr_auc": None,
            "f2": None,
            "brier": None,
            "high_risk_capture": None,
            "false_auto_clear": None,
            "review_burden": float(review_capacity),
        })
        return result

    k = max(1, int(len(score) * review_capacity))
    top_idx = np.argsort(score)[::-1][:k]
    review_mask = np.zeros(len(score), dtype=bool)
    review_mask[top_idx] = True

    positives = max(1, int(y.sum()))
    high_risk_capture = float(y[review_mask].sum() / positives)
    false_auto_clear = float(y[~review_mask].sum() / positives)

    result.update({
        "status": "PASS",
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "f2": float(fbeta_score(y, pred, beta=2, zero_division=0)),
        "brier": float(brier_score_loss(y, score)),
        "high_risk_capture": high_risk_capture,
        "false_auto_clear": false_auto_clear,
        "review_burden": float(review_capacity),
        "score_mean": float(np.mean(score)),
        "score_p95": float(np.quantile(score, 0.95)),
    })
    return result


def _composite_score(m: dict[str, Any]) -> float:
    if m.get("status") != "PASS":
        return -1e9
    pr_auc = m.get("pr_auc") or 0.0
    capture = m.get("high_risk_capture") or 0.0
    false_auto = m.get("false_auto_clear") or 1.0
    brier = m.get("brier") or 1.0
    f2 = m.get("f2") or 0.0
    return 0.35 * pr_auc + 0.30 * capture - 0.20 * false_auto + 0.10 * (1 - brier) + 0.05 * f2


def _psi(expected: np.ndarray, observed: np.ndarray, bins: int = 10) -> float:
    expected = np.asarray(expected, dtype=float)
    observed = np.asarray(observed, dtype=float)
    expected = expected[np.isfinite(expected)]
    observed = observed[np.isfinite(observed)]
    if len(expected) < 10 or len(observed) < 10:
        return 0.0

    cuts = np.quantile(expected, np.linspace(0, 1, bins + 1))
    cuts = np.unique(cuts)
    if len(cuts) < 3:
        return 0.0

    e_counts, _ = np.histogram(expected, bins=cuts)
    o_counts, _ = np.histogram(observed, bins=cuts)

    e_pct = e_counts / max(1, e_counts.sum())
    o_pct = o_counts / max(1, o_counts.sum())

    eps = 1e-6
    return float(np.sum((o_pct - e_pct) * np.log((o_pct + eps) / (e_pct + eps))))


def _fit_evaluate_candidates(train: pd.DataFrame, val: pd.DataFrame, max_features: int, random_state: int) -> tuple[str, dict[str, Any], dict[str, Pipeline]]:
    models: dict[str, Pipeline] = {}
    rows: dict[str, Any] = {}

    for name in ["vanilla_text_logreg", "hybrid_text_numeric_logreg", "numeric_hist_gradient_boosting"]:
        model = _build_model(name, max_features=max_features, random_state=random_state)
        t0 = time.perf_counter()
        model.fit(_features(train), _labels(train))
        fit_sec = time.perf_counter() - t0

        score = _score_model(model, _features(val))
        metrics = _metrics_for_scores(_labels(val), score, review_capacity=0.35)
        metrics["fit_seconds"] = float(fit_sec)
        metrics["composite_score"] = float(_composite_score(metrics))

        models[name] = model
        rows[name] = metrics

    best_name = max(rows, key=lambda k: rows[k]["composite_score"])
    return best_name, rows, models


def _review_capacity_frontier(model: Pipeline, test: pd.DataFrame) -> list[dict[str, Any]]:
    score = _score_model(model, _features(test))
    y = _labels(test)
    rows = []
    for cap in REVIEW_CAPACITIES:
        m = _metrics_for_scores(y, score, review_capacity=cap)
        m["capacity"] = cap
        rows.append(m)
    return rows


def _split_train_val_test(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    train_end = int(n * 0.60)
    val_end = int(n * 0.75)
    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    if len(train) < 100 or len(val) < 50 or len(test) < 50:
        raise ValueError(f"Not enough rows for temporal split: train={len(train)}, val={len(val)}, test={len(test)}")
    return train, val, test


def _window_splits(test: pd.DataFrame, n_windows: int) -> list[pd.DataFrame]:
    idx_splits = np.array_split(np.arange(len(test)), n_windows)
    return [test.iloc[idx].copy() for idx in idx_splits if len(idx) > 0]


def _evaluate_policy_static(model: Pipeline, test_windows: list[pd.DataFrame], policy_name: str) -> list[dict[str, Any]]:
    rows = []
    for i, win in enumerate(test_windows, start=1):
        score = _score_model(model, _features(win))
        metrics = _metrics_for_scores(_labels(win), score, review_capacity=0.35)
        metrics.update({
            "policy": policy_name,
            "window": i,
            "window_rows": int(len(win)),
            "window_start": str(win["_event_time"].min()),
            "window_end": str(win["_event_time"].max()),
            "retrained_before_window": False,
            "drift_psi": None,
            "triggered_retrain_after_window": False,
        })
        rows.append(metrics)
    return rows


def _evaluate_policy_quarterly(df: pd.DataFrame, test_windows: list[pd.DataFrame], champion_name: str, max_features: int, random_state: int) -> list[dict[str, Any]]:
    rows = []
    for i, win in enumerate(test_windows, start=1):
        train_until = int(win["_pos"].min())
        train_rows = df.iloc[:train_until].copy()
        model = _build_model(champion_name, max_features=max_features, random_state=random_state + i)
        model.fit(_features(train_rows), _labels(train_rows))

        score = _score_model(model, _features(win))
        metrics = _metrics_for_scores(_labels(win), score, review_capacity=0.35)
        metrics.update({
            "policy": "quarterly_retrain",
            "window": i,
            "window_rows": int(len(win)),
            "window_start": str(win["_event_time"].min()),
            "window_end": str(win["_event_time"].max()),
            "retrained_before_window": True,
            "drift_psi": None,
            "triggered_retrain_after_window": False,
        })
        rows.append(metrics)
    return rows


def _evaluate_policy_drift_triggered(
    df: pd.DataFrame,
    train_initial: pd.DataFrame,
    test_windows: list[pd.DataFrame],
    champion_name: str,
    max_features: int,
    random_state: int,
    psi_threshold: float,
    pr_auc_drop_threshold: float,
    baseline_pr_auc: float,
) -> list[dict[str, Any]]:
    rows = []
    model = _build_model(champion_name, max_features=max_features, random_state=random_state)
    model.fit(_features(train_initial), _labels(train_initial))
    baseline_scores = _score_model(model, _features(train_initial.sample(n=min(len(train_initial), 10000), random_state=random_state)))

    retrain_next = False

    for i, win in enumerate(test_windows, start=1):
        if retrain_next:
            train_until = int(win["_pos"].min())
            train_rows = df.iloc[:train_until].copy()
            model = _build_model(champion_name, max_features=max_features, random_state=random_state + i)
            model.fit(_features(train_rows), _labels(train_rows))
            baseline_scores = _score_model(model, _features(train_rows.sample(n=min(len(train_rows), 10000), random_state=random_state + i)))
            retrained_before = True
        else:
            retrained_before = False

        score = _score_model(model, _features(win))
        psi = _psi(baseline_scores, score)
        metrics = _metrics_for_scores(_labels(win), score, review_capacity=0.35)

        current_pr_auc = metrics.get("pr_auc")
        pr_auc_trigger = (
            current_pr_auc is not None
            and baseline_pr_auc is not None
            and current_pr_auc < baseline_pr_auc * pr_auc_drop_threshold
        )
        drift_trigger = psi > psi_threshold
        trigger_retrain = bool(pr_auc_trigger or drift_trigger)

        metrics.update({
            "policy": "drift_triggered_retrain",
            "window": i,
            "window_rows": int(len(win)),
            "window_start": str(win["_event_time"].min()),
            "window_end": str(win["_event_time"].max()),
            "retrained_before_window": retrained_before,
            "drift_psi": float(psi),
            "triggered_retrain_after_window": trigger_retrain,
            "trigger_reason": "psi" if drift_trigger else ("pr_auc_drop" if pr_auc_trigger else "none"),
        })
        rows.append(metrics)
        retrain_next = trigger_retrain

    return rows


def _latency_ms(model: Pipeline, df: pd.DataFrame, n: int = 1000) -> dict[str, float]:
    sample = df.sample(n=min(n, len(df)), random_state=42)
    timings = []
    for _ in range(5):
        t0 = time.perf_counter()
        _ = _score_model(model, _features(sample))
        timings.append((time.perf_counter() - t0) * 1000.0)
    return {
        "batch_rows": int(len(sample)),
        "p50_ms": float(np.quantile(timings, 0.50)),
        "p95_ms": float(np.quantile(timings, 0.95)),
        "mean_ms": float(np.mean(timings)),
    }


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", default=os.environ.get("PAYMENTOPS_EXTERNAL_DATA", ""))
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--cfpb-rows", type=int, default=50000)
    parser.add_argument("--ibm-rows", type=int, default=100000)
    parser.add_argument("--ibm-chunk-size", type=int, default=50000)
    parser.add_argument("--ibm-max-chunks", type=int, default=40)
    parser.add_argument("--max-features", type=int, default=5000)
    parser.add_argument("--n-windows", type=int, default=4)
    parser.add_argument("--psi-threshold", type=float, default=0.20)
    parser.add_argument("--pr-auc-drop-threshold", type=float, default=0.85)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    external_root = Path(args.external_root)
    if not external_root.exists():
        raise FileNotFoundError(f"External root does not exist: {external_root}")

    reports_dir = Path("reports")
    registry_dir = Path("artifacts/model_registry")
    output_dir = external_root / "operational_backtest_outputs"
    models_dir = output_dir / "models"
    _ensure_dirs(reports_dir, registry_dir, output_dir, models_dir)

    if args.input_csv:
        common_path = Path(args.input_csv)
    else:
        common_path = _find_or_build_external_common_schema(
            external_root=external_root,
            cfpb_rows=args.cfpb_rows,
            ibm_rows=args.ibm_rows,
            ibm_chunk_size=args.ibm_chunk_size,
            ibm_max_chunks=args.ibm_max_chunks,
            force_rebuild=args.force_rebuild,
        )

    df = _prepare_operational_frame(common_path)
    train, val, test = _split_train_val_test(df)

    champion_name, candidate_metrics, candidate_models = _fit_evaluate_candidates(
        train=train,
        val=val,
        max_features=args.max_features,
        random_state=args.random_state,
    )

    # Save candidate models fitted on initial train.
    stamp = _now_stamp()
    saved_models = {}
    for name, model in candidate_models.items():
        path = models_dir / f"{stamp}_{name}.joblib"
        joblib.dump(model, path)
        saved_models[name] = str(path)

    # Refit champion on train + validation for final test/frontier.
    champion_model = _build_model(champion_name, max_features=args.max_features, random_state=args.random_state)
    train_val = pd.concat([train, val], ignore_index=True)
    champion_model.fit(_features(train_val), _labels(train_val))

    champion_path = models_dir / f"{stamp}_champion_{champion_name}_train_val.joblib"
    joblib.dump(champion_model, champion_path)

    test_score = _score_model(champion_model, _features(test))
    final_test_metrics = _metrics_for_scores(_labels(test), test_score, review_capacity=0.35)
    frontier = _review_capacity_frontier(champion_model, test)
    pd.DataFrame(frontier).to_csv(output_dir / "review_capacity_frontier.csv", index=False)

    test_windows = _window_splits(test, args.n_windows)

    static_rows = _evaluate_policy_static(
        model=candidate_models[champion_name],
        test_windows=test_windows,
        policy_name="static_initial_model",
    )
    quarterly_rows = _evaluate_policy_quarterly(
        df=df,
        test_windows=test_windows,
        champion_name=champion_name,
        max_features=args.max_features,
        random_state=args.random_state,
    )

    baseline_pr_auc = candidate_metrics[champion_name].get("pr_auc") or 0.0
    drift_rows = _evaluate_policy_drift_triggered(
        df=df,
        train_initial=train,
        test_windows=test_windows,
        champion_name=champion_name,
        max_features=args.max_features,
        random_state=args.random_state,
        psi_threshold=args.psi_threshold,
        pr_auc_drop_threshold=args.pr_auc_drop_threshold,
        baseline_pr_auc=baseline_pr_auc,
    )

    policy_rows = static_rows + quarterly_rows + drift_rows
    policy_df = pd.DataFrame(policy_rows)
    policy_df.to_csv(output_dir / "operational_policy_backtest_metrics.csv", index=False)

    policy_summary = (
        policy_df.groupby("policy", dropna=False)[
            ["pr_auc", "roc_auc", "f2", "brier", "high_risk_capture", "false_auto_clear", "review_burden"]
        ]
        .mean(numeric_only=True)
        .reset_index()
        .to_dict(orient="records")
    )

    latency = _latency_ms(champion_model, test)

    model_registry = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": "External public-data operational backtest only. No proprietary bank data, production payment logs, or regulatory certification.",
        "common_schema_input": str(common_path),
        "external_output_dir": str(output_dir),
        "champion_model": champion_name,
        "champion_model_path": str(champion_path),
        "candidate_model_paths": saved_models,
        "candidate_validation_metrics": candidate_metrics,
        "final_test_metrics": final_test_metrics,
        "latency": latency,
    }
    (registry_dir / "operational_model_versions.json").write_text(
        json.dumps(model_registry, indent=2),
        encoding="utf-8",
    )

    result = {
        "status": "PASS",
        "external_root": str(external_root),
        "common_schema_input": str(common_path),
        "rows": int(len(df)),
        "source_counts": {str(k): int(v) for k, v in df["source_dataset"].value_counts().to_dict().items()},
        "label_counts": {str(k): int(v) for k, v in df["risk_label"].value_counts().to_dict().items()},
        "temporal_split": {
            "train_rows": int(len(train)),
            "validation_rows": int(len(val)),
            "test_rows": int(len(test)),
            "train_start": str(train["_event_time"].min()),
            "train_end": str(train["_event_time"].max()),
            "test_start": str(test["_event_time"].min()),
            "test_end": str(test["_event_time"].max()),
        },
        "champion_model": champion_name,
        "candidate_validation_metrics": candidate_metrics,
        "final_test_metrics": final_test_metrics,
        "review_capacity_frontier": frontier,
        "policy_summary": policy_summary,
        "policy_rows": policy_rows,
        "latency": latency,
        "external_artifacts": {
            "output_dir": str(output_dir),
            "models_dir": str(models_dir),
            "review_capacity_frontier_csv": str(output_dir / "review_capacity_frontier.csv"),
            "policy_backtest_csv": str(output_dir / "operational_policy_backtest_metrics.csv"),
            "champion_model_path": str(champion_path),
        },
    }

    (reports_dir / "operational_backtest_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    candidate_rows = []
    for name, m in candidate_metrics.items():
        candidate_rows.append({
            "model": name,
            "pr_auc": _safe_float(m.get("pr_auc")),
            "roc_auc": _safe_float(m.get("roc_auc")),
            "f2": _safe_float(m.get("f2")),
            "brier": _safe_float(m.get("brier")),
            "high_risk_capture": _safe_float(m.get("high_risk_capture")),
            "false_auto_clear": _safe_float(m.get("false_auto_clear")),
            "composite_score": _safe_float(m.get("composite_score")),
        })

    md = []
    md.append("# Operational Backtest\n")
    md.append("## Claim boundary\n")
    md.append("This operational backtest uses local external public-data samples only. It does not use proprietary bank data, production payment logs, real customer account data, or regulatory certification.\n")
    md.append("## Dataset\n")
    md.append(f"- Common schema input: `{common_path}`\n")
    md.append(f"- Rows: `{len(df)}`\n")
    md.append(f"- Source counts: `{result['source_counts']}`\n")
    md.append(f"- Label counts: `{result['label_counts']}`\n")
    md.append("## Temporal split\n")
    md.append("```json\n" + json.dumps(result["temporal_split"], indent=2) + "\n```\n")
    md.append("## Champion/challenger validation\n")
    md.append(_md_table(candidate_rows, ["model", "pr_auc", "roc_auc", "f2", "brier", "high_risk_capture", "false_auto_clear", "composite_score"]))
    md.append("\n## Selected champion\n")
    md.append(f"- Champion: `{champion_name}`\n")
    md.append(f"- Saved champion model: `{champion_path}`\n")
    md.append("## Final test metrics at 35% review capacity\n")
    md.append("```json\n" + json.dumps(final_test_metrics, indent=2) + "\n```\n")
    md.append("## Review-capacity frontier\n")
    md.append(_md_table(frontier, ["capacity", "pr_auc", "roc_auc", "f2", "brier", "high_risk_capture", "false_auto_clear", "review_burden"]))
    md.append("\n## Static vs quarterly vs drift-triggered retraining\n")
    md.append(_md_table(policy_summary, ["policy", "pr_auc", "roc_auc", "f2", "brier", "high_risk_capture", "false_auto_clear", "review_burden"]))
    md.append("\n## Latency\n")
    md.append("```json\n" + json.dumps(latency, indent=2) + "\n```\n")
    md.append("## External artifacts\n")
    md.append(f"- Model/output directory: `{output_dir}`\n")
    md.append(f"- Policy backtest CSV: `{output_dir / 'operational_policy_backtest_metrics.csv'}`\n")
    md.append(f"- Review frontier CSV: `{output_dir / 'review_capacity_frontier.csv'}`\n")
    md.append("## Interpretation\n")
    md.append("- Use this as an operational ML experiment, separate from the GitHub-clean sample release gate.\n")
    md.append("- Prefer wording such as `external public-data operational backtest`.\n")
    md.append("- Keep generated models and large operational artifacts outside the repository.\n")

    (reports_dir / "24_operational_backtest.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "rows": int(len(df)),
        "champion_model": champion_name,
        "final_test_metrics": final_test_metrics,
        "policy_summary": policy_summary,
        "latency": latency,
        "report": "reports/24_operational_backtest.md",
        "external_output_dir": str(output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
