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
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.scripts.run_operational_backtest import (
    _prepare_operational_frame,
    _split_train_val_test,
    _features,
    _labels,
    _score_model,
)
from src.scripts.run_external_validation import _find_ibm_transaction_file


REVIEW_CAPACITIES = [0.05, 0.10, 0.20, 0.35, 0.50]


NUMERIC_FEATURES = [
    "amount",
    "log_amount",
    "sender_tx_count",
    "receiver_tx_count",
    "sender_total_amount",
    "receiver_total_amount",
    "sender_avg_amount",
    "receiver_avg_amount",
    "sender_unique_receivers",
    "receiver_unique_senders",
    "pair_tx_count",
    "pair_total_amount",
    "currency_tx_count",
    "currency_avg_amount",
    "amount_to_currency_avg",
    "amount_percentile_by_currency",
]

CATEGORICAL_FEATURES = [
    "payment_currency",
    "receiving_currency",
    "payment_format",
]


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _first_existing_col(df: pd.DataFrame, candidates: list[str], default: Any = "") -> pd.Series:
    lower_map = {c.lower().strip(): c for c in df.columns}
    for name in candidates:
        key = name.lower().strip()
        if key in lower_map:
            return df[lower_map[key]]
    return pd.Series([default] * len(df), index=df.index)


def _find_ibm_file(external_root: Path) -> Path:
    path = _find_ibm_transaction_file(external_root)
    if path is None:
        raise FileNotFoundError(
            "No IBM AML transaction CSV found under external_root/ibm_aml. "
            "Expected files such as HI-Small_Trans.csv or LI-Small_Trans.csv."
        )
    return path


def _load_ibm_raw_sample(
    ibm_path: Path,
    max_rows: int,
    chunk_size: int,
    max_chunks: int,
    random_state: int,
) -> pd.DataFrame:
    """Load a leakage-safe, positive-enriched IBM AML sample from the raw transaction CSV."""
    frames: list[pd.DataFrame] = []
    rng = np.random.default_rng(random_state)

    for chunk_idx, chunk in enumerate(pd.read_csv(ibm_path, chunksize=chunk_size)):
        if chunk_idx >= max_chunks:
            break

        chunk = chunk.copy()
        label_raw = _first_existing_col(
            chunk,
            ["Is Laundering", "is_laundering", "risk_label", "isFraud"],
            default=0,
        )
        label = pd.to_numeric(label_raw, errors="coerce").fillna(0).astype(int).clip(0, 1)
        chunk["_risk_label_tmp"] = label

        positives = chunk[chunk["_risk_label_tmp"] == 1]
        negatives = chunk[chunk["_risk_label_tmp"] == 0]

        if len(positives) > 0:
            frames.append(positives)

        if len(negatives) > 0:
            keep_neg = min(len(negatives), max(2000, max_rows // max(1, max_chunks)))
            frames.append(negatives.sample(n=keep_neg, random_state=random_state + chunk_idx))

        if sum(len(x) for x in frames) >= max_rows:
            break

    if not frames:
        raise ValueError(f"No rows were loaded from IBM AML file: {ibm_path}")

    data = pd.concat(frames, ignore_index=True)
    if len(data) > max_rows:
        pos = data[data["_risk_label_tmp"] == 1]
        neg = data[data["_risk_label_tmp"] == 0]
        keep_pos = min(len(pos), max_rows // 2)
        keep_neg = max_rows - keep_pos
        sampled = []
        if keep_pos > 0:
            sampled.append(pos.sample(n=keep_pos, random_state=random_state))
        if keep_neg > 0 and len(neg) > 0:
            sampled.append(neg.sample(n=min(keep_neg, len(neg)), random_state=random_state))
        data = pd.concat(sampled, ignore_index=True)

    return data.reset_index(drop=True)


def _standardize_ibm_raw(raw: pd.DataFrame) -> pd.DataFrame:
    sender = _first_existing_col(raw, ["From ID", "Sender", "sender", "from_id"], default="unknown_sender").astype(str)
    receiver = _first_existing_col(raw, ["To ID", "Receiver", "receiver", "to_id"], default="unknown_receiver").astype(str)
    amount = pd.to_numeric(_first_existing_col(raw, ["Amount", "amount"], default=0), errors="coerce").fillna(0.0)
    label = pd.to_numeric(
        _first_existing_col(raw, ["Is Laundering", "is_laundering", "risk_label", "isFraud", "_risk_label_tmp"], default=0),
        errors="coerce",
    ).fillna(0).astype(int).clip(0, 1)

    payment_currency = _first_existing_col(raw, ["Payment Currency", "payment_currency", "Currency", "currency"], default="UNK").astype(str)
    receiving_currency = _first_existing_col(raw, ["Receiving Currency", "receiving_currency"], default="UNK").astype(str)
    payment_format = _first_existing_col(raw, ["Payment Format", "payment_format", "Format"], default="UNK").astype(str)
    event_time = _first_existing_col(raw, ["Timestamp", "event_time", "Date", "datetime"], default="1970-01-01").astype(str)

    df = pd.DataFrame(
        {
            "case_id": [f"ibm_raw_behavior_{i}" for i in range(len(raw))],
            "source_dataset": "ibm_aml_raw_behavior",
            "event_time": event_time,
            "case_type": "aml_transaction",
            "amount": amount,
            "risk_label": label,
            "route_label": label.map({1: "compliance_review", 0: "auto_route"}),
            "sender_id": sender,
            "receiver_id": receiver,
            "payment_currency": payment_currency.fillna("UNK"),
            "receiving_currency": receiving_currency.fillna("UNK"),
            "payment_format": payment_format.fillna("UNK"),
        }
    )

    df["text"] = (
        "AML transaction sender "
        + df["sender_id"].astype(str)
        + " receiver "
        + df["receiver_id"].astype(str)
        + " payment currency "
        + df["payment_currency"].astype(str)
        + " receiving currency "
        + df["receiving_currency"].astype(str)
        + " format "
        + df["payment_format"].astype(str)
        + " amount "
        + df["amount"].round(2).astype(str)
    )

    parsed = pd.to_datetime(df["event_time"], errors="coerce", utc=True)
    fallback = pd.Series(pd.date_range("2023-01-01", periods=len(df), freq="min", tz="UTC"), index=df.index)
    df["_event_time"] = parsed.fillna(fallback)
    df = df.sort_values(["_event_time", "case_id"]).reset_index(drop=True)
    df["_pos"] = np.arange(len(df))
    df["log_amount"] = np.log1p(df["amount"].clip(lower=0))
    df["text_length"] = df["text"].str.len().clip(0, 5000)
    df["is_cfpb"] = 0
    df["is_ibm_aml"] = 1
    df["event_rank"] = df["_pos"] / max(1, len(df) - 1)
    return df


class BehaviorFeatureMapper:
    def __init__(self) -> None:
        self.sender_stats: pd.DataFrame | None = None
        self.receiver_stats: pd.DataFrame | None = None
        self.pair_stats: pd.DataFrame | None = None
        self.currency_stats: pd.DataFrame | None = None
        self.global_amount_mean: float = 1.0

    def fit(self, train: pd.DataFrame) -> "BehaviorFeatureMapper":
        work = train.copy()
        work["amount"] = pd.to_numeric(work["amount"], errors="coerce").fillna(0.0)
        self.global_amount_mean = float(work["amount"].mean()) if len(work) else 1.0
        if self.global_amount_mean <= 0:
            self.global_amount_mean = 1.0

        self.sender_stats = work.groupby("sender_id").agg(
            sender_tx_count=("case_id", "count"),
            sender_total_amount=("amount", "sum"),
            sender_avg_amount=("amount", "mean"),
            sender_unique_receivers=("receiver_id", "nunique"),
        )
        self.receiver_stats = work.groupby("receiver_id").agg(
            receiver_tx_count=("case_id", "count"),
            receiver_total_amount=("amount", "sum"),
            receiver_avg_amount=("amount", "mean"),
            receiver_unique_senders=("sender_id", "nunique"),
        )
        self.pair_stats = work.groupby(["sender_id", "receiver_id"]).agg(
            pair_tx_count=("case_id", "count"),
            pair_total_amount=("amount", "sum"),
        )
        self.currency_stats = work.groupby("payment_currency").agg(
            currency_tx_count=("case_id", "count"),
            currency_avg_amount=("amount", "mean"),
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.sender_stats is None or self.receiver_stats is None or self.pair_stats is None or self.currency_stats is None:
            raise RuntimeError("BehaviorFeatureMapper must be fit before transform.")

        out = df.copy()
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)

        out = out.merge(self.sender_stats, how="left", left_on="sender_id", right_index=True)
        out = out.merge(self.receiver_stats, how="left", left_on="receiver_id", right_index=True)
        out = out.merge(self.pair_stats, how="left", left_on=["sender_id", "receiver_id"], right_index=True)
        out = out.merge(self.currency_stats, how="left", left_on="payment_currency", right_index=True)

        fill_zero_cols = [
            "sender_tx_count", "receiver_tx_count", "sender_total_amount", "receiver_total_amount",
            "sender_unique_receivers", "receiver_unique_senders", "pair_tx_count", "pair_total_amount", "currency_tx_count",
        ]
        for col in fill_zero_cols:
            out[col] = pd.to_numeric(out.get(col, 0), errors="coerce").fillna(0.0)

        out["sender_avg_amount"] = pd.to_numeric(out.get("sender_avg_amount", self.global_amount_mean), errors="coerce").fillna(self.global_amount_mean)
        out["receiver_avg_amount"] = pd.to_numeric(out.get("receiver_avg_amount", self.global_amount_mean), errors="coerce").fillna(self.global_amount_mean)
        out["currency_avg_amount"] = pd.to_numeric(out.get("currency_avg_amount", self.global_amount_mean), errors="coerce").fillna(self.global_amount_mean)
        out["amount_to_currency_avg"] = out["amount"] / out["currency_avg_amount"].replace(0, self.global_amount_mean)

        # Leakage-safe percentile proxy using the train-fitted currency average as denominator.
        out["amount_percentile_by_currency"] = out.groupby("payment_currency")["amount"].rank(pct=True).fillna(0.5)
        return out


def _build_text_model(max_features: int, random_state: int) -> Pipeline:
    pre = ColumnTransformer(
        [("text", TfidfVectorizer(max_features=max_features, ngram_range=(1, 2), min_df=2), "text")],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", pre),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear", random_state=random_state)),
        ]
    )


def _build_behavior_hgb(random_state: int) -> Pipeline:
    pre = ColumnTransformer(
        [
            ("num", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", pre),
            (
                "model",
                HistGradientBoostingClassifier(
                    max_iter=200,
                    learning_rate=0.06,
                    l2_regularization=0.02,
                    max_leaf_nodes=31,
                    random_state=random_state,
                ),
            ),
        ]
    )


def _build_behavior_logreg(random_state: int) -> Pipeline:
    pre = ColumnTransformer(
        [
            ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", max_categories=30), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("preprocess", pre),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear", random_state=random_state)),
        ]
    )


def _model_score(model: Any, X: pd.DataFrame) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    raw = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-raw))


def _safe_pr_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    if len(np.unique(y)) < 2:
        return None
    return float(average_precision_score(y, score))


def _safe_roc_auc(y: np.ndarray, score: np.ndarray) -> float | None:
    if len(np.unique(y)) < 2:
        return None
    return float(roc_auc_score(y, score))


def _ece(y: np.ndarray, score: np.ndarray, n_bins: int = 10) -> float:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score).astype(float), 0.0, 1.0)
    bins = np.linspace(0, 1, n_bins + 1)
    value = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (score >= lo) & (score <= hi if hi == 1 else score < hi)
        if np.any(mask):
            value += float(mask.mean()) * abs(float(y[mask].mean()) - float(score[mask].mean()))
    return float(value)


def _eval_scores(y: np.ndarray, score: np.ndarray, review_capacity: float, threshold: float = 0.5) -> dict[str, Any]:
    y = np.asarray(y).astype(int)
    score = np.clip(np.asarray(score).astype(float), 0.0, 1.0)
    pred = (score >= threshold).astype(int)

    k = max(1, int(len(score) * review_capacity))
    idx = np.argsort(score)[::-1][:k]
    review = np.zeros(len(score), dtype=bool)
    review[idx] = True
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
    }


def _best_threshold(y_val: np.ndarray, val_score: np.ndarray, n_thresholds: int) -> float:
    best_threshold = 0.5
    best_f2 = -1.0
    for threshold in np.linspace(0.01, 0.99, n_thresholds):
        pred = (val_score >= threshold).astype(int)
        value = float(fbeta_score(y_val, pred, beta=2, zero_division=0))
        if value > best_f2:
            best_f2 = value
            best_threshold = float(threshold)
    return best_threshold


def _split_df(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = df.sort_values(["_event_time", "case_id"]).reset_index(drop=True)
    n = len(df)
    train_end = int(n * 0.60)
    val_end = int(n * 0.75)
    return df.iloc[:train_end].copy(), df.iloc[train_end:val_end].copy(), df.iloc[val_end:].copy()


def _prepare_cfpb(common_csv: Path) -> pd.DataFrame:
    df = _prepare_operational_frame(common_csv)
    cfpb = df[df["source_dataset"].astype(str).str.contains("cfpb", case=False, na=False)].copy()
    if len(cfpb) == 0:
        return cfpb
    cfpb["sender_id"] = "NA"
    cfpb["receiver_id"] = "NA"
    cfpb["payment_currency"] = "NA"
    cfpb["receiving_currency"] = "NA"
    cfpb["payment_format"] = "NA"
    for col in NUMERIC_FEATURES:
        if col not in cfpb.columns:
            cfpb[col] = 0.0
    for col in CATEGORICAL_FEATURES:
        if col not in cfpb.columns:
            cfpb[col] = "NA"
    return cfpb


def _fit_if_two_classes(model: Any, train: pd.DataFrame, feature_frame_fn) -> Any | None:
    y = train["risk_label"].astype(int).to_numpy()
    if len(np.unique(y)) < 2:
        return None
    model.fit(feature_frame_fn(train), y)
    return model


def _constant_score(train: pd.DataFrame, n: int) -> np.ndarray:
    rate = float(train["risk_label"].astype(int).mean()) if len(train) else 0.0
    return np.full(n, rate)


def _text_features(df: pd.DataFrame) -> pd.DataFrame:
    return df[["text"]].copy()


def _behavior_features(df: pd.DataFrame) -> pd.DataFrame:
    cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    return df[cols].copy()


def _combined_features(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["text"] + NUMERIC_FEATURES + CATEGORICAL_FEATURES
    return df[cols].copy()


def _write_md_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        values = []
        for col in columns:
            val = row.get(col)
            if isinstance(val, float):
                values.append(f"{val:.4f}")
            elif val is None:
                values.append("")
            else:
                values.append(str(val))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, sep] + body)


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
    output_dir = external_root / "source_specific_aml_behavior_outputs"
    models_dir = output_dir / "models"
    _ensure_dirs(reports_dir, output_dir, models_dir)

    stamp = _now_stamp()

    ibm_path = _find_ibm_file(external_root)
    raw_ibm = _load_ibm_raw_sample(
        ibm_path=ibm_path,
        max_rows=args.max_ibm_rows,
        chunk_size=args.chunk_size,
        max_chunks=args.max_chunks,
        random_state=args.random_state,
    )
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

    y_combined_val = combined_val["risk_label"].astype(int).to_numpy()
    y_combined_test = combined_test["risk_label"].astype(int).to_numpy()
    y_ibm_val = ibm_val["risk_label"].astype(int).to_numpy()
    y_ibm_test = ibm_test["risk_label"].astype(int).to_numpy()

    results: list[dict[str, Any]] = []
    scores_for_slices: dict[str, np.ndarray] = {}

    # Combined vanilla text baseline.
    combined_text = _build_text_model(args.max_features, args.random_state)
    combined_text.fit(_text_features(combined_train), combined_train["risk_label"].astype(int))
    combined_text_val_score = _model_score(combined_text, _text_features(combined_val))
    combined_text_test_score = _model_score(combined_text, _text_features(combined_test))
    combined_text_threshold = _best_threshold(y_combined_val, combined_text_val_score, args.n_thresholds)
    row = _eval_scores(y_combined_test, combined_text_test_score, args.review_capacity, combined_text_threshold)
    row.update({"model": "combined_text_logreg_baseline", "slice": "combined_test", "selected_threshold": combined_text_threshold})
    results.append(row)
    scores_for_slices["combined_text_logreg_baseline"] = combined_text_test_score
    joblib.dump(combined_text, models_dir / f"{stamp}_combined_text_logreg_baseline.joblib")

    # IBM text baseline.
    ibm_text = _build_text_model(args.max_features, args.random_state)
    ibm_text.fit(_text_features(ibm_train), ibm_train["risk_label"].astype(int))
    ibm_text_val_score = _model_score(ibm_text, _text_features(ibm_val))
    ibm_text_test_score = _model_score(ibm_text, _text_features(ibm_test))
    ibm_text_threshold = _best_threshold(y_ibm_val, ibm_text_val_score, args.n_thresholds)
    row = _eval_scores(y_ibm_test, ibm_text_test_score, args.review_capacity, ibm_text_threshold)
    row.update({"model": "ibm_text_logreg_baseline", "slice": "ibm_aml_only", "selected_threshold": ibm_text_threshold})
    results.append(row)
    joblib.dump(ibm_text, models_dir / f"{stamp}_ibm_text_logreg_baseline.joblib")

    # IBM behavior logistic baseline.
    ibm_behavior_logreg = _build_behavior_logreg(args.random_state)
    ibm_behavior_logreg.fit(_behavior_features(ibm_train), ibm_train["risk_label"].astype(int))
    ibm_behavior_logreg_val_score = _model_score(ibm_behavior_logreg, _behavior_features(ibm_val))
    ibm_behavior_logreg_test_score = _model_score(ibm_behavior_logreg, _behavior_features(ibm_test))
    ibm_behavior_logreg_threshold = _best_threshold(y_ibm_val, ibm_behavior_logreg_val_score, args.n_thresholds)
    row = _eval_scores(y_ibm_test, ibm_behavior_logreg_test_score, args.review_capacity, ibm_behavior_logreg_threshold)
    row.update({"model": "ibm_behavior_logreg", "slice": "ibm_aml_only", "selected_threshold": ibm_behavior_logreg_threshold})
    results.append(row)
    joblib.dump(ibm_behavior_logreg, models_dir / f"{stamp}_ibm_behavior_logreg.joblib")

    # IBM behavior HGB.
    ibm_behavior_hgb = _build_behavior_hgb(args.random_state)
    ibm_behavior_hgb.fit(_behavior_features(ibm_train), ibm_train["risk_label"].astype(int))
    ibm_behavior_hgb_val_score = _model_score(ibm_behavior_hgb, _behavior_features(ibm_val))
    ibm_behavior_hgb_test_score = _model_score(ibm_behavior_hgb, _behavior_features(ibm_test))
    ibm_behavior_hgb_threshold = _best_threshold(y_ibm_val, ibm_behavior_hgb_val_score, args.n_thresholds)
    row = _eval_scores(y_ibm_test, ibm_behavior_hgb_test_score, args.review_capacity, ibm_behavior_hgb_threshold)
    row.update({"model": "ibm_behavior_hgb", "slice": "ibm_aml_only", "selected_threshold": ibm_behavior_hgb_threshold})
    results.append(row)
    joblib.dump(ibm_behavior_hgb, models_dir / f"{stamp}_ibm_behavior_hgb.joblib")

    # Source-specific router: CFPB text model when possible, IBM HGB behavior model for IBM rows.
    router_test_score = np.zeros(len(combined_test), dtype=float)
    router_val_score = np.zeros(len(combined_val), dtype=float)

    is_ibm_test = combined_test["source_dataset"].astype(str).str.contains("ibm|aml", case=False, regex=True, na=False).to_numpy()
    is_ibm_val = combined_val["source_dataset"].astype(str).str.contains("ibm|aml", case=False, regex=True, na=False).to_numpy()
    is_cfpb_test = combined_test["source_dataset"].astype(str).str.contains("cfpb", case=False, regex=True, na=False).to_numpy()
    is_cfpb_val = combined_val["source_dataset"].astype(str).str.contains("cfpb", case=False, regex=True, na=False).to_numpy()

    router_test_score[is_ibm_test] = _model_score(ibm_behavior_hgb, _behavior_features(combined_test.loc[is_ibm_test]))
    router_val_score[is_ibm_val] = _model_score(ibm_behavior_hgb, _behavior_features(combined_val.loc[is_ibm_val]))

    cfpb_model = _fit_if_two_classes(_build_text_model(args.max_features, args.random_state), cfpb_train, _text_features) if len(cfpb_train) else None
    if cfpb_model is not None:
        router_test_score[is_cfpb_test] = _model_score(cfpb_model, _text_features(combined_test.loc[is_cfpb_test]))
        router_val_score[is_cfpb_val] = _model_score(cfpb_model, _text_features(combined_val.loc[is_cfpb_val]))
        joblib.dump(cfpb_model, models_dir / f"{stamp}_cfpb_text_model.joblib")
    else:
        cfpb_train_rate = float(cfpb_train["risk_label"].astype(int).mean()) if len(cfpb_train) else 0.0
        router_test_score[is_cfpb_test] = cfpb_train_rate
        router_val_score[is_cfpb_val] = cfpb_train_rate

    router_threshold = _best_threshold(y_combined_val, router_val_score, args.n_thresholds)
    row = _eval_scores(y_combined_test, router_test_score, args.review_capacity, router_threshold)
    row.update({"model": "source_specific_router_cfpb_text_ibm_behavior_hgb", "slice": "combined_test", "selected_threshold": router_threshold})
    results.append(row)
    scores_for_slices["source_specific_router_cfpb_text_ibm_behavior_hgb"] = router_test_score

    # Slice evaluations for the two key combined workflows.
    slice_rows: list[dict[str, Any]] = []
    for model_name, score in scores_for_slices.items():
        temp = combined_test.copy()
        temp["_score"] = score
        src = temp["source_dataset"].astype(str)
        slices = {
            "combined_test": temp,
            "ibm_aml_only": temp[src.str.contains("ibm|aml", case=False, regex=True, na=False)],
            "cfpb_only": temp[src.str.contains("cfpb", case=False, regex=True, na=False)],
            "high_amount_slice": temp[pd.to_numeric(temp["amount"], errors="coerce").fillna(0) >= pd.to_numeric(temp["amount"], errors="coerce").fillna(0).quantile(0.80)],
            "low_amount_slice": temp[pd.to_numeric(temp["amount"], errors="coerce").fillna(0) <= pd.to_numeric(temp["amount"], errors="coerce").fillna(0).quantile(0.50)],
        }
        for slice_name, frame in slices.items():
            if len(frame) == 0:
                continue
            y = frame["risk_label"].astype(int).to_numpy()
            s = frame["_score"].to_numpy()
            metrics = _eval_scores(y, s, args.review_capacity, threshold=0.5)
            metrics.update({"model": model_name, "slice": slice_name})
            slice_rows.append(metrics)

    results_df = pd.DataFrame(results)
    slice_df = pd.DataFrame(slice_rows)
    results_df.to_csv(output_dir / "source_specific_model_results.csv", index=False)
    slice_df.to_csv(output_dir / "source_specific_slice_results.csv", index=False)

    baseline_row = next(r for r in results if r["model"] == "combined_text_logreg_baseline")
    router_row = next(r for r in results if r["model"] == "source_specific_router_cfpb_text_ibm_behavior_hgb")
    ibm_text_row = next(r for r in results if r["model"] == "ibm_text_logreg_baseline")
    ibm_hgb_row = next(r for r in results if r["model"] == "ibm_behavior_hgb")

    def pct_improve(new: float | None, old: float | None, lower_is_better: bool = False) -> float | None:
        if new is None or old is None or old == 0:
            return None
        return (old - new) / old if lower_is_better else (new - old) / old

    claim_summary = {
        "router_vs_combined_text_baseline": {
            "pr_auc_pct_change": pct_improve(router_row.get("pr_auc"), baseline_row.get("pr_auc")),
            "roc_auc_pct_change": pct_improve(router_row.get("roc_auc"), baseline_row.get("roc_auc")),
            "f2_pct_change": pct_improve(router_row.get("f2"), baseline_row.get("f2")),
            "brier_pct_reduction": pct_improve(router_row.get("brier"), baseline_row.get("brier"), lower_is_better=True),
            "high_risk_capture_point_change": (router_row.get("high_risk_capture") or 0) - (baseline_row.get("high_risk_capture") or 0),
            "false_auto_clear_pct_reduction": pct_improve(router_row.get("false_auto_clear"), baseline_row.get("false_auto_clear"), lower_is_better=True),
        },
        "ibm_behavior_hgb_vs_ibm_text_baseline": {
            "pr_auc_pct_change": pct_improve(ibm_hgb_row.get("pr_auc"), ibm_text_row.get("pr_auc")),
            "roc_auc_pct_change": pct_improve(ibm_hgb_row.get("roc_auc"), ibm_text_row.get("roc_auc")),
            "f2_pct_change": pct_improve(ibm_hgb_row.get("f2"), ibm_text_row.get("f2")),
            "brier_pct_reduction": pct_improve(ibm_hgb_row.get("brier"), ibm_text_row.get("brier"), lower_is_better=True),
            "high_risk_capture_point_change": (ibm_hgb_row.get("high_risk_capture") or 0) - (ibm_text_row.get("high_risk_capture") or 0),
            "false_auto_clear_pct_reduction": pct_improve(ibm_hgb_row.get("false_auto_clear"), ibm_text_row.get("false_auto_clear"), lower_is_better=True),
        },
    }

    resume_safe_claims = []
    claims_not_to_use = [
        "Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.",
        "Do not claim large model-performance gains unless the generated claim_summary shows a material positive change.",
        "Do not claim CFPB source-specific performance if CFPB has one-class labels in the local sample.",
    ]

    if claim_summary["router_vs_combined_text_baseline"].get("f2_pct_change") is not None:
        resume_safe_claims.append(
            "Built a source-specific PaymentOps risk workflow using CFPB narrative routing and IBM AML raw transaction behavior features, then compared it against a combined text-only baseline under temporal validation."
        )
    if claim_summary["ibm_behavior_hgb_vs_ibm_text_baseline"].get("pr_auc_pct_change") is not None:
        resume_safe_claims.append(
            "Engineered IBM AML sender, receiver, pair, currency, and amount-anomaly behavior features and evaluated histogram gradient boosting against an IBM text-only baseline."
        )

    result = {
        "status": "PASS",
        "claim_boundary": "External public-data and synthetic IBM AML behavior experiment only. No proprietary bank data, production payment logs, real customer account data, or regulatory certification.",
        "ibm_raw_path": str(ibm_path),
        "common_csv": str(common_csv),
        "rows": {
            "ibm_total": int(len(ibm_df)),
            "cfpb_total": int(len(cfpb_df)),
            "combined_train": int(len(combined_train)),
            "combined_val": int(len(combined_val)),
            "combined_test": int(len(combined_test)),
        },
        "model_results": results,
        "slice_results": slice_rows,
        "claim_summary": claim_summary,
        "resume_safe_claims": resume_safe_claims,
        "claims_not_to_use": claims_not_to_use,
        "external_artifacts": {
            "output_dir": str(output_dir),
            "models_dir": str(models_dir),
            "source_specific_model_results": str(output_dir / "source_specific_model_results.csv"),
            "source_specific_slice_results": str(output_dir / "source_specific_slice_results.csv"),
        },
    }

    (reports_dir / "source_specific_aml_behavior_metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    cols = ["model", "slice", "rows", "positives", "pr_auc", "roc_auc", "f2", "brier", "ece", "high_risk_capture", "false_auto_clear", "capture_lift_vs_random", "selected_threshold"]
    md = []
    md.append("# Source-Specific AML Behavior Experiment\n")
    md.append("## Claim boundary\n")
    md.append(result["claim_boundary"] + "\n")
    md.append("## Data\n")
    md.append(f"- IBM raw path: `{ibm_path}`\n")
    md.append(f"- Common CSV: `{common_csv}`\n")
    md.append("```json\n" + json.dumps(result["rows"], indent=2) + "\n```\n")
    md.append("## Model comparison\n")
    md.append(_write_md_table(results, cols))
    md.append("\n## Source and risk slices\n")
    slice_cols = ["model", "slice", "rows", "positives", "positive_rate", "pr_auc", "roc_auc", "f2", "brier", "ece", "high_risk_capture", "false_auto_clear"]
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

    (reports_dir / "27_source_specific_aml_behavior_experiment.md").write_text("\n".join(md), encoding="utf-8")

    claims_md = ["# Source-Specific AML Behavior Resume Claims\n"]
    claims_md.append("## Use only if consistent with latest metrics\n")
    for claim in resume_safe_claims:
        claims_md.append(f"- {claim}")
    claims_md.append("\n## Do not use\n")
    for claim in claims_not_to_use:
        claims_md.append(f"- {claim}")
    (reports_dir / "27_source_specific_aml_behavior_resume_claims.md").write_text("\n".join(claims_md), encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "rows": result["rows"],
        "baseline": baseline_row,
        "source_specific_router": router_row,
        "ibm_text_baseline": ibm_text_row,
        "ibm_behavior_hgb": ibm_hgb_row,
        "claim_summary": claim_summary,
        "report": "reports/27_source_specific_aml_behavior_experiment.md",
        "external_output_dir": str(output_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
