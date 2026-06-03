from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    fbeta_score,
    brier_score_loss,
)
from sklearn.model_selection import train_test_split

from src.data.adapters.cfpb_full_adapter import standardize_cfpb


def _find_ibm_transaction_file(root: Path) -> Path | None:
    ibm_root = root / "ibm_aml"
    if not ibm_root.exists():
        return None

    preferred = [
        "HI-Small_Trans.csv",
        "LI-Small_Trans.csv",
        "HI-Medium_Trans.csv",
        "LI-Medium_Trans.csv",
    ]
    for name in preferred:
        p = ibm_root / name
        if p.exists():
            return p

    files = sorted(ibm_root.rglob("*_Trans.csv"), key=lambda p: p.stat().st_size)
    return files[0] if files else None


def _standardize_ibm_chunked(
    path: Path,
    max_rows: int = 50000,
    chunk_size: int = 50000,
    max_chunks: int = 20,
) -> pd.DataFrame:
    collected = []
    total_seen = 0

    for i, chunk in enumerate(pd.read_csv(path, chunksize=chunk_size)):
        if i >= max_chunks:
            break

        total_seen += len(chunk)

        def col(df, *names, default=""):
            for n in names:
                if n in df.columns:
                    return df[n].fillna(default)
            return pd.Series([default] * len(df), index=df.index)

        label_raw = col(chunk, "Is Laundering", "is_laundering", "risk_label", "isFraud", default=0)
        label = pd.to_numeric(label_raw, errors="coerce").fillna(0).astype(int).clip(0, 1)
        chunk = chunk.copy()
        chunk["_risk_label_tmp"] = label

        pos = chunk[chunk["_risk_label_tmp"] == 1]
        neg = chunk[chunk["_risk_label_tmp"] == 0]

        # Keep positives whenever found, plus a capped negative sample.
        if len(pos) > 0:
            collected.append(pos)
        if len(neg) > 0:
            keep_neg = min(len(neg), max(1000, max_rows // max_chunks))
            collected.append(neg.sample(n=keep_neg, random_state=42))

        current = sum(len(x) for x in collected)
        if current >= max_rows:
            break

    if not collected:
        return pd.DataFrame()

    raw = pd.concat(collected, ignore_index=True).head(max_rows)

    def col(df, *names, default=""):
        for n in names:
            if n in df.columns:
                return df[n].fillna(default)
        return pd.Series([default] * len(df), index=df.index)

    amount = pd.to_numeric(col(raw, "Amount", "amount", default=0), errors="coerce").fillna(0.0)
    label_raw = col(raw, "Is Laundering", "is_laundering", "risk_label", "isFraud", "_risk_label_tmp", default=0)
    label = pd.to_numeric(label_raw, errors="coerce").fillna(0).astype(int).clip(0, 1)
    sender = col(raw, "From ID", "Sender", "sender", default="unknown_sender").astype(str)
    receiver = col(raw, "To ID", "Receiver", "receiver", default="unknown_receiver").astype(str)
    currency = col(raw, "Payment Currency", "currency", default="UNK").astype(str)

    return pd.DataFrame({
        "case_id": [f"ibm_aml_external_{i}" for i in range(len(raw))],
        "source_dataset": "ibm_aml_external_public_synthetic",
        "event_time": col(raw, "Timestamp", "event_time", default="1970-01-01").astype(str),
        "case_type": "aml_transaction",
        "amount": amount,
        "text": (
            "AML transaction from " + sender
            + " to " + receiver
            + " currency " + currency
            + " amount " + amount.round(2).astype(str)
        ),
        "risk_label": label,
        "route_label": label.map({1: "compliance_review", 0: "auto_route"}),
        "payment_status": "NA",
        "exception_type": "aml_laundering_label",
        "issue_group": "aml_risk",
    })


def _evaluate_text_risk(df: pd.DataFrame) -> dict:
    work = df.dropna(subset=["text", "risk_label"]).copy()
    work["risk_label"] = pd.to_numeric(work["risk_label"], errors="coerce").fillna(0).astype(int).clip(0, 1)

    class_counts = work["risk_label"].value_counts().to_dict()
    if len(class_counts) < 2 or len(work) < 50:
        return {
            "status": "SKIPPED",
            "reason": "Need at least two classes and at least 50 rows.",
            "rows": int(len(work)),
            "class_counts": {str(k): int(v) for k, v in class_counts.items()},
        }

    min_class = min(class_counts.values())
    stratify = work["risk_label"] if min_class >= 2 else None

    train, test = train_test_split(
        work,
        test_size=0.30,
        random_state=42,
        stratify=stratify,
    )

    vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2), min_df=2)
    X_train = vectorizer.fit_transform(train["text"].astype(str))
    X_test = vectorizer.transform(test["text"].astype(str))

    model = LogisticRegression(max_iter=500, class_weight="balanced")
    model.fit(X_train, train["risk_label"])
    score = model.predict_proba(X_test)[:, 1]
    pred = (score >= 0.5).astype(int)

    y = test["risk_label"].to_numpy()
    review_capacity = 0.35
    k = max(1, int(len(score) * review_capacity))
    review_idx = score.argsort()[::-1][:k]
    reviewed = pd.Series(False, index=range(len(score)))
    reviewed.iloc[review_idx] = True

    positives = max(1, int(y.sum()))
    high_risk_capture = float(y[reviewed.to_numpy()].sum() / positives)
    false_auto_clear = float(y[~reviewed.to_numpy()].sum() / positives)

    return {
        "status": "PASS",
        "rows": int(len(work)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "roc_auc": float(roc_auc_score(y, score)),
        "pr_auc": float(average_precision_score(y, score)),
        "f2": float(fbeta_score(y, pred, beta=2, zero_division=0)),
        "brier": float(brier_score_loss(y, score)),
        "review_capacity": review_capacity,
        "high_risk_capture": high_risk_capture,
        "false_auto_clear": false_auto_clear,
        "review_burden": float(review_capacity),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", default=os.environ.get("PAYMENTOPS_EXTERNAL_DATA", ""))
    parser.add_argument("--cfpb-rows", type=int, default=50000)
    parser.add_argument("--ibm-rows", type=int, default=50000)
    parser.add_argument("--ibm-chunk-size", type=int, default=50000)
    parser.add_argument("--ibm-max-chunks", type=int, default=20)
    args = parser.parse_args()

    root = Path(args.external_root)
    reports = Path("reports")
    processed = root / "validation_outputs"
    reports.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)

    frames = []
    detected = {}

    cfpb_path = root / "cfpb" / "complaints.csv"
    detected["cfpb_path"] = str(cfpb_path)
    detected["cfpb_exists"] = cfpb_path.exists()

    if cfpb_path.exists():
        cfpb = standardize_cfpb(cfpb_path, max_rows=args.cfpb_rows)
        frames.append(cfpb)
        detected["cfpb_rows_loaded"] = int(len(cfpb))

    ibm_path = _find_ibm_transaction_file(root)
    detected["ibm_transaction_path"] = str(ibm_path) if ibm_path else None
    detected["ibm_exists"] = ibm_path is not None

    if ibm_path:
        ibm = _standardize_ibm_chunked(
            ibm_path,
            max_rows=args.ibm_rows,
            chunk_size=args.ibm_chunk_size,
            max_chunks=args.ibm_max_chunks,
        )
        if len(ibm) > 0:
            frames.append(ibm)
        detected["ibm_rows_loaded"] = int(len(ibm))

    if frames:
        combined = pd.concat(frames, ignore_index=True)
    else:
        combined = pd.DataFrame()

    out_csv = processed / "external_common_case_schema.csv"
    combined.to_csv(out_csv, index=False)

    source_counts = combined["source_dataset"].value_counts().to_dict() if len(combined) else {}
    label_counts = combined["risk_label"].value_counts().to_dict() if len(combined) else {}
    null_counts = combined[["case_id", "source_dataset", "event_time", "case_type", "text", "risk_label", "route_label"]].isna().sum().to_dict() if len(combined) else {}

    metrics = _evaluate_text_risk(combined) if len(combined) else {
        "status": "SKIPPED",
        "reason": "No external rows loaded.",
    }

    result = {
        "external_root": str(root),
        "output_csv": str(out_csv),
        "detected": detected,
        "total_rows": int(len(combined)),
        "source_counts": {str(k): int(v) for k, v in source_counts.items()},
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "null_counts": {str(k): int(v) for k, v in null_counts.items()},
        "text_risk_eval": metrics,
        "claim_boundary": "External public-data validation only. No proprietary bank data, no production payment logs, no regulatory certification.",
    }

    (reports / "external_full_data_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    md = []
    md.append("# External Full-Data Validation\n")
    md.append("## Claim boundary\n")
    md.append("This report validates local external public-data adapters. It does not use proprietary bank data, real customer account data, or production payment logs.\n")
    md.append("## Data sources detected\n")
    md.append(f"- External root: `{root}`\n")
    md.append(f"- CFPB path exists: `{detected.get('cfpb_exists')}`; rows loaded: `{detected.get('cfpb_rows_loaded', 0)}`\n")
    md.append(f"- IBM AML transaction path: `{detected.get('ibm_transaction_path')}`; rows loaded: `{detected.get('ibm_rows_loaded', 0)}`\n")
    md.append("## Common-schema output\n")
    md.append(f"- Output CSV: `{out_csv}`\n")
    md.append(f"- Total rows: `{len(combined)}`\n")
    md.append("## Source counts\n")
    md.append(pd.Series(source_counts).to_markdown() if source_counts else "_No rows loaded._")
    md.append("\n## Label counts\n")
    md.append(pd.Series(label_counts).to_markdown() if label_counts else "_No labels loaded._")
    md.append("\n## Text-risk evaluation\n")
    md.append("```json\n" + json.dumps(metrics, indent=2) + "\n```\n")
    md.append("## Interpretation\n")
    md.append("- This is a public-data adapter validation, separate from the GitHub-clean sample release gate.\n")
    md.append("- Use these metrics only with wording such as `external public-data validation sample`.\n")
    md.append("- Keep full external datasets outside the repository.\n")

    (reports / "23_external_full_data_validation.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
