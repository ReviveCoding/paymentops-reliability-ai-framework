from __future__ import annotations

import json
from datetime import datetime, timezone
from src.utils import ARTIFACTS_DIR, REPORTS_DIR, write_json, write_report
from src.models.transformer_issue_router import write_transformer_readiness_report


def write_aws_readiness_pack() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    model_registry = {
        "status": "sagemaker_compatible_manifest_only",
        "model_package_group_name": "paymentops-risk-routing",
        "current_candidate": {
            "model_name": "rule-prior-residual-risk-router",
            "version": "0.1.0-local",
            "approval_status": "PendingManualApproval",
            "model_artifact_path": "s3://<bucket>/paymentops/models/rule_prior_residual/model.tar.gz",
            "inference_image": "<account>.dkr.ecr.<region>.amazonaws.com/paymentops-risk-router:latest",
            "supported_content_types": ["application/json"],
            "supported_response_types": ["application/json"],
            "metrics": ["pr_auc", "f2", "brier", "ece", "false_auto_clear_rate"],
        },
        "claim_boundary": "Manifest is SageMaker-compatible scaffolding only. It is not evidence of an AWS run or deployment.",
        "generated_at": now,
    }
    feature_store = {
        "status": "feature_store_style_manifest_only",
        "offline_store_prefix": "s3://<bucket>/paymentops/offline_features/",
        "online_feature_group": "paymentops-risk-routing-online",
        "entity_key": "case_id",
        "event_time_key": "event_time",
        "feature_groups": [
            {"name": "case_context_features", "features": ["case_type", "issue_group", "payment_status", "exception_type"]},
            {"name": "risk_features", "features": ["amount", "case_health_timestep", "rule_prior_score", "residual_score"]},
            {"name": "evidence_features", "features": ["evidence_slot_recall", "evidence_slot_precision", "source_conflict_flag"]},
        ],
        "backfill_plan": "Run src.data.adapters over local public exports, then materialize feature_table partitions by event_date.",
        "claim_boundary": "Schema-governance scaffold only unless actual offline/online feature store resources are created.",
        "generated_at": now,
    }
    pipeline = {
        "status": "sagemaker_pipeline_definition_scaffold_only",
        "steps": [
            "DataQualityAndSchemaValidation",
            "FeatureMaterialization",
            "VanillaBaselineTraining",
            "ResidualRiskModelTraining",
            "CalibrationAndThresholdSelection",
            "ModelEvaluation",
            "RegisterModelPendingApproval",
        ],
        "inputs": {"train": "s3://<bucket>/paymentops/splits/train/", "calibration": "s3://<bucket>/paymentops/splits/calibration/", "test": "s3://<bucket>/paymentops/splits/test/"},
        "outputs": {"metrics": "s3://<bucket>/paymentops/reports/metrics.json", "model_registry": "paymentops-risk-routing"},
    }
    emr = {
        "status": "emr_spark_job_config_scaffold_only",
        "entrypoint": "src/data/spark_feature_pipeline.py",
        "spark_submit_args": ["--master", "yarn", "--deploy-mode", "cluster"],
        "input_paths": ["s3://<bucket>/paymentops/raw/cfpb/", "s3://<bucket>/paymentops/raw/fraud/"],
        "output_path": "s3://<bucket>/paymentops/processed/features/",
        "claim_boundary": "EMR-compatible job configuration only. No EMR execution is claimed.",
    }
    write_json(ARTIFACTS_DIR / "aws" / "model_registry_manifest.json", model_registry)
    write_json(ARTIFACTS_DIR / "aws" / "feature_store_manifest.json", feature_store)
    write_json(ARTIFACTS_DIR / "aws" / "sagemaker_pipeline_definition.json", pipeline)
    write_json(ARTIFACTS_DIR / "aws" / "emr_spark_job_config.json", emr)
    body = f"""
## Purpose

Add cloud-production-readiness evidence without overstating execution. These artifacts are compatible with common SageMaker/EMR-style workflows but are **not** actual AWS run logs.

## Added artifacts

| Artifact | Purpose | Claim boundary |
|---|---|---|
| `artifacts/aws/model_registry_manifest.json` | SageMaker-style model group/version metadata | Manifest only |
| `artifacts/aws/feature_store_manifest.json` | Offline/online feature schema governance | Manifest only |
| `artifacts/aws/sagemaker_pipeline_definition.json` | Train/evaluate/register pipeline outline | Definition scaffold only |
| `artifacts/aws/emr_spark_job_config.json` | EMR-compatible Spark job config | Config scaffold only |

## Resume-safe wording

Safe: `SageMaker-compatible model registry manifests, feature-store-style schema governance, and EMR-compatible Spark job configuration`.

Unsafe unless actually run: `deployed on AWS`, `ran EMR jobs`, or `registered a model in SageMaker Model Registry`.
"""
    write_report(REPORTS_DIR / "aws_sagemaker_readiness.md", "AWS and SageMaker Readiness Pack", body)
    return {"model_registry": model_registry, "feature_store": feature_store, "pipeline": pipeline, "emr": emr}


def write_dataset_adapter_report() -> None:
    body = """
## Purpose

Document full-public-dataset adapter readiness while keeping the repository small and sample-data runnable.

## Added adapters

| Adapter | Local input expected | Output |
|---|---|---|
| `src/data/adapters/cfpb_full_adapter.py` | CFPB complaint CSV export | Project common case schema |
| `src/data/adapters/ieee_cis_adapter.py` | IEEE-CIS transaction CSV and optional identity CSV | Project common case schema |
| `src/data/adapters/ibm_aml_adapter.py` | IBM AML-style transaction CSV | Project common case schema |

## Boundary

The adapters do not download public datasets and do not include large raw files. They only standardize user-provided local public exports.
"""
    write_report(REPORTS_DIR / "full_dataset_adapter_readiness.md", "Full Public Dataset Adapter Readiness", body)


def write_cicd_docker_report() -> None:
    body = """
## Purpose

Add repository hygiene and CI/CD readiness evidence.

## Added files

| File | Purpose |
|---|---|
| `Dockerfile` | Containerized FastAPI service and local project runtime |
| `.github/workflows/ci.yml` | GitHub Actions workflow that installs dependencies, runs `make all`, and uploads reports/artifacts |

## Boundary

This is CI/CD-ready scaffolding. A remote GitHub Actions pass should only be claimed after pushing to GitHub and verifying a successful workflow run.
"""
    write_report(REPORTS_DIR / "ci_cd_docker_readiness.md", "CI/CD and Docker Readiness", body)


def write_model_registry_report() -> None:
    versions = {
        "registry_name": "paymentops-local-model-registry",
        "versions": [
            {"name": "vanilla_risk_model", "version": "0.1.0", "stage": "baseline", "approval": "ReferenceOnly"},
            {"name": "rule_prior_residual_risk_router", "version": "0.1.0", "stage": "candidate", "approval": "PendingManualReview"},
            {"name": "transformer_issue_router", "version": "0.0.0-scaffold", "stage": "fine_tuning_ready", "approval": "NotTrained"},
        ],
        "claim_boundary": "Local manifest only. This is not a hosted MLflow or SageMaker registry unless later deployed and logged.",
    }
    write_json(ARTIFACTS_DIR / "model_registry" / "model_versions.json", versions)
    body = f"""
## Local model registry manifest

```json
{json.dumps(versions, indent=2)}
```
"""
    write_report(REPORTS_DIR / "model_registry_manifest.md", "Model Registry Manifest", body)


def main() -> dict:
    aws = write_aws_readiness_pack()
    transformer = write_transformer_readiness_report()
    write_dataset_adapter_report()
    write_cicd_docker_report()
    write_model_registry_report()
    return {"aws": aws, "transformer": transformer}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2)[:4000])
