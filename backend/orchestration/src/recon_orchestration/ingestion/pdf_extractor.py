# backend/orchestration/src/recon_orchestration/ingestion/pdf_extractor.py
"""Extracts raw text per page, and rasterizes a page to PNG when it needs
vision-based extraction instead. Uses PyMuPDF's own renderer — no external
binary (poppler, tesseract) needed, which matters given this project's
Windows-specific pain with system-level installs elsewhere (Postgres port
conflicts, native services)."""
import pdfplumber
import pymupdf

def _looks_garbled(text: str) -> bool:
    """Catches broken font-encoding pages: non-empty text that's actually
    nonsense (replacement characters, or every glyph mismapped). A cheap
    heuristic, not a guarantee."""
    if not text:
        return False
    replacement_ratio = text.count("\ufffd") / max(len(text), 1)
    printable_ratio = sum(c.isprintable() or c.isspace() for c in text) / max(len(text), 1)
    return replacement_ratio > 0.05 or printable_ratio < 0.7


def extract_pages(pdf_path: str) -> list[dict]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            needs_vision = len(text.strip()) == 0 or _looks_garbled(text)
            pages.append({"page_number": i + 1, "text": text, "needs_vision": needs_vision})
    return pages


def rasterize_page(pdf_path: str, page_number: int, dpi: int = 200) -> bytes:
    doc = pymupdf.open(pdf_path)
    try:
        pix = doc[page_number - 1].get_pixmap(dpi=dpi)
        return pix.tobytes("png")
    finally:
        doc.close()