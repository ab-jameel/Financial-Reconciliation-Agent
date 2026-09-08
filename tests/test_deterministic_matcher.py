"""Tests the deterministic (exact-key) matcher."""

from datetime import date
from decimal import Decimal
from recon_common.models import Transaction, LedgerEntry, DatasetSplit, ExceptionType, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic

def test_exact_match_clears():
    """Assert an exact (amount, currency, date, reference) match returns MATCHED."""
    txn = Transaction(id="T1", date=date(2026,8,1), amount=Decimal("100.00"), currency="USD",
                       reference="REF-1", description="x", dataset_split=DatasetSplit.TUNING,
                       label_exception_type=ExceptionType.CLEAN_MATCH)
    led = LedgerEntry(id="L1", date=date(2026,8,1), amount=Decimal("100.00"), currency="USD",
                       reference="REF-1", description="y", dataset_split=DatasetSplit.TUNING)
    status, matched = match_deterministic(txn, [led])
    assert status == MatchStatus.MATCHED
    assert matched.id == "L1"

def test_currency_mismatch_is_never_matched_despite_same_amount_date_reference():
    """Assert a currency mismatch yields EXCEPTION even when amount/date/reference agree."""
    txn = Transaction(id="T2", date=date(2026,8,1), amount=Decimal("100.00"), currency="USD",
                       reference="REF-2", description="x", dataset_split=DatasetSplit.TUNING,
                       label_exception_type=ExceptionType.CURRENCY_ISSUE)
    led = LedgerEntry(id="L2", date=date(2026,8,1), amount=Decimal("100.00"), currency="EUR",
                       reference="REF-2", description="y", dataset_split=DatasetSplit.TUNING)
    status, matched = match_deterministic(txn, [led])
    assert status == MatchStatus.EXCEPTION
