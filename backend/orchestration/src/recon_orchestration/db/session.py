"""SQLAlchemy engine and session factory for the orchestration database."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_engine():
    """Return a sync SQLAlchemy engine bound to DATABASE_URL."""
    return create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", ""))

SessionLocal = sessionmaker(bind=get_engine())
