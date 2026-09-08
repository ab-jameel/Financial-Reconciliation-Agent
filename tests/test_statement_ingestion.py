"""Tests statement-ingestion helper functions."""

from recon_orchestration.ingestion.statement_ingestion import _to_transaction, _synthesize_transaction_id

def test_same_row_produces_same_id_twice():
    """Assert the synthesized id is deterministic for the same row."""
    raw = {"date": "2026-08-01", "amount": "50.00", "currency": "USD", "description": "Coffee Shop"}
    assert _synthesize_transaction_id(raw, "s.pdf") == _synthesize_transaction_id(raw, "s.pdf")

def test_missing_date_fails_validation_gracefully():
    """Assert a row without a date yields None rather than raising."""
    assert _to_transaction({"amount": "50.00", "description": "x"}, "s.pdf") is None

def test_valid_row_has_no_ground_truth_label():
    """Assert a valid production row has no ground-truth label."""
    raw = {"date": "2026-08-01", "amount": "50.00", "currency": "USD", "description": "x", "reference": "CHK1"}
    txn = _to_transaction(raw, "s.pdf")
    assert txn.dataset_split.value == "production"
    assert txn.label_exception_type is None
