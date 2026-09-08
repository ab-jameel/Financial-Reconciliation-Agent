"""Tests the investigator's pure arithmetic tool functions."""

from decimal import Decimal
from datetime import date
from recon_orchestration.investigator.tools import compute_date_delta, compute_amount_delta

def test_compute_date_delta():
    """Assert compute_date_delta returns the absolute day difference."""
    assert compute_date_delta(date(2026, 8, 1), date(2026, 8, 4)) == 3

def test_compute_amount_delta():
    """Assert compute_amount_delta returns the absolute amount difference."""
    assert compute_amount_delta(Decimal("100.00"), Decimal("100.75")) == Decimal("0.75")
