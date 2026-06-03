from src.serving.api_contract_validator import validate_api_contract


def test_api_contract_validation_passes():
    result = validate_api_contract()
    assert result["api_contract_status"] == "PASS"
    assert result["checks"]["POST /investigate"] is True
