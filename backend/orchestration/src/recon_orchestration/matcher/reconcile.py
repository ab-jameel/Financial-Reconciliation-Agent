"""Determines whether a transaction should auto-clear.

Applies the deterministic match key, then verifies the referenced invoice
exists and the ledger entry has not already been claimed by another
transaction. All three conditions must hold to clear without review.
"""

from recon_common.models import Transaction, LedgerEntry, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.safety_checks import check_invoice_exists


def reconcile(transaction: Transaction, ledger_entries: list[LedgerEntry],
              load_valid_invoices_fn, claim_fn) -> tuple[MatchStatus, LedgerEntry | None]:
    """Decide whether a transaction clears without review.

    Requires the deterministic key to match, the referenced invoice to
    exist, and the ledger entry to be unclaimed. Returns
    (MatchStatus.MATCHED, entry) or (MatchStatus.EXCEPTION, None).
    """
    status, matched = match_deterministic(transaction, ledger_entries)
    if status != MatchStatus.MATCHED:
        return status, None  # Skip invoice/claim lookups when the case is already headed to investigation

    if not check_invoice_exists(matched.model_dump(), load_valid_invoices_fn()):
        return MatchStatus.EXCEPTION, None
    if not claim_fn(matched.id):
        return MatchStatus.EXCEPTION, None  # already claimed by a different case — a duplicate

    return MatchStatus.MATCHED, matched
