# AWS and SageMaker Readiness Pack

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
