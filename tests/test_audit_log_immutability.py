"""Verifies the ERP app role cannot UPDATE or DELETE audit-log rows."""

import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError


def test_erp_app_role_cannot_update_or_delete_audit_log():
    """Assert both UPDATE and DELETE on audit_log fail with permission denied."""
    engine = create_engine(os.environ["ERP_DATABASE_URL"].replace("+asyncpg", ""))
    with engine.connect() as conn:
        with pytest.raises(ProgrammingError, match="permission denied"):
            conn.execute(text("UPDATE audit_log SET event_type = 'tampered' WHERE id = (SELECT MIN(id) FROM audit_log)"))
        conn.rollback()
        with pytest.raises(ProgrammingError, match="permission denied"):
            conn.execute(text("DELETE FROM audit_log WHERE id = (SELECT MIN(id) FROM audit_log)"))
