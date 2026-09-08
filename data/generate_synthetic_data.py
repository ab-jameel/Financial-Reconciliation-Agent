"""Generates the synthetic tuning and held-out datasets used for evaluation."""

import json
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from faker import Faker
from recon_common.models import DatasetSplit, ExceptionType

GENERATOR_VERSION = "v4"
SEED_TUNING = 20260828
SEED_HELD_OUT = 20260829  # deliberately different, never derived from the other

OUTPUT_DIR = Path(__file__).parent / "generated"

EXCEPTION_COUNTS = {
    ExceptionType.CLEAN_MATCH: 40,
    ExceptionType.AMOUNT_MISMATCH: 10,
    ExceptionType.DATE_MISMATCH: 10,
    ExceptionType.DUPLICATE: 8,
    ExceptionType.CURRENCY_ISSUE: 8,
    ExceptionType.MISSING_INVOICE: 8,
    ExceptionType.POLICY_SENSITIVE: 8,
}

def _bank_style_description(vendor: str, rng: random.Random) -> str:
    """Render a vendor name in bank-feed style, independent of exception type.

    Applies description drift (abbreviations, processor prefixes, truncation)
    unrelated to whether the amount or date also mismatches.
    """
    base = vendor
    for suffix in (" LLC", " Inc.", " Inc", " Corp.", " Corp", " Ltd", " Co"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break

    style = rng.choices(
        ["identical", "prefixed", "truncated", "acronym", "suffixed_ref"],
        weights=[20, 20, 20, 20, 20],
    )[0]
    if style == "identical":
        return base
    if style == "prefixed":
        return f"{rng.choice(['SQ *', 'TST* ', 'PAYPAL *', 'POS DEBIT '])}{base}"
    if style == "truncated":
        return base[:16].rstrip()
    if style == "acronym":
        words = [w for w in base.split() if w]
        acr = "".join(w[0].upper() for w in words if w[0].isalpha())
        tail = words[-1].upper()[:4] if words else ""
        return f"{acr} {tail}".strip()
    return f"{base} #{rng.randint(1000, 9999)}"  # suffixed_ref

def generate_split(split: DatasetSplit, seed: int, id_prefix: str):
    """Generate one split's transactions, ledger entries, and invoices.

    Applies the per-exception-type mutations to a shared base record, and
    appends a duplicate transaction for each DUPLICATE case.
    """
    rng = random.Random(seed)
    fake = Faker()
    fake.seed_instance(seed)

    transactions, ledger_entries, invoices = [], [], []
    counter = 0

    for exc_type, count in EXCEPTION_COUNTS.items():
        for _ in range(count):
            counter += 1
            txn_id = f"{id_prefix}-TXN-{counter:04d}"
            led_id = f"{id_prefix}-LED-{counter:04d}"
            inv_id = f"{id_prefix}-INV-{counter:04d}"

            base_date = date(2026, 8, 1) + timedelta(days=rng.randint(0, 27))
            base_amount = Decimal(rng.randrange(1000, 500000)) / 100
            reference = f"REF-{rng.randint(100000, 999999)}"
            currency = "USD"
            vendor = fake.company()

            txn_desc = _bank_style_description(vendor, rng)
            led_desc = vendor
            led_amount, led_date, led_currency, led_reference = (
                base_amount, base_date, currency, reference,
            )
            invoice_number = f"INV-{rng.randint(10000, 99999)}"

            if exc_type == ExceptionType.AMOUNT_MISMATCH:
                led_amount = base_amount + Decimal(rng.choice([5, -5, 12.50]))
            elif exc_type == ExceptionType.DATE_MISMATCH:
                led_date = base_date + timedelta(days=rng.choice([-3, 3, 5]))
            elif exc_type == ExceptionType.CURRENCY_ISSUE:
                led_currency = rng.choice(["EUR", "GBP"])
            elif exc_type == ExceptionType.MISSING_INVOICE:
                invoice_number = "INV-00000"  # doesn't exist in invoices table
            elif exc_type == ExceptionType.DUPLICATE:
                pass  # a duplicate transaction is appended below
            elif exc_type == ExceptionType.POLICY_SENSITIVE:
                led_amount = base_amount + Decimal("1.50")  # straddles v1's $1.00 and v2's $2.00 thresholds
                # Split these cases across the v2 effective date (2026-07-15) so
                # the same $1.50 delta is material under v1 but immaterial under v2.
                if rng.random() < 0.5:
                    base_date = date(2026, 6, 1) + timedelta(days=rng.randint(0, 30))

            transactions.append({
                "id": txn_id, "date": base_date.isoformat(), "amount": str(base_amount),
                "currency": currency, "reference": reference, "description": txn_desc,
                "dataset_split": split.value, "label_exception_type": exc_type.value,
            })
            ledger_entries.append({
                "id": led_id, "date": led_date.isoformat(), "amount": str(led_amount),
                "currency": led_currency, "reference": led_reference, "description": led_desc,
                "invoice_number": invoice_number if exc_type != ExceptionType.MISSING_INVOICE else "INV-00000",
                "dataset_split": split.value,
            })
            if exc_type != ExceptionType.MISSING_INVOICE:
                invoices.append({
                    "id": inv_id, "invoice_number": invoice_number, "amount": str(base_amount),
                    "currency": currency, "due_date": base_date.isoformat(),
                    "dataset_split": split.value,
                })

            if exc_type == ExceptionType.DUPLICATE:
                counter += 1
                dup_id = f"{id_prefix}-TXN-{counter:04d}"
                transactions.append({
                    **transactions[-1], "id": dup_id,
                })

    return transactions, ledger_entries, invoices


def write_split(split: DatasetSplit, seed: int, id_prefix: str):
    """Write one split's generated JSON files (transactions, ledger entries, invoices, manifest)."""
    out = OUTPUT_DIR / split.value
    out.mkdir(parents=True, exist_ok=True)
    txns, leds, invs = generate_split(split, seed, id_prefix)

    (out / "transactions.json").write_text(json.dumps(txns, indent=2))
    (out / "ledger_entries.json").write_text(json.dumps(leds, indent=2))
    (out / "invoices.json").write_text(json.dumps(invs, indent=2))
    (out / "manifest.json").write_text(json.dumps({
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "split": split.value,
        "counts": {k.value: v for k, v in EXCEPTION_COUNTS.items()},
    }, indent=2))
    print(f"Wrote {split.value}: {len(txns)} transactions -> {out}")


if __name__ == "__main__":
    write_split(DatasetSplit.TUNING, SEED_TUNING, "TUNE")
    write_split(DatasetSplit.HELD_OUT, SEED_HELD_OUT, "HOLD")
