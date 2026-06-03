from __future__ import annotations

import pandas as pd
from pathlib import Path
from src.utils import DATA_DIR, read_jsonl

COMMON_COLUMNS = [
    "case_id", "source_dataset", "event_time", "case_type", "amount", "text", "risk_label",
    "route_label", "payment_status", "exception_type", "issue_group"
]


def load_common_cases() -> pd.DataFrame:
    frames = []
    cfpb_path = DATA_DIR / "sample_public" / "cfpb_sample.csv"
    fraud_path = DATA_DIR / "sample_public" / "fraud_sample.csv"
    iso_path = DATA_DIR / "synthetic" / "iso20022_cases.jsonl"

    if cfpb_path.exists():
        c = pd.read_csv(cfpb_path)
        frames.append(pd.DataFrame({
            "case_id": c["complaint_id"],
            "source_dataset": c["source_dataset"],
            "event_time": c["event_time"],
            "case_type": "customer_complaint",
            "amount": 0.0,
            "text": c["consumer_complaint_narrative"],
            "risk_label": c["risk_label"].astype(int),
            "route_label": c["route_label"],
            "payment_status": "NA",
            "exception_type": c["issue"],
            "issue_group": c["issue_group"],
        }))
    if fraud_path.exists():
        f = pd.read_csv(fraud_path)
        frames.append(pd.DataFrame({
            "case_id": f["transaction_id"],
            "source_dataset": f["source_dataset"],
            "event_time": f["event_time"],
            "case_type": "fraud_transaction",
            "amount": f["amount"].astype(float),
            "text": f["narrative"],
            "risk_label": f["risk_label"].astype(int),
            "route_label": f["route_label"],
            "payment_status": "NA",
            "exception_type": "fraud_score",
            "issue_group": "fraud_risk",
        }))
    if iso_path.exists():
        rows = read_jsonl(iso_path)
        i = pd.DataFrame(rows)
        frames.append(pd.DataFrame({
            "case_id": i["case_id"],
            "source_dataset": i["source_dataset"],
            "event_time": i["event_time"],
            "case_type": "iso20022_payment_case",
            "amount": i["amount"].astype(float),
            "text": i["narrative"],
            "risk_label": i["risk_label"].astype(int),
            "route_label": i["route_label"],
            "payment_status": i["payment_status"],
            "exception_type": i["exception_type"],
            "issue_group": "payment_investigation",
        }))

    if not frames:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    df = pd.concat(frames, ignore_index=True)
    return df[COMMON_COLUMNS]


def save_common_cases() -> Path:
    outdir = DATA_DIR / "processed"
    outdir.mkdir(parents=True, exist_ok=True)
    df = load_common_cases()
    out = outdir / "common_case_schema_sample.csv"
    df.to_csv(out, index=False)
    try:
        df.to_parquet(outdir / "common_case_schema_sample.parquet", index=False)
    except Exception:
        pass
    return out


if __name__ == "__main__":
    print(save_common_cases())
