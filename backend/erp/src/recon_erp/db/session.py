# backend/erp/src/recon_erp/db/session.py — deliberately uses ERP_DATABASE_URL,
# the least-privileged runtime role, NEVER the superuser DATABASE_URL
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_engine():
    return create_engine(os.environ["ERP_DATABASE_URL"].replace("+asyncpg", ""))

SessionLocal = sessionmaker(bind=get_engine())