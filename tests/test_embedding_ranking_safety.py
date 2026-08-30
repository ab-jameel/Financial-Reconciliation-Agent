# tests/test_embedding_ranking_safety.py
from decimal import Decimal
from datetime import date
from recon_common.models import Transaction, LedgerEntry, DatasetSplit, ExceptionType, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.ranking import rank_candidates


def test_high_similarity_alone_never_produces_a_match():
    """Two descriptions that are near-paraphrases of each other, but with a
    mismatched date, must NOT be flagged as matched — no matter how high the
    embedding similarity score is."""
    txn = Transaction(
        id="TEST-TXN-1", date=date(2026, 8, 5), amount=Decimal("1200.00"),
        currency="USD", reference="REF-111111", description="Amazon Web Services LLC",
        dataset_split=DatasetSplit.TUNING, label_exception_type=ExceptionType.DATE_MISMATCH,
    )
    ledger = LedgerEntry(
        id="TEST-LED-1", date=date(2026, 8, 9), amount=Decimal("1200.00"),
        currency="USD", reference="REF-111111", description="AWS Cloud Hosting",
        dataset_split=DatasetSplit.TUNING,
    )

    status, matched_entry = match_deterministic(txn, [ledger])
    assert status != MatchStatus.MATCHED
    assert matched_entry is None

    candidates = rank_candidates(txn, [ledger])
    assert candidates[0].similarity_score > 0.7  # confirms it WOULD look like a strong match
    # and yet: nothing about calling rank_candidates can set status to MATCHED —
    # RankedCandidate has no field that could do that. This assertion is really
    # a type-shape check as much as a behavior check.
    assert not hasattr(candidates[0], "is_match")