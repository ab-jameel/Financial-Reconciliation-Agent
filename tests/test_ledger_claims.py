"""Verifies ledger-claim atomicity against real Postgres."""

import uuid
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.matcher.claims import try_claim_ledger_entry


def test_second_claim_on_same_ledger_entry_fails_at_the_db_level():
    """Assert a second claim on the same ledger entry fails at the database level."""
    ledger_entry_id = f"LED-{uuid.uuid4().hex[:8]}"
    session_a, session_b = SessionLocal(), SessionLocal()
    try:
        assert try_claim_ledger_entry(session_a, ledger_entry_id, "CASE-A") is True
        assert try_claim_ledger_entry(session_b, ledger_entry_id, "CASE-B") is False
    finally:
        session_a.close()
        session_b.close()
