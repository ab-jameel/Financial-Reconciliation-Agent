"""Stress helper: runs a case to the human-review interrupt."""

import sys
from dotenv import load_dotenv
load_dotenv()
from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.checkpointer import get_checkpointer
from recon_orchestration.graph.state import GRAPH_VERSION

def main(case_id: str):
    """Run the graph for case_id and assert it pauses at the review interrupt."""
    with get_checkpointer() as checkpointer:
        checkpointer.setup()
        graph = build_graph(checkpointer)
        result = graph.invoke({
            "case_id": case_id, "graph_version": GRAPH_VERSION,
            "transaction": {"id": case_id, "date": "2026-08-01", "amount": "105.00",
                             "currency": "USD", "reference": "REF-STRESS", "description": "stress",
                             "dataset_split": "tuning", "label_exception_type": "amount_mismatch"},
            "candidate_ledger_entries": [{"id": "L-STRESS", "date": "2026-08-01", "amount": "100.00",
                             "currency": "USD", "reference": "REF-STRESS", "description": "stress ledger",
                             "invoice_number": None, "dataset_split": "tuning"}],
            "rejection_cycle_count": 0,
        }, config={"configurable": {"thread_id": case_id}})
    assert "__interrupt__" in result
    print("PAUSED_OK")

if __name__ == "__main__":
    main(sys.argv[1])
