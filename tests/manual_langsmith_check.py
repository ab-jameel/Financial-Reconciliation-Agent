# tests/manual_langsmith_check.py — run once by hand, not part of CI
from langsmith import traceable

@traceable(name="phase0_smoke_trace")
def ping():
    return {"status": "ok", "phase": 0}

if __name__ == "__main__":
    print(ping())