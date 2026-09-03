# tests/test_case_index.py
import uuid
from recon_orchestration.graph.case_index import update_case_index
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import CaseIndexRow

def test_update_case_index_inserts_then_updates():
    case_id = f"idx-{uuid.uuid4().hex[:8]}"
    update_case_index(case_id, "pending_review")
    update_case_index(case_id, "approved_pending_writeback")
    session = SessionLocal()
    row = session.get(CaseIndexRow, case_id)
    session.close()
    assert row.status == "approved_pending_writeback"