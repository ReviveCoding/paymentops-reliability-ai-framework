from src.scripts.run_data import main as run_data
from src.modelops.readiness_pack import write_aws_readiness_pack
from src.modelops.feature_store_validator import validate_feature_store_contract


def test_feature_store_validator_passes_on_generated_data():
    run_data()
    write_aws_readiness_pack()
    result = validate_feature_store_contract()
    assert result["passed"]
    assert result["row_count"] > 0
