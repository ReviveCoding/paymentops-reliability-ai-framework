# Source-Specific AML Behavior Experiment

## Claim boundary

External public-data and synthetic IBM AML behavior experiment only. No proprietary bank data, production payment logs, real customer account data, or regulatory certification.

## Data

- IBM raw path: `C:\Users\bjw-0\Downloads\paymentops_external_data\ibm_aml\HI-Small_Trans.csv`

- Common CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\validation_outputs\external_common_case_schema.csv`

```json
{
  "ibm_total": 323927,
  "cfpb_total": 200000,
  "combined_train": 314356,
  "combined_val": 78589,
  "combined_test": 130982
}
```

## Model comparison

| model | slice | rows | positives | pr_auc | roc_auc | f2 | brier | ece | high_risk_capture | false_auto_clear | capture_lift_vs_random | selected_threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined_text_logreg_baseline | combined_test | 130982 | 3449 | 0.1828 | 0.8904 | 0.4371 | 0.0972 | 0.1810 | 0.9223 | 0.0777 | 2.6351 | 0.6470 |
| ibm_text_logreg_baseline | ibm_aml_only | 80982 | 2088 | 0.1685 | 0.9011 | 0.4694 | 0.1345 | 0.2735 | 0.9363 | 0.0637 | 2.6752 | 0.7548 |
| ibm_behavior_logreg | ibm_aml_only | 80982 | 2088 | 0.1612 | 0.8885 | 0.3578 | 0.2570 | 0.4190 | 0.9387 | 0.0613 | 2.6820 | 0.9018 |
| ibm_behavior_hgb | ibm_aml_only | 80982 | 2088 | 0.2047 | 0.9052 | 0.4816 | 0.0228 | 0.0135 | 0.9397 | 0.0603 | 2.6847 | 0.0198 |
| source_specific_router_cfpb_text_ibm_behavior_hgb | combined_test | 130982 | 3449 | 0.1502 | 0.8546 | 0.2770 | 0.0412 | 0.0376 | 0.9385 | 0.0615 | 2.6815 | 0.2844 |

## Source and risk slices

| model | slice | rows | positives | positive_rate | pr_auc | roc_auc | f2 | brier | ece | high_risk_capture | false_auto_clear |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined_text_logreg_baseline | combined_test | 130982 | 3449 | 0.0263 | 0.1828 | 0.8904 | 0.4367 | 0.0972 | 0.1810 | 0.9223 | 0.0777 |
| combined_text_logreg_baseline | ibm_aml_only | 80982 | 2088 | 0.0258 | 0.1582 | 0.8978 | 0.4572 | 0.1033 | 0.2075 | 0.9353 | 0.0647 |
| combined_text_logreg_baseline | cfpb_only | 50000 | 1361 | 0.0272 | 0.2211 | 0.8892 | 0.4012 | 0.0872 | 0.1381 | 0.9221 | 0.0779 |
| combined_text_logreg_baseline | high_amount_slice | 130982 | 3449 | 0.0263 | 0.1828 | 0.8904 | 0.4367 | 0.0972 | 0.1810 | 0.9223 | 0.0777 |
| combined_text_logreg_baseline | low_amount_slice | 130982 | 3449 | 0.0263 | 0.1828 | 0.8904 | 0.4367 | 0.0972 | 0.1810 | 0.9223 | 0.0777 |
| source_specific_router_cfpb_text_ibm_behavior_hgb | combined_test | 130982 | 3449 | 0.0263 | 0.1502 | 0.8546 | 0.2248 | 0.0412 | 0.0376 | 0.9385 | 0.0615 |
| source_specific_router_cfpb_text_ibm_behavior_hgb | ibm_aml_only | 80982 | 2088 | 0.0258 | 0.2047 | 0.9052 | 0.0000 | 0.0228 | 0.0135 | 0.9397 | 0.0603 |
| source_specific_router_cfpb_text_ibm_behavior_hgb | cfpb_only | 50000 | 1361 | 0.0272 | 0.2222 | 0.8906 | 0.3987 | 0.0710 | 0.1130 | 0.9258 | 0.0742 |
| source_specific_router_cfpb_text_ibm_behavior_hgb | high_amount_slice | 130982 | 3449 | 0.0263 | 0.1502 | 0.8546 | 0.2248 | 0.0412 | 0.0376 | 0.9385 | 0.0615 |
| source_specific_router_cfpb_text_ibm_behavior_hgb | low_amount_slice | 130982 | 3449 | 0.0263 | 0.1502 | 0.8546 | 0.2248 | 0.0412 | 0.0376 | 0.9385 | 0.0615 |

## Claim summary

```json
{
  "router_vs_combined_text_baseline": {
    "pr_auc_pct_change": -0.1785374018363763,
    "roc_auc_pct_change": -0.04024216815414726,
    "f2_pct_change": -0.36638009339744826,
    "brier_pct_reduction": 0.5757549926369426,
    "high_risk_capture_point_change": 0.01623659031603364,
    "false_auto_clear_pct_reduction": 0.20895522388059706
  },
  "ibm_behavior_hgb_vs_ibm_text_baseline": {
    "pr_auc_pct_change": 0.2149629497896805,
    "roc_auc_pct_change": 0.0045692913424790005,
    "f2_pct_change": 0.02599332180793005,
    "brier_pct_reduction": 0.8303842979521376,
    "high_risk_capture_point_change": 0.0033524904214560225,
    "false_auto_clear_pct_reduction": 0.05263157894736832
  }
}
```

## Resume-safe claims

- Built a source-specific PaymentOps risk workflow using CFPB narrative routing and IBM AML raw transaction behavior features, then compared it against a combined text-only baseline under temporal validation.
- Engineered IBM AML sender, receiver, pair, currency, and amount-anomaly behavior features and evaluated histogram gradient boosting against an IBM text-only baseline.

## Claims not to use

- Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.
- Do not claim large model-performance gains unless the generated claim_summary shows a material positive change.
- Do not claim CFPB source-specific performance if CFPB has one-class labels in the local sample.

## External artifacts

- output_dir: `C:\Users\bjw-0\Downloads\paymentops_external_data\source_specific_aml_behavior_outputs`
- models_dir: `C:\Users\bjw-0\Downloads\paymentops_external_data\source_specific_aml_behavior_outputs\models`
- source_specific_model_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\source_specific_aml_behavior_outputs\source_specific_model_results.csv`
- source_specific_slice_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\source_specific_aml_behavior_outputs\source_specific_slice_results.csv`