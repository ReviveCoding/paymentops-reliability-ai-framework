from __future__ import annotations

from src.agents.langgraph_payment_agent import USE_LANGGRAPH, run_payment_agent
from src.agents.mcp_tools import export_mcp_artifacts
from src.utils import (
    ARTIFACTS_DIR,
    DATA_DIR,
    REPORTS_DIR,
    read_jsonl,
    write_json,
    write_report,
)


def main() -> None:
    export_mcp_artifacts()
    cases = read_jsonl(DATA_DIR / "synthetic" / "iso20022_cases.jsonl")[:5]
    docs = read_jsonl(DATA_DIR / "synthetic" / "payment_policy_docs.jsonl")
    traces = []
    for case in cases:
        state = run_payment_agent(case, docs)
        traces.append(
            {
                "case_id": case["case_id"],
                "risk_score": state["risk_score"],
                "final_action": state["final_action"],
                "summary": state["summary"],
                "trace": state["trace"],
            }
        )
    write_json(ARTIFACTS_DIR / "sample_agent_traces" / "agent_traces.json", traces)
    body = """
## Agent mode

- LangGraph dependency available: `{}`
- Fallback deterministic graph used when LangGraph is unavailable.

## Sample traces

```json
{}
```
""".format(USE_LANGGRAPH, __import__("json").dumps(traces, indent=2)[:6000])
    write_report(
        REPORTS_DIR / "05_agent_trace_examples.md", "Agent Trace Examples", body
    )


if __name__ == "__main__":
    main()
