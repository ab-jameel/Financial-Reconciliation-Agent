"""Evaluates the agent on the held-out split and writes metrics to disk."""

import asyncio, json, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from recon_orchestration.db.session import SessionLocal
from recon_orchestration.matcher.reconcile import reconcile
from recon_orchestration.db.tables import TransactionRow, LedgerEntryRow, InvoiceRow
from recon_orchestration.matcher.deterministic import match_deterministic
from recon_orchestration.investigator.loop import investigate
from recon_orchestration.investigator.tracing import configure_litellm_tracing
from recon_orchestration.eval.metrics import precision_recall_f1
from recon_common.models import Transaction, LedgerEntry, MatchStatus, ExceptionType

SPLIT = "held_out"  # hardcoded — this script must never touch tuning
configure_litellm_tracing()


async def main():
    """Run the matcher and investigator over the held-out split and write metrics."""
    session = SessionLocal()
    txn_rows = session.query(TransactionRow).filter_by(dataset_split=SPLIT).order_by(TransactionRow.id).all()
    led_rows = session.query(LedgerEntryRow).filter_by(dataset_split=SPLIT).all()
    ledgers = [LedgerEntry(**{c.name: getattr(r, c.name) for c in r.__table__.columns}) for r in led_rows]
    valid_invoices = {r[0] for r in session.query(InvoiceRow.invoice_number).filter_by(dataset_split=SPLIT).all()}

    claimed_ids: set[str] = set()
    def _claim(ledger_entry_id: str) -> bool:
        if ledger_entry_id in claimed_ids:
            return False
        claimed_ids.add(ledger_entry_id)
        return True

    tp = fp = fn = manual_review_count = 0
    disposition_correct = disposition_total = 0
    total_cost = total_latency = 0.0
    n_investigated = 0
    results = []

    for row in txn_rows:
        txn = Transaction(**{c.name: getattr(row, c.name) for c in row.__table__.columns})
        should_match = txn.label_exception_type == ExceptionType.CLEAN_MATCH
        status, matched = reconcile(txn, ledgers, load_valid_invoices_fn=lambda: valid_invoices, claim_fn=_claim)

        if status == MatchStatus.MATCHED:
            if should_match:
                tp += 1
            else:
                fp += 1  # not expected by construction, but not assumed
            results.append({"id": txn.id, "label": txn.label_exception_type.value, "agent_status": "matched"})
            continue

        # The exception path always requires manual review regardless of confidence.
        manual_review_count += 1
        if should_match:
            fn += 1

        start = time.perf_counter()
        disposition = await investigate(
            txn.model_dump(mode="json"),
            [le.model_dump(mode="json") for le in ledgers],
            None,
        )
        elapsed = time.perf_counter() - start
        total_latency += elapsed
        total_cost += disposition.get("_llm_cost_usd", 0.0)
        n_investigated += 1

        disposition_total += 1
        if disposition.get("disposition") == txn.label_exception_type.value:
            disposition_correct += 1

        results.append({
            "id": txn.id, "label": txn.label_exception_type.value, "agent_status": "exception",
            "predicted_disposition": disposition.get("disposition"),
            "confidence": disposition.get("confidence"),
            "latency_s": elapsed, "cost_usd": disposition.get("_llm_cost_usd", 0.0),
        })

    session.close()

    metrics = precision_recall_f1(tp, fp, fn)
    metrics["pct_manual_review"] = manual_review_count / len(txn_rows)
    metrics["n_transactions"] = len(txn_rows)
    metrics["correct_disposition_rate"] = (disposition_correct / disposition_total) if disposition_total else None
    metrics["avg_cost_per_transaction_usd"] = total_cost / len(txn_rows)
    metrics["avg_latency_per_investigated_case_s"] = (total_latency / n_investigated) if n_investigated else None

    out_dir = Path("data/generated/held_out")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agent_metrics.json").write_text(json.dumps(metrics, indent=2))
    (out_dir / "agent_case_results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
