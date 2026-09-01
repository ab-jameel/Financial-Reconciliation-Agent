# backend/orchestration/src/recon_orchestration/api/app.py
from dotenv import load_dotenv
load_dotenv()

import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.types import Command

from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.checkpointer import get_checkpointer
from recon_orchestration.graph.state import GRAPH_VERSION
from recon_orchestration.graph.migrations import migrate_state_if_needed, UnmigratableCheckpointError

app = FastAPI()


class StartCaseRequest(BaseModel):
    transaction: dict
    candidate_ledger_entries: list[dict]


class ReviewDecision(BaseModel):
    decision: str  # "approve" | "reject"
    reason: str | None = None
    reviewer_role: str

def _config(case_id: str):
    return {"configurable": {"thread_id": case_id}}  # fixed scheme: one thread per case


@app.post("/cases")
def start_case(req: StartCaseRequest):
    case_id = req.transaction.get("id") or str(uuid.uuid4())
    with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        result = graph.invoke({
            "case_id": case_id, "graph_version": GRAPH_VERSION,
            "transaction": req.transaction, "candidate_ledger_entries": req.candidate_ledger_entries,
            "rejection_cycle_count": 0,
        }, config=_config(case_id))
    return {"case_id": case_id, "result": result}


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    with get_checkpointer() as checkpointer:
        snapshot = build_graph(checkpointer).get_state(_config(case_id))
    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case_id": case_id, "state": snapshot.values, "next_nodes": snapshot.next}


@app.post("/cases/{case_id}/review")
def review_case(case_id: str, decision: ReviewDecision):
    with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        snapshot = graph.get_state(_config(case_id))
        if snapshot is None or not snapshot.values:
            raise HTTPException(status_code=404, detail="Case not found")
        try:
            migrate_state_if_needed(snapshot.values)
        except UnmigratableCheckpointError as e:
            raise HTTPException(status_code=409, detail=str(e))
        result = graph.invoke(Command(resume=decision.model_dump()), config=_config(case_id))
    return {"case_id": case_id, "result": result}