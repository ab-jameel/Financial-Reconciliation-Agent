"""Tests ERP write-back safety: token validation, idempotency, and the hash chain."""

from fastapi.testclient import TestClient
from recon_erp.app import app
from recon_orchestration.erp_client.approval_token import issue_approval_token

client = TestClient(app)


def _req(case_id="CASE-1", amount="100.00", entity="Acme Corp"):
    """Return a minimal journal-entry request body."""
    return {"case_id": case_id, "entity": entity, "amount": amount, "currency": "USD", "description": "test posting"}


def test_missing_token_rejected():
    """Assert a request without an authorization token is rejected with 401."""
    resp = client.post("/journal-entries", json=_req("CASE-NO-TOKEN"), headers={"Idempotency-Key": "idem-no-token"})
    assert resp.status_code == 401


def test_expired_token_rejected(monkeypatch):
    """Assert an expired token is rejected with 403."""
    import recon_orchestration.erp_client.approval_token as token_mod
    monkeypatch.setattr(token_mod, "TOKEN_TTL_SECONDS", -10)  # forces exp into the past at issuance time
    req = _req("CASE-EXPIRED")
    token = issue_approval_token(req["case_id"], req["amount"], req["currency"], req["entity"], "accountant", "post")
    resp = client.post("/journal-entries", json=req, headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-expired"})
    assert resp.status_code == 403


def test_token_scoped_to_wrong_amount_rejected():
    """Assert a token bound to a different amount is rejected with 403."""
    req = _req("CASE-SCOPE", amount="100.00")
    token = issue_approval_token(req["case_id"], "999.00", req["currency"], req["entity"], "accountant", "post")  # wrong amount baked in
    resp = client.post("/journal-entries", json=req, headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-scope"})
    assert resp.status_code == 403


def test_token_scoped_to_wrong_entity_rejected():
    """Assert a token bound to a different entity is rejected with 403."""
    req = _req("CASE-ENTITY", entity="Acme Corp")
    token = issue_approval_token(req["case_id"], req["amount"], req["currency"], "A Different Vendor Inc", "accountant", "post")
    resp = client.post("/journal-entries", json=req, headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-entity"})
    assert resp.status_code == 403


def test_replayed_idempotency_key_does_not_double_post():
    """Assert replaying the same idempotency key returns the original entry."""
    req = _req("CASE-IDEMPOTENT")
    token = issue_approval_token(req["case_id"], req["amount"], req["currency"], req["entity"], "accountant", "post")
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "idem-replay-1"}
    first = client.post("/journal-entries", json=req, headers=headers)
    second = client.post("/journal-entries", json=req, headers=headers)  # same key, replayed
    assert first.status_code == 201 and second.status_code == 201
    assert second.json()["id"] == first.json()["id"]  # returned the SAME entry, didn't post a second one


def test_full_case_sequence_and_hash_chain_intact():
    """Assert a full post/reverse sequence leaves an intact, verifiable hash chain."""
    case_id = "CASE-FULL-SEQUENCE"
    req = _req(case_id, amount="250.00")

    post_token = issue_approval_token(case_id, req["amount"], req["currency"], req["entity"], "accountant", "post")
    posted = client.post("/journal-entries", json=req, headers={"Authorization": f"Bearer {post_token}", "Idempotency-Key": f"{case_id}-post"})
    entry_id = posted.json()["id"]

    reverse_token = issue_approval_token(case_id, req["amount"], req["currency"], req["entity"], "senior_accountant", "reverse")
    client.post(f"/journal-entries/{entry_id}/reverse", json={"reason": "test rollback"},
                headers={"Authorization": f"Bearer {reverse_token}", "Idempotency-Key": f"{case_id}-reverse"})

    assert client.get(f"/journal-entries/{entry_id}").json()["status"] == "reversed"

    import os, json as _json
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from recon_erp.db.tables import AuditLogRow
    from recon_erp.audit import _compute_hash

    engine = create_engine(os.environ["ERP_DATABASE_URL"].replace("+asyncpg", ""))
    session = sessionmaker(bind=engine)()
    events = session.query(AuditLogRow).filter_by(case_id=case_id).order_by(AuditLogRow.id).all()
    session.close()

    assert [e.event_type for e in events] == ["posted", "reversed"]
    previous_hash = events[0].previous_event_hash
    for event in events:
        recomputed = _compute_hash(previous_hash, event.event_type, event.case_id, _json.loads(event.payload), event.created_at)
        assert recomputed == event.event_hash, "hash chain broken"
        previous_hash = event.event_hash
