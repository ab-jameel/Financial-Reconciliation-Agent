# backend/erp/src/recon_erp/app.py
from dotenv import load_dotenv
load_dotenv()

import time
import uuid
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from recon_erp.db.session import SessionLocal
from recon_erp.db.tables import JournalEntryRow, IdempotencyKeyRow
from recon_erp.token_verify import verify_token, TokenError
from recon_erp.audit import append_audit_event
from recon_common.detail_hash import compute_detail_hash

app = FastAPI()


def _serialize(entry: JournalEntryRow) -> dict:
    return {
        "id": entry.id, "case_id": entry.case_id, "entity": entry.entity,
        "amount": str(entry.amount), "currency": entry.currency, "status": entry.status,
        "original_entry_id": entry.original_entry_id, "reversed_entry_id": entry.reversed_entry_id,
    }


class PostJournalEntryRequest(BaseModel):
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
    session = SessionLocal()
    entry = session.get(JournalEntryRow, entry_id)
    session.close()
    if entry is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _serialize(entry)


class ReverseRequest(BaseModel):
    reason: str


@app.post("/journal-entries/{entry_id}/reverse", status_code=201)
def reverse_journal_entry(
    entry_id: str,
    req: ReverseRequest,
    authorization: str | None = Header(None),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
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
            payload = verify_token(token, "reverse", expected_hash, original.case_id)  # note: scoped "reverse", a "post" token cannot be reused here
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