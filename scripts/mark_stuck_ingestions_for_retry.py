# scripts/mark_stuck_ingestions_for_retry.py
"""One-time remediation: any case_index row still at 'processing' from
before the per-transaction error handling existed has no real graph
progress behind it. Reclassify as 'ingestion_failed' so the next ingestion
call correctly retries it instead of skipping it forever."""
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