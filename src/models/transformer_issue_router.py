from __future__ import annotations

from pathlib import Path
import json
import pandas as pd
from src.utils import DATA_DIR, REPORTS_DIR, ARTIFACTS_DIR, write_report, write_json


DEFAULT_MODEL = "distilbert-base-uncased"


def build_label_maps(df: pd.DataFrame, label_col: str = "issue_group") -> dict:
    labels = sorted(str(x) for x in df[label_col].dropna().unique())
    label2id = {label: i for i, label in enumerate(labels)}
    id2label = {i: label for label, i in label2id.items()}
    return {"label2id": label2id, "id2label": id2label}


def write_transformer_readiness_report() -> dict:
    """Create a Transformer fine-tuning readiness pack without requiring downloads.

    This is intentionally a scaffold. It documents the exact task, label space,
    config, and command boundaries. It does not claim that a Transformer was
    trained unless the user later runs it with an actual model/backend.
    """
    cfpb_path = DATA_DIR / "sample_public" / "cfpb_sample.csv"
    df = pd.read_csv(cfpb_path) if cfpb_path.exists() else pd.DataFrame({"issue_group": ["unknown"], "consumer_complaint_narrative": [""]})
    maps = build_label_maps(df)
    pack = {
        "status": "fine_tuning_ready_scaffold_only",
        "base_model": DEFAULT_MODEL,
        "task": "financial_operations_issue_routing",
        "text_column": "consumer_complaint_narrative",
        "label_column": "issue_group",
        "num_labels": len(maps["label2id"]),
        "label2id": maps["label2id"],
        "id2label": maps["id2label"],
        "claim_boundary": "No Transformer fine-tuning run is claimed until a user executes the optional training path and saves run logs.",
        "recommended_metrics": ["macro_f1", "weighted_f1", "per_issue_f1", "calibration_error"],
    }
    write_json(ARTIFACTS_DIR / "transformer" / "issue_router_readiness.json", pack)
    body = f"""
## Purpose

Provide a Transformer fine-tuning-ready scaffold for the CFPB-style financial-operations issue-routing task.

## Status

**Scaffold only.** No pretrained Transformer is downloaded or fine-tuned by default, so this remains local and reproducible without external model access.

## Configuration

```json
{json.dumps(pack, indent=2)}
```

## Optional execution path

1. Install optional dependencies, for example `transformers`, `datasets`, and `torch`.
2. Use `{DEFAULT_MODEL}` or another approved encoder model.
3. Fine-tune on full CFPB public complaint exports after mapping the target labels.
4. Save training logs, validation metrics, model card, and claim boundary before adding resume wording.

## Resume-safe wording

Safe now: `Transformer fine-tuning-ready issue-routing scaffold`.

Unsafe unless actually run: `fine-tuned a Transformer model` or `deployed Transformer model in production`.
"""
    write_report(REPORTS_DIR / "transformer_finetuning_readiness.md", "Transformer Fine-Tuning Readiness", body)
    return pack


if __name__ == "__main__":
    print(json.dumps(write_transformer_readiness_report(), indent=2))
