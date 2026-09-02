# tests/test_reconcile_safety.py
from datetime import date
from decimal import Decimal
from recon_common.models import Transaction, LedgerEntry, DatasetSplit, ExceptionType, MatchStatus
from recon_orchestration.matcher.reconcile import reconcile


def _txn(id_, label=ExceptionType.CLEAN_MATCH):
    return Transaction(id=id_, date=date(2026, 8, 1), amount=Decimal("100.00"), currency="USD",
                        reference="REF-DUP", description="x", dataset_split=DatasetSplit.TUNING,
                        label_exception_type=label)

def _led(invoice_number="INV-REAL"):
    return LedgerEntry(id="L-DUP", date=date(2026, 8, 1), amount=Decimal("100.00"), currency="USD",
                        reference="REF-DUP", description="y", invoice_number=invoice_number,
                        dataset_split=DatasetSplit.TUNING)


def test_second_claim_on_same_ledger_entry_is_exception_not_matched():
    claimed = set()
    def claim_fn(led_id):
        if led_id in claimed:
            return False
        claimed.add(led_id)
        return True

    ledger = _led()
    status_1, _ = reconcile(_txn("T1"), [ledger], load_valid_invoices_fn=lambda: {"INV-REAL"}, claim_fn=claim_fn)
    status_2, matched_2 = reconcile(_txn("T2", label=ExceptionType.DUPLICATE), [ledger],
                                     load_valid_invoices_fn=lambda: {"INV-REAL"}, claim_fn=claim_fn)
    assert status_1 == MatchStatus.MATCHED
    assert status_2 == MatchStatus.EXCEPTION  # the duplicate, NOT silently cleared
    assert matched_2 is None


def test_nonexistent_invoice_is_exception_even_with_perfect_key_match():
    status, matched = reconcile(
        _txn("T3", label=ExceptionType.MISSING_INVOICE), [_led(invoice_number="INV-DOES-NOT-EXIST")],
        load_valid_invoices_fn=lambda: {"INV-REAL", "INV-OTHER"},
        claim_fn=lambda led_id: True,
    )
    assert status == MatchStatus.EXCEPTION
    assert matched is None


def test_genuine_clean_match_still_clears():
    status, matched = reconcile(_txn("T4"), [_led()], load_valid_invoices_fn=lambda: {"INV-REAL"}, claim_fn=lambda led_id: True)
    assert status == MatchStatus.MATCHED
    assert matched.id == "L-DUP"