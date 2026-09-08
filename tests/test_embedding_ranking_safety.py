"""Verifies high embedding similarity alone never produces a match verdict."""

from decimal import Decimal
from datetime import date
from recon_common.models import Transaction, LedgerEntry, DatasetSplit, ExceptionType, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.ranking import rank_candidates


def test_high_similarity_alone_never_produces_a_match():
    """Assert near-paraphrase descriptions with a mismatched date are not matched."""
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
    assert candidates[0].similarity_score > 0.7  # confirms it would look like a strong match
    # rank_candidates cannot produce a match verdict: RankedCandidate has no such field.
    assert not hasattr(candidates[0], "is_match")
