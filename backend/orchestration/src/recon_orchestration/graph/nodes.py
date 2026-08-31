# backend/orchestration/src/recon_orchestration/graph/nodes.py
from langgraph.types import interrupt
from recon_common.models import Transaction, LedgerEntry, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.ranking import rank_candidates

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
    # Placeholder until Phase 3's ReAct + Reflection investigator. Note this
    # produces a proposal, full stop — nothing here can set approval_state.
    reason = state.get("rejection_reason")
    explanation = "Placeholder investigator output (Phase 3 replaces this)."
    if reason:
        explanation += f" Reinvestigating after rejection: {reason}"
    return {"proposed_disposition": {"confidence": 0.5, "explanation": explanation}}


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
    # Placeholder — Phase 4 replaces this with a real HTTP call to the mock
    # ERP carrying a signed approval token. Reachable ONLY via
    # approval_state == "approved", which only apply_decision_node sets,
    # which only runs after an actual human resume.
    return {"case_status": "posted_placeholder"}


def escalate_node(state):
    return {"case_status": "escalated_unresolved"}