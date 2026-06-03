# PaymentOps Data Card

## Data sources

| Source | Type | Purpose |
|---|---|---|
| CFPB-style sample | public-style sample | issue routing, complaint triage, escalation proxy |
| Fraud benchmark-style sample | synthetic benchmark-style sample | fraud/risk classification and review ranking |
| ISO 20022-inspired sample | synthetic workflow | payment status, exception routing, RAG investigation |
| Payment policy docs | synthetic policy docs | evidence retrieval and grounded summaries |

## Data boundary

The repository does not include raw CFPB exports, real bank records, real customer account data, or production payment logs. Large datasets should be stored outside Git and linked through adapter scripts.
