# backend/orchestration/src/recon_orchestration/graph/build.py
from langgraph.graph import StateGraph, START, END
from recon_orchestration.graph.state import ReconciliationState
from recon_orchestration.graph import nodes as n


def build_graph(checkpointer):
    b = StateGraph(ReconciliationState)

    b.add_node("ingestion", n.ingestion_node)
    b.add_node("matcher", n.matcher_node)
    b.add_node("close_case", n.close_case_node)
    b.add_node("investigator", n.investigator_node)
    b.add_node("prepare_review", n.prepare_review_node)
    b.add_node("human_review", n.human_review_node)
    b.add_node("apply_decision", n.apply_decision_node)
    b.add_node("write_back", n.write_back_node)
    b.add_node("escalate", n.escalate_node)

    b.add_edge(START, "ingestion")
    b.add_edge("ingestion", "matcher")
    b.add_conditional_edges("matcher", n.route_after_matcher,
                             {"close_case": "close_case", "investigator": "investigator"})
    b.add_edge("close_case", END)
    b.add_edge("investigator", "prepare_review")
    b.add_edge("prepare_review", "human_review")
    b.add_edge("human_review", "apply_decision")
    b.add_conditional_edges("apply_decision", n.route_after_decision,
                             {"write_back": "write_back", "investigator": "investigator", "escalate": "escalate"})
    b.add_edge("write_back", END)
    b.add_edge("escalate", END)

    return b.compile(checkpointer=checkpointer)