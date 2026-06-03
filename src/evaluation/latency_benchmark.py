from __future__ import annotations

import time
import numpy as np
from src.utils import REPORTS_DIR, DATA_DIR, read_jsonl, write_report, write_json
from src.agents.langgraph_payment_agent import run_payment_agent


def run_latency_benchmark(n: int = 20) -> dict:
    cases = read_jsonl(DATA_DIR / "synthetic" / "iso20022_cases.jsonl")[:n]
    docs = read_jsonl(DATA_DIR / "synthetic" / "payment_policy_docs.jsonl")
    lat = []
    for case in cases:
        t0 = time.perf_counter()
        run_payment_agent(case, docs)
        lat.append((time.perf_counter() - t0) * 1000)
    arr = np.array(lat)
    metrics = {"p50_latency_ms": float(np.percentile(arr, 50)), "p95_latency_ms": float(np.percentile(arr, 95)), "p99_latency_ms": float(np.percentile(arr, 99)), "runs": int(len(arr))}
    write_json(REPORTS_DIR / "latency_metrics.json", metrics)
    body = f"""
| Metric | Value |
|---|---:|
| Runs | {metrics['runs']} |
| p50 latency ms | {metrics['p50_latency_ms']:.2f} |
| p95 latency ms | {metrics['p95_latency_ms']:.2f} |
| p99 latency ms | {metrics['p99_latency_ms']:.2f} |

The latency benchmark runs the local deterministic agent. It does not include network/API latency from external LLM services.
"""
    write_report(REPORTS_DIR / "08_latency_report.md", "Latency Report", body)
    return metrics


if __name__ == "__main__":
    print(run_latency_benchmark())
