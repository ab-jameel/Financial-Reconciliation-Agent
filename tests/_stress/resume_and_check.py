# tests/_stress/resume_and_check.py
import sys
from dotenv import load_dotenv
load_dotenv()
from langgraph.types import Command
from recon_orchestration.graph.build import build_graph
from recon_orchestration.graph.checkpointer import get_checkpointer

def main(case_id: str):
    with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": case_id}}
        snapshot = graph.get_state(config)
        assert snapshot is not None and snapshot.values, "checkpoint missing after restart"
        payload = snapshot.values["pending_review"]
        assert payload["transaction"]["reference"] == "REF-STRESS"
        print("PAYLOAD_INTACT_OK")

        result = graph.invoke(Command(resume={"decision": "approve"}), config=config)
        assert result["case_status"] == "posted_placeholder"
        print("RESUME_OK")

if __name__ == "__main__":
    main(sys.argv[1])