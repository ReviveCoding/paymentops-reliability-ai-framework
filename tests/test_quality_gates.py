from src.data.common_schema import load_common_cases
from src.data.quality_gates import validate_common_cases


def test_common_cases_quality_after_generation():
    df = load_common_cases()
    result = validate_common_cases(df)
    assert result["row_count"] >= 0
    if result["row_count"] > 0:
        assert result["duplicates"] == 0
