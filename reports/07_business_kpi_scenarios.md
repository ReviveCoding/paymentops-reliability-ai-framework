# Business KPI Scenario Report

## Scenario comparison

| Scenario | High-risk capture | False auto-clear | Review burden | Unsupported action rate | p95 latency ms |
|---|---:|---:|---:|---:|---:|
| S0 Manual review only | 1.000 | 0.000 | 1.000 | 0.000 | 200 |
| S1 Vanilla ML | 0.531 | 0.469 | 0.297 | 0.080 | 450 |
| S2 Residual correction + CHT | 0.612 | 0.388 | 0.446 | 0.050 | 650 |
| S3 RAG evidence gate | 0.612 | 0.388 | 0.450 | 0.000 | 900 |
| S4 Agent + release gate | 0.612 | 0.388 | 0.450 | 0.000 | 1100 |

## Interpretation

Manual review maximizes capture but creates unsustainable review burden. Vanilla ML reduces burden but can miss high-risk cases. The reliability-enhanced path is designed to improve the risk/burden tradeoff, and the agent/release-gate layer adds evidence and permission controls.
