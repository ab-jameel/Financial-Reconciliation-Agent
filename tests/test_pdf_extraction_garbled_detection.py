# tests/test_pdf_extraction_garbled_detection.py
from recon_orchestration.ingestion.pdf_extractor import _looks_garbled

def test_normal_text_is_not_garbled():
    assert _looks_garbled("Date: 2026-08-01  Amount: $354.95  AWS Cloud Hosting") is False

def test_replacement_characters_flagged_as_garbled():
    assert _looks_garbled("\ufffd\ufffd\ufffd garbled \ufffd\ufffd text \ufffd\ufffd here") is True