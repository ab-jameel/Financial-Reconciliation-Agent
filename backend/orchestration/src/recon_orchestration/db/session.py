# backend/orchestration/src/recon_orchestration/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_engine():
    return create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    # sync engine for scripts/tests; the graph will use the async URL directly in Phase 2

SessionLocal = sessionmaker(bind=get_engine())