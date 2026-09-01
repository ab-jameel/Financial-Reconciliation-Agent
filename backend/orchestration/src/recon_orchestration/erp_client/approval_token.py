# backend/orchestration/src/recon_orchestration/erp_client/approval_token.py
import os
import time
import jwt
from pathlib import Path
from recon_common.detail_hash import compute_detail_hash

TOKEN_TTL_SECONDS = 300  # short-lived: 5 minutes


def _private_key() -> str:
    return Path(os.environ["ERP_TOKEN_PRIVATE_KEY_PATH"]).read_text()


def issue_approval_token(case_id: str, amount: str, currency: str, entity: str,
                          reviewer_role: str, action: str = "post") -> str:
    """Issued only from here — this module is never imported by recon_erp,
    which never even has the private key on disk. That asymmetry, not a
    convention, is what stops the ERP from ever minting its own tokens."""
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