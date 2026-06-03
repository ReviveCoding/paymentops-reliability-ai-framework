# Score Alignment Blend Resume Claims

## Use only if consistent with latest metrics

- Added source-wise score normalization, percentile alignment, calibration, and validation-tuned blending to diagnose and reduce score-scale mismatch between CFPB text and IBM AML behavior models.
- Selected a validation-constrained blended router that preserved or improved combined-baseline PR-AUC/F2 while reducing calibration error and false auto-clear on the future test split.

## Do not use

- Do not claim proprietary bank data, production payment logs, JPMC data, or regulatory certification.
- Do not claim the aligned router beat the combined baseline unless test_constraints_pass is true and PR-AUC/F2 are not degraded.
- Do not claim normalization alone solved the issue; use the selected validation-tuned blend result.