"""Issuance of short-lived approval tokens for ERP write-back."""

import os
import time
import jwt
from pathlib import Path
from recon_common.detail_hash import compute_detail_hash

TOKEN_TTL_SECONDS = 300  # short-lived: 5 minutes


def _private_key() -> str:
    """Return the ERP token private key read from disk."""
    return Path(os.environ["ERP_TOKEN_PRIVATE_KEY_PATH"]).read_text()


def issue_approval_token(case_id: str, amount: str, currency: str, entity: str,
                          reviewer_role: str, action: str = "post") -> str:
    """Sign a short-lived RS256 token authorizing a single write-back action.

    This module is never imported by the ERP service, which does not have
    access to the private key and therefore cannot mint its own tokens.
    """
    now = int(time.time())
    payload = {
        "case_id": case_id,
        "detail_hash": compute_detail_hash(case_id, amount, currency, entity),
        "entity": entity,
        "amount": amount,
        "reviewer_role": reviewer_role,
        "action": action,  # "post" or "reverse" — scoped separately, one can't be reused as the other
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, _private_key(), algorithm="RS256")
