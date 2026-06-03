# Score Alignment and Blended Router Experiment

## Claim boundary

External public-data score-alignment and source-blending experiment only. No proprietary bank data, production payment logs, real customer account data, or regulatory certification.

## Why this experiment was added

The previous source-specific router improved calibration and false auto-clear but degraded global PR-AUC/F2, suggesting source score-scale mismatch. This experiment fits source-wise MinMax, percentile, sigmoid, isotonic, and validation-tuned baseline-plus-source blends.

## Data

```json
{
  "ibm_total": 323927,
  "cfpb_total": 200000,
  "combined_train": 314356,
  "combined_val": 78589,
  "combined_test": 130982
}
```

## Baseline test metrics

```json
{
  "rows": 130982,
  "positives": 3449,
  "positive_rate": 0.02633186239330595,
  "threshold": 0.647,
  "pr_auc": 0.18281993932961219,
  "roc_auc": 0.8904050034934079,
  "f2": 0.4371148139694134,
  "precision": 0.15891174204255823,
  "recall": 0.7773267613801101,
  "brier": 0.09716914062679648,
  "ece": 0.18104135733355897,
  "high_risk_capture": 0.9222963177732676,
  "false_auto_clear": 0.07770368222673239,
  "review_capacity": 0.35,
  "capture_lift_vs_random": 2.6351323364950505,
  "false_auto_clear_reduction_vs_random": 0.8804558734973348,
  "model": "combined_text_logreg_baseline",
  "selected_threshold": 0.647,
  "family": "baseline",
  "alpha_baseline": 1.0,
  "source_variant": "none"
}
```

## Selected blend on validation

```json
{
  "rows": 78589,
  "positives": 1352,
  "positive_rate": 0.017203425415770655,
  "threshold": 0.07859999999999999,
  "pr_auc": 0.15248034731662458,
  "roc_auc": 0.897982717146709,
  "f2": 0.36642238507661556,
  "precision": 0.12220713492161461,
  "recall": 0.7322485207100592,
  "brier": 0.015219012429493873,
  "ece": 3.372809771459824e-18,
  "high_risk_capture": 0.9223372781065089,
  "false_auto_clear": 0.07766272189349112,
  "review_capacity": 0.35,
  "capture_lift_vs_random": 2.635249366018597,
  "false_auto_clear_reduction_vs_random": 0.8805188893946291,
  "model": "blend_baseline_0.00_plus_source_isotonic_calibrated_router_1.00",
  "selected_threshold": 0.07859999999999999,
  "selection_objective": 0.30864584655847,
  "family": "blend",
  "alpha_baseline": 0.0,
  "source_variant": "source_isotonic_calibrated_router",
  "eligible_on_validation": true,
  "failed_validation_constraints": ""
}
```

## Selected blend on final test

```json
{
  "rows": 130982,
  "positives": 3449,
  "positive_rate": 0.02633186239330595,
  "threshold": 0.07859999999999999,
  "pr_auc": 0.21032700539599172,
  "roc_auc": 0.904483447677214,
  "f2": 0.45257335894548584,
  "precision": 0.16666666666666666,
  "recall": 0.7924035952449986,
  "brier": 0.022396546297113445,
  "ece": 0.006402920140881797,
  "high_risk_capture": 0.9417222383299507,
  "false_auto_clear": 0.05827776167004929,
  "review_capacity": 0.35,
  "capture_lift_vs_random": 2.690634966657002,
  "false_auto_clear_reduction_vs_random": 0.9103419051230011,
  "model": "blend_baseline_0.00_plus_source_isotonic_calibrated_router_1.00",
  "selected_threshold": 0.07859999999999999,
  "family": "blend",
  "alpha_baseline": 0.0,
  "source_variant": "source_isotonic_calibrated_router",
  "test_constraints_pass": true,
  "failed_test_constraints": "",
  "selection_status": "PASS_ELIGIBLE_BLEND_FOUND"
}
```

## Top test candidates by objective

| model | family | source_variant | alpha_baseline | rows | positives | pr_auc | roc_auc | f2 | brier | ece | high_risk_capture | false_auto_clear | capture_lift_vs_random | selected_threshold | test_constraints_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| source_sigmoid_calibrated_router | base_candidate | source_sigmoid_calibrated_router |  | 130982 | 3449 | 0.2190 | 0.9042 | 0.4521 | 0.0225 | 0.0056 | 0.9420 | 0.0580 | 2.6915 | 0.0492 |  |
| blend_baseline_0.00_plus_source_sigmoid_calibrated_router_1.00 | blend | source_sigmoid_calibrated_router | 0.0000 | 130982 | 3449 | 0.2190 | 0.9042 | 0.4521 | 0.0225 | 0.0056 | 0.9420 | 0.0580 | 2.6915 | 0.0492 |  |
| source_isotonic_calibrated_router | base_candidate | source_isotonic_calibrated_router |  | 130982 | 3449 | 0.2103 | 0.9045 | 0.4526 | 0.0224 | 0.0064 | 0.9417 | 0.0583 | 2.6906 | 0.0786 |  |
| blend_baseline_0.00_plus_source_isotonic_calibrated_router_1.00 | blend | source_isotonic_calibrated_router | 0.0000 | 130982 | 3449 | 0.2103 | 0.9045 | 0.4526 | 0.0224 | 0.0064 | 0.9417 | 0.0583 | 2.6906 | 0.0786 | True |
| blend_baseline_0.05_plus_source_sigmoid_calibrated_router_0.95 | blend | source_sigmoid_calibrated_router | 0.0500 | 130982 | 3449 | 0.2189 | 0.9009 | 0.4522 | 0.0223 | 0.0040 | 0.9333 | 0.0667 | 2.6666 | 0.0786 |  |
| blend_baseline_0.05_plus_source_isotonic_calibrated_router_0.95 | blend | source_isotonic_calibrated_router | 0.0500 | 130982 | 3449 | 0.2216 | 0.9007 | 0.4523 | 0.0222 | 0.0050 | 0.9307 | 0.0693 | 2.6592 | 0.1178 |  |
| blend_baseline_0.10_plus_source_isotonic_calibrated_router_0.90 | blend | source_isotonic_calibrated_router | 0.1000 | 130982 | 3449 | 0.2211 | 0.8989 | 0.4526 | 0.0224 | 0.0125 | 0.9295 | 0.0705 | 2.6558 | 0.1374 |  |
| blend_baseline_0.10_plus_source_sigmoid_calibrated_router_0.90 | blend | source_sigmoid_calibrated_router | 0.1000 | 130982 | 3449 | 0.2190 | 0.8983 | 0.4521 | 0.0225 | 0.0132 | 0.9304 | 0.0696 | 2.6583 | 0.1080 |  |
| blend_baseline_0.15_plus_source_isotonic_calibrated_router_0.85 | blend | source_isotonic_calibrated_router | 0.1500 | 130982 | 3449 | 0.2208 | 0.8983 | 0.4522 | 0.0231 | 0.0218 | 0.9284 | 0.0716 | 2.6525 | 0.1668 |  |
| blend_baseline_0.20_plus_source_sigmoid_calibrated_router_0.80 | blend | source_sigmoid_calibrated_router | 0.2000 | 130982 | 3449 | 0.2200 | 0.8967 | 0.4516 | 0.0242 | 0.0318 | 0.9266 | 0.0734 | 2.6476 | 0.1962 |  |
| blend_baseline_0.15_plus_source_sigmoid_calibrated_router_0.85 | blend | source_sigmoid_calibrated_router | 0.1500 | 130982 | 3449 | 0.2192 | 0.8970 | 0.4511 | 0.0231 | 0.0225 | 0.9264 | 0.0736 | 2.6467 | 0.1472 |  |
| blend_baseline_0.20_plus_source_isotonic_calibrated_router_0.80 | blend | source_isotonic_calibrated_router | 0.2000 | 130982 | 3449 | 0.2171 | 0.8978 | 0.4518 | 0.0241 | 0.0312 | 0.9275 | 0.0725 | 2.6500 | 0.1962 |  |
| blend_baseline_0.25_plus_source_sigmoid_calibrated_router_0.75 | blend | source_sigmoid_calibrated_router | 0.2500 | 130982 | 3449 | 0.2200 | 0.8963 | 0.4461 | 0.0256 | 0.0412 | 0.9261 | 0.0739 | 2.6459 | 0.1962 |  |
| blend_baseline_0.25_plus_source_isotonic_calibrated_router_0.75 | blend | source_isotonic_calibrated_router | 0.2500 | 130982 | 3449 | 0.2170 | 0.8979 | 0.4449 | 0.0256 | 0.0405 | 0.9269 | 0.0731 | 2.6484 | 0.2256 |  |
| blend_baseline_0.30_plus_source_sigmoid_calibrated_router_0.70 | blend | source_sigmoid_calibrated_router | 0.3000 | 130982 | 3449 | 0.2193 | 0.8955 | 0.4457 | 0.0275 | 0.0505 | 0.9237 | 0.0763 | 2.6393 | 0.2256 |  |
| blend_baseline_0.35_plus_source_sigmoid_calibrated_router_0.65 | blend | source_sigmoid_calibrated_router | 0.3500 | 130982 | 3449 | 0.2187 | 0.8952 | 0.4451 | 0.0298 | 0.0598 | 0.9237 | 0.0763 | 2.6393 | 0.2550 |  |
| blend_baseline_0.30_plus_source_isotonic_calibrated_router_0.70 | blend | source_isotonic_calibrated_router | 0.3000 | 130982 | 3449 | 0.2167 | 0.8974 | 0.4456 | 0.0274 | 0.0499 | 0.9237 | 0.0763 | 2.6393 | 0.2452 |  |
| blend_baseline_0.40_plus_source_sigmoid_calibrated_router_0.60 | blend | source_sigmoid_calibrated_router | 0.4000 | 130982 | 3449 | 0.2183 | 0.8948 | 0.4449 | 0.0325 | 0.0691 | 0.9232 | 0.0768 | 2.6376 | 0.2844 |  |
| blend_baseline_0.35_plus_source_isotonic_calibrated_router_0.65 | blend | source_isotonic_calibrated_router | 0.3500 | 130982 | 3449 | 0.2162 | 0.8969 | 0.4456 | 0.0297 | 0.0593 | 0.9235 | 0.0765 | 2.6384 | 0.2746 |  |
| blend_baseline_0.45_plus_source_sigmoid_calibrated_router_0.55 | blend | source_sigmoid_calibrated_router | 0.4500 | 130982 | 3449 | 0.2172 | 0.8944 | 0.4439 | 0.0356 | 0.0785 | 0.9223 | 0.0777 | 2.6351 | 0.3236 |  |

## Source-slice comparison

| model | slice | rows | positives | pr_auc | roc_auc | f2 | brier | ece | high_risk_capture | false_auto_clear |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| combined_text_logreg_baseline | combined_test | 130982 | 3449 | 0.1828 | 0.8904 | 0.4371 | 0.0972 | 0.1810 | 0.9223 | 0.0777 |
| combined_text_logreg_baseline | ibm_aml_only | 80982 | 2088 | 0.1582 | 0.8978 | 0.4586 | 0.1033 | 0.2075 | 0.9353 | 0.0647 |
| combined_text_logreg_baseline | cfpb_only | 50000 | 1361 | 0.2211 | 0.8892 | 0.3951 | 0.0872 | 0.1381 | 0.9221 | 0.0779 |
| blend_baseline_0.00_plus_source_isotonic_calibrated_router_1.00 | combined_test | 130982 | 3449 | 0.2103 | 0.9045 | 0.4526 | 0.0224 | 0.0064 | 0.9417 | 0.0583 |
| blend_baseline_0.00_plus_source_isotonic_calibrated_router_1.00 | ibm_aml_only | 80982 | 2088 | 0.2012 | 0.9057 | 0.4816 | 0.0217 | 0.0069 | 0.9382 | 0.0618 |
| blend_baseline_0.00_plus_source_isotonic_calibrated_router_1.00 | cfpb_only | 50000 | 1361 | 0.1957 | 0.8890 | 0.3980 | 0.0235 | 0.0056 | 0.9295 | 0.0705 |

## Claim summary

```json
{
  "best_aligned_vs_combined_text_baseline": {
    "pr_auc_pct_change": 0.15045987963482543,
    "roc_auc_pct_change": 0.015811281527586714,
    "f2_pct_change": 0.035364953284685884,
    "brier_pct_reduction": 0.7695096802066692,
    "ece_pct_reduction": 0.9646328317728818,
    "high_risk_capture_point_change": 0.01942592055668313,
    "false_auto_clear_pct_reduction": 0.25000000000000006
  }
}
```

## Resume-safe claims

- Added source-wise score normalization, percentile alignment, calibration, and validation-tuned blending to diagnose and reduce score-scale mismatch between CFPB text and IBM AML behavior models.
- Selected a validation-constrained blended router that preserved or improved combined-baseline PR-AUC/F2 while reducing calibration error and false auto-clear on the future test split.

## Claims not to use

- Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.
- Do not claim the aligned router beat the combined baseline unless test_constraints_pass is true and PR-AUC/F2 are not degraded.
- Do not claim normalization alone solved the issue; use the selected validation-tuned blend result.

## External artifacts

- output_dir: `C:\Users\bjw-0\Downloads\paymentops_external_data\score_alignment_blend_outputs`
- models_dir: `C:\Users\bjw-0\Downloads\paymentops_external_data\score_alignment_blend_outputs\models`
- score_alignment_validation_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\score_alignment_blend_outputs\score_alignment_validation_results.csv`
- score_alignment_test_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\score_alignment_blend_outputs\score_alignment_test_results.csv`
- score_alignment_source_slice_results: `C:\Users\bjw-0\Downloads\paymentops_external_data\score_alignment_blend_outputs\score_alignment_source_slice_results.csv`