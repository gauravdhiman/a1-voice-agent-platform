"""Contract tests for the call-log failure details migration."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

MIGRATION_PATH = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "20260902000001_add_call_failure_details.py"
)


def _load_migration():
    """Load the migration module without bootstrapping the application."""
    spec = importlib.util.spec_from_file_location(
        "call_failure_migration", MIGRATION_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failure_details_migration_has_one_connected_revision():
    """The new schema change attaches to the current Alembic head."""
    migration = _load_migration()

    assert migration.revision == "20260902000001"
    assert migration.down_revision == "20260901000002"


def test_failure_details_migration_adds_indexed_nullable_columns():
    """Failure metadata is additive and searchable without changing old rows."""
    migration = _load_migration()
    migration.op = MagicMock()

    migration.upgrade()

    added_columns = [
        call.args[1].name for call in migration.op.add_column.call_args_list
    ]
    assert added_columns == ["failure_code", "failure_message"]
    migration.op.create_index.assert_called_once_with(
        "ix_call_logs_failure_code", "call_logs", ["failure_code"]
    )
