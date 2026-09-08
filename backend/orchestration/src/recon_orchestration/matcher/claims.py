"""Atomic claim of a ledger entry by a case, enforced at the database level."""

from sqlalchemy import text

def try_claim_ledger_entry(session, ledger_entry_id: str, case_id: str) -> bool:
    """Attempt an atomic claim via INSERT ... ON CONFLICT DO NOTHING.

    Returns True if this case won the claim; False means another case has
    already claimed the entry, so this transaction is a duplicate.
    """
    result = session.execute(text("""
        INSERT INTO ledger_claims (ledger_entry_id, case_id, claimed_at)
        VALUES (:led_id, :case_id, now())
        ON CONFLICT (ledger_entry_id) DO NOTHING
    """), {"led_id": ledger_entry_id, "case_id": case_id})
    session.commit()
    return result.rowcount == 1
