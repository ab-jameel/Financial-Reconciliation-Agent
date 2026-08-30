# data/load_to_postgres.py
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow, LedgerEntryRow, InvoiceRow

GENERATED = Path(__file__).parent / "generated"

def load_split(split: str):
    session = SessionLocal()
    for fname, Row in [
        ("transactions.json", TransactionRow),
        ("ledger_entries.json", LedgerEntryRow),
        ("invoices.json", InvoiceRow),
    ]:
        rows = json.loads((GENERATED / split / fname).read_text())
        for r in rows:
            session.merge(Row(**r))
    session.commit()
    session.close()
    print(f"Loaded {split} into Postgres.")

if __name__ == "__main__":
    load_split("tuning")
    load_split("held_out")