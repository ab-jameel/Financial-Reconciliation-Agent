# backend/orchestration/src/recon_orchestration/matcher/reconcile.py
"""Single source of truth for whether a transaction is REALLY cleared —
used by both matcher_node (the live graph) and the eval scripts, so the two
can never again independently diverge on this decision. The deterministic
key alone is necessary but not sufficient: it says nothing about whether
the invoice actually exists, or whether some OTHER transaction already
claimed this exact ledger entry."""
from recon_common.models import Transaction, LedgerEntry, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.safety_checks import check_invoice_exists


def reconcile(transaction: Transaction, ledger_entries: list[LedgerEntry],
              load_valid_invoices_fn, claim_fn) -> tuple[MatchStatus, LedgerEntry | None]:
    status, matched = match_deterministic(transaction, ledger_entries)
    if status != MatchStatus.MATCHED:
        return status, None  # lazy: invoice/claim lookups never run for cases already headed to investigation

    if not check_invoice_exists(matched.model_dump(), load_valid_invoices_fn()):
        return MatchStatus.EXCEPTION, None
    if not claim_fn(matched.id):
        return MatchStatus.EXCEPTION, None  # already claimed by a different case — a duplicate

    return MatchStatus.MATCHED, matched