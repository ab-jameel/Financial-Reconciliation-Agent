"""One-time schema migration adding PRODUCTION support. Safe to rerun."""

from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
with engine.connect() as conn:
    conn.execute(text("COMMIT"))  # ALTER TYPE ... ADD VALUE can't run inside an open transaction
    conn.execute(text("ALTER TYPE datasetsplit ADD VALUE IF NOT EXISTS 'PRODUCTION'"))
    conn.execute(text("ALTER TABLE transactions ALTER COLUMN label_exception_type DROP NOT NULL"))
    conn.commit()
print("Migration applied.")
