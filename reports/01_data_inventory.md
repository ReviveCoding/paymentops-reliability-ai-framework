# Data Inventory and Quality Gates

## Claim boundary

This repository uses public-style sample data and synthetic ISO 20022-inspired payment cases. It does not include proprietary bank data or production payment logs.

## Data quality result

- Passed: `True`
- Total rows: `288`
- Duplicate case IDs: `0`
- Invalid labels: `0`

## Source inventory

| Source | Rows |
|---|---:|
| fraud_benchmark_style_sample | 120 |
| cfpb_style_public_sample | 96 |
| synthetic_iso20022 | 72 |

## Required field null counts

```json
{'case_id': 0, 'source_dataset': 0, 'event_time': 0, 'case_type': 0, 'text': 0, 'risk_label': 0, 'route_label': 0}
```

## Notes

The data layer is designed to be replaceable with real public CFPB exports, a real fraud benchmark, and additional governance datasets later. The sample data keeps the repository runnable without external downloads.
