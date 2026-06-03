# Controls Matrix

| AI RMF Function | Control | Evidence | Status |
|---|---|---|---|
| Govern | Claim boundary | README.md and CLAIM_BOUNDARY.md | Implemented |
| Govern | Intended/prohibited use | model_card.md | Implemented |
| Map | Dataset source inventory | 01_data_inventory.md | Implemented |
| Map | Synthetic/public boundary | data_card.md | Implemented |
| Measure | Calibration metrics | 03_reliability_ablation.md | Implemented |
| Measure | Evidence-slot metrics | 04_rag_and_evidence_eval.md | Implemented |
| Measure | Latency benchmark | 08_latency_report.md | Implemented |
| Measure | Worst-slice and stress tests | 11_worst_slice_and_stress_report.md | Implemented |
| Measure | Feature-store contract validation | 12_feature_store_backfill_validation.md | Implemented |
| Measure | Security guardrail smoke tests | 13_security_guardrail_eval.md | Implemented |
| Manage | Permission gate | src/agents/permission_gates.py | Implemented |
| Manage | Human-review routing | agent traces | Implemented |
| Manage | Release gate | 09_release_decision.md | Implemented |
