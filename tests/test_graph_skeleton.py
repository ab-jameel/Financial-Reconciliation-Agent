# tests/test_graph_skeleton.py
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.state import GRAPH_VERSION
from unittest.mock import patch


def _txn(amount="100.00"):
    return {"id": "T1", "date": "2026-08-01", "amount": amount, "currency": "USD",
            "reference": "REF-1", "description": "x",
            "dataset_split": "tuning", "label_exception_type": "clean_match"}


def _led():
    return {"id": "L1", "date": "2026-08-01", "amount": "100.00", "currency": "USD",
            "reference": "REF-1", "description": "y", "invoice_number": None,
            "dataset_split": "tuning"}


def _run(graph, thread_id, txn_amount):
    config = {"configurable": {"thread_id": thread_id}}
    return graph.invoke({
        "case_id": thread_id, "graph_version": GRAPH_VERSION,
        "transaction": _txn(txn_amount), "candidate_ledger_entries": [_led()],
        "rejection_cycle_count": 0,
    }, config=config), config

def _fake_completion(*args, **kwargs):
    class FakeMessage:
        tool_calls = None
        content = '{"confidence": 0.5, "explanation": "stub", "disposition": "exception"}'
        def model_dump(self): return {"role": "assistant", "content": self.content}
    class FakeChoice:
        message = FakeMessage()
    class FakeResponse:
        choices = [FakeChoice()]
    return FakeResponse()


def test_matched_transaction_closes_without_review():
    graph = build_graph(MemorySaver())
    result, _ = _run(graph, "t-matched", "100.00")
    assert result["case_status"] == "closed_matched"
    assert "__interrupt__" not in result


@patch("recon_orchestration.investigator.loop.litellm.completion", side_effect=_fake_completion)
@patch("recon_orchestration.investigator.loop.search_related_transactions", return_value=[])
@patch("recon_orchestration.investigator.loop.retrieve_policy", return_value={"policy_name": "x", "version": 1, "text": "..."})
def test_exception_pauses_with_persisted_payload(mock_policy, mock_related, mock_llm):
    graph = build_graph(MemorySaver())
    result, config = _run(graph, "t-exception", "105.00")
    assert "__interrupt__" in result
    snapshot = graph.get_state(config)
    assert snapshot.values["pending_review"]["case_id"] == "t-exception"


@patch("recon_orchestration.investigator.loop.litellm.completion", side_effect=_fake_completion)
@patch("recon_orchestration.investigator.loop.search_related_transactions", return_value=[])
@patch("recon_orchestration.investigator.loop.retrieve_policy", return_value={"policy_name": "x", "version": 1, "text": "..."})
def test_approval_reaches_write_back(mock_policy, mock_related, mock_llm):
    graph = build_graph(MemorySaver())
    _, config = _run(graph, "t-approve", "105.00")
    result = graph.invoke(Command(resume={"decision": "approve"}), config=config)
    assert result["approval_state"] == "approved"
    assert result["case_status"] == "posted_placeholder"


@patch("recon_orchestration.investigator.loop.litellm.completion", side_effect=_fake_completion)
@patch("recon_orchestration.investigator.loop.search_related_transactions", return_value=[])
@patch("recon_orchestration.investigator.loop.retrieve_policy", return_value={"policy_name": "x", "version": 1, "text": "..."})
def test_rejection_cycles_then_escalates(mock_policy, mock_related, mock_llm):
    graph = build_graph(MemorySaver())
    _, config = _run(graph, "t-reject", "105.00")
    for _ in range(2):
        result = graph.invoke(Command(resume={"decision": "reject", "reason": "check again"}), config=config)
        assert "__interrupt__" in result
    result = graph.invoke(Command(resume={"decision": "reject", "reason": "still no"}), config=config)
    assert result["approval_state"] == "escalated_unresolved"


def test_write_back_only_reachable_via_apply_decision():
    """Structural proof, not a string search: no edge lets the investigator
    or matcher reach write-back directly."""
    edges = {(e.source, e.target) for e in build_graph(MemorySaver()).get_graph().edges}
    assert ("investigator", "write_back") not in edges
    assert ("matcher", "write_back") not in edges
    assert {src for (src, tgt) in edges if tgt == "write_back"} == {"apply_decision"}