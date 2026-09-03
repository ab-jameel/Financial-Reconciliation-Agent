# tests/test_audit_log_endpoint_verification.py
from fastapi.testclient import TestClient
from recon_erp.app import app
from recon_orchestration.erp_client.approval_token import issue_approval_token

client = TestClient(app)

def test_audit_log_endpoint_reports_verified_true_for_untampered_events():
    case_id = "CASE-AUDIT-ENDPOINT-TEST"
    req = {"case_id": case_id, "entity": "Test Co", "amount": "50.00", "currency": "USD", "description": "test"}
    token = issue_approval_token(case_id, req["amount"], req["currency"], req["entity"], "accountant", "post")
    client.post("/journal-entries", json=req, headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"{case_id}-post"})
    events = client.get(f"/audit-log?case_id={case_id}").json()
    assert len(events) >= 1
    assert all(e["verified"] for e in events)