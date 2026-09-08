"""FastAPI service exposing the mock ERP: journal-entry posting, reversal, and the audit log."""

from dotenv import load_dotenv
load_dotenv()

import time
import uuid
import json
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from recon_erp.db.session import SessionLocal
from recon_erp.db.tables import JournalEntryRow, IdempotencyKeyRow
from recon_erp.token_verify import verify_token, TokenError
from recon_erp.audit import append_audit_event, _compute_hash
from recon_common.detail_hash import compute_detail_hash
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

def _serialize(entry: JournalEntryRow) -> dict:
    """Return a journal entry row as a JSON-serializable dict."""
    return {
        "id": entry.id, "case_id": entry.case_id, "entity": entry.entity,
        "amount": str(entry.amount), "currency": entry.currency, "status": entry.status,
        "original_entry_id": entry.original_entry_id, "reversed_entry_id": entry.reversed_entry_id,
    }


class PostJournalEntryRequest(BaseModel):
    """Request body for posting a journal entry."""

    case_id: str
    entity: str
    amount: str
    currency: str
    description: str


@app.post("/journal-entries", status_code=201)
def post_journal_entry(
    req: PostJournalEntryRequest,
    authorization: str | None = Header(None),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    """Post a new journal entry after verifying the approval token, honoring idempotency."""
    session = SessionLocal()
    try:
        existing = session.get(IdempotencyKeyRow, idempotency_key)
        if existing is not None:
            return _serialize(session.get(JournalEntryRow, existing.journal_entry_id))

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.removeprefix("Bearer ")

        expected_hash = compute_detail_hash(req.case_id, req.amount, req.currency, req.entity)
        try:
            payload = verify_token(token, "post", expected_hash, req.case_id)
        except TokenError as e:
            raise HTTPException(status_code=403, detail=str(e))

        entry_id = str(uuid.uuid4())
        entry = JournalEntryRow(id=entry_id, case_id=req.case_id, entity=req.entity, amount=req.amount,
                                 currency=req.currency, description=req.description, status="posted",
                                 created_at=time.time())
        session.add(entry)
        session.add(IdempotencyKeyRow(idempotency_key=idempotency_key, journal_entry_id=entry_id, created_at=time.time()))
        append_audit_event(session, "posted", req.case_id, entry_id, {
            "amount": req.amount, "currency": req.currency, "entity": req.entity,
            "reviewer_role": payload["reviewer_role"],
        })
        session.commit()
        return _serialize(entry)
    finally:
        session.close()


@app.get("/journal-entries/{entry_id}")
def get_journal_entry(entry_id: str):
    """Return a single journal entry by id, or 404 if it does not exist."""
    session = SessionLocal()
    entry = session.get(JournalEntryRow, entry_id)
    session.close()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(entry)


class ReverseRequest(BaseModel):
    """Request body for reversing a journal entry."""

    reason: str


@app.post("/journal-entries/{entry_id}/reverse", status_code=201)
def reverse_journal_entry(
    entry_id: str,
    req: ReverseRequest,
    authorization: str | None = Header(None),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    """Reverse a posted journal entry and post a negating entry.

    Requires a token scoped to the "reverse" action; a "post" token is
    rejected.
    """
    session = SessionLocal()
    try:
        existing = session.get(IdempotencyKeyRow, idempotency_key)
        if existing is not None:
            return _serialize(session.get(JournalEntryRow, existing.journal_entry_id))

        original = session.get(JournalEntryRow, entry_id)
        if original is None:
            raise HTTPException(status_code=404, detail="Original entry not found")
        if original.status == "reversed":
            raise HTTPException(status_code=409, detail="Entry already reversed")

        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.removeprefix("Bearer ")

        expected_hash = compute_detail_hash(original.case_id, str(original.amount), original.currency, original.entity)
        try:
            payload = verify_token(token, "reverse", expected_hash, original.case_id)
        except TokenError as e:
            raise HTTPException(status_code=403, detail=str(e))

        reversing_id = str(uuid.uuid4())
        reversing = JournalEntryRow(
            id=reversing_id, case_id=original.case_id, entity=original.entity,
            amount=str(-float(original.amount)), currency=original.currency,
            description=f"Reversal of {entry_id}: {req.reason}", status="posted",
            original_entry_id=entry_id, created_at=time.time(),
        )
        original.status = "reversed"
        original.reversed_entry_id = reversing_id
        session.add(reversing)
        session.add(IdempotencyKeyRow(idempotency_key=idempotency_key, journal_entry_id=reversing_id, created_at=time.time()))
        append_audit_event(session, "reversed", original.case_id, reversing_id, {
            "original_entry_id": entry_id, "reason": req.reason, "reviewer_role": payload["reviewer_role"],
        })
        session.commit()
        return _serialize(reversing)
    finally:
        session.close()

@app.get("/audit-log")
def list_audit_log(case_id: str | None = None):
    """Return audit-log events, optionally filtered by case_id, with per-event hash verification."""
    from recon_erp.db.tables import AuditLogRow
    session = SessionLocal()
    try:
        query = session.query(AuditLogRow)
        if case_id:
            query = query.filter_by(case_id=case_id)
        rows = query.order_by(AuditLogRow.id).all()
        events = []
        for r in rows:
            payload = json.loads(r.payload)
            recomputed = _compute_hash(r.previous_event_hash, r.event_type, r.case_id, payload, r.created_at)
            events.append({
                "id": r.id, "event_type": r.event_type, "case_id": r.case_id,
                "journal_entry_id": r.journal_entry_id, "payload": payload,
                "previous_event_hash": r.previous_event_hash, "event_hash": r.event_hash,
                "created_at": r.created_at,
                "verified": recomputed == r.event_hash,
            })
        return events
    finally:
        session.close()
