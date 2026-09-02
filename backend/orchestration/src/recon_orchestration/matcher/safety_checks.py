# backend/orchestration/src/recon_orchestration/matcher/safety_checks.py
def check_invoice_exists(ledger_entry: dict, valid_invoice_numbers: set[str]) -> bool:
    invoice_number = ledger_entry.get("invoice_number")
    return invoice_number is not None and invoice_number in valid_invoice_numbers