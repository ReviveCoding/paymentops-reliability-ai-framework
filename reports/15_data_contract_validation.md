# Data Contract Validation

## Purpose

This report implements a lightweight Great-Expectations-style data contract for the common case schema. It is dependency-light so the project remains local/GitHub runnable, but it preserves the production pattern of explicit expectations, validation results, and human-readable documentation.

## Result

**PASS**

| Expectation | Result | Observed | Details |
|---|---|---|---|
| all_required_columns_present | PASS | `[]` | Common case schema must contain all required columns. |
| case_id_non_null | PASS | `0` | No case_id should be null. |
| case_id_unique | PASS | `0` | case_id should uniquely identify a case. |
| event_time_parseable | PASS | `0` | All event_time values should parse as datetimes. |
| case_type_allowed | PASS | `['customer_complaint', 'fraud_transaction', 'iso20022_payment_case']` | case_type must stay inside the documented ontology. |
| amount_non_negative | PASS | `0.0` | amount should be non-negative. |
| text_non_empty | PASS | `0` | All cases should have text/narrative for routing and RAG. |
| risk_label_binary | PASS | `[0, 1]` | risk_label must be binary for this benchmark. |
| route_label_allowed | PASS | `['analyst_review', 'auto_resolve', 'compliance_review']` | route_label must be an allowed route. |
| source_dataset_non_null | PASS | `0` | source_dataset should not be null. |
| payment_status_non_null | PASS | `0` | payment_status should not be null. |
| exception_type_non_null | PASS | `0` | exception_type should not be null. |
| issue_group_non_null | PASS | `0` | issue_group should not be null. |

## Artifact

The expectation suite is saved at `artifacts/data_contracts/common_case_expectation_suite.json`.
