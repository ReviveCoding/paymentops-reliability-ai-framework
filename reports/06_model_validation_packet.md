# Model Validation Packet

## Purpose

Document validation evidence for the local PaymentOps Reliability AI Framework.

## Govern

- Intended use: offline portfolio and model-validation demonstration.
- Prohibited use: real payment decisioning, production use, or regulatory certification.
- Human-review policy: weak evidence, source conflict, high-impact action, or elevated risk must route to review.

## Map

- Data sources: CFPB-style sample, fraud benchmark-style sample, synthetic ISO 20022-inspired payment cases, synthetic policy docs.
- Claim boundary: no proprietary bank data and no production deployment.

## Measure

```json
{
  "issue_router": {
    "macro_f1": 1.0,
    "weighted_f1": 1.0
  },
  "vanilla_risk": {
    "roc_auc": 0.8282967032967032,
    "pr_auc": 0.8475384888822581,
    "f1": 0.6578947368421053,
    "f2": 0.5605381165917953,
    "precision": 0.9259259259259259,
    "recall": 0.5102040816326531,
    "brier": 0.17801833997097705,
    "ece": 0.12769360535959512,
    "high_risk_capture": 0.5306122448979592,
    "false_auto_clear_rate": 0.46938775510204084,
    "review_burden": 0.297029702970297
  },
  "enhanced_risk": {
    "roc_auc": 0.79925431711146,
    "pr_auc": 0.8307245084991213,
    "f1": 0.6756756756756757,
    "f2": 0.5656108597283813,
    "precision": 1.0,
    "recall": 0.5102040816326531,
    "brier": 0.15360763099263952,
    "ece": 0.07279475556269374,
    "high_risk_capture": 0.6122448979591837,
    "false_auto_clear_rate": 0.3877551020408163,
    "review_burden": 0.44554455445544555,
    "policy_objective": 1.1568213272710584,
    "selected_score_name": "ml_residual",
    "selected_review_capacity": 0.45
  },
  "operating_policy": {
    "constraint_status": "PASS",
    "selected_policy": {
      "score_name": "ml_residual",
      "temperature": 1.0,
      "review_capacity": 0.45,
      "prior_weight": null,
      "metrics": {
        "roc_auc": 0.79925431711146,
        "pr_auc": 0.8307245084991213,
        "f1": 0.6756756756756757,
        "f2": 0.5656108597283813,
        "precision": 1.0,
        "recall": 0.5102040816326531,
        "brier": 0.15360763099263952,
        "ece": 0.07279475556269374,
        "high_risk_capture": 0.6122448979591837,
        "false_auto_clear_rate": 0.3877551020408163,
        "review_burden": 0.44554455445544555,
        "policy_objective": 1.1568213272710584,
        "selected_score_name": "ml_residual",
        "selected_review_capacity": 0.45
      },
      "objective": 1.1568213272710584
    }
  },
  "scaled_calibration": {
    "brier": 0.1542356629277943,
    "ece": 0.07782801657653302
  },
  "rag": {
    "baseline_evidence_slot_recall": 0.4000000000000001,
    "baseline_evidence_slot_precision": 1.0,
    "baseline_evidence_slot_f1": 0.5714285714285714,
    "enhanced_evidence_slot_recall": 1.0,
    "enhanced_evidence_slot_precision": 1.0,
    "enhanced_evidence_slot_f1": 1.0,
    "citation_support_rate": 1.0,
    "unsupported_claim_rate": 0.0
  }
}
```

## Robustness, feature-store, and guardrail checks

```json
{
  "robustness": {
    "slice_count": 21,
    "worst_false_auto_clear_slices": [
      {
        "slice_type": "exception_type",
        "slice": "communication tactics",
        "n": 3,
        "roc_auc": 0.5,
        "pr_auc": 0.3333333333333333,
        "f1": 0.0,
        "f2": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "brier": 0.22536594654004147,
        "ece": 0.056068924707178336,
        "high_risk_capture": 0.0,
        "false_auto_clear_rate": 1.0,
        "review_burden": 0.3333333333333333
      },
      {
        "slice_type": "payment_status",
        "slice": "PDNG",
        "n": 4,
        "roc_auc": 0.5,
        "pr_auc": 0.5,
        "f1": 1.0,
        "f2": 0.9999999999997999,
        "precision": 1.0,
        "recall": 1.0,
        "brier": 0.0043006501479079294,
        "ece": 0.056811298006791966,
        "high_risk_capture": 0.25,
        "false_auto_clear_rate": 0.75,
        "review_burden": 0.25
      },
      {
        "slice_type": "payment_status",
        "slice": "RJCT",
        "n": 4,
        "roc_auc": 0.5,
        "pr_auc": 0.5,
        "f1": 1.0,
        "f2": 0.9999999999997999,
        "precision": 1.0,
        "recall": 1.0,
        "brier": 0.0007947119918318579,
        "ece": 0.014311891537499899,
        "high_risk_capture": 0.25,
        "false_auto_clear_rate": 0.75,
        "review_burden": 0.25
      },
      {
        "slice_type": "exception_type",
        "slice": "amount_limit",
        "n": 4,
        "roc_auc": 0.5,
        "pr_auc": 0.5,
        "f1": 1.0,
        "f2": 0.9999999999997999,
        "precision": 1.0,
        "recall": 1.0,
        "brier": 0.0015594539493569287,
        "ece": 0.0280028497443352,
        "high_risk_capture": 0.25,
        "false_auto_clear_rate": 0.75,
        "review_burden": 0.25
      },
      {
        "slice_type": "exception_type",
        "slice": "duplicate_payment",
        "n": 4,
        "roc_auc": 0.5,
        "pr_auc": 0.5,
        "f1": 1.0,
        "f2": 0.9999999999997999,
        "precision": 1.0,
        "recall": 1.0,
        "brier": 0.004646870012434836,
        "ece": 0.06812726253872747,
        "high_risk_capture": 0.25,
        "false_auto_clear_rate": 0.75,
        "review_burden": 0.25
      },
      {
        "slice_type": "exception_type",
        "slice": "status_mismatch",
        "n": 4,
        "roc_auc": 0.5,
        "pr_auc": 0.5,
        "f1": 1.0,
        "f2": 0.9999999999997999,
        "precision": 1.0,
        "recall": 1.0,
        "brier": 0.0026787609839681796,
        "ece": 0.03667579980751834,
        "high_risk_capture": 0.25,
        "false_auto_clear_rate": 0.75,
        "review_burden": 0.25
      },
      {
        "slice_type": "case_type",
        "slice": "fraud_transaction",
        "n": 45,
        "roc_auc": 0.43067226890756305,
        "pr_auc": 0.3859708943734105,
        "f1": 0.1111111111111111,
        "f2": 0.07246376811592418,
        "precision": 1.0,
        "recall": 0.058823529411764705,
        "brier": 0.23682566916369774,
        "ece": 0.08898547904057899,
        "high_risk_capture": 0.35294117647058826,
        "false_auto_clear_rate": 0.6470588235294118,
        "review_burden": 0.4444444444444444
      },
      {
        "slice_type": "exception_type",
        "slice": "fraud_score",
        "n": 45,
        "roc_auc": 0.43067226890756305,
        "pr_auc": 0.3859708943734105,
        "f1": 0.1111111111111111,
        "f2": 0.07246376811592418,
        "precision": 1.0,
        "recall": 0.058823529411764705,
        "brier": 0.23682566916369774,
        "ece": 0.08898547904057899,
        "high_risk_capture": 0.35294117647058826,
        "false_auto_clear_rate": 0.6470588235294118,
        "review_burden": 0.4444444444444444
      }
    ],
    "worst_calibration_slices": [
      {
        "slice_type": "exception_type",
        "slice": "future_dated",
        "n": 3,
        "roc_auc": 1.0,
        "pr_auc": 1.0,
        "f1": 0.0,
        "f2"
```

## Manage

- Permission gates block unsafe actions.
- PII redaction and prompt-injection smoke tests are included.
- Feature-store-style schema/backfill validation is included.
- Worst-slice and stress-test reports surface fragile local slices.
- Release gate returns PASS/REVIEW/BLOCK.
- Audit logs preserve case_id, risk score, evidence document IDs, and final action.

## Known limitations

- Sample data is intentionally small for local reproducibility.
- The RAG layer uses deterministic templates and BM25-style retrieval by default.
- LangGraph and external LLM backends are optional.
- AWS/SageMaker files are compatibility scaffolds only unless actual run logs are added.
- AWS/SageMaker readiness pack, model registry manifests, feature-store-style schema governance, and Transformer fine-tuning scaffold are not evidence of actual cloud execution or fine-tuning.
- Security guardrail tests are local synthetic smoke tests, not a formal penetration test or privacy certification.
