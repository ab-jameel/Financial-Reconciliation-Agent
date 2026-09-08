"""Baseline matcher used for comparison: string similarity only."""

from rapidfuzz import fuzz
from recon_common.models import Transaction, LedgerEntry, MatchStatus

CONFIDENCE_THRESHOLD = 85.0


def match_baseline(
    transaction: Transaction, ledger_entries: list[LedgerEntry]
) -> tuple[MatchStatus, LedgerEntry | None, float]:
    """Match by description string similarity alone.

    Returns (MATCHED, entry, score) when the best token-sort similarity is
    at or above the threshold, otherwise (MANUAL_REVIEW, None, score).
    """
    best_score, best_entry = 0.0, None
    for le in ledger_entries:
        score = fuzz.token_sort_ratio(transaction.description, le.description)
        if score > best_score:
            best_score, best_entry = score, le

    if best_score >= CONFIDENCE_THRESHOLD:
        return MatchStatus.MATCHED, best_entry, best_score
    return MatchStatus.MANUAL_REVIEW, None, best_score
