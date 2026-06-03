.PHONY: setup data train evaluate agent readiness report serve test quickall all clean

setup:
	pip install -r requirements.txt

data:
	python -m src.scripts.run_data

train:
	python -m src.evaluation.ablation_runner

agent:
	python -m src.scripts.run_agent

readiness:
	python -m src.scripts.run_readiness

evaluate:
	python -m src.evaluation.scenario_kpi_runner
	python -m src.evaluation.robustness_runner
	python -m src.modelops.feature_store_validator
	python -m src.security.security_eval
	python -m src.evaluation.latency_benchmark
	python -m src.governance.release_gate

report:
	python -m src.governance.validation_packet
	python -m src.governance.controls_matrix
	python -m src.governance.model_card
	python -m src.governance.data_card

serve:
	uvicorn src.serving.app:app --reload --port 8000

test:
	python -m src.scripts.run_tests

quickall:
	python -m src.scripts.run_all
	python -m src.scripts.run_tests

all: quickall

clean:
	rm -rf data/sample_public data/synthetic data/processed reports artifacts .pytest_cache
