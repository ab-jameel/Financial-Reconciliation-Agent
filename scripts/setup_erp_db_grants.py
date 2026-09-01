# scripts/setup_erp_db_grants.py
"""Run once, using the admin/superuser connection, after init_erp_db.py.
Creates recon_erp_app: a role that does NOT own these tables, so REVOKE
actually restricts it (unlike revoking from the owner, which Postgres
ignores). No UPDATE/DELETE grant on audit_log is the whole point."""
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

ERP_APP_PASSWORD = os.environ.get("ERP_APP_DB_PASSWORD", "erp_app_dev_only")


def main():
    engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    with engine.connect() as conn:
        conn.execute(text(f"""
            DO $$
            BEGIN
               IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'recon_erp_app') THEN
                  CREATE ROLE recon_erp_app LOGIN PASSWORD '{ERP_APP_PASSWORD}';
               END IF;
            END
            $$;
        """))
        conn.execute(text("REVOKE ALL ON journal_entries, audit_log, idempotency_keys FROM PUBLIC;"))
        conn.execute(text("REVOKE ALL ON journal_entries, audit_log, idempotency_keys FROM recon_erp_app;"))
        conn.execute(text("GRANT SELECT, INSERT, UPDATE ON journal_entries TO recon_erp_app;"))
        conn.execute(text("GRANT SELECT, INSERT ON audit_log TO recon_erp_app;"))       # no UPDATE, no DELETE
        conn.execute(text("GRANT SELECT, INSERT ON idempotency_keys TO recon_erp_app;"))
        conn.execute(text("GRANT USAGE, SELECT ON audit_log_id_seq TO recon_erp_app;"))
        conn.commit()
    print("recon_erp_app configured — no UPDATE/DELETE possible on audit_log, even from the app itself.")


if __name__ == "__main__":
    main()