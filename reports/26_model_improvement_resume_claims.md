# Model Improvement Resume Claims

## Use these claims only if consistent with the latest report

- Constrained champion `text_plus_amount_text_length` satisfied baseline-safety constraints against the vanilla text baseline across ranking, threshold-optimized detection, calibration, and review-capacity metrics.
- At 35% review capacity, the selected constrained workflow captured 0.9071 of high-risk cases with false auto-clear 0.0929.
- Validation-selected threshold optimization selected threshold 0.6100 for `text_plus_amount_text_length`, producing optimized F2 0.3890 on the future test split.

## Do not use

- Do not claim hybrid or all-numeric features improved every metric unless the constrained champion is not vanilla and all hard constraints passed.
- Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.
- Do not claim source-identity features are production-safe; they are ablation-only unless source-separated evaluation supports them.