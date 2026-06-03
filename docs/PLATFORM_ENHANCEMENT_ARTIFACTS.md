# PaymentOps Platform Enhancement Artifacts

This enhancement adds three targeted screening-gap artifacts:

1. Local PySpark ETL feature-store artifact
2. AWS/S3/SageMaker-style architecture artifact
3. LangGraph PaymentOps agentic review wrapper

## Claim boundary

These artifacts are local/public/proxy portfolio artifacts. They do not claim production AWS deployment, real payment logs, JPMC systems, real customer data, or regulatory certification.

## Run commands

```powershell
$env:PAYMENTOPS_EXTERNAL_DATA = "C:\Users\bjw-0\Downloads\paymentops_external_data"

python -m src.scripts.run_pyspark_etl_feature_store
python -m src.scripts.run_aws_sagemaker_style_artifact
python -m src.scripts.run_langgraph_paymentops_wrapper
```

## Optional live S3 upload

Only run this if you have valid AWS credentials and a safe test bucket.

```powershell
$env:PAYMENTOPS_AWS_BUCKET = "<your-test-bucket>"
$env:AWS_REGION = "us-east-1"

python -m src.scripts.run_aws_sagemaker_style_artifact --live-s3 --bucket $env:PAYMENTOPS_AWS_BUCKET
```

## Expected reports

- `reports/29_pyspark_etl_feature_store_artifact.md`
- `reports/pyspark_etl_feature_store_metrics.json`
- `reports/30_aws_s3_sagemaker_style_artifact.md`
- `reports/aws_sagemaker_style_artifact_metrics.json`
- `reports/31_langgraph_paymentops_wrapper.md`
- `reports/langgraph_paymentops_wrapper_metrics.json`

## Resume-safe wording after successful runs

Added local PySpark ETL, AWS/S3/SageMaker-style architecture artifacts, and a LangGraph-based agentic review wrapper to the PaymentOps reliability framework, producing feature-store Parquet outputs, S3/SageMaker request manifests, and human-review routing reports under public/proxy, non-production claim boundaries.
