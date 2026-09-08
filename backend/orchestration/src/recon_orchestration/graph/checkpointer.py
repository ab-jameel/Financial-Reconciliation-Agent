"""Postgres-backed checkpoint access for durable graph state across restarts."""

import os
from contextlib import contextmanager
from langgraph.checkpoint.postgres import PostgresSaver


def get_checkpoint_uri() -> str:
    """Return the Postgres connection string used for LangGraph checkpoints."""
    return os.environ["POSTGRES_CHECKPOINT_URI"]


@contextmanager
def get_checkpointer():
    """Yield a PostgresSaver bound to the configured checkpoint connection string."""
    with PostgresSaver.from_conn_string(get_checkpoint_uri()) as checkpointer:
        yield checkpointer
