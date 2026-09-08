"""Verifies JSON extraction succeeds when the model prefixes its response with explanatory text."""

import pytest
from recon_orchestration.investigator.loop import _extract_json_object


def test_extracts_json_after_reasoning_prose():
    """Assert the JSON object is extracted when preceded by reasoning prose."""
    text = (
        "Based on the evidence, the amount differs by $5.00, exceeding the "
        "$2.00 materiality threshold.\n"
        '{"confidence": 0.95, "explanation": "details", "disposition": "amount_mismatch"}'
    )
    result = _extract_json_object(text)
    assert result["disposition"] == "amount_mismatch"
    assert result["confidence"] == 0.95


def test_still_handles_pure_json():
    """Assert a response that is already pure JSON parses directly."""
    text = '{"confidence": 0.5, "explanation": "x", "disposition": "clean_match"}'
    assert _extract_json_object(text)["disposition"] == "clean_match"


def test_raises_when_no_json_present():
    """Assert a response with no JSON raises."""
    with pytest.raises(Exception):
        _extract_json_object("no json here at all")
