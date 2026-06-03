# Feature Store and Backfill Validation

## Purpose

The previous version contained feature-store-style manifests. This validator adds a local schema/backfill smoke test so the readiness pack is not only documentation.

## Validation results

| Check | Value |
|---|---:|
| Passed | `True` |
| Rows | 288 |
| Duplicate case IDs | 0 |
| Event-time parse rate | 1.000 |
| Event-date partitions | 96 |
| Missing required features | `[]` |

## Source counts

```json
{
  "fraud_benchmark_style_sample": 120,
  "cfpb_style_public_sample": 96,
  "synthetic_iso20022": 72
}
```

## Boundary

This is a local feature-store contract validation. It does not claim a deployed SageMaker Feature Store, EMR job, or online low-latency feature service.
