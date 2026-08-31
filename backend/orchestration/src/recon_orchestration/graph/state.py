# backend/orchestration/src/recon_orchestration/graph/state.py
from typing import TypedDict, Optional

GRAPH_VERSION = "v1"


class ReconciliationState(TypedDict, total=False):
    case_id: str
    graph_version: str
    transaction: dict
    candidate_ledger_entries: list[dict]
    match_status: str
    matched_ledger_entry_id: Optional[str]
    ranked_candidates: list[dict]
    proposed_disposition: Optional[dict]
    pending_review: Optional[dict]
    _last_decision: Optional[dict]
    approval_state: str
    rejection_cycle_count: int
    rejection_reason: Optional[str]
    case_status: str