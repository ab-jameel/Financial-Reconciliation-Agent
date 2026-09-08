"""LangSmith tracing configuration and cost extraction for LLM calls."""

import litellm


def configure_litellm_tracing():
    """Route every litellm.completion call to LangSmith for tracing.

    Tracing is per-call, tagged with the case_id metadata passed at call
    time, not a single nested trace per case.
    """
    litellm.success_callback = ["langsmith"]
    litellm.failure_callback = ["langsmith"]


def extract_cost(response) -> float:
    """Return the response cost reported by litellm, or 0.0 when unavailable."""
    try:
        return float(response._hidden_params.get("response_cost") or 0.0)
    except Exception:
        return 0.0
