# Baseline vs Method Claim Report

## Claim boundary

This report compares final-test baselines and reliability-enhanced methods using local external public-data samples only. It does not use proprietary bank data, production payment logs, real customer account data, or regulatory certification.

## Dataset

- Input common schema: `C:\Users\bjw-0\Downloads\paymentops_external_data\validation_outputs\external_common_case_schema.csv`

- Rows: `523927`

- Source counts: `{'ibm_aml_external_public_synthetic': 323927, 'cfpb_full_public_adapter': 200000}`

- Label counts: `{'0': 512951, '1': 10976}`

## Temporal split

```json
{
  "train_rows": 314356,
  "validation_rows": 78589,
  "test_rows": 130982,
  "test_positives": 3056,
  "test_positive_rate": 0.023331450122917652
}
```

## Final-test baseline vs method comparison

| model | pr_auc | roc_auc | f2 | brier | ece | high_risk_capture | false_auto_clear | capture_lift_vs_random | false_auto_clear_reduction_vs_random |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_review_expected | 0.0233 |  |  |  |  | 0.3500 | 0.6500 | 1.0000 | 0.0000 |
| random_score_baseline | 0.0231 | 0.4919 | 0.0956 | 0.3341 | 0.4772 | 0.3357 | 0.6643 | 0.9592 | -0.0219 |
| amount_rule_baseline | 0.0233 | 0.5000 | 0.1067 | 0.2500 | 0.4767 | 0.4103 | 0.5897 | 1.1724 | 0.0928 |
| source_rule_baseline | 0.0223 | 0.4768 | 0.0000 | 0.1415 | 0.2993 | 0.3622 | 0.6378 | 1.0350 | 0.0188 |
| vanilla_text_logreg | 0.2044 | 0.8849 | 0.3657 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 2.5907 | 0.8565 |
| hybrid_text_numeric_logreg | 0.2027 | 0.8872 | 0.1855 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 2.5991 | 0.8611 |
| hybrid_text_numeric_logreg_sigmoid_calibrated | 0.2027 | 0.8872 | 0.0894 | 0.0213 | 0.0201 | 0.9097 | 0.0903 | 2.5991 | 0.8611 |

## Reviewer-capacity lift frontier

| model | capacity | pr_auc | roc_auc | brier | ece | high_risk_capture | false_auto_clear | capture_lift_vs_random |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random_score_baseline | 0.0500 | 0.0231 | 0.4919 | 0.3341 | 0.4772 | 0.0527 | 0.9473 | 1.0537 |
| random_score_baseline | 0.1000 | 0.0231 | 0.4919 | 0.3341 | 0.4772 | 0.0988 | 0.9012 | 0.9882 |
| random_score_baseline | 0.2000 | 0.0231 | 0.4919 | 0.3341 | 0.4772 | 0.1908 | 0.8092 | 0.9539 |
| random_score_baseline | 0.3500 | 0.0231 | 0.4919 | 0.3341 | 0.4772 | 0.3357 | 0.6643 | 0.9592 |
| random_score_baseline | 0.5000 | 0.0231 | 0.4919 | 0.3341 | 0.4772 | 0.4866 | 0.5134 | 0.9732 |
| vanilla_text_logreg | 0.0500 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.4391 | 0.5609 | 8.7827 |
| vanilla_text_logreg | 0.1000 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.6518 | 0.3482 | 6.5183 |
| vanilla_text_logreg | 0.2000 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.8207 | 0.1793 | 4.1034 |
| vanilla_text_logreg | 0.3500 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 2.5907 |
| vanilla_text_logreg | 0.5000 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9473 | 0.0527 | 1.8946 |
| hybrid_text_numeric_logreg | 0.0500 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.4365 | 0.5635 | 8.7304 |
| hybrid_text_numeric_logreg | 0.1000 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.6538 | 0.3462 | 6.5380 |
| hybrid_text_numeric_logreg | 0.2000 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.8240 | 0.1760 | 4.1198 |
| hybrid_text_numeric_logreg | 0.3500 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 2.5991 |
| hybrid_text_numeric_logreg | 0.5000 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9519 | 0.0481 | 1.9038 |
| hybrid_text_numeric_logreg_sigmoid_calibrated | 0.0500 | 0.2027 | 0.8872 | 0.0213 | 0.0201 | 0.4365 | 0.5635 | 8.7304 |
| hybrid_text_numeric_logreg_sigmoid_calibrated | 0.1000 | 0.2027 | 0.8872 | 0.0213 | 0.0201 | 0.6538 | 0.3462 | 6.5380 |
| hybrid_text_numeric_logreg_sigmoid_calibrated | 0.2000 | 0.2027 | 0.8872 | 0.0213 | 0.0201 | 0.8240 | 0.1760 | 4.1198 |
| hybrid_text_numeric_logreg_sigmoid_calibrated | 0.3500 | 0.2027 | 0.8872 | 0.0213 | 0.0201 | 0.9097 | 0.0903 | 2.5991 |
| hybrid_text_numeric_logreg_sigmoid_calibrated | 0.5000 | 0.2027 | 0.8872 | 0.0213 | 0.0201 | 0.9519 | 0.0481 | 1.9038 |

## Claim summary

```json
{
  "hybrid_vs_vanilla": {
    "pr_auc_pct_change": -0.008554281868462802,
    "roc_auc_pct_change": 0.002608555755152955,
    "f2_pct_change": -0.4927411396665598,
    "brier_pct_reduction": -2.309916555470231,
    "ece_pct_reduction": -1.5483386091883722,
    "high_risk_capture_point_change": 0.0029450261780105125,
    "false_auto_clear_pct_reduction": 0.03157894736842105
  },
  "calibrated_hybrid_vs_uncalibrated_hybrid": {
    "brier_pct_reduction": 0.9351024021210157,
    "ece_pct_reduction": 0.959389177970366,
    "high_risk_capture_point_change": 0.0,
    "false_auto_clear_pct_reduction": 0.0
  },
  "hybrid_vs_random_review": {
    "capture_lift_vs_random": 2.599102468212416,
    "false_auto_clear_reduction_vs_random": 0.8610551751913009,
    "random_expected_high_risk_capture": 0.35,
    "hybrid_high_risk_capture": 0.9096858638743456,
    "random_expected_false_auto_clear": 0.65,
    "hybrid_false_auto_clear": 0.09031413612565445
  },
  "calibrated_hybrid_vs_random_review": {
    "capture_lift_vs_random": 2.599102468212416,
    "false_auto_clear_reduction_vs_random": 0.8610551751913009,
    "random_expected_high_risk_capture": 0.35,
    "calibrated_high_risk_capture": 0.9096858638743456,
    "random_expected_false_auto_clear": 0.65,
    "calibrated_false_auto_clear": 0.09031413612565445
  }
}
```

## How to use in resume

- Use only claims supported by this report.

- Prefer `external public-data final-test comparison` or `external public-data operational backtest` wording.

- Do not claim proprietary bank data, production deployment, JPMC data, or regulatory certification.

## External artifacts

- Comparison CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\baseline_claim_outputs\final_test_baseline_vs_method_comparison.csv`

- Review-capacity frontier CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\baseline_claim_outputs\review_capacity_lift_frontier.csv`

- Model artifacts: `C:\Users\bjw-0\Downloads\paymentops_external_data\baseline_claim_outputs\models`
