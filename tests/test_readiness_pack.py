from pathlib import Path
import json

from src.modelops.readiness_pack import main
from src.models.transformer_issue_router import write_transformer_readiness_report
from src.data.adapters.ieee_cis_adapter import standardize_ieee_cis
from src.data.adapters.ibm_aml_adapter import standardize_ibm_aml


def test_readiness_pack_outputs():
    main()
    required = [
        Path("artifacts/aws/model_registry_manifest.json"),
        Path("artifacts/aws/feature_store_manifest.json"),
        Path("artifacts/aws/sagemaker_pipeline_definition.json"),
        Path("artifacts/aws/emr_spark_job_config.json"),
        Path("artifacts/model_registry/model_versions.json"),
        Path("reports/aws_sagemaker_readiness.md"),
        Path("reports/transformer_finetuning_readiness.md"),
    ]
    for p in required:
        assert p.exists(), p
    manifest = json.loads(Path("artifacts/aws/model_registry_manifest.json").read_text())
    assert manifest["status"] == "sagemaker_compatible_manifest_only"


def test_transformer_readiness_has_label_maps():
    pack = write_transformer_readiness_report()
    assert pack["status"] == "fine_tuning_ready_scaffold_only"
    assert pack["num_labels"] >= 1
    assert "claim_boundary" in pack


def test_public_dataset_adapters_on_tiny_files(tmp_path):
    ieee = tmp_path / "ieee.csv"
    ieee.write_text("TransactionID,TransactionDT,TransactionAmt,ProductCD,isFraud\n1,10,42.5,W,1\n2,11,5.0,C,0\n")
    out_ieee = standardize_ieee_cis(ieee)
    assert set(["case_id", "risk_label", "route_label"]).issubset(out_ieee.columns)
    assert out_ieee["risk_label"].sum() == 1

    aml = tmp_path / "aml.csv"
    aml.write_text("Timestamp,Amount,Payment Currency,From ID,To ID,Is Laundering\n2026-01-01,100,USD,A,B,1\n")
    out_aml = standardize_ibm_aml(aml)
    assert out_aml.iloc[0]["route_label"] == "compliance_review"
