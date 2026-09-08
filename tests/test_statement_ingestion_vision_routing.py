"""Tests vision-vs-text routing during statement ingestion."""

from unittest.mock import patch
from recon_orchestration.ingestion.statement_ingestion import ingest_statement

@patch("recon_orchestration.ingestion.statement_ingestion.rasterize_page")
@patch("recon_orchestration.ingestion.statement_ingestion.extract_transactions_from_page_image")
@patch("recon_orchestration.ingestion.statement_ingestion.extract_transactions_from_page_text")
@patch("recon_orchestration.ingestion.statement_ingestion.extract_pages")
def test_scanned_page_routes_to_vision_not_text(mock_pages, mock_text, mock_vision, mock_rasterize, tmp_path, monkeypatch):
    """Assert a page flagged for vision is routed to the vision extractor, not text."""
    monkeypatch.setenv("RECON_FAKE_INVESTIGATOR", "1")
    mock_pages.return_value = [{"page_number": 1, "text": "", "needs_vision": True}]
    mock_rasterize.return_value = b"fake-png-bytes"
    mock_vision.return_value = []

    dummy_pdf = tmp_path / "scanned.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 fake")
    ingest_statement(str(dummy_pdf), "scanned.pdf")

    mock_vision.assert_called_once_with(b"fake-png-bytes")
    mock_text.assert_not_called()
