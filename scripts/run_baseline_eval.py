# scripts/run_baseline_eval.py
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow, LedgerEntryRow
from recon_orchestration.matcher.baseline import match_baseline
from recon_orchestration.eval.metrics import precision_recall_f1
from recon_common.models import Transaction, LedgerEntry, MatchStatus, ExceptionType

SPLIT = sys.argv[1] if len(sys.argv) > 1 else "tuning"

def main():
    session = SessionLocal()
    txn_rows = session.query(TransactionRow).filter_by(dataset_split=SPLIT).all()
    led_rows = session.query(LedgerEntryRow).filter_by(dataset_split=SPLIT).all()
    ledgers = [LedgerEntry(**{c.name: getattr(r, c.name) for c in r.__table__.columns}) for r in led_rows]

    tp = fp = fn = manual_review_count = 0
    for row in txn_rows:
        txn = Transaction(**{c.name: getattr(row, c.name) for c in row.__table__.columns})
        status, _, _ = match_baseline(txn, ledgers)
        should_match = txn.label_exception_type == ExceptionType.CLEAN_MATCH

        if status == MatchStatus.MATCHED and should_match:
            tp += 1
        elif status == MatchStatus.MATCHED and not should_match:
            fp += 1
        elif status == MatchStatus.MANUAL_REVIEW:
            manual_review_count += 1
            if should_match:
                fn += 1

    metrics = precision_recall_f1(tp, fp, fn)
    metrics["pct_manual_review"] = manual_review_count / len(txn_rows)
    metrics["n_transactions"] = len(txn_rows)

    out_path = Path(f"data/generated/{SPLIT}/baseline_metrics.json")
    out_path.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()