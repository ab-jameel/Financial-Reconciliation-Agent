"""Loads generated JSON datasets into the orchestration Postgres database."""

import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow, LedgerEntryRow, InvoiceRow

GENERATED = Path(__file__).parent / "generated"

def load_split(split: str):
    """Replace the given split's rows with the generated JSON for that split."""
    session = SessionLocal()
    for fname, Row in [
        ("transactions.json", TransactionRow),
        ("ledger_entries.json", LedgerEntryRow),
        ("invoices.json", InvoiceRow),
    ]:
        session.query(Row).filter_by(dataset_split=split).delete()  # purge stale rows first
        rows = json.loads((GENERATED / split / fname).read_text())
        for r in rows:
            session.merge(Row(**r))
    session.commit()
    session.close()
    print(f"Loaded {split} into Postgres ({split} rows fully replaced, not just upserted).")

if __name__ == "__main__":
    load_split("tuning")
    load_split("held_out")
