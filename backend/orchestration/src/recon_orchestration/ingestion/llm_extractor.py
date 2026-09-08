"""LLM-based extraction of transactions from statement text and page images."""

import base64, json, os
import litellm
from recon_orchestration.utils.json_extract import extract_json_array

MODEL = os.environ.get("LLM_MODEL")
VISION_MODEL = os.environ.get("LLM_VISION_MODEL", MODEL)


class VisionExtractionError(Exception):
    """Raised when the vision model call itself fails."""
    pass


TRANSACTION_SCHEMA_DESCRIPTION = """
Each object needs exactly these fields:
- "date": ISO 8601 (YYYY-MM-DD). Infer the year from the statement period
  if omitted; if unrecoverable, use null and note it in extraction_notes.
- "amount": a plain positive decimal string.
- "transaction_type": "debit" or "credit".
- "currency": ISO code; default "USD" and note the assumption if not stated.
- "description": the statement's own line text, verbatim.
- "reference": any check/confirmation/trace number visible, or null.
- "raw_source_line": the exact original text (or your transcription of the
  image row) this came from.
- "extraction_confidence": your own 0-1 confidence in this parse.
- "extraction_notes": any assumption or illegible field, or null.
"""

EXTRACTION_PROMPT = f"""You are extracting transactions from a bank account
statement page (given as text). Extract EVERY transaction line as a JSON
array. Your FINAL message must be ONLY the JSON array — no prose before or
after it.
{TRANSACTION_SCHEMA_DESCRIPTION}
Return an empty array for pages with no transaction lines. Never invent a
transaction that isn't actually present in the text."""

VISION_EXTRACTION_PROMPT = f"""You are extracting transactions from a
photo/scan of a bank account statement page. The image may have skew,
shadows, watermarks, letterhead, or low contrast. Read carefully — if a
specific digit is genuinely illegible, say so in extraction_notes rather
than inventing a plausible-looking number. Extract EVERY transaction line
as a JSON array. Your FINAL message must be ONLY the JSON array.
{TRANSACTION_SCHEMA_DESCRIPTION}
Return an empty array for pages with no transaction lines. Never invent a
transaction that isn't actually present in the image."""


def extract_transactions_from_page_text(page_text: str) -> list[dict]:
    """Extract transactions from statement text.

    Returns an empty list for blank pages or when the output does not parse
    as a JSON array.
    """
    if not page_text.strip():
        return []
    response = litellm.completion(model=MODEL, messages=[
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": page_text},
    ])
    try:
        return extract_json_array(response.choices[0].message.content)
    except json.JSONDecodeError:
        return []


def extract_transactions_from_page_image(image_bytes: bytes) -> list[dict]:
    """Extract transactions from a page image via the vision model.

    Raises VisionExtractionError when the vision call itself fails; returns
    an empty list when the output does not parse as a JSON array.
    """
    b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        response = litellm.completion(model=VISION_MODEL, messages=[
            {"role": "system", "content": VISION_EXTRACTION_PROMPT},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]},
        ])
    except Exception as e:
        raise VisionExtractionError(
            f"Vision call failed — check LLM_VISION_MODEL supports image input: {e}"
        ) from e
    try:
        return extract_json_array(response.choices[0].message.content)
    except json.JSONDecodeError:
        return []
