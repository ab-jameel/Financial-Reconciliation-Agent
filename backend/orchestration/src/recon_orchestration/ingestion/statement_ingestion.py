# backend/orchestration/src/recon_orchestration/ingestion/statement_ingestion.py
import hashlib
from datetime import date as Date
from decimal import Decimal, InvalidOperation

from recon_common.models import Transaction, LedgerEntry, DatasetSplit
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow, LedgerEntryRow, CaseIndexRow
from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.checkpointer import get_checkpointer
from recon_orchestration.graph.state import GRAPH_VERSION
from recon_orchestration.graph.case_index import update_case_index
from recon_orchestration.ingestion.pdf_extractor import extract_pages, rasterize_page
from recon_orchestration.ingestion.llm_extractor import (
    extract_transactions_from_page_text, extract_transactions_from_page_image, VisionExtractionError,
)


def _synthesize_transaction_id(raw: dict, source_filename: str) -> str:
    """Deterministic ID from content, not a random UUID — re-ingesting the
    SAME statement resolves to the SAME id, giving natural idempotency
    instead of duplicate rows on every re-run."""
    basis = "|".join([source_filename, str(raw.get("date")), str(raw.get("amount")),
                       str(raw.get("currency")), str(raw.get("description"))])
    return f"PDF-{hashlib.sha256(basis.encode()).hexdigest()[:16]}"


def _to_transaction(raw: dict, source_filename: str) -> Transaction | None:
    """None (not an exception) for a row that fails validation — one bad
    row must not abort the whole statement."""
    try:
        if not raw.get("date"):
            return None
        return Transaction(
            id=_synthesize_transaction_id(raw, source_filename),
            date=Date.fromisoformat(raw["date"]), amount=Decimal(str(raw["amount"])),
            currency=raw.get("currency", "USD"), reference=raw.get("reference") or "",
            description=raw.get("description", ""),
            dataset_split=DatasetSplit.PRODUCTION, label_exception_type=None,
        )
    except (KeyError, InvalidOperation, ValueError):
        return None


def ingest_statement(pdf_path: str, source_filename: str) -> dict:
    pages = extract_pages(pdf_path)

    raw_extracted, vision_errors = [], []
    text_pages_used = vision_pages_used = 0
    for page in pages:
        if page["needs_vision"]:
            try:
                image_bytes = rasterize_page(pdf_path, page["page_number"])
                raw_extracted.extend(extract_transactions_from_page_image(image_bytes))
                vision_pages_used += 1
            except VisionExtractionError as e:
                vision_errors.append({"page_number": page["page_number"], "error": str(e)})
        else:
            raw_extracted.extend(extract_transactions_from_page_text(page["text"]))
            text_pages_used += 1

    parsed, failed_rows = [], []
    for raw in raw_extracted:
        txn = _to_transaction(raw, source_filename)
        (parsed if txn else failed_rows).append(txn or raw)

    session = SessionLocal()
    try:
        existing_ids = {r.id for r in session.query(TransactionRow.id).filter(
            TransactionRow.id.in_([t.id for t in parsed])).all()} if parsed else set()
        for txn in parsed:
            if txn.id not in existing_ids:
                session.merge(TransactionRow(**txn.model_dump(mode="json")))
        session.commit()

        already_cased_ids = {r.case_id for r in session.query(CaseIndexRow.case_id).filter(
            CaseIndexRow.case_id.in_([t.id for t in parsed]),
            CaseIndexRow.status != "ingestion_failed",  # failed ones stay retryable
        ).all()} if parsed else set()
        pending_transactions = [t for t in parsed if t.id not in already_cased_ids]

        ledger_candidates = [
            LedgerEntry(**{c.name: getattr(r, c.name) for c in r.__table__.columns}).model_dump(mode="json")
            for r in session.query(LedgerEntryRow).filter_by(dataset_split=DatasetSplit.PRODUCTION.value).all()
        ]
    finally:
        session.close()

    created_case_ids, case_creation_errors = [], []
    with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        for txn in pending_transactions:
            update_case_index(txn.id, "processing")
            try:
                graph.invoke({
                    "case_id": txn.id, "graph_version": GRAPH_VERSION,
                    "transaction": txn.model_dump(mode="json"),
                    "candidate_ledger_entries": ledger_candidates, "rejection_cycle_count": 0,
                }, config={"configurable": {"thread_id": txn.id}})
                created_case_ids.append(txn.id)
            except Exception as e:
                update_case_index(txn.id, "ingestion_failed")
                case_creation_errors.append({"transaction_id": txn.id, "error": str(e)})

    return {
        "source_filename": source_filename, "pages_processed": len(pages),
        "pages_extracted_via_text": text_pages_used, "pages_extracted_via_vision": vision_pages_used,
        "vision_errors": vision_errors, "rows_extracted": len(raw_extracted),
        "rows_failed_validation": len(failed_rows), "failed_rows": failed_rows[:20],
        "transactions_already_known": len(parsed) - len(pending_transactions),
        "new_transactions_created": len(created_case_ids),
        "case_ids": created_case_ids, "case_creation_errors": case_creation_errors,
    }