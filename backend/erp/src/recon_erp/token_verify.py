"""Verification of RS256 approval tokens issued by the orchestration service."""

import os
import jwt
from pathlib import Path


class TokenError(Exception):
    """Raised when a token is invalid, expired, or out of scope."""
    pass


def _public_key() -> str:
    """Return the ERP token public key read from disk."""
    return Path(os.environ["ERP_TOKEN_PUBLIC_KEY_PATH"]).read_text()


def verify_token(token: str, expected_action: str, expected_detail_hash: str, expected_case_id: str) -> dict:
    """Decode and validate an approval token, returning its claims on success.

    Raises TokenError if the signature is invalid, the token is expired, or
    the token's action, case_id, or detail_hash does not match the request.
    """
    try:
        payload = jwt.decode(token, _public_key(), algorithms=["RS256"])
    except jwt.ExpiredSignatureError:
        raise TokenError("Token expired")
    except jwt.InvalidTokenError as e:
        raise TokenError(f"Invalid token: {e}")

    if payload.get("action") != expected_action:
        raise TokenError(f"Token scoped for action={payload.get('action')!r}, expected {expected_action!r}")
    if payload.get("case_id") != expected_case_id:
        raise TokenError("Token case_id does not match request")
    if payload.get("detail_hash") != expected_detail_hash:
        raise TokenError("Token detail_hash does not match request payload — scope mismatch")
    return payload
