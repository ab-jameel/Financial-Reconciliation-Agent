# backend/orchestration/src/recon_orchestration/api/app.py
from dotenv import load_dotenv
load_dotenv()

import uuid, os, json, tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from langgraph.types import Command
from fastapi.middleware.cors import CORSMiddleware

from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.checkpointer import get_checkpointer
from recon_orchestration.graph.state import GRAPH_VERSION
from recon_orchestration.graph.migrations import migrate_state_if_needed, UnmigratableCheckpointError
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import CaseIndexRow
from recon_orchestration.graph.case_index import update_case_index
from recon_orchestration.ingestion.statement_ingestion import ingest_statement


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])


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
    update_case_index(case_id, "processing")
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

@app.get("/cases")
def list_cases(status: str | None = None):
    session = SessionLocal()
    try:
        query = session.query(CaseIndexRow)
        if status:
            query = query.filter_by(status=status)
        rows = query.order_by(CaseIndexRow.updated_at.desc()).all()
        return [{"case_id": r.case_id, "status": r.status, "updated_at": r.updated_at} for r in rows]
    finally:
        session.close()


@app.get("/dashboard/summary")
def dashboard_summary():
    from pathlib import Path
    base = Path("data/generated/held_out")  # relative to CWD — launch uvicorn from repo root
    def _read(name):
        p = base / name
        return json.loads(p.read_text()) if p.exists() else None
    return {"baseline": _read("baseline_metrics.json"), "agent": _read("agent_metrics.json"), "comparison": _read("comparison.json")}

@app.post("/statements/ingest")
def ingest_statement_endpoint(file: UploadFile = File(...)):
    """Deliberately a SYNC endpoint, not async def — investigator_node still
    uses asyncio.run() internally (a known Phase 3 simplification). FastAPI
    runs sync path operations in a worker thread with no event loop, exactly
    like the existing /cases endpoint. Making this async def breaks the same
    way unless the graph becomes natively async end-to-end first."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    try:
        return ingest_statement(tmp_path, file.filename)
    finally:
        os.unlink(tmp_path)