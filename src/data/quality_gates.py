from __future__ import annotations

from pathlib import Path
import pandas as pd
from src.utils import DATA_DIR, REPORTS_DIR, write_report
from src.data.common_schema import load_common_cases

REQUIRED = ["case_id", "source_dataset", "event_time", "case_type", "text", "risk_label", "route_label"]


def validate_common_cases(df: pd.DataFrame) -> dict:
    errors = []
    missing_cols = [c for c in REQUIRED if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")
    if not df.empty:
        null_counts = df[REQUIRED].isna().sum().to_dict()
        duplicates = int(df["case_id"].duplicated().sum())
        invalid_labels = int((~df["risk_label"].isin([0, 1])).sum())
    else:
        null_counts = {}
        duplicates = 0
        invalid_labels = 0
        errors.append("No rows found")
    return {
        "passed": not errors and duplicates == 0 and invalid_labels == 0,
        "errors": errors,
        "row_count": int(len(df)),
        "null_counts": null_counts,
        "duplicates": duplicates,
        "invalid_labels": invalid_labels,
        "source_counts": df["source_dataset"].value_counts().to_dict() if not df.empty else {},
    }


def write_data_inventory() -> dict:
    df = load_common_cases()
    result = validate_common_cases(df)
    source_rows = "\n".join([f"| {k} | {v} |" for k, v in result["source_counts"].items()])
    body = f"""
## Claim boundary

This repository uses public-style sample data and synthetic ISO 20022-inspired payment cases. It does not include proprietary bank data or production payment logs.

## Data quality result

- Passed: `{result['passed']}`
- Total rows: `{result['row_count']}`
- Duplicate case IDs: `{result['duplicates']}`
- Invalid labels: `{result['invalid_labels']}`

## Source inventory

| Source | Rows |
|---|---:|
{source_rows}

## Required field null counts

```json
{result['null_counts']}
```

## Notes

The data layer is designed to be replaceable with real public CFPB exports, a real fraud benchmark, and additional governance datasets later. The sample data keeps the repository runnable without external downloads.
"""
    write_report(REPORTS_DIR / "01_data_inventory.md", "Data Inventory and Quality Gates", body)
    return result


if __name__ == "__main__":
    print(write_data_inventory())
