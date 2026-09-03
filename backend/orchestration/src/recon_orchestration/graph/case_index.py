# backend/orchestration/src/recon_orchestration/graph/case_index.py
import time
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import CaseIndexRow

def update_case_index(case_id: str, status: str):
    session = SessionLocal()
    try:
        row = session.get(CaseIndexRow, case_id)
        if row is None:
            session.add(CaseIndexRow(case_id=case_id, status=status, updated_at=time.time()))
        else:
            row.status, row.updated_at = status, time.time()
        session.commit()
    finally:
        session.close()