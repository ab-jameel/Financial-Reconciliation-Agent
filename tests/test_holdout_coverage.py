# tests/test_holdout_coverage.py
import json
from pathlib import Path

def test_held_out_covers_all_exception_categories():
    manifest = json.loads(Path("data/generated/held_out/manifest.json").read_text())
    counts = manifest["counts"]
    expected = {"clean_match", "amount_mismatch", "date_mismatch", "duplicate",
                "currency_issue", "missing_invoice", "policy_sensitive"}
    assert set(counts.keys()) == expected
    assert all(v > 0 for v in counts.values()), f"Held-out set has a zero-count category: {counts}"