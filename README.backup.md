# PaymentOps Reliability AI Framework

A local/GitHub-runnable production-style offline framework for public financial-operations data and synthetic ISO 20022-inspired payment workflows. The project establishes vanilla ML/RAG baselines, then upgrades them with reliability modules inspired by data-centric prognostics, residual bias correction, evidence coverage expansion, ABC-style correction, agent routing, and governance release gates.

## Claim Boundary

This project uses public financial-operations-style sample data and synthetic ISO 20022-inspired payment workflows. It does not use proprietary JPMorgan Chase data, proprietary bank data, real customer account data, or production payment transaction logs. All ISO 20022 payment-message workflows are synthetic and designed for offline evaluation. The project is a local/GitHub-runnable production-style framework, not a production deployment.

## Why this project exists

The project is designed to demonstrate a full PaymentOps applied AI/ML workflow:

- public financial operations NLP and review routing, based on CFPB-style complaint workflows
- synthetic ISO 20022 pacs.008/pacs.002 payment investigation cases
- fraud/risk benchmark-style scoring
- vanilla baselines for ML, RAG, and rule routing
- reliability-enhanced modules for calibration, residual correction, evidence coverage, and action safety
- LangGraph-compatible agent orchestration with deterministic fallback
- MCP-style tool/resource/prompt artifacts
- FastAPI serving scaffold
- model validation, controls matrix, business KPI scenarios, latency report, and release gate

## Architecture

```text
sample data -> quality gates -> vanilla baselines -> reliability modules -> RAG/evidence evaluation
            -> agent orchestration -> model validation -> business KPI scenarios -> release decision
```

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
make all
```

The repository is intentionally self-contained. It creates small sample/synthetic datasets under `data/` and does not download large public datasets.

## Make commands

```bash
make setup      # install dependencies
make data       # generate sample/synthetic data and data inventory report
make train      # run vanilla and reliability-enhanced model evaluation
make evaluate   # run RAG/evidence, KPI, latency, and release-gate evaluation
make agent      # run the payment investigation agent and write traces
make report     # assemble governance/model-validation reports
make serve      # start FastAPI service locally
make test       # run pytest
make all        # data -> train -> agent -> evaluate -> report -> test
```

## Core modules

| Layer | Purpose |
|---|---|
| `src/data/` | Generate and validate CFPB-style, fraud-style, and ISO 20022-inspired samples; create common case schema |
| `src/baselines/` | Vanilla issue routing, risk scoring, BM25-style retrieval, and rule routing |
| `src/reliability/` | Case Health Timestep, rule-prior residual correction, calibration, threshold policy, evidence coverage expansion, ABC evidence/action correction |
| `src/rag/` | Retrieval, reranking, grounded summary, and RAG metrics |
| `src/agents/` | LangGraph-compatible/fallback agent, MCP-style tools, permission gates, source-conflict checker, audit logging |
| `src/governance/` | Model card, data card, validation packet, controls matrix, release gate |
| `src/evaluation/` | Metrics, ablation runner, business scenario runner, latency benchmark |
| `src/serving/` | FastAPI application scaffold |

## Specialty-inspired reliability modules

| Research idea | Project module | PaymentOps purpose |
|---|---|---|
| Physical Health Timestep | Case Health Timestep | Converts raw event age into case-risk maturity signal |
| Physics-informed residual bias correction | Rule-prior residual correction | Combines interpretable policy/rule priors with learned residual risk |
| Probability-based Bbox | Evidence coverage expansion | Uses lower-ranked candidate evidence to recover missing evidence slots |
| ABC Bbox | ABC evidence/action correction | Expands coverage first, then removes weak/conflicting/unsupported evidence and unsafe actions |
| KPI impact assessment | Business KPI scenario release gate | Translates model metrics into risk, review burden, compliance, and latency tradeoffs |

## Required outputs

After `make all`, the following files should exist:

```text
reports/01_data_inventory.md
reports/02_baseline_results.md
reports/03_reliability_ablation.md
reports/04_rag_and_evidence_eval.md
reports/05_agent_trace_examples.md
reports/06_model_validation_packet.md
reports/07_business_kpi_scenarios.md
reports/08_latency_report.md
reports/09_release_decision.md
artifacts/mcp/tools.json
artifacts/mcp/resources.json
artifacts/mcp/prompts.json
artifacts/sample_audit_logs/agent_audit_log.jsonl
```

## Resume-safe wording

Built a local/GitHub-runnable PaymentOps reliability AI framework using public-style financial operations samples, a fraud benchmark-style sample, and ISO 20022-inspired synthetic pacs.008/pacs.002 workflows, combining vanilla ML/RAG baselines, calibrated risk scoring, specialty-inspired reliability modules, LangGraph-compatible agent routing, MCP-style tool artifacts, FastAPI serving, model-validation packets, and PASS/REVIEW/BLOCK release gates.

## Limitations

- This is not a production deployment.
- The repository uses sample/synthetic data for portability.
- The ISO 20022 cases are synthetic and are not real payment messages.
- The MCP implementation is artifact-compatible and tool-contract-oriented; it is not a hosted enterprise MCP server.
- LangGraph is optional. A deterministic fallback agent is used when LangGraph is unavailable.
- AWS/SageMaker files are compatibility scaffolds only unless an actual user-run log is added later.



## Final optimization loop added

The latest version adds the final high-ROI hardening loop:

- Operating-policy frontier search for risk capture, false auto-clear, review burden, Brier, and ECE tradeoffs.
- Worst-slice and stress robustness report.
- Feature-store/backfill contract validation over the generated feature table.
- PII redaction and prompt-injection guardrail smoke tests.
- Deterministic local test harness used by `make all`.

Additional generated reports:

```text
reports/10_operating_policy_frontier.md
reports/11_worst_slice_and_stress_report.md
reports/12_feature_store_backfill_validation.md
reports/13_security_guardrail_eval.md
reports/14_final_optimization_audit.md
```

## Improvement pack added

This version adds higher-ROI evidence for the JPMC Payments Applied AI/ML role:

- SageMaker-compatible model registry, feature-store-style schema governance, SageMaker pipeline, and EMR Spark job configuration manifests.
- Transformer fine-tuning-ready issue-router scaffold for CFPB-style financial-operations text classification.
- Full public dataset adapters for CFPB exports, IEEE-CIS fraud files, and IBM AML-style transactions.
- Dockerfile and GitHub Actions workflow for CI/CD readiness.
- Local model registry manifest for baseline, candidate, and optional Transformer models.

All of these additions preserve the same claim boundary: they are local/offline scaffolds or compatibility artifacts unless the user later executes a real cloud run, public-data full run, or Transformer fine-tuning run and saves logs.

## Additional readiness outputs

```text
reports/aws_sagemaker_readiness.md
reports/transformer_finetuning_readiness.md
reports/full_dataset_adapter_readiness.md
reports/ci_cd_docker_readiness.md
reports/model_registry_manifest.md
artifacts/aws/model_registry_manifest.json
artifacts/aws/feature_store_manifest.json
artifacts/aws/sagemaker_pipeline_definition.json
artifacts/aws/emr_spark_job_config.json
artifacts/model_registry/model_versions.json
artifacts/transformer/issue_router_readiness.json
```


## Second hardening loop added

The latest version adds another weakness-analysis and hardening loop:

- Lightweight data-contract validation with an expectation-suite artifact.
- Source-stratified temporal drift and champion/challenger backtest.
- OpenTelemetry-style local traces, metrics, and logs.
- Synthetic red-team evaluation for prompt-injection, PII, and missing-evidence cases.
- FastAPI/OpenAPI contract validation.
- Repository runnability and efficiency audit from a clean local run.

Final local verification: `make clean && make all` passed with 19 tests, release gate PASS, and no large committed raw datasets.
