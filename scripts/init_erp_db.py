# scripts/init_erp_db.py — uses the SUPERUSER connection, since only the owner can CREATE TABLE
from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine
from recon_erp.db.tables import Base

if __name__ == "__main__":
    engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    Base.metadata.create_all(engine)
    print("ERP tables created.")