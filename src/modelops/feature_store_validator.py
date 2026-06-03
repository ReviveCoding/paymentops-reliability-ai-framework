from __future__ import annotations

import json
import pandas as pd
from src.utils import ARTIFACTS_DIR, DATA_DIR, REPORTS_DIR, write_json, write_report


def validate_feature_store_contract() -> dict:
    feature_path = DATA_DIR / "processed" / "feature_table.csv"
    manifest_path = ARTIFACTS_DIR / "aws" / "feature_store_manifest.json"
    df = pd.read_csv(feature_path) if feature_path.exists() else pd.DataFrame()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    required = {"case_id", "event_time", "case_type", "amount", "risk_label", "route_label", "text_length", "amount_log"}
    missing = sorted(required - set(df.columns))
    duplicate_case_ids = int(df["case_id"].duplicated().sum()) if "case_id" in df.columns and not df.empty else 0
    event_time_parse_rate = 0.0
    if "event_time" in df.columns and not df.empty:
        parsed = pd.to_datetime(df["event_time"], errors="coerce")
        event_time_parse_rate = float(parsed.notna().mean())
        df["event_date"] = parsed.dt.date.astype(str)
    partitions = int(df["event_date"].nunique()) if "event_date" in df.columns else 0
    source_counts = df["source_dataset"].value_counts().to_dict() if "source_dataset" in df.columns and not df.empty else {}
    result = {
        "passed": not missing and duplicate_case_ids == 0 and event_time_parse_rate >= 0.99,
        "missing_required_features": missing,
        "duplicate_case_ids": duplicate_case_ids,
        "event_time_parse_rate": event_time_parse_rate,
        "row_count": int(len(df)),
        "partition_count_by_event_date": partitions,
        "source_counts": source_counts,
        "manifest_status": manifest.get("status", "missing"),
        "claim_boundary": "Local feature-store-style validation only; no online/offline managed feature store is claimed.",
    }
    write_json(REPORTS_DIR / "feature_store_validation.json", result)
    body = f"""
## Purpose

The previous version contained feature-store-style manifests. This validator adds a local schema/backfill smoke test so the readiness pack is not only documentation.

## Validation results

| Check | Value |
|---|---:|
| Passed | `{result['passed']}` |
| Rows | {result['row_count']} |
| Duplicate case IDs | {result['duplicate_case_ids']} |
| Event-time parse rate | {result['event_time_parse_rate']:.3f} |
| Event-date partitions | {result['partition_count_by_event_date']} |
| Missing required features | `{result['missing_required_features']}` |

## Source counts

```json
{json.dumps(source_counts, indent=2)}
```

## Boundary

This is a local feature-store contract validation. It does not claim a deployed SageMaker Feature Store, EMR job, or online low-latency feature service.
"""
    write_report(REPORTS_DIR / "12_feature_store_backfill_validation.md", "Feature Store and Backfill Validation", body)
    return result


if __name__ == "__main__":
    print(json.dumps(validate_feature_store_contract(), indent=2))
