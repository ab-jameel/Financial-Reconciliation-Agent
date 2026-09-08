"""Deterministic hash binding an approval token to a transaction's details."""

import hashlib
import json


def compute_detail_hash(case_id: str, amount: str, currency: str, entity: str) -> str:
    """Return a SHA-256 hex digest over the canonical JSON of the given fields.

    The digest is embedded in approval tokens so the ERP can verify that a
    token matches the request it is attached to.
    """
    canonical = json.dumps(
        {"case_id": case_id, "amount": amount, "currency": currency, "entity": entity},
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
