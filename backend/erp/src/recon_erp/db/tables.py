"""SQLAlchemy table models for the ERP service: journal entries, audit log, and idempotency keys."""

from sqlalchemy import Column, String, Numeric, Float, Text, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class JournalEntryRow(Base):
    """A posted or reversed journal entry."""

    __tablename__ = "journal_entries"
    id = Column(String, primary_key=True)
    case_id = Column(String, nullable=False, index=True)
    entity = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    currency = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, nullable=False, default="posted")  # posted | reversed
    original_entry_id = Column(String, nullable=True)
    reversed_entry_id = Column(String, nullable=True)
    created_at = Column(Float, nullable=False)


class AuditLogRow(Base):
    """One entry in the tamper-evident audit log hash chain."""

    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)  # ordering must be reliable for the hash chain
    event_type = Column(String, nullable=False)
    case_id = Column(String, nullable=False, index=True)
    journal_entry_id = Column(String, nullable=True)
    payload = Column(Text, nullable=False)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    created_at = Column(Float, nullable=False)


class IdempotencyKeyRow(Base):
    """Records an idempotency key so a replayed request returns the same entry."""

    __tablename__ = "idempotency_keys"
    idempotency_key = Column(String, primary_key=True)
    journal_entry_id = Column(String, nullable=False)
    created_at = Column(Float, nullable=False)
