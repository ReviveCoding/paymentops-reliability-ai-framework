# Transformer Fine-Tuning Readiness

## Purpose

Provide a Transformer fine-tuning-ready scaffold for the CFPB-style financial-operations issue-routing task.

## Status

**Scaffold only.** No pretrained Transformer is downloaded or fine-tuned by default, so this remains local and reproducible without external model access.

## Configuration

```json
{
  "status": "fine_tuning_ready_scaffold_only",
  "base_model": "distilbert-base-uncased",
  "task": "financial_operations_issue_routing",
  "text_column": "consumer_complaint_narrative",
  "label_column": "issue_group",
  "num_labels": 4,
  "label2id": {
    "credit_card": 0,
    "debt_collection": 1,
    "mortgage": 2,
    "payment_or_transfer": 3
  },
  "id2label": {
    "0": "credit_card",
    "1": "debt_collection",
    "2": "mortgage",
    "3": "payment_or_transfer"
  },
  "claim_boundary": "No Transformer fine-tuning run is claimed until a user executes the optional training path and saves run logs.",
  "recommended_metrics": [
    "macro_f1",
    "weighted_f1",
    "per_issue_f1",
    "calibration_error"
  ]
}
```

## Optional execution path

1. Install optional dependencies, for example `transformers`, `datasets`, and `torch`.
2. Use `distilbert-base-uncased` or another approved encoder model.
3. Fine-tune on full CFPB public complaint exports after mapping the target labels.
4. Save training logs, validation metrics, model card, and claim boundary before adding resume wording.

## Resume-safe wording

Safe now: `Transformer fine-tuning-ready issue-routing scaffold`.

Unsafe unless actually run: `fine-tuned a Transformer model` or `deployed Transformer model in production`.
