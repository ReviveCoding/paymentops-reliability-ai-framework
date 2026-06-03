from __future__ import annotations

from pathlib import Path
import pandas as pd

CFPB_COLUMN_ALIASES = {
    "complaint_id": ["Complaint ID", "complaint_id", "complaintId"],
    "event_time": ["Date received", "date_received", "event_time"],
    "text": ["Consumer complaint narrative", "consumer_complaint_narrative", "text", "narrative"],
    "issue_group": ["Issue", "issue", "issue_group"],
    "product": ["Product", "product"],
    "timely": ["Timely response?", "timely_response", "timely"],
    "response": ["Company response to consumer", "company_response", "response"],
}


def _pick(df: pd.DataFrame, names: list[str], default: str = "") -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name].fillna(default)
    return pd.Series([default] * len(df))


def standardize_cfpb(path: str | Path, max_rows: int | None = None) -> pd.DataFrame:
    """Map a local CFPB complaint export into the project common schema.

    The function intentionally avoids network downloads. Users can export CFPB
    complaints separately and pass the local CSV path.
    """
    df = pd.read_csv(path, nrows=max_rows)
    text = _pick(df, CFPB_COLUMN_ALIASES["text"], "")
    issue = _pick(df, CFPB_COLUMN_ALIASES["issue_group"], "unknown_issue")
    timely = _pick(df, CFPB_COLUMN_ALIASES["timely"], "Yes").astype(str).str.lower()
    response = _pick(df, CFPB_COLUMN_ALIASES["response"], "").astype(str).str.lower()
    risk = ((timely.str.contains("no")) | response.str.contains("closed with monetary relief|in progress|untimely", regex=True)).astype(int)
    out = pd.DataFrame({
        "case_id": _pick(df, CFPB_COLUMN_ALIASES["complaint_id"], "cfpb_unknown").astype(str),
        "source_dataset": "cfpb_full_public_adapter",
        "event_time": _pick(df, CFPB_COLUMN_ALIASES["event_time"], "1970-01-01").astype(str),
        "case_type": "customer_complaint",
        "amount": 0.0,
        "text": text.astype(str),
        "risk_label": risk.astype(int),
        "route_label": risk.map({1: "analyst_review", 0: "auto_route"}),
        "payment_status": "NA",
        "exception_type": issue.astype(str),
        "issue_group": issue.astype(str),
    })
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("csv_path")
    p.add_argument("--out", default="data/processed/cfpb_full_common_schema.csv")
    p.add_argument("--max-rows", type=int, default=5000)
    args = p.parse_args()
    result = standardize_cfpb(args.csv_path, args.max_rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(f"wrote {args.out} rows={len(result)}")
