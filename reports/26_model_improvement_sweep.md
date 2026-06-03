# Model Improvement Sweep

## Claim boundary

External public-data model-improvement sweep only. No proprietary bank data, production payment logs, real customer account data, or regulatory certification.

## Dataset

- Input CSV: `C:\Users\bjw-0\Downloads\paymentops_external_data\validation_outputs\external_common_case_schema.csv`

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

## Feature ablation and calibrated stacking summary

| model | allowed_champion | pr_auc | roc_auc | brier | ece | capacity_high_risk_capture | capacity_false_auto_clear | capture_lift_vs_random | opt_threshold | opt_f2 | opt_precision | opt_recall | opt_review_burden |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vanilla_text_only | True | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 2.5907 | 0.6100 | 0.3877 | 0.1472 | 0.6554 | 0.1039 |
| text_plus_amount | True | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 2.5907 | 0.6100 | 0.3877 | 0.1472 | 0.6554 | 0.1039 |
| text_plus_amount_text_length | True | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 2.5916 | 0.6100 | 0.3890 | 0.1482 | 0.6554 | 0.1032 |
| text_plus_source_flags | False | 0.2045 | 0.8850 | 0.0990 | 0.1937 | 0.9071 | 0.0929 | 2.5916 | 0.6100 | 0.3873 | 0.1471 | 0.6545 | 0.1038 |
| text_plus_event_rank | False | 0.2029 | 0.8870 | 0.3284 | 0.4947 | 0.9094 | 0.0906 | 2.5982 | 0.8400 | 0.3467 | 0.1065 | 0.7942 | 0.1739 |
| text_plus_safe_numeric_without_source_or_event_rank | True | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 2.5916 | 0.6100 | 0.3890 | 0.1482 | 0.6554 | 0.1032 |
| text_plus_all_numeric | False | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 2.5991 | 0.8500 | 0.3517 | 0.1098 | 0.7830 | 0.1664 |
| numeric_hist_gradient_boosting_safe | True | 0.0337 | 0.6178 | 0.0236 | 0.0253 | 0.5255 | 0.4745 | 1.5015 | 0.0100 | 0.1068 | 0.0233 | 0.9993 | 0.9986 |
| score_level_stacking_text_amount | True | 0.2044 | 0.8849 | 0.1151 | 0.2374 | 0.9067 | 0.0933 | 2.5907 | 0.6900 | 0.3873 | 0.1468 | 0.6561 | 0.1043 |
| score_level_stacking_text_safe_numeric | True | 0.1835 | 0.8825 | 0.1068 | 0.2203 | 0.9031 | 0.0969 | 2.5804 | 0.7000 | 0.3962 | 0.1574 | 0.6381 | 0.0946 |
| calibrated_stacking_text_safe_numeric | True | 0.1835 | 0.8825 | 0.0205 | 0.0027 | 0.9031 | 0.0969 | 2.5804 | 0.0800 | 0.3979 | 0.1620 | 0.6257 | 0.0901 |

## Constrained champion selection

| model | eligible | failed_constraints | selection_score | baseline_model |
| --- | --- | --- | --- | --- |
| vanilla_text_only | True |  | 0.2717 | vanilla_text_only |
| text_plus_amount | False | brier,ece | 0.2717 | vanilla_text_only |
| text_plus_amount_text_length | True |  | 0.2721 | vanilla_text_only |
| text_plus_source_flags | False | not_allowed_as_champion_due_to_shortcut_or_ablation_purpose | 0.2718 | vanilla_text_only |
| text_plus_event_rank | False | not_allowed_as_champion_due_to_shortcut_or_ablation_purpose | 0.2262 | vanilla_text_only |
| text_plus_safe_numeric_without_source_or_event_rank | True |  | 0.2721 | vanilla_text_only |
| text_plus_all_numeric | False | not_allowed_as_champion_due_to_shortcut_or_ablation_purpose | 0.2274 | vanilla_text_only |
| numeric_hist_gradient_boosting_safe | False | pr_auc,roc_auc,opt_f2,capture,false_auto_clear | 0.0364 | vanilla_text_only |
| score_level_stacking_text_amount | False | brier,ece | 0.2679 | vanilla_text_only |
| score_level_stacking_text_safe_numeric | False | pr_auc,brier,ece,capture,false_auto_clear | 0.2647 | vanilla_text_only |
| calibrated_stacking_text_safe_numeric | False | pr_auc,capture,false_auto_clear | 0.2845 | vanilla_text_only |

## Selected constrained champion

- Champion decision: `text_plus_amount_text_length`

## Baseline metrics

```json
{
  "model": "vanilla_text_only",
  "allowed_champion": true,
  "fit_seconds": 22.598261300001468,
  "pr_auc": 0.20443253743340856,
  "roc_auc": 0.8849383589666081,
  "brier": 0.09913266907475965,
  "ece": 0.19406264183638305,
  "capacity_high_risk_capture": 0.9067408376963351,
  "capacity_false_auto_clear": 0.09325916230366492,
  "capture_lift_vs_random": 2.590688107703815,
  "false_auto_clear_reduction_vs_random": 0.8565243656866693,
  "fixed05_f2": 0.36566993089444205,
  "fixed05_precision": 0.12196187667267464,
  "fixed05_recall": 0.7306937172774869,
  "opt_threshold": 0.61,
  "opt_f2": 0.38765240952196633,
  "opt_precision": 0.14716038498273457,
  "opt_recall": 0.6554319371727748,
  "opt_high_risk_capture": 0.6554319371727748,
  "opt_false_auto_clear": 0.34456806282722513,
  "opt_review_burden": 0.1039150417614634
}
```

## Champion metrics

```json
{
  "model": "text_plus_amount_text_length",
  "allowed_champion": true,
  "fit_seconds": 28.33372909999889,
  "pr_auc": 0.20431906024099575,
  "roc_auc": 0.8851939839360664,
  "brier": 0.09879185430925888,
  "ece": 0.19371477054972247,
  "capacity_high_risk_capture": 0.9070680628272252,
  "capacity_false_auto_clear": 0.09293193717277487,
  "capture_lift_vs_random": 2.591623036649215,
  "false_auto_clear_reduction_vs_random": 0.8570277889649617,
  "fixed05_f2": 0.3658816583573865,
  "fixed05_precision": 0.12215286903197548,
  "fixed05_recall": 0.7300392670157068,
  "opt_threshold": 0.61,
  "opt_f2": 0.3890377966825933,
  "opt_precision": 0.1481618462904061,
  "opt_recall": 0.6554319371727748,
  "opt_high_risk_capture": 0.6554319371727748,
  "opt_false_auto_clear": 0.34456806282722513,
  "opt_review_burden": 0.10321265517399338
}
```

## Source-separated evaluation

| model | slice | status | rows | positives | positive_rate | pr_auc | roc_auc | brier | ece | high_risk_capture | false_auto_clear | f2_at_05 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vanilla_text_only | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| vanilla_text_only | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| vanilla_text_only | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| vanilla_text_only | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| vanilla_text_only | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| vanilla_text_only | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2028 | 0.8737 | 0.0973 | 0.1836 | 0.8888 | 0.1112 | 0.3757 |
| vanilla_text_only | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2113 | 0.9036 | 0.1010 | 0.2045 | 0.9367 | 0.0633 | 0.3548 |
| text_plus_amount | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| text_plus_amount | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| text_plus_amount | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| text_plus_amount | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| text_plus_amount | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.0991 | 0.1941 | 0.9067 | 0.0933 | 0.3657 |
| text_plus_amount | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2028 | 0.8737 | 0.0973 | 0.1836 | 0.8888 | 0.1112 | 0.3757 |
| text_plus_amount | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2113 | 0.9036 | 0.1010 | 0.2045 | 0.9367 | 0.0633 | 0.3548 |
| text_plus_amount_text_length | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_amount_text_length | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| text_plus_amount_text_length | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_amount_text_length | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_amount_text_length | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_amount_text_length | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2030 | 0.8738 | 0.0970 | 0.1834 | 0.8916 | 0.1084 | 0.3760 |
| text_plus_amount_text_length | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2112 | 0.9040 | 0.1006 | 0.2041 | 0.9375 | 0.0625 | 0.3548 |
| text_plus_source_flags | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2045 | 0.8850 | 0.0990 | 0.1937 | 0.9071 | 0.0929 | 0.3658 |
| text_plus_source_flags | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| text_plus_source_flags | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2045 | 0.8850 | 0.0990 | 0.1937 | 0.9071 | 0.0929 | 0.3658 |
| text_plus_source_flags | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2045 | 0.8850 | 0.0990 | 0.1937 | 0.9071 | 0.0929 | 0.3658 |
| text_plus_source_flags | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2045 | 0.8850 | 0.0990 | 0.1937 | 0.9071 | 0.0929 | 0.3658 |
| text_plus_source_flags | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2028 | 0.8737 | 0.0972 | 0.1833 | 0.8893 | 0.1107 | 0.3754 |
| text_plus_source_flags | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2114 | 0.9036 | 0.1008 | 0.2042 | 0.9360 | 0.0640 | 0.3554 |
| text_plus_event_rank | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2029 | 0.8870 | 0.3284 | 0.4947 | 0.9094 | 0.0906 | 0.1860 |
| text_plus_event_rank | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| text_plus_event_rank | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2029 | 0.8870 | 0.3284 | 0.4947 | 0.9094 | 0.0906 | 0.1860 |
| text_plus_event_rank | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2029 | 0.8870 | 0.3284 | 0.4947 | 0.9094 | 0.0906 | 0.1860 |
| text_plus_event_rank | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2029 | 0.8870 | 0.3284 | 0.4947 | 0.9094 | 0.0906 | 0.1860 |
| text_plus_event_rank | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2025 | 0.8737 | 0.3379 | 0.4998 | 0.8916 | 0.1084 | 0.1996 |
| text_plus_event_rank | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2067 | 0.9021 | 0.3189 | 0.4895 | 0.9329 | 0.0671 | 0.1707 |
| text_plus_safe_numeric_without_source_or_event_rank | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_safe_numeric_without_source_or_event_rank | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| text_plus_safe_numeric_without_source_or_event_rank | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_safe_numeric_without_source_or_event_rank | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_safe_numeric_without_source_or_event_rank | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2043 | 0.8852 | 0.0988 | 0.1937 | 0.9071 | 0.0929 | 0.3659 |
| text_plus_safe_numeric_without_source_or_event_rank | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2030 | 0.8738 | 0.0970 | 0.1834 | 0.8916 | 0.1084 | 0.3760 |
| text_plus_safe_numeric_without_source_or_event_rank | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2112 | 0.9040 | 0.1006 | 0.2041 | 0.9375 | 0.0625 | 0.3548 |
| text_plus_all_numeric | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 0.1855 |
| text_plus_all_numeric | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| text_plus_all_numeric | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 0.1855 |
| text_plus_all_numeric | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 0.1855 |
| text_plus_all_numeric | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2027 | 0.8872 | 0.3281 | 0.4945 | 0.9097 | 0.0903 | 0.1855 |
| text_plus_all_numeric | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2022 | 0.8739 | 0.3378 | 0.4999 | 0.8911 | 0.1089 | 0.1991 |
| text_plus_all_numeric | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2065 | 0.9024 | 0.3184 | 0.4892 | 0.9314 | 0.0686 | 0.1703 |
| numeric_hist_gradient_boosting_safe | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.0337 | 0.6178 | 0.0236 | 0.0253 | 0.5255 | 0.4745 | 0.0000 |
| numeric_hist_gradient_boosting_safe | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| numeric_hist_gradient_boosting_safe | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.0337 | 0.6178 | 0.0236 | 0.0253 | 0.5255 | 0.4745 | 0.0000 |
| numeric_hist_gradient_boosting_safe | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.0337 | 0.6178 | 0.0236 | 0.0253 | 0.5255 | 0.4745 | 0.0000 |
| numeric_hist_gradient_boosting_safe | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.0337 | 0.6178 | 0.0236 | 0.0253 | 0.5255 | 0.4745 | 0.0000 |
| numeric_hist_gradient_boosting_safe | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.0374 | 0.6118 | 0.0266 | 0.0239 | 0.5287 | 0.4713 | 0.0000 |
| numeric_hist_gradient_boosting_safe | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.0292 | 0.6195 | 0.0206 | 0.0266 | 0.5229 | 0.4771 | 0.0000 |
| score_level_stacking_text_amount | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.1151 | 0.2374 | 0.9067 | 0.0933 | 0.3552 |
| score_level_stacking_text_amount | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| score_level_stacking_text_amount | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.1151 | 0.2374 | 0.9067 | 0.0933 | 0.3552 |
| score_level_stacking_text_amount | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.1151 | 0.2374 | 0.9067 | 0.0933 | 0.3552 |
| score_level_stacking_text_amount | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.2044 | 0.8849 | 0.1151 | 0.2374 | 0.9067 | 0.0933 | 0.3552 |
| score_level_stacking_text_amount | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.2028 | 0.8737 | 0.1127 | 0.2285 | 0.8888 | 0.1112 | 0.3685 |
| score_level_stacking_text_amount | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.2113 | 0.9036 | 0.1175 | 0.2464 | 0.9367 | 0.0633 | 0.3409 |
| score_level_stacking_text_safe_numeric | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.1068 | 0.2203 | 0.9031 | 0.0969 | 0.3588 |
| score_level_stacking_text_safe_numeric | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| score_level_stacking_text_safe_numeric | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.1068 | 0.2203 | 0.9031 | 0.0969 | 0.3588 |
| score_level_stacking_text_safe_numeric | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.1068 | 0.2203 | 0.9031 | 0.0969 | 0.3588 |
| score_level_stacking_text_safe_numeric | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.1068 | 0.2203 | 0.9031 | 0.0969 | 0.3588 |
| score_level_stacking_text_safe_numeric | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.1906 | 0.8705 | 0.1047 | 0.2110 | 0.8842 | 0.1158 | 0.3700 |
| score_level_stacking_text_safe_numeric | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.1814 | 0.9029 | 0.1089 | 0.2298 | 0.9337 | 0.0663 | 0.3467 |
| calibrated_stacking_text_safe_numeric | combined_test | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.0205 | 0.0027 | 0.9031 | 0.0969 | 0.0000 |
| calibrated_stacking_text_safe_numeric | ibm_aml_only | EMPTY | 0 | 0 |  |  |  |  |  |  |  |  |
| calibrated_stacking_text_safe_numeric | cfpb_only | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.0205 | 0.0027 | 0.9031 | 0.0969 | 0.0000 |
| calibrated_stacking_text_safe_numeric | high_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.0205 | 0.0027 | 0.9031 | 0.0969 | 0.0000 |
| calibrated_stacking_text_safe_numeric | low_amount_slice | PASS | 130982 | 3056 | 0.0233 | 0.1835 | 0.8825 | 0.0205 | 0.0027 | 0.9031 | 0.0969 | 0.0000 |
| calibrated_stacking_text_safe_numeric | late_time_window | PASS | 65541 | 1744 | 0.0266 | 0.1906 | 0.8705 | 0.0233 | 0.0052 | 0.8842 | 0.1158 | 0.0000 |
| calibrated_stacking_text_safe_numeric | early_time_window | PASS | 65441 | 1312 | 0.0200 | 0.1814 | 0.9029 | 0.0177 | 0.0064 | 0.9337 | 0.0663 | 0.0000 |

## Resume-safe claims

- Constrained champion `text_plus_amount_text_length` satisfied baseline-safety constraints against the vanilla text baseline across ranking, threshold-optimized detection, calibration, and review-capacity metrics.
- At 35% review capacity, the selected constrained workflow captured 0.9071 of high-risk cases with false auto-clear 0.0929.
- Validation-selected threshold optimization selected threshold 0.6100 for `text_plus_amount_text_length`, producing optimized F2 0.3890 on the future test split.

## Claims not to use

- Do not claim hybrid or all-numeric features improved every metric unless the constrained champion is not vanilla and all hard constraints passed.
- Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.
- Do not claim source-identity features are production-safe; they are ablation-only unless source-separated evaluation supports them.

## External artifacts

- output_dir: `C:\Users\bjw-0\Downloads\paymentops_external_data\model_improvement_outputs`
- models_dir: `C:\Users\bjw-0\Downloads\paymentops_external_data\model_improvement_outputs\models`
- feature_ablation_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\model_improvement_outputs\feature_ablation_results.csv`
- threshold_optimization_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\model_improvement_outputs\threshold_optimization_results.csv`
- source_slice_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\model_improvement_outputs\source_slice_results.csv`
- constrained_champion_selection: `C:\Users\bjw-0\Downloads\paymentops_external_data\model_improvement_outputs\constrained_champion_selection.csv`