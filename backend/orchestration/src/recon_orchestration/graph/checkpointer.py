# backend/orchestration/src/recon_orchestration/graph/checkpointer.py
import os
from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver


def get_checkpoint_uri() -> str:
    return os.environ["POSTGRES_CHECKPOINT_URI"]


@contextmanager
def get_checkpointer():
    with PostgresSaver.from_conn_string(get_checkpoint_uri()) as checkpointer:
        yield checkpointer