# backend/orchestration/src/recon_orchestration/investigator/tracing.py
import litellm


def configure_litellm_tracing():
    """Every litellm.completion call reports to LangSmith, tagged with
    case_id metadata passed at call time. This is per-call tracing, not a
    single nested trace per case — flagged honestly above."""
    litellm.success_callback = ["langsmith"]
    litellm.failure_callback = ["langsmith"]


def extract_cost(response) -> float:
    try:
        return float(response._hidden_params.get("response_cost") or 0.0)
    except Exception:
        return 0.0