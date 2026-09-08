"""Manual LangSmith tracing smoke check (run by hand, not part of CI)."""

from langsmith import traceable

@traceable(name="phase0_smoke_trace")
def ping():
    """Return a small status dict to confirm LangSmith tracing works."""
    return {"status": "ok", "phase": 0}

if __name__ == "__main__":
    print(ping())
