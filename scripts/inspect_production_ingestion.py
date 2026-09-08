"""Prints all production-ingested transactions."""

from dotenv import load_dotenv
load_dotenv()
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow
from recon_common.models import DatasetSplit

session = SessionLocal()
rows = session.query(TransactionRow).filter_by(dataset_split=DatasetSplit.PRODUCTION).order_by(TransactionRow.date).all()
for r in rows:
    ref = r.reference or "(none)"
    print(f"{r.id} | {r.date} | {r.amount:>10} {r.currency} | ref={ref:15} | {r.description}")
session.close()
