# backend/orchestration/src/recon_orchestration/matcher/baseline.py
from rapidfuzz import fuzz
from recon_common.models import Transaction, LedgerEntry, MatchStatus

CONFIDENCE_THRESHOLD = 85.0


def match_baseline(
    transaction: Transaction, ledger_entries: list[LedgerEntry]
) -> tuple[MatchStatus, LedgerEntry | None, float]:
    """The 'before' world: crude string similarity, no deterministic key, no
    embeddings. Anything under the threshold goes to manual review."""
    best_score, best_entry = 0.0, None
    for le in ledger_entries:
        score = fuzz.token_sort_ratio(transaction.description, le.description)
        if score > best_score:
            best_score, best_entry = score, le

    if best_score >= CONFIDENCE_THRESHOLD:
        return MatchStatus.MATCHED, best_entry, best_score
    return MatchStatus.MANUAL_REVIEW, None, best_score