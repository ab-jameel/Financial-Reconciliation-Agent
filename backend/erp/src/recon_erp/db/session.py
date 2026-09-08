"""SQLAlchemy engine and session factory for the ERP database.

Binds to ERP_DATABASE_URL, the least-privileged runtime role, never the
superuser connection.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_engine():
    """Return a sync SQLAlchemy engine for the ERP database."""
    return create_engine(os.environ["ERP_DATABASE_URL"].replace("+asyncpg", ""))

SessionLocal = sessionmaker(bind=get_engine())
