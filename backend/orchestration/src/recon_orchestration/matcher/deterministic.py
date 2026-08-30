# backend/orchestration/src/recon_orchestration/matcher/deterministic.py
from recon_common.models import Transaction, LedgerEntry, MatchStatus


def _key(amount, currency, txn_date, reference):
    return (amount, currency, txn_date, reference)


def match_deterministic(
    transaction: Transaction, ledger_entries: list[LedgerEntry]
) -> tuple[MatchStatus, LedgerEntry | None]:
    index = {
        _key(le.amount, le.currency, le.date, le.reference): le
        for le in ledger_entries
    }
    hit = index.get(_key(transaction.amount, transaction.currency, transaction.date, transaction.reference))
    if hit is not None:
        return MatchStatus.MATCHED, hit
    return MatchStatus.EXCEPTION, None