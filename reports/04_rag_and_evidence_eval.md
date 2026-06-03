# RAG and Evidence Reliability Evaluation

## Purpose

Evaluate whether coverage-adaptive retrieval and ABC-style evidence deflation improve evidence-slot coverage over a vanilla fixed top-k retrieval baseline.

## Required evidence slots

`['customer_impact', 'payment_status', 'policy_rule', 'required_action', 'risk_reason']`

## Results

| Metric | Vanilla BM25 Top-1 | Coverage + ABC Correction |
|---|---:|---:|
| Evidence-slot Recall | 0.400 | 1.000 |
| Evidence-slot Precision | 1.000 | 1.000 |
| Evidence-slot F1 | 0.571 | 1.000 |
| Citation support rate | - | 1.000 |
| Unsupported claim rate | - | 0.000 |

## Interpretation

The vanilla baseline intentionally uses a narrow top-1 evidence path to mimic fixed-top-k under-coverage. The enhanced path expands evidence only when missing evidence slots are discovered, then deflates unsupported or duplicate evidence. This implements the same reliability logic as a recall-first expansion followed by precision-oriented correction.
