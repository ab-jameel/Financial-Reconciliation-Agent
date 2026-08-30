# backend/common/src/recon_common/models.py
from datetime import date as Date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel


class DatasetSplit(str, Enum):
    TUNING = "tuning"
    HELD_OUT = "held_out"


class ExceptionType(str, Enum):
    CLEAN_MATCH = "clean_match"
    AMOUNT_MISMATCH = "amount_mismatch"
    DATE_MISMATCH = "date_mismatch"
    DUPLICATE = "duplicate"
    CURRENCY_ISSUE = "currency_issue"
    MISSING_INVOICE = "missing_invoice"
    POLICY_SENSITIVE = "policy_sensitive"


class MatchStatus(str, Enum):
    MATCHED = "matched"          # deterministic only — never set by ranking
    EXCEPTION = "exception"
    MANUAL_REVIEW = "manual_review"  # baseline's fallback bucket


class Transaction(BaseModel):
    id: str                      # prefixed per split, e.g. "TUNE-TXN-0001"
    date: Date
    amount: Decimal
    currency: str
    reference: str
    description: str
    dataset_split: DatasetSplit
    label_exception_type: ExceptionType  # ground truth, for eval only


class LedgerEntry(BaseModel):
    id: str
    date: Date
    amount: Decimal
    currency: str
    reference: str
    description: str
    invoice_number: str | None = None
    dataset_split: DatasetSplit


class Invoice(BaseModel):
    id: str
    invoice_number: str
    amount: Decimal
    currency: str
    due_date: Date
    dataset_split: DatasetSplit


class RankedCandidate(BaseModel):
    """Output of the ranking layer. No `is_match` field, on purpose —
    this type cannot be mistaken for a match verdict."""
    ledger_entry_id: str
    similarity_score: float