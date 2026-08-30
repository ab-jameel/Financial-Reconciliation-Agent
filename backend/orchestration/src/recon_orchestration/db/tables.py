# backend/orchestration/src/recon_orchestration/db/tables.py
from sqlalchemy import Column, String, Date, Numeric, Enum as SAEnum
from sqlalchemy.orm import declarative_base
from recon_common.models import DatasetSplit, ExceptionType

Base = declarative_base()


class TransactionRow(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False)
    amount = Column(Numeric, nullable=False)
    currency = Column(String, nullable=False)
    reference = Column(String, nullable=False)
    description = Column(String, nullable=False)
    dataset_split = Column(SAEnum(DatasetSplit), nullable=False, index=True)
    label_exception_type = Column(SAEnum(ExceptionType), nullable=False)


class LedgerEntryRow(Base):
    __tablename__ = "ledger_entries"
    id = Column(String, primary_key=True)
    date = Column(Date, nullable=False)
    amount = Column(Numeric, nullable=False)
    currency = Column(String, nullable=False)
    reference = Column(String, nullable=False)
    description = Column(String, nullable=False)
    invoice_number = Column(String, nullable=True)
    dataset_split = Column(SAEnum(DatasetSplit), nullable=False, index=True)


class InvoiceRow(Base):
    __tablename__ = "invoices"
    id = Column(String, primary_key=True)
    invoice_number = Column(String, nullable=False, index=True)
    amount = Column(Numeric, nullable=False)
    currency = Column(String, nullable=False)
    due_date = Column(Date, nullable=False)
    dataset_split = Column(SAEnum(DatasetSplit), nullable=False, index=True)