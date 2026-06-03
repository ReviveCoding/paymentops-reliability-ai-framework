from __future__ import annotations

from src.scripts.run_data import main as run_data
from src.evaluation.ablation_runner import run_ablation
from src.scripts.run_agent import main as run_agent
from src.evaluation.scenario_kpi_runner import run_business_kpi_scenarios
from src.evaluation.latency_benchmark import run_latency_benchmark
from src.governance.release_gate import run_release_gate
from src.modelops.readiness_pack import main as run_readiness
from src.modelops.feature_store_validator import validate_feature_store_contract
from src.evaluation.robustness_runner import run_robustness
from src.security.security_eval import run_security_eval
from src.governance.validation_packet import write_validation_packet
from src.governance.controls_matrix import write_controls_matrix
from src.governance.model_card import write_model_card
from src.governance.data_card import write_data_card
from src.modelops.data_contract_validator import run_data_contract_validation
from src.monitoring.drift_backtest import run_drift_backtest
from src.observability.telemetry_eval import run_telemetry_eval
from src.security.red_team_eval import run_red_team_eval
from src.modelops.repository_audit import run_repository_audit
from src.serving.api_contract_validator import validate_api_contract
from src.modelops.final_runnability_verification import run_final_runnability_verification


def main() -> None:
    run_data()
    run_ablation()
    run_agent()
    run_business_kpi_scenarios()
    run_robustness()
    validate_feature_store_contract()
    run_data_contract_validation()
    run_drift_backtest()
    run_telemetry_eval()
    run_red_team_eval()
    validate_api_contract()
    run_security_eval()
    run_latency_benchmark()
    run_readiness()
    write_validation_packet()
    write_controls_matrix()
    write_model_card()
    write_data_card()
    run_repository_audit()
    run_release_gate()
    run_final_runnability_verification()


if __name__ == "__main__":
    main()
