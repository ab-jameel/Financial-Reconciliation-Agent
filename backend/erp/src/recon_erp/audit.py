# backend/erp/src/recon_erp/audit.py
import hashlib
import json
import time

GENESIS_HASH = "0" * 64


def _compute_hash(previous_hash: str, event_type: str, case_id: str, payload: dict, timestamp: float) -> str:
    canonical = json.dumps({
        "previous_hash": previous_hash, "event_type": event_type,
        "case_id": case_id, "payload": payload, "timestamp": timestamp,
    }, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def append_audit_event(session, event_type: str, case_id: str, journal_entry_id, payload: dict):
    from recon_erp.db.tables import AuditLogRow
    last = session.query(AuditLogRow).order_by(AuditLogRow.id.desc()).first()
    previous_hash = last.event_hash if last else GENESIS_HASH
    timestamp = time.time()
    event_hash = _compute_hash(previous_hash, event_type, case_id, payload, timestamp)
    row = AuditLogRow(
        event_type=event_type, case_id=case_id, journal_entry_id=journal_entry_id,
        payload=json.dumps(payload, default=str), previous_event_hash=previous_hash,
        event_hash=event_hash, created_at=timestamp,
    )
    session.add(row)
    return row