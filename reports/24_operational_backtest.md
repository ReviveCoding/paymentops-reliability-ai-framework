# Operational Backtest

## Claim boundary

This operational backtest uses local external public-data samples only. It does not use proprietary bank data, production payment logs, real customer account data, or regulatory certification.

## Dataset

- Common schema input: `C:\Users\bjw-0\Downloads\paymentops_external_data\validation_outputs\external_common_case_schema.csv`

- Rows: `523927`

- Source counts: `{'ibm_aml_external_public_synthetic': 323927, 'cfpb_full_public_adapter': 200000}`

- Label counts: `{'0': 512951, '1': 10976}`

## Temporal split

```json
{
  "train_rows": 314356,
  "validation_rows": 78589,
  "test_rows": 130982,
  "train_start": "2020-05-18 00:00:00+00:00",
  "train_end": "2022-09-09 07:48:00+00:00",
  "test_start": "2023-12-12 00:00:00+00:00",
  "test_end": "2026-04-29 00:00:00+00:00"
}
```

## Champion/challenger validation

| model | pr_auc | roc_auc | f2 | brier | high_risk_capture | false_auto_clear | composite_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vanilla_text_logreg | 0.1583 | 0.7687 | 0.3005 | 0.1598 | 0.6297 | 0.3703 | 0.2693 |
| hybrid_text_numeric_logreg | 0.1655 | 0.7878 | 0.1943 | 0.3284 | 0.7715 | 0.2285 | 0.3206 |
| numeric_hist_gradient_boosting | 0.0378 | 0.5356 | 0.0000 | 0.0329 | 0.3863 | 0.6137 | 0.1031 |

## Selected champion

- Champion: `hybrid_text_numeric_logreg`

- Saved champion model: `C:\Users\bjw-0\Downloads\paymentops_external_data\operational_backtest_outputs\models\20260603_145728_champion_hybrid_text_numeric_logreg_train_val.joblib`

## Final test metrics at 35% review capacity

```json
{
  "rows": 130982,
  "positives": 3056,
  "positive_rate": 0.023331450122917652,
  "review_capacity": 0.35,
  "status": "PASS",
  "roc_auc": 0.8921334787953736,
  "pr_auc": 0.2160014166243938,
  "f2": 0.32039619971700023,
  "brier": 0.14685960086921943,
  "high_risk_capture": 0.9172120418848168,
  "false_auto_clear": 0.08278795811518325,
  "review_burden": 0.35,
  "score_mean": 0.2736481989707391,
  "score_p95": 0.9368101219535391
}
```

## Review-capacity frontier

| capacity | pr_auc | roc_auc | f2 | brier | high_risk_capture | false_auto_clear | review_burden |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0500 | 0.2160 | 0.8921 | 0.3204 | 0.1469 | 0.4467 | 0.5533 | 0.0500 |
| 0.1000 | 0.2160 | 0.8921 | 0.3204 | 0.1469 | 0.6499 | 0.3501 | 0.1000 |
| 0.2000 | 0.2160 | 0.8921 | 0.3204 | 0.1469 | 0.8226 | 0.1774 | 0.2000 |
| 0.3500 | 0.2160 | 0.8921 | 0.3204 | 0.1469 | 0.9172 | 0.0828 | 0.3500 |
| 0.5000 | 0.2160 | 0.8921 | 0.3204 | 0.1469 | 0.9601 | 0.0399 | 0.5000 |

## Static vs quarterly vs drift-triggered retraining

| policy | pr_auc | roc_auc | f2 | brier | high_risk_capture | false_auto_clear | review_burden |
| --- | --- | --- | --- | --- | --- | --- | --- |
| drift_triggered_retrain | 0.2281 | 0.9127 | 0.3492 | 0.1402 | 0.9560 | 0.0440 | 0.3500 |
| quarterly_retrain | 0.2305 | 0.9140 | 0.3720 | 0.1131 | 0.9571 | 0.0429 | 0.3500 |
| static_initial_model | 0.2064 | 0.8862 | 0.1838 | 0.3281 | 0.9078 | 0.0922 | 0.3500 |

## Latency

```json
{
  "batch_rows": 1000,
  "p50_ms": 131.75399999454385,
  "p95_ms": 136.68261999991955,
  "mean_ms": 132.3482799998601
}
```

## External artifacts

- Model/output directory: `C:\Users\bjw-0\Downloads\paymentops_external_data\operational_backtest_outputs`

- Policy backtest CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\operational_backtest_outputs\operational_policy_backtest_metrics.csv`

- Review frontier CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\operational_backtest_outputs\review_capacity_frontier.csv`

## Interpretation

- Use this as an operational ML experiment, separate from the GitHub-clean sample release gate.

- Prefer wording such as `external public-data operational backtest`.

- Keep generated models and large operational artifacts outside the repository.
