"""Tests dedup/idempotency with extraction fully mocked."""

from unittest.mock import patch
from recon_orchestration.ingestion.statement_ingestion import ingest_statement

@patch("recon_orchestration.ingestion.statement_ingestion.extract_transactions_from_page_text")
@patch("recon_orchestration.ingestion.statement_ingestion.extract_pages")
def test_reingesting_same_statement_creates_no_duplicates(mock_pages, mock_extract, tmp_path, monkeypatch):
    """Assert re-ingesting the same statement creates no duplicate transactions."""
    monkeypatch.setenv("RECON_FAKE_INVESTIGATOR", "1")  # avoid a real LLM call for the resulting exception case
    mock_pages.return_value = [{"page_number": 1, "text": "statement text", "needs_vision": False}]
    mock_extract.return_value = [{"date": "2026-08-01", "amount": "75.00", "currency": "USD",
                                    "description": "Test Vendor", "reference": None}]
    dummy_pdf = tmp_path / "statement.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")

    first = ingest_statement(str(dummy_pdf), "statement.pdf")
    second = ingest_statement(str(dummy_pdf), "statement.pdf")

    assert first["new_transactions_created"] == 1
    assert second["new_transactions_created"] == 0
