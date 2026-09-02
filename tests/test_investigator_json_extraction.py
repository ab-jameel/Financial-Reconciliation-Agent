# tests/test_investigator_json_extraction.py
"""Regression test for a real bug found via a live trace: json.loads()
silently discarded a correct answer because the model added reasoning
prose before the JSON. Every earlier mocked test used pure-JSON fixtures,
which is exactly why none of them caught this."""
import pytest
from recon_orchestration.investigator.loop import _extract_json_object


def test_extracts_json_after_reasoning_prose():
    text = (
        "Based on the evidence, the amount differs by $5.00, exceeding the "
        "$2.00 materiality threshold.\n"
        '{"confidence": 0.95, "explanation": "details", "disposition": "amount_mismatch"}'
    )
    result = _extract_json_object(text)
    assert result["disposition"] == "amount_mismatch"
    assert result["confidence"] == 0.95


def test_still_handles_pure_json():
    text = '{"confidence": 0.5, "explanation": "x", "disposition": "clean_match"}'
    assert _extract_json_object(text)["disposition"] == "clean_match"


def test_raises_when_no_json_present():
    with pytest.raises(Exception):
        _extract_json_object("no json here at all")