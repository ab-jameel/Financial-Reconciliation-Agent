"""Creates the LangGraph checkpoint tables."""

from dotenv import load_dotenv
load_dotenv()
from recon_orchestration.graph.checkpointer import get_checkpointer

if __name__ == "__main__":
    with get_checkpointer() as checkpointer:
        checkpointer.setup()
    print("Checkpoint tables created.")
