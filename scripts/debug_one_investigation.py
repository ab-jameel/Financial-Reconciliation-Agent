# scripts/debug_one_investigation.py
"""Runs the investigator on exactly ONE real held-out transaction and prints
every LLM call's tool_calls and content directly -- bypasses LangSmith UI
navigation entirely, so there's no ambiguity about which trace we're
looking at."""
import asyncio, json
from dotenv import load_dotenv
load_dotenv()

from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow, LedgerEntryRow
from recon_common.models import Transaction, LedgerEntry

SPLIT = "held_out"
TARGET_LABEL = "amount_mismatch"  # change to inspect a different category


async def main():
    session = SessionLocal()
    row = (session.query(TransactionRow)
           .filter_by(dataset_split=SPLIT, label_exception_type=TARGET_LABEL)
           .order_by(TransactionRow.id).first())
    txn = Transaction(**{c.name: getattr(row, c.name) for c in row.__table__.columns})
    led_rows = session.query(LedgerEntryRow).filter_by(dataset_split=SPLIT).all()
    ledgers = [LedgerEntry(**{c.name: getattr(r, c.name) for c in r.__table__.columns}) for r in led_rows]
    session.close()

    print(f"Investigating {txn.id} (true label: {txn.label_exception_type.value})\n")

    import litellm
    original_completion = litellm.completion
    call_num = 0

    def traced_completion(*args, **kwargs):
        nonlocal call_num
        call_num += 1
        response = original_completion(*args, **kwargs)
        msg = response.choices[0].message
        print(f"--- LLM call #{call_num} ---")
        print("tool_calls:", getattr(msg, "tool_calls", None))
        print("content:", msg.content)
        print()
        return response

    litellm.completion = traced_completion  # module-level patch — loop.py calls litellm.completion(...) dynamically, so this is picked up without touching loop.py itself

    from recon_orchestration.investigator.loop import investigate
    result = await investigate(txn.model_dump(mode="json"), [l.model_dump(mode="json") for l in ledgers], None)

    print("=== FINAL RESULT ===")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())