from __future__ import annotations

import argparse
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path


def external_root() -> Path:
    return Path(os.environ.get("PAYMENTOPS_EXTERNAL_DATA", Path.cwd().parent / "paymentops_external_data"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_model_package(out_dir: Path) -> Path:
    package_dir = out_dir / "model_package"
    package_dir.mkdir(parents=True, exist_ok=True)

    write_text(
        package_dir / "inference.py",
        "import json\n\n"
        "def model_fn(model_dir):\n"
        "    return {'model_type': 'paymentops_calibrated_risk_router'}\n\n"
        "def predict_fn(input_data, model):\n"
        "    return {'risk_score': 0.5, 'review_route': 'human_review'}\n",
    )

    write_text(
        package_dir / "model_card.json",
        json.dumps(
            {
                "model_name": "paymentops-calibrated-risk-router",
                "model_type": "SageMaker-style local artifact",
                "claim_boundary": "Architecture artifact only unless launched in a real AWS account. No proprietary bank data.",
                "intended_use": "PaymentOps-style public/proxy risk-routing evaluation.",
                "not_intended_use": "Production payment decisions or regulatory certification.",
            },
            indent=2,
        ),
    )

    write_text(
        package_dir / "metrics.json",
        json.dumps(
            {
                "pr_auc_improvement_pct": 15.0,
                "brier_reduction_pct": 76.9,
                "false_auto_clear_reduction_pct": 25.0,
                "source": "Existing local PaymentOps benchmark report",
            },
            indent=2,
        ),
    )

    tar_path = out_dir / "model.tar.gz"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as tar:
        for p in package_dir.iterdir():
            tar.add(p, arcname=p.name)
    return tar_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create AWS/S3/SageMaker-style artifacts without requiring live AWS execution.")
    parser.add_argument("--bucket", default=os.environ.get("PAYMENTOPS_AWS_BUCKET", ""))
    parser.add_argument("--prefix", default=os.environ.get("PAYMENTOPS_AWS_PREFIX", "paymentops-reliability-ai-framework"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument("--role-arn", default=os.environ.get("PAYMENTOPS_SAGEMAKER_ROLE_ARN", "arn:aws:iam::<account-id>:role/<sagemaker-execution-role>"))
    parser.add_argument("--live-s3", action="store_true")
    args = parser.parse_args()

    root = external_root()
    out_dir = root / "aws_sagemaker_style_artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    model_tar = make_model_package(out_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    job_name = f"paymentops-calibrated-router-{run_id}"

    bucket_token = args.bucket if args.bucket else "<bucket>"
    s3_model_uri = f"s3://{bucket_token}/{args.prefix}/model/model.tar.gz"
    s3_request_uri = f"s3://{bucket_token}/{args.prefix}/sagemaker/sagemaker_create_training_job_request.json"
    s3_output_uri = f"s3://{bucket_token}/{args.prefix}/sagemaker-output/"

    training_job_request = {
        "TrainingJobName": job_name,
        "RoleArn": args.role_arn,
        "AlgorithmSpecification": {
            "TrainingImage": "<replace-with-valid-training-image-uri>",
            "TrainingInputMode": "File",
        },
        "InputDataConfig": [
            {
                "ChannelName": "train",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"s3://{bucket_token}/{args.prefix}/train/",
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "ContentType": "text/csv",
            }
        ],
        "OutputDataConfig": {"S3OutputPath": s3_output_uri},
        "ResourceConfig": {
            "InstanceType": "ml.m5.large",
            "InstanceCount": 1,
            "VolumeSizeInGB": 10,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 900},
        "Tags": [
            {"Key": "Project", "Value": "PaymentOpsReliabilityAI"},
            {"Key": "ClaimBoundary", "Value": "public-proxy-local-artifact"},
        ],
    }

    request_path = out_dir / "sagemaker_create_training_job_request.json"
    write_text(request_path, json.dumps(training_job_request, indent=2))

    uploaded = []
    if args.live_s3:
        if not args.bucket:
            raise ValueError("Use --bucket or set PAYMENTOPS_AWS_BUCKET for --live-s3.")
        import boto3

        s3 = boto3.client("s3", region_name=args.region)
        for local_path, key in [
            (model_tar, f"{args.prefix}/model/model.tar.gz"),
            (request_path, f"{args.prefix}/sagemaker/sagemaker_create_training_job_request.json"),
        ]:
            s3.upload_file(str(local_path), args.bucket, key)
            uploaded.append({"local_path": str(local_path), "s3_uri": f"s3://{args.bucket}/{key}"})

    manifest = {
        "status": "PASS",
        "live_s3_requested": bool(args.live_s3),
        "bucket": args.bucket or None,
        "prefix": args.prefix,
        "region": args.region,
        "model_tar": str(model_tar),
        "sagemaker_request_json": str(request_path),
        "s3_model_uri": s3_model_uri,
        "s3_request_uri": s3_request_uri,
        "s3_output_uri": s3_output_uri,
        "uploaded": uploaded,
        "claim_boundary": "S3/SageMaker-style architecture artifact. Only S3 upload is live if --live-s3 is used with valid AWS credentials and bucket.",
    }

    manifest_path = out_dir / "aws_sagemaker_style_manifest.json"
    write_text(manifest_path, json.dumps(manifest, indent=2))

    write_text(
        out_dir / "aws_cli_commands.md",
        "# AWS CLI commands\n\n"
        "## Optional S3 upload\n\n"
        f"aws s3 cp \"{model_tar}\" \"{s3_model_uri}\"\n"
        f"aws s3 cp \"{request_path}\" \"{s3_request_uri}\"\n\n"
        "## Optional SageMaker training job launch\n\n"
        "Only run after replacing placeholder image URI, role ARN, bucket, and data paths.\n\n"
        f"aws sagemaker create-training-job --cli-input-json file://\"{request_path}\"\n",
    )

    report_path = Path("reports") / "30_aws_s3_sagemaker_style_artifact.md"
    metrics_path = Path("reports") / "aws_sagemaker_style_artifact_metrics.json"
    write_text(metrics_path, json.dumps(manifest, indent=2))
    write_text(
        report_path,
        "# AWS/S3/SageMaker-Style Artifact\n\n"
        "## Claim boundary\n\n"
        "This is an AWS/S3/SageMaker-style architecture artifact. It does not claim production AWS deployment, real bank infrastructure, or a launched SageMaker training job unless optional live commands are executed in a valid AWS account.\n\n"
        "## Outputs\n\n"
        f"- Model package: `{model_tar}`\n"
        f"- SageMaker CreateTrainingJob request JSON: `{request_path}`\n"
        f"- Manifest: `{manifest_path}`\n"
        f"- Live S3 upload requested: `{args.live_s3}`\n"
        f"- Uploaded objects: `{uploaded}`\n\n"
        "## Resume-safe wording\n\n"
        "Added AWS/S3/SageMaker-style architecture artifacts, including a model package, S3 URI manifest, CreateTrainingJob request template, and optional boto3 S3 upload path under public/proxy data boundaries.\n",
    )

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
