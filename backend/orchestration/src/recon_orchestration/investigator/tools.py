# backend/orchestration/src/recon_orchestration/investigator/tools.py
from datetime import date as Date
from decimal import Decimal
from recon_orchestration.db.session import SessionLocal
from recon_orchestration.db.tables import TransactionRow


def compute_date_delta(date_a: Date, date_b: Date) -> int:
    return abs((date_a - date_b).days)


def compute_amount_delta(amount_a: Decimal, amount_b: Decimal) -> Decimal:
    return abs(amount_a - amount_b)


def search_related_transactions(reference: str, dataset_split: str, exclude_id: str) -> list[dict]:
    """Restricted to the SAME dataset_split as the case under investigation —
    the tuning/held-out separation from Phase 1 has to hold inside the
    investigator's tools too, not just at the top-level query layer."""
    session = SessionLocal()
    rows = (
        session.query(TransactionRow)
        .filter(TransactionRow.reference == reference)
        .filter(TransactionRow.dataset_split == dataset_split)
        .filter(TransactionRow.id != exclude_id)
        .all()
    )
    session.close()
    return [{"id": r.id, "date": r.date.isoformat(), "amount": str(r.amount), "description": r.description} for r in rows]


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "retrieve_policy", "description": "Fetch the accounting policy text in effect on the transaction's date.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Topic to search for, e.g. 'materiality threshold'"},
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "search_related_transactions", "description": "Find other transactions sharing the same reference number, within the same dataset split.",
        "parameters": {"type": "object", "properties": {
            "reference": {"type": "string"},
        }, "required": ["reference"]},
    }},
    {"type": "function", "function": {
        "name": "compute_date_delta", "description": "Absolute number of days between two dates.",
        "parameters": {"type": "object", "properties": {
            "date_a": {"type": "string"}, "date_b": {"type": "string"},
        }, "required": ["date_a", "date_b"]},
    }},
    {"type": "function", "function": {
        "name": "compute_amount_delta", "description": "Absolute difference between two amounts.",
        "parameters": {"type": "object", "properties": {
            "amount_a": {"type": "string"}, "amount_b": {"type": "string"},
        }, "required": ["amount_a", "amount_b"]},
    }},
]