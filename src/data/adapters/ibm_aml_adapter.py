from __future__ import annotations

from pathlib import Path
import pandas as pd


def standardize_ibm_aml(path: str | Path, max_rows: int | None = None) -> pd.DataFrame:
    """Map a local IBM AML-style transaction CSV into the common schema.

    Expected flexible columns include Timestamp, Amount, Payment Currency,
    Sender/Receiver identifiers, and a binary laundering/fraud label such as
    Is Laundering. Missing columns are safely defaulted for portability.
    """
    df = pd.read_csv(path, nrows=max_rows)
    def col(*names, default=""):
        for n in names:
            if n in df.columns:
                return df[n].fillna(default)
        return pd.Series([default] * len(df))
    amount = pd.to_numeric(col("Amount", "amount", default=0), errors="coerce").fillna(0.0)
    label_raw = col("Is Laundering", "is_laundering", "risk_label", "isFraud", default=0)
    label = pd.to_numeric(label_raw, errors="coerce").fillna(0).astype(int).clip(0, 1)
    sender = col("From ID", "Sender", "sender", default="unknown_sender").astype(str)
    receiver = col("To ID", "Receiver", "receiver", default="unknown_receiver").astype(str)
    currency = col("Payment Currency", "currency", default="UNK").astype(str)
    out = pd.DataFrame({
        "case_id": [f"ibm_aml_{i}" for i in range(len(df))],
        "source_dataset": "ibm_aml_public_synthetic_adapter",
        "event_time": col("Timestamp", "event_time", default="1970-01-01").astype(str),
        "case_type": "aml_transaction",
        "amount": amount,
        "text": "AML transaction from " + sender + " to " + receiver + " currency " + currency + " amount " + amount.round(2).astype(str),
        "risk_label": label,
        "route_label": label.map({1: "compliance_review", 0: "auto_route"}),
        "payment_status": "NA",
        "exception_type": "aml_laundering_label",
        "issue_group": "aml_risk",
    })
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("csv_path")
    p.add_argument("--out", default="data/processed/ibm_aml_common_schema.csv")
    p.add_argument("--max-rows", type=int, default=5000)
    args = p.parse_args()
    result = standardize_ibm_aml(args.csv_path, args.max_rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(f"wrote {args.out} rows={len(result)}")
