from __future__ import annotations

from fastapi import FastAPI
from src.serving.schemas import CaseRequest, CaseResponse
from src.serving.health import health
from src.agents.langgraph_payment_agent import run_payment_agent
from src.utils import DATA_DIR, read_jsonl

app = FastAPI(title="PaymentOps Reliability AI Framework", version="0.1.0")

@app.get("/health")
def health_endpoint():
    return health()

@app.post("/investigate", response_model=CaseResponse)
def investigate(req: CaseRequest):
    docs = read_jsonl(DATA_DIR / "synthetic" / "payment_policy_docs.jsonl")
    case = req.model_dump()
    state = run_payment_agent(case, docs)
    return CaseResponse(case_id=req.case_id, risk_score=state["risk_score"], final_action=state["final_action"], summary=state["summary"])
