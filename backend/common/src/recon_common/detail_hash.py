# backend/common/src/recon_common/detail_hash.py
import hashlib
import json


def compute_detail_hash(case_id: str, amount: str, currency: str, entity: str) -> str:
    canonical = json.dumps(
        {"case_id": case_id, "amount": amount, "currency": currency, "entity": entity},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()