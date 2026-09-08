"""Reclassifies stuck 'processing' cases as 'ingestion_failed' for retry."""

from dotenv import load_dotenv
load_dotenv()
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import CaseIndexRow

session = SessionLocal()
stuck = session.query(CaseIndexRow).filter_by(status="processing").all()
for row in stuck:
    row.status = "ingestion_failed"
session.commit()
print(f"Reclassified {len(stuck)} stuck case(s) — rerun ingestion to retry them.")
session.close()
