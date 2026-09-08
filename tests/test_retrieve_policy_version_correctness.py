"""Verifies policy-version selection by effective date."""

import pytest
from datetime import date
from recon_orchestration.investigator.policy_store import retrieve_policy, NoPolicyInEffectError

def test_returns_v1_before_v2_effective_date():
    """Assert version 1 is returned for a date before v2's effective date."""
    result = retrieve_policy("materiality threshold", date(2026, 3, 1))
    assert result["version"] == 1
    assert "$1.00" in result["text"]

def test_returns_v2_on_and_after_effective_date():
    """Assert version 2 is returned on and after its effective date."""
    result = retrieve_policy("materiality threshold", date(2026, 7, 15))
    assert result["version"] == 2
    assert "$2.00" in result["text"]

def test_raises_when_transaction_predates_every_version():
    """Assert NoPolicyInEffectError is raised when the date predates every version."""
    with pytest.raises(NoPolicyInEffectError):
        retrieve_policy("materiality threshold", date(2025, 1, 1))
