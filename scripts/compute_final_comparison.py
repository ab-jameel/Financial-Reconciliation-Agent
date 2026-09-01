# scripts/compute_final_comparison.py
import json
from pathlib import Path

baseline = json.loads(Path("data/generated/held_out/baseline_metrics.json").read_text())
agent = json.loads(Path("data/generated/held_out/agent_metrics.json").read_text())

baseline_manual = round(baseline["pct_manual_review"] * baseline["n_transactions"])
agent_manual = round(agent["pct_manual_review"] * agent["n_transactions"])
pct_fewer = (baseline_manual - agent_manual) / baseline_manual if baseline_manual else None

comparison = {
    "baseline": baseline, "agent": agent,
    "baseline_manual_review_count": baseline_manual,
    "agent_manual_review_count": agent_manual,
    "pct_fewer_manual_touches": pct_fewer,
}
Path("data/generated/held_out/comparison.json").write_text(json.dumps(comparison, indent=2))
print(json.dumps(comparison, indent=2))