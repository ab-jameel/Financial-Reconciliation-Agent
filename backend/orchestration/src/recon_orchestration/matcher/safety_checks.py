"""Safety checks applied before a transaction is allowed to clear."""

def check_invoice_exists(ledger_entry: dict, valid_invoice_numbers: set[str]) -> bool:
    """Return True if the ledger entry references an invoice that exists.

    Returns False when the ledger entry carries no invoice number or the
    number is not present in the valid set.
    """
    invoice_number = ledger_entry.get("invoice_number")
    return invoice_number is not None and invoice_number in valid_invoice_numbers
