"""Node implementations for the reconciliation graph."""

from recon_common.models import Transaction, LedgerEntry, MatchStatus
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.matcher.ranking import rank_candidates
from recon_orchestration.erp_client.client import post_journal_entry
from recon_orchestration.erp_client.approval_token import issue_approval_token
from recon_orchestration.investigator.loop import investigate
from recon_orchestration.matcher.reconcile import reconcile
from recon_orchestration.matcher.claims import try_claim_ledger_entry
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import InvoiceRow
from recon_orchestration.graph.case_index import update_case_index
from langgraph.types import interrupt
import asyncio
import os


MAX_REINVESTIGATION_CYCLES = 2


def _load_valid_invoice_numbers(dataset_split: str) -> set[str]:
    """Return the set of invoice numbers present for the given dataset split."""
    session = SessionLocal()
    try:
        return {r[0] for r in session.query(InvoiceRow.invoice_number).filter_by(dataset_split=dataset_split).all()}
    finally:
        session.close()


def _claim_fn_for_case(case_id: str):
    """Return a closure that claims a ledger entry on behalf of the given case."""
    def _claim(ledger_entry_id: str) -> bool:
        session = SessionLocal()
        try:
            return try_claim_ledger_entry(session, ledger_entry_id, case_id)
        finally:
            session.close()
    return _claim


def ingestion_node(state):
    """Return an empty state update (ingestion is currently a pass-through)."""
    return {}


def matcher_node(state):
    """Run deterministic matching, falling back to ranking, and return the result.

    On a match, returns the matched ledger-entry id; otherwise returns the
    ranked candidate list for downstream investigation.
    """
    txn = Transaction(**state["transaction"])
    ledgers = [LedgerEntry(**le) for le in state["candidate_ledger_entries"]]
    status, matched = reconcile(
        txn, ledgers,
        load_valid_invoices_fn=lambda: _load_valid_invoice_numbers(txn.dataset_split),
        claim_fn=_claim_fn_for_case(state["case_id"]),
    )

    if status == MatchStatus.MATCHED:
        return {"match_status": status.value, "matched_ledger_entry_id": matched.id}

    ranked = rank_candidates(txn, ledgers)
    return {"match_status": status.value, "ranked_candidates": [c.model_dump() for c in ranked]}


def route_after_matcher(state):
    """Return the next node: 'close_case' when matched, otherwise 'investigator'."""
    return "close_case" if state["match_status"] == MatchStatus.MATCHED.value else "investigator"


def close_case_node(state):
    """Record the case as closed and matched in the case index."""
    update_case_index(state["case_id"], "closed_matched")
    return {"case_status": "closed_matched"}


def investigator_node(state):
    """Run the investigator (or the stress-test stub) and return its disposition."""
    if os.environ.get("RECON_FAKE_INVESTIGATOR") == "1":
        return {"proposed_disposition": {"confidence": 0.5, "explanation": "stress-test stub", "disposition": "exception"}}
    txn = state["transaction"]
    ledgers = state.get("candidate_ledger_entries", [])
    reason = state.get("rejection_reason")
    disposition = asyncio.run(investigate(txn, ledgers, reason))
    return {"proposed_disposition": disposition}


def prepare_review_node(state):
    """Assemble the pending-review payload and mark the case as pending review."""
    payload = {
        "case_id": state["case_id"],
        "transaction": state["transaction"],
        "match_status": state["match_status"],
        "ranked_candidates": state.get("ranked_candidates", []),
        "proposed_disposition": state["proposed_disposition"],
        "rejection_cycle_count": state.get("rejection_cycle_count", 0),
    }
    update_case_index(state["case_id"], "pending_review")
    return {"pending_review": payload}


def human_review_node(state):
    """Interrupt for human review and capture the reviewer's decision."""
    decision = interrupt(state["pending_review"])
    return {"_last_decision": decision}


def apply_decision_node(state):
    """Apply the reviewer's decision: approve, re-investigate, or escalate."""
    decision = state["_last_decision"]
    if decision["decision"] == "approve":
        update_case_index(state["case_id"], "approved_pending_writeback")
        return {"approval_state": "approved"}

    cycle = state.get("rejection_cycle_count", 0) + 1
    if cycle <= MAX_REINVESTIGATION_CYCLES:
        update_case_index(state["case_id"], "pending_review")
        return {
            "approval_state": "rejected_reinvestigate",
            "rejection_cycle_count": cycle,
            "rejection_reason": decision.get("reason"),
            "pending_review": None,
        }
    update_case_index(state["case_id"], "escalated_unresolved")
    return {"approval_state": "escalated_unresolved", "rejection_cycle_count": cycle}


def route_after_decision(state):
    """Return the next node based on the approval state."""
    return {"approved": "write_back", "rejected_reinvestigate": "investigator"}.get(
        state["approval_state"], "escalate"
    )


def write_back_node(state):
    """Issue an approval token and post the journal entry to the ERP."""
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
    update_case_index(state["case_id"], "posted")
    return {"case_status": "posted", "journal_entry": result}


def escalate_node(state):
    """Mark the case as escalated and unresolved."""
    return {"case_status": "escalated_unresolved"}
