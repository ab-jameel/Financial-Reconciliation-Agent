# scripts/analyze_disposition_confusion.py
import json
from collections import defaultdict
from pathlib import Path

results = json.loads(Path("data/generated/held_out/agent_case_results.json").read_text())
exception_cases = [r for r in results if r["agent_status"] == "exception"]

confusion = defaultdict(lambda: defaultdict(int))
for r in exception_cases:
    confusion[r["label"]][r.get("predicted_disposition")] += 1

for true_label, preds in sorted(confusion.items()):
    total = sum(preds.values())
    print(f"\n{true_label} (n={total}):")
    for pred, count in sorted(preds.items(), key=lambda kv: -kv[1]):
        print(f"  -> predicted {pred!r}: {count} ({count/total:.0%})")