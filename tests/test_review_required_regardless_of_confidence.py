# tests/test_review_required_regardless_of_confidence.py
"""Phase 3's version of the Phase 2 structural test: even with the REAL
investigator producing a very high confidence, the graph must still pause
for human review. Stubs litellm so this runs in CI without real API calls
or nondeterminism."""
from unittest.mock import patch
from langgraph.checkpoint.memory import MemorySaver
from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.state import GRAPH_VERSION


def _fake_completion(*args, **kwargs):
    class FakeMessage:
        tool_calls = None
        content = '{"confidence": 0.99, "explanation": "Very confident.", "disposition": "clear"}'
        def model_dump(self): return {"role": "assistant", "content": self.content}
    class FakeChoice:
        message = FakeMessage()
    class FakeResponse:
        choices = [FakeChoice()]
    return FakeResponse()


@patch("recon_orchestration.investigator.loop.litellm.completion", side_effect=_fake_completion)
@patch("recon_orchestration.investigator.loop.search_related_transactions", return_value=[])
@patch("recon_orchestration.investigator.loop.retrieve_policy", return_value={"policy_name": "x", "version": 1, "text": "..."})
def test_high_confidence_investigator_still_pauses_for_review(mock_policy, mock_related, mock_llm):
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": "t-high-conf"}}
    result = graph.invoke({
        "case_id": "t-high-conf", "graph_version": GRAPH_VERSION,
        "transaction": {"id": "T1", "date": "2026-08-01", "amount": "105.00", "currency": "USD",
                         "reference": "REF-1", "description": "x", "dataset_split": "tuning",
                         "label_exception_type": "amount_mismatch"},
        "candidate_ledger_entries": [], "rejection_cycle_count": 0,
    }, config=config)

    assert "__interrupt__" in result  # confidence=0.99 still didn't skip review
    snapshot = graph.get_state(config)
    assert snapshot.values["pending_review"]["proposed_disposition"]["confidence"] == 0.99