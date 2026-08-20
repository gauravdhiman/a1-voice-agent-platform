"""Regression test for fresh Supabase master-data seeder privileges."""

import importlib.util
from pathlib import Path


def _load_migration_module():
    """Load the grant migration without importing the application."""
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260819000001_grant_master_data_service_role.py"
    )
    spec = importlib.util.spec_from_file_location(
        "grant_master_data_service_role", migration_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_service_role_receives_public_schema_access(monkeypatch) -> None:
    """Fresh local Supabase must expose current and future app tables."""
    migration = _load_migration_module()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    grant_sql = " ".join(" ".join(statements).upper().split())

    assert "GRANT USAGE ON SCHEMA PUBLIC TO SERVICE_ROLE" in grant_sql
    assert (
        "ALTER DEFAULT PRIVILEGES IN SCHEMA PUBLIC GRANT SELECT, INSERT, "
        "UPDATE, DELETE ON TABLES TO SERVICE_ROLE"
    ) in grant_sql
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE PUBLIC.%I" in grant_sql
    assert "PG_CATALOG.PG_TABLES" in grant_sql
    assert "GRANT USAGE, SELECT ON SEQUENCE PUBLIC.%I" in grant_sql
    assert "SEQUENCES.SEQUENCE_NAME" in grant_sql
