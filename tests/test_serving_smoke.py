from src.scripts.run_data import main as run_data
from src.serving.app import health_endpoint, investigate
from src.serving.schemas import CaseRequest


def test_health_endpoint_returns_ok():
    assert health_endpoint()["status"] == "ok"


def test_investigate_endpoint_direct_smoke():
    run_data()
    response = investigate(
        CaseRequest(
            case_id="smoke_case",
            text="Customer reports a duplicate pending payment and asks for investigation.",
        )
    )
    assert response.case_id == "smoke_case"
    assert 0.0 <= response.risk_score <= 1.0
    assert response.final_action in {"auto_resolve", "human_review_required", "compliance_review", "block"}
    assert "smoke_case" in response.summary
