"""Tests the per-case status index updates."""

import uuid
from recon_orchestration.graph.case_index import update_case_index
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import CaseIndexRow

def test_update_case_index_inserts_then_updates():
    """Assert a case index row is created on first write and updated on the second."""
    case_id = f"idx-{uuid.uuid4().hex[:8]}"
    update_case_index(case_id, "pending_review")
    update_case_index(case_id, "approved_pending_writeback")
    session = SessionLocal()
    row = session.get(CaseIndexRow, case_id)
    session.close()
    assert row.status == "approved_pending_writeback"
