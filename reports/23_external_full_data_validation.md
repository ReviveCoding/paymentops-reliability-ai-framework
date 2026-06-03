# External Full-Data Validation

## Claim boundary

This report validates local external public-data adapters. It does not use proprietary bank data, real customer account data, or production payment logs.

## Data sources detected

- External root: `C:\Users\bjw-0\Downloads\paymentops_external_data`

- CFPB path exists: `True`; rows loaded: `50000`

- IBM AML transaction path: `C:\Users\bjw-0\Downloads\paymentops_external_data\ibm_aml\HI-Small_Trans.csv`; rows loaded: `50000`

## Common-schema output

- Output CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\validation_outputs\external_common_case_schema.csv`

- Total rows: `100000`

## Source counts

|                                   |     0 |
|:----------------------------------|------:|
| cfpb_full_public_adapter          | 50000 |
| ibm_aml_external_public_synthetic | 50000 |

## Label counts

|    |     0 |
|---:|------:|
|  0 | 97976 |
|  1 |  2024 |

## Text-risk evaluation

```json
{
  "status": "PASS",
  "rows": 100000,
  "train_rows": 70000,
  "test_rows": 30000,
  "class_counts": {
    "0": 97976,
    "1": 2024
  },
  "roc_auc": 0.8167752063707915,
  "pr_auc": 0.16876524689136715,
  "f2": 0.3253652058432935,
  "brier": 0.11958904558755418,
  "review_capacity": 0.35,
  "high_risk_capture": 0.7446457990115322,
  "false_auto_clear": 0.2553542009884679,
  "review_burden": 0.35
}
```

## Interpretation

- This is a public-data adapter validation, separate from the GitHub-clean sample release gate.

- Use these metrics only with wording such as `external public-data validation sample`.

- Keep full external datasets outside the repository.
