"""Tests tolerant JSON-array extraction from LLM output."""

from recon_orchestration.utils.json_extract import extract_json_array

def test_extracts_array_after_reasoning_prose():
    """Assert a JSON array is extracted when preceded by prose."""
    text = 'Here are the transactions:\n[{"date": "2026-08-01", "amount": "10.00"}]'
    assert extract_json_array(text) == [{"date": "2026-08-01", "amount": "10.00"}]
