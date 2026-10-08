"""Exercise catalog migrations against an explicitly selected isolated local DB.

Set CREDIT_CATALOG_TEST_DATABASE_URL to the worktree launcher's local DB URL.
Every test, including function replacement and role changes, rolls back its
transaction. Shared remote databases are deliberately rejected.
"""

import importlib.util
import os
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import psycopg2
import pytest
from psycopg2.extras import Json
from src.billing.credit_catalog import CREDIT_PACKS

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def catalog_migration():
    """Load the migration without changing Alembic revision state."""
    path = (
        Path(__file__).parents[2]
        / "alembic/versions/20261007000001_four_tier_credit_product_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("four_pack_database_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def catalog_db(catalog_migration, monkeypatch):
    """Provide a transaction confined to an explicitly configured local database."""
    database_url = os.environ.get("CREDIT_CATALOG_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("CREDIT_CATALOG_TEST_DATABASE_URL is required for real SQL tests")
    if urlsplit(database_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        pytest.fail("Credit catalog SQL tests require an isolated loopback database")

    connection = psycopg2.connect(database_url, connect_timeout=5)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = '5s'")
            cursor.execute("SET LOCAL lock_timeout = '2s'")
            monkeypatch.setattr(catalog_migration.op, "execute", cursor.execute)
            catalog_migration.upgrade()
            yield cursor
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def approved_products():
    """Use unique provider fixture identifiers while preserving approved prices."""
    suffix = uuid4().hex
    return [
        {
            "name": pack["name"],
            "description": pack["description"],
            "stripe_price_id": f"price_test_{suffix}_{pack['credit_amount']}",
            "stripe_product_id": f"prod_test_{suffix}_{pack['credit_amount']}",
            "credit_amount": pack["credit_amount"],
            "price_amount": round(pack["price_usd"] * 100),
            "currency": "USD",
        }
        for pack in CREDIT_PACKS
    ]


def _sync(cursor, products):
    """Invoke the actual database RPC with a JSON payload."""
    cursor.execute(
        "SELECT public.sync_credit_product_catalog(%s::jsonb)", (Json(products),)
    )
    return cursor.fetchone()[0]


def _snapshot(cursor):
    """Capture all product fields to detect even partial catalog mutations."""
    cursor.execute("SELECT to_jsonb(p) FROM credit_products p ORDER BY id")
    return cursor.fetchall()


def _assert_rejected_without_writes(cursor, products, message):
    """Recover an expected failed statement and prove the catalog is unchanged."""
    before = _snapshot(cursor)
    cursor.execute("SAVEPOINT rejected_sync")
    with pytest.raises(psycopg2.Error, match=message):
        _sync(cursor, products)
    cursor.execute("ROLLBACK TO SAVEPOINT rejected_sync")
    assert _snapshot(cursor) == before


@pytest.mark.parametrize("invalid", [None, {}, "not an array", [], [None] * 3])
def test_catalog_rejects_non_array_and_incomplete_payloads(catalog_db, invalid):
    _assert_rejected_without_writes(catalog_db, invalid, "credit catalog must")


@pytest.mark.parametrize(
    "field,value",
    [
        ("credit_amount", 400),
        ("credit_amount", None),
        ("price_amount", 501),
        ("price_amount", None),
        ("price_amount", -500),
        ("currency", "EUR"),
        ("currency", None),
        ("name", ""),
        ("name", None),
        ("name", "n" * 101),
        ("stripe_price_id", ""),
        ("stripe_price_id", None),
        ("stripe_price_id", "p" * 256),
        ("stripe_product_id", ""),
        ("stripe_product_id", None),
        ("stripe_product_id", "p" * 256),
    ],
)
def test_catalog_rejects_invalid_pack_fields(
    catalog_db, approved_products, field, value
):
    products = deepcopy(approved_products)
    products[0][field] = value
    _assert_rejected_without_writes(catalog_db, products, "credit catalog")


@pytest.mark.parametrize(
    "field", ["credit_amount", "name", "stripe_price_id", "stripe_product_id"]
)
def test_catalog_rejects_duplicate_pack_identifiers(
    catalog_db, approved_products, field
):
    products = deepcopy(approved_products)
    products[1][field] = products[0][field]
    _assert_rejected_without_writes(catalog_db, products, "credit catalog")


def test_catalog_sync_is_complete_repeatable_and_preserves_product_ids(
    catalog_db, approved_products
):
    suffix = uuid4().hex
    catalog_db.execute(
        """INSERT INTO credit_products
           (name, stripe_price_id, stripe_product_id, credit_amount, price_amount,
            currency, is_active)
           VALUES (%s, %s, %s, 400, 1000, 'USD', true) RETURNING id""",
        (f"Retired test pack {suffix}", f"price_old_{suffix}", f"prod_old_{suffix}"),
    )
    retired_id = catalog_db.fetchone()[0]

    assert _sync(catalog_db, approved_products) == 4
    catalog_db.execute(
        "SELECT name, id, credit_amount, price_amount FROM credit_products "
        "WHERE is_active ORDER BY credit_amount"
    )
    first = catalog_db.fetchall()
    assert [(row[2], row[3]) for row in first] == [
        (200, 500),
        (500, 1200),
        (1000, 2300),
        (2000, 4400),
    ]
    assert _sync(catalog_db, list(reversed(approved_products))) == 4
    catalog_db.execute(
        "SELECT name, id, credit_amount, price_amount FROM credit_products "
        "WHERE is_active ORDER BY credit_amount"
    )
    assert catalog_db.fetchall() == first
    catalog_db.execute(
        "SELECT is_active FROM credit_products WHERE id = %s", (retired_id,)
    )
    assert catalog_db.fetchone() == (False,)


def test_upsert_conflict_rolls_back_activation_and_earlier_pack_updates(
    catalog_db, approved_products
):
    suffix = uuid4().hex
    catalog_db.execute(
        """INSERT INTO credit_products
           (name, stripe_price_id, stripe_product_id, credit_amount, price_amount,
            currency, is_active)
           VALUES (%s, %s, %s, 400, 1000, 'USD', false)""",
        (
            f"Conflicting test pack {suffix}",
            approved_products[1]["stripe_price_id"],
            f"prod_conflict_{suffix}",
        ),
    )
    _assert_rejected_without_writes(catalog_db, approved_products, "unique constraint")


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_customer_roles_cannot_switch_the_catalog(catalog_db, approved_products, role):
    before = _snapshot(catalog_db)
    catalog_db.execute("SAVEPOINT denied_sync")
    catalog_db.execute(f"SET LOCAL ROLE {role}")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        _sync(catalog_db, approved_products)
    catalog_db.execute("ROLLBACK TO SAVEPOINT denied_sync")
    assert _snapshot(catalog_db) == before


def test_service_role_can_sync_approved_catalog(catalog_db, approved_products):
    catalog_db.execute("SET LOCAL ROLE service_role")
    assert _sync(catalog_db, approved_products) == 4


def test_downgrade_restores_previous_validation_without_changing_active_rows(
    catalog_db, approved_products, catalog_migration
):
    assert _sync(catalog_db, approved_products) == 4
    before = _snapshot(catalog_db)
    catalog_migration.downgrade()
    assert _snapshot(catalog_db) == before
    _assert_rejected_without_writes(catalog_db, approved_products, "exactly 3 packs")
    previous = []
    for amount, price in catalog_migration._PREVIOUS_PACKS:
        previous.append(
            {
                "name": f"{amount} Credits Pack",
                "description": "Previous catalog",
                "credit_amount": amount,
                "price_amount": price,
                "currency": "usd",
                "stripe_price_id": f"price_previous_{amount}_{uuid4().hex}",
                "stripe_product_id": f"prod_previous_{amount}_{uuid4().hex}",
            }
        )
    assert _sync(catalog_db, previous) == 3
    catalog_db.execute(
        "SELECT credit_amount, price_amount, currency FROM credit_products "
        "WHERE is_active ORDER BY credit_amount"
    )
    assert catalog_db.fetchall() == [
        (200, 500, "USD"),
        (400, 1000, "USD"),
        (1000, 2500, "USD"),
    ]
