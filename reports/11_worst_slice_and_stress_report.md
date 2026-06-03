# Worst-Slice and Stress Robustness Report

## Purpose

This report closes a remaining weakness from the first enhanced version: aggregate metrics alone can hide weak slices. The project now reports worst-slice false auto-clear, calibration, and simple stress tests on local sample data.

## Worst false-auto-clear slices

| Slice type | Slice | n | False auto-clear | Review burden | ECE |
|---|---|---:|---:|---:|---:|
| exception_type | communication tactics | 3 | 1.000 | 0.333 | 0.056 |
| payment_status | PDNG | 4 | 0.750 | 0.250 | 0.057 |
| payment_status | RJCT | 4 | 0.750 | 0.250 | 0.014 |
| exception_type | amount_limit | 4 | 0.750 | 0.250 | 0.028 |
| exception_type | duplicate_payment | 4 | 0.750 | 0.250 | 0.068 |
| exception_type | status_mismatch | 4 | 0.750 | 0.250 | 0.037 |
| case_type | fraud_transaction | 45 | 0.647 | 0.444 | 0.089 |
| exception_type | fraud_score | 45 | 0.647 | 0.444 | 0.089 |

## Worst calibration slices

| Slice type | Slice | n | ECE | False auto-clear | Review burden |
|---|---|---:|---:|---:|---:|
| exception_type | future_dated | 3 | 0.356 | 0.000 | 0.333 |
| exception_type | overdraft fee | 4 | 0.292 | 0.000 | 0.250 |
| exception_type | refund not received | 3 | 0.218 | 0.000 | 0.333 |
| payment_status | ACSP | 6 | 0.204 | 0.500 | 0.333 |
| amount_bucket | low_amount | 42 | 0.140 | 0.471 | 0.429 |
| case_type | customer_complaint | 30 | 0.135 | 0.267 | 0.433 |
| amount_bucket | no_amount | 30 | 0.135 | 0.267 | 0.433 |
| amount_bucket | medium_amount | 27 | 0.112 | 0.267 | 0.444 |

## Stress tests

| Stress test | Value |
|---|---:|
| Amount 3x PSI | 0.457 |
| Amount 3x mean rule-prior shift | 0.027 |
| Payment-status pending/status-mismatch mean rule-prior shift | 0.212 |

## Interpretation

The project now surfaces whether the release gate is driven by a few fragile slices. This is still a local/sample-data stress test, not evidence of production robustness.
