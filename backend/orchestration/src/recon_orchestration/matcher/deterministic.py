"""Deterministic matching on the exact (amount, currency, date, reference) key."""

from recon_common.models import Transaction, LedgerEntry, MatchStatus


def _key(amount, currency, txn_date, reference):
    """Return the tuple used as the exact-match key."""
    return (amount, currency, txn_date, reference)


def match_deterministic(
    transaction: Transaction, ledger_entries: list[LedgerEntry]
) -> tuple[MatchStatus, LedgerEntry | None]:
    """Return (MATCHED, entry) when a ledger entry exactly matches the key, else (EXCEPTION, None)."""
    index = {
        _key(le.amount, le.currency, le.date, le.reference): le
        for le in ledger_entries
    }
    hit = index.get(_key(transaction.amount, transaction.currency, transaction.date, transaction.reference))
    if hit is not None:
        return MatchStatus.MATCHED, hit
    return MatchStatus.EXCEPTION, None
