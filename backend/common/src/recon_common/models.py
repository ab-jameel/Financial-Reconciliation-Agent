"""Shared domain models and enums exchanged between the orchestration and ERP services."""

from datetime import date as Date
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel


class DatasetSplit(str, Enum):
    """Partition a record belongs to: tuning, held_out, or production."""

    TUNING = "tuning"
    HELD_OUT = "held_out"
    PRODUCTION = "production"  # real, PDF-ingested transactions — never mixed into eval splits


class ExceptionType(str, Enum):
    """Ground-truth exception category used to label synthetic data and classify dispositions."""

    CLEAN_MATCH = "clean_match"
    AMOUNT_MISMATCH = "amount_mismatch"
    DATE_MISMATCH = "date_mismatch"
    DUPLICATE = "duplicate"
    CURRENCY_ISSUE = "currency_issue"
    MISSING_INVOICE = "missing_invoice"
    POLICY_SENSITIVE = "policy_sensitive"


class MatchStatus(str, Enum):
    """Outcome of the matching step: matched, exception, or manual review."""

    MATCHED = "matched"          # deterministic only — never set by ranking
    EXCEPTION = "exception"
    MANUAL_REVIEW = "manual_review"  # baseline's fallback bucket


class Transaction(BaseModel):
    """A bank transaction line to be reconciled against the ledger."""

    id: str                      # prefixed per split, e.g. "TUNE-TXN-0001"
    date: Date
    amount: Decimal
    currency: str
    reference: str
    description: str
    dataset_split: DatasetSplit
    label_exception_type: ExceptionType | None = None  # None for real (non-synthetic) transactions


class LedgerEntry(BaseModel):
    """A ledger entry that may correspond to a transaction."""

    id: str
    date: Date
    amount: Decimal
    currency: str
    reference: str
    description: str
    invoice_number: str | None = None
    dataset_split: DatasetSplit


class Invoice(BaseModel):
    """An invoice record used to verify that a ledger entry references a real invoice."""

    id: str
    invoice_number: str
    amount: Decimal
    currency: str
    due_date: Date
    dataset_split: DatasetSplit


class RankedCandidate(BaseModel):
    """A ranked ledger-entry candidate returned by the ranking layer.

    Carries no match-verdict field, so it cannot be mistaken for a match
    decision.
    """

    ledger_entry_id: str
    similarity_score: float
