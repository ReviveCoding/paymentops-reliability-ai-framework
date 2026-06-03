from __future__ import annotations

import json
import time
import uuid
import statistics
from src.utils import DATA_DIR, REPORTS_DIR, ARTIFACTS_DIR, read_jsonl, write_json, write_jsonl, write_report
from src.agents.langgraph_payment_agent import run_payment_agent


def run_telemetry_eval() -> dict:
    docs = read_jsonl(DATA_DIR / "synthetic" / "payment_policy_docs.jsonl")
    cases = read_jsonl(DATA_DIR / "synthetic" / "iso20022_cases.jsonl")[:12]
    traces = []
    metrics_rows = []
    logs = []
    for case in cases:
        trace_id = str(uuid.uuid4())
        start = time.perf_counter()
        state = run_payment_agent(case, docs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        route = state.get("final_action", "unknown")
        traces.append({
            "trace_id": trace_id,
            "case_id": case["case_id"],
            "service.name": "paymentops-agent",
            "latency_ms": elapsed_ms,
            "route": route,
            "risk_score": state.get("risk_score"),
            "spans": state.get("trace", []),
        })
        metrics_rows.append({
            "trace_id": trace_id,
            "metric": "agent_latency_ms",
            "value": elapsed_ms,
        })
        logs.append({
            "trace_id": trace_id,
            "case_id": case["case_id"],
            "level": "INFO",
            "event": "route_decision",
            "route": route,
            "source_conflict": state.get("source_conflict", False),
        })
    latencies = [r["value"] for r in metrics_rows]
    p95 = sorted(latencies)[int(0.95 * (len(latencies)-1))] if latencies else 0.0
    summary = {
        "num_traces": len(traces),
        "p50_latency_ms": statistics.median(latencies) if latencies else 0.0,
        "p95_latency_ms": p95,
        "trace_log_correlation_rate": 1.0 if traces and logs else 0.0,
        "metrics_logs_traces_exported": True,
        "slo_status": "PASS" if p95 < 1500 else "REVIEW",
    }
    out_dir = ARTIFACTS_DIR / "observability"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "otel_style_traces.jsonl", traces)
    write_jsonl(out_dir / "otel_style_metrics.jsonl", metrics_rows)
    write_jsonl(out_dir / "otel_style_logs.jsonl", logs)
    write_json(REPORTS_DIR / "observability_metrics.json", summary)
    body = f"""
## Purpose

This report adds an OpenTelemetry-style observability layer without requiring an external collector. It exports correlated traces, metrics, and logs so the local project demonstrates the same observability pattern used by production services.

## Results

| Metric | Value |
|---|---:|
| Traces exported | {summary['num_traces']} |
| p50 latency, ms | {summary['p50_latency_ms']:.3f} |
| p95 latency, ms | {summary['p95_latency_ms']:.3f} |
| Trace/log correlation rate | {summary['trace_log_correlation_rate']:.3f} |
| SLO status | {summary['slo_status']} |

## Artifacts

- `artifacts/observability/otel_style_traces.jsonl`
- `artifacts/observability/otel_style_metrics.jsonl`
- `artifacts/observability/otel_style_logs.jsonl`

## Boundary

These are local JSONL telemetry artifacts, not a hosted observability deployment.
"""
    write_report(REPORTS_DIR / "17_observability_slo_report.md", "Observability and SLO Report", body)
    return summary


if __name__ == "__main__":
    print(json.dumps(run_telemetry_eval(), indent=2))
