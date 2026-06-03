from __future__ import annotations

from pathlib import Path
import pandas as pd


def standardize_ieee_cis(transaction_csv: str | Path, identity_csv: str | Path | None = None, max_rows: int | None = None) -> pd.DataFrame:
    """Map local IEEE-CIS Fraud Detection CSV files into the common schema.

    The adapter expects the Kaggle-style transaction file with TransactionID,
    TransactionDT, TransactionAmt, ProductCD, and isFraud. Identity data is
    optional and only used for lightweight narrative enrichment when supplied.
    """
    tx = pd.read_csv(transaction_csv, nrows=max_rows)
    if identity_csv and Path(identity_csv).exists():
        try:
            ident = pd.read_csv(identity_csv, nrows=max_rows)
            if "TransactionID" in tx.columns and "TransactionID" in ident.columns:
                tx = tx.merge(ident, on="TransactionID", how="left", suffixes=("", "_id"))
        except Exception:
            pass
    def col(name, default=""):
        return tx[name].fillna(default) if name in tx.columns else pd.Series([default] * len(tx))
    amount = pd.to_numeric(col("TransactionAmt", 0), errors="coerce").fillna(0.0)
    label = pd.to_numeric(col("isFraud", 0), errors="coerce").fillna(0).astype(int).clip(0, 1)
    product = col("ProductCD", "UNK").astype(str)
    out = pd.DataFrame({
        "case_id": col("TransactionID", "ieee_unknown").astype(str),
        "source_dataset": "ieee_cis_public_fraud_adapter",
        "event_time": col("TransactionDT", "0").astype(str),
        "case_type": "fraud_transaction",
        "amount": amount,
        "text": "IEEE-CIS transaction product " + product + " amount " + amount.round(2).astype(str),
        "risk_label": label,
        "route_label": label.map({1: "analyst_review", 0: "auto_route"}),
        "payment_status": "NA",
        "exception_type": "fraud_probability_label",
        "issue_group": "fraud_risk",
    })
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("transaction_csv")
    p.add_argument("--identity-csv", default=None)
    p.add_argument("--out", default="data/processed/ieee_cis_common_schema.csv")
    p.add_argument("--max-rows", type=int, default=5000)
    args = p.parse_args()
    result = standardize_ieee_cis(args.transaction_csv, args.identity_csv, args.max_rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out, index=False)
    print(f"wrote {args.out} rows={len(result)}")
