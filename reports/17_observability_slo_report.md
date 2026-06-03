# Observability and SLO Report

## Purpose

This report adds an OpenTelemetry-style observability layer without requiring an external collector. It exports correlated traces, metrics, and logs so the local project demonstrates the same observability pattern used by production services.

## Results

| Metric | Value |
|---|---:|
| Traces exported | 12 |
| p50 latency, ms | 3.314 |
| p95 latency, ms | 3.492 |
| Trace/log correlation rate | 1.000 |
| SLO status | PASS |

## Artifacts

- `artifacts/observability/otel_style_traces.jsonl`
- `artifacts/observability/otel_style_metrics.jsonl`
- `artifacts/observability/otel_style_logs.jsonl`

## Boundary

These are local JSONL telemetry artifacts, not a hosted observability deployment.
