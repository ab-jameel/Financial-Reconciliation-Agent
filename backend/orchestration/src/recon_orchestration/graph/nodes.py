# backend/orchestration/src/recon_orchestration/graph/nodes.py
from recon_common.models import Transaction, LedgerEntry, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.ranking import rank_candidates
from recon_orchestration.erp_client.client import post_journal_entry
from recon_orchestration.erp_client.approval_token import issue_approval_token
from recon_orchestration.investigator.loop import investigate
from langgraph.types import interrupt
import asyncio
import os


MAX_REINVESTIGATION_CYCLES = 2


def ingestion_node(state):
    # Phase 2: just a pass-through validating the shape. Multi-source
    # ReWOO-planned fetching arrives in Phase 3.
    return {}


def matcher_node(state):
    txn = Transaction(**state["transaction"])
    ledgers = [LedgerEntry(**le) for le in state["candidate_ledger_entries"]]
    status, matched = match_deterministic(txn, ledgers)

    if status == MatchStatus.MATCHED:
        return {"match_status": status.value, "matched_ledger_entry_id": matched.id}

    ranked = rank_candidates(txn, ledgers)
    return {"match_status": status.value, "ranked_candidates": [c.model_dump() for c in ranked]}


def route_after_matcher(state):
    return "close_case" if state["match_status"] == MatchStatus.MATCHED.value else "investigator"


def close_case_node(state):
    return {"case_status": "closed_matched"}


def investigator_node(state):
    if os.environ.get("RECON_FAKE_INVESTIGATOR") == "1":
        return {"proposed_disposition": {"confidence": 0.5, "explanation": "stress-test stub", "disposition": "exception"}}
    txn = state["transaction"]
    ledgers = state.get("candidate_ledger_entries", [])
    reason = state.get("rejection_reason")
    disposition = asyncio.run(investigate(txn, ledgers, reason))
    return {"proposed_disposition": disposition}


def prepare_review_node(state):
    payload = {
        "case_id": state["case_id"],
        "transaction": state["transaction"],
        "match_status": state["match_status"],
        "ranked_candidates": state.get("ranked_candidates", []),
        "proposed_disposition": state["proposed_disposition"],
        "rejection_cycle_count": state.get("rejection_cycle_count", 0),
    }
    return {"pending_review": payload}  # committed to checkpoint BEFORE the pause


def human_review_node(state):
    decision = interrupt(state["pending_review"])
    return {"_last_decision": decision}


def apply_decision_node(state):
    decision = state["_last_decision"]
    if decision["decision"] == "approve":
        return {"approval_state": "approved"}

    cycle = state.get("rejection_cycle_count", 0) + 1
    if cycle <= MAX_REINVESTIGATION_CYCLES:
        return {
            "approval_state": "rejected_reinvestigate",
            "rejection_cycle_count": cycle,
            "rejection_reason": decision.get("reason"),
            "pending_review": None,
        }
    return {"approval_state": "escalated_unresolved", "rejection_cycle_count": cycle}


def route_after_decision(state):
    return {"approved": "write_back", "rejected_reinvestigate": "investigator"}.get(
        state["approval_state"], "escalate"
    )


def write_back_node(state):
    txn = state["transaction"]
    decision = state["_last_decision"]
    entity = txn["description"]

    if os.environ.get("RECON_FAKE_ERP") == "1":
        return {"case_status": "posted_stub", "journal_entry": {"id": "STUB-JE", "status": "posted"}}

    token = issue_approval_token(
        case_id=state["case_id"], amount=txn["amount"], currency=txn["currency"],
        entity=entity, reviewer_role=decision["reviewer_role"], action="post",
    )
    result = post_journal_entry(
        case_id=state["case_id"], entity=entity, amount=txn["amount"], currency=txn["currency"],
        description=f"Reconciliation write-back for {state['case_id']}",
        token=token, idempotency_key=f"{state['case_id']}-post",
    )
    return {"case_status": "posted", "journal_entry": result}


def escalate_node(state):
    return {"case_status": "escalated_unresolved"}