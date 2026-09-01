# backend/orchestration/src/recon_orchestration/erp_client/client.py
import os
import httpx

ERP_BASE_URL = os.environ.get("ERP_BASE_URL", "http://localhost:8001")


def post_journal_entry(case_id, entity, amount, currency, description, token, idempotency_key) -> dict:
    response = httpx.post(
        f"{ERP_BASE_URL}/journal-entries",
        json={"case_id": case_id, "entity": entity, "amount": amount, "currency": currency, "description": description},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()