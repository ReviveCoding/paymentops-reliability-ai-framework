from src.scripts.run_data import main as run_data
from src.modelops.data_contract_validator import run_data_contract_validation
from src.monitoring.drift_backtest import run_drift_backtest
from src.observability.telemetry_eval import run_telemetry_eval
from src.security.red_team_eval import run_red_team_eval
from src.modelops.repository_audit import run_repository_audit


def test_data_contract_validation_passes():
    run_data()
    result = run_data_contract_validation()
    assert result["passed"] is True
    assert result["num_expectations"] >= 8


def test_drift_backtest_outputs_status():
    run_data()
    result = run_drift_backtest()
    assert result["drift_status"] in {"PASS", "REVIEW"}
    assert result["risk_score_psi"] >= 0


def test_observability_exports_telemetry():
    run_data()
    result = run_telemetry_eval()
    assert result["metrics_logs_traces_exported"] is True
    assert result["num_traces"] > 0


def test_red_team_agent_safety_passes():
    run_data()
    result = run_red_team_eval()
    assert result["red_team_status"] == "PASS"


def test_repository_audit_passes():
    result = run_repository_audit()
    assert result["audit_status"] == "PASS"
