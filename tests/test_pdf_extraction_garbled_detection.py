"""Tests garbled-text detection for PDF-extracted pages."""

from recon_orchestration.ingestion.pdf_extractor import _looks_garbled

def test_normal_text_is_not_garbled():
    """Assert ordinary statement text is not flagged as garbled."""
    assert _looks_garbled("Date: 2026-08-01  Amount: $354.95  AWS Cloud Hosting") is False

def test_replacement_characters_flagged_as_garbled():
    """Assert text full of replacement characters is flagged as garbled."""
    assert _looks_garbled("\ufffd\ufffd\ufffd garbled \ufffd\ufffd text \ufffd\ufffd here") is True
