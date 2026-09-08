"""Extracts raw text per page and rasterizes pages to PNG for vision-based extraction.

Uses PyMuPDF's renderer so no external binary (poppler, tesseract) is required.
"""

import pdfplumber
import pymupdf

def _looks_garbled(text: str) -> bool:
    """Return True when text looks like broken font encoding.

    Heuristic: a high ratio of replacement characters, or a low ratio of
    printable characters.
    """
    if not text:
        return False
    replacement_ratio = text.count("\ufffd") / max(len(text), 1)
    printable_ratio = sum(c.isprintable() or c.isspace() for c in text) / max(len(text), 1)
    return replacement_ratio > 0.05 or printable_ratio < 0.7


def extract_pages(pdf_path: str) -> list[dict]:
    """Return per-page text, flagging pages that need vision-based extraction."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            needs_vision = len(text.strip()) == 0 or _looks_garbled(text)
            pages.append({"page_number": i + 1, "text": text, "needs_vision": needs_vision})
    return pages


def rasterize_page(pdf_path: str, page_number: int, dpi: int = 200) -> bytes:
    """Rasterize a single PDF page to PNG bytes."""
    doc = pymupdf.open(pdf_path)
    try:
        pix = doc[page_number - 1].get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()
