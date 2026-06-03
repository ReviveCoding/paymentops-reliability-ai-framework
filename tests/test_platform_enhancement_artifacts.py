from pathlib import Path


def test_platform_enhancement_scripts_exist():
    expected = [
        Path("src/scripts/run_pyspark_etl_feature_store.py"),
        Path("src/scripts/run_aws_sagemaker_style_artifact.py"),
        Path("src/scripts/run_langgraph_paymentops_wrapper.py"),
        Path("docs/PLATFORM_ENHANCEMENT_ARTIFACTS.md"),
    ]
    for path in expected:
        assert path.exists(), f"Missing {path}"


def test_claim_boundaries_are_present():
    files = [
        Path("src/scripts/run_pyspark_etl_feature_store.py"),
        Path("src/scripts/run_aws_sagemaker_style_artifact.py"),
        Path("src/scripts/run_langgraph_paymentops_wrapper.py"),
        Path("docs/PLATFORM_ENHANCEMENT_ARTIFACTS.md"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "No production" in combined
    assert "public/proxy" in combined
    assert "JPMC" in combined
