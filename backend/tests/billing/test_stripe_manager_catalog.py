"""Stripe catalog sync only manages explicitly owned launch products."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from scripts import stripe_manager


def _approved_credit_products():
    return [
        {
            "name": pack["name"],
            "description": pack["description"],
            "stripe_price_id": f"price_{pack['credit_amount']}",
            "stripe_product_id": f"prod_{pack['credit_amount']}",
            "credit_amount": pack["credit_amount"],
            "price_amount": int(pack["price_usd"] * 100),
            "currency": "USD",
        }
        for pack in stripe_manager.CREDIT_PACKS
    ]


def _stripe_credit_prices():
    owner = stripe_manager.CREDIT_CATALOG_OWNER
    prices = []
    for pack in stripe_manager.CREDIT_PACKS:
        amount = pack["credit_amount"]
        product = SimpleNamespace(
            id=f"prod_{amount}",
            name=pack["name"],
            description=pack["description"],
            active=True,
            metadata={"catalog_owner": owner, "credit_amount": str(amount)},
        )
        prices.append(
            SimpleNamespace(
                id=f"price_{amount}",
                product=product,
                type="one_time",
                unit_amount=int(pack["price_usd"] * 100),
                currency="usd",
                metadata={"catalog_owner": owner},
            )
        )
    return prices


def test_analysis_ignores_unowned_credit_like_products():
    manager = stripe_manager.StripeManager()
    owner = stripe_manager.CREDIT_CATALOG_OWNER
    managed_product = SimpleNamespace(
        id="prod_managed",
        name="200 Credits Pack",
        description="200 credits",
        active=True,
        metadata={"catalog_owner": owner, "credit_amount": "200"},
    )
    legacy_product = SimpleNamespace(
        id="prod_other",
        name="100 Credits Pack",
        description="",
        active=True,
        metadata={"credit_amount": "100"},
    )
    prices = [
        SimpleNamespace(
            id="price_managed",
            product=managed_product,
            type="one_time",
            unit_amount=500,
            currency="usd",
            metadata={"catalog_owner": owner},
        ),
        SimpleNamespace(
            id="price_other",
            product=legacy_product,
            type="one_time",
            unit_amount=1500,
            currency="usd",
            metadata={},
        ),
    ]

    _, credit_products = manager.analyze_stripe_data(prices)

    assert [product["stripe_price_id"] for product in credit_products] == [
        "price_managed"
    ]
    assert manager._credit_amount_from_product(legacy_product) is None


def test_analysis_ignores_managed_credit_price_outside_approved_catalog():
    manager = stripe_manager.StripeManager()
    product = SimpleNamespace(
        id="prod_managed",
        name="200 Credits Pack",
        description="200 credits",
        active=True,
        metadata={
            "catalog_owner": stripe_manager.CREDIT_CATALOG_OWNER,
            "credit_amount": "200",
        },
    )
    price = SimpleNamespace(
        id="price_wrong_amount",
        product=product,
        type="one_time",
        unit_amount=1500,
        currency="usd",
        metadata={"catalog_owner": stripe_manager.CREDIT_CATALOG_OWNER},
    )

    _, credit_products = manager.analyze_stripe_data([price])

    assert credit_products == []


def test_credit_event_seed_preserves_platform_admin_rates(monkeypatch):
    manager = stripe_manager.StripeManager()
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.insert.return_value = query
    query.execute.side_effect = [
        MagicMock(data=[{"id": "event-1", "credit_cost": 13}]),
        *[MagicMock(data=[]) for _ in range(8)],
    ]

    client = MagicMock()
    client.table.return_value = query
    monkeypatch.setattr(
        stripe_manager, "supabase_config", SimpleNamespace(client=client)
    )

    manager.seed_credit_events()

    query.update.assert_not_called()
    assert query.insert.call_count == 4


def test_credit_product_seed_rejects_an_incomplete_catalog_without_db_access(
    monkeypatch,
):
    manager = stripe_manager.StripeManager()
    client = MagicMock()
    monkeypatch.setattr(
        stripe_manager, "supabase_config", SimpleNamespace(client=client)
    )

    assert (
        manager.seed_credit_products(
            [{"name": "Only one pack", "credit_amount": 200}], dry_run=False
        )
        is False
    )
    client.table.assert_not_called()


def test_credit_product_seed_switches_complete_catalog_with_one_atomic_rpc(
    monkeypatch,
):
    manager = stripe_manager.StripeManager()
    client = MagicMock()
    client.rpc.return_value.execute.return_value = MagicMock(data=3)
    monkeypatch.setattr(
        stripe_manager,
        "supabase_config",
        SimpleNamespace(client=client, service_client=client),
    )
    products = _approved_credit_products()

    assert manager.seed_credit_products(products) is True

    client.rpc.assert_called_once_with(
        "sync_credit_product_catalog", {"p_products": products}
    )
    client.table.assert_not_called()


def test_credit_product_seed_failure_does_not_leave_partial_pack_writes(
    monkeypatch,
):
    manager = stripe_manager.StripeManager()
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError(
        "injected failure after processing the first pack"
    )
    monkeypatch.setattr(
        stripe_manager,
        "supabase_config",
        SimpleNamespace(client=client, service_client=client),
    )
    products = _approved_credit_products()

    assert manager.seed_credit_products(products) is False

    client.rpc.assert_called_once_with(
        "sync_credit_product_catalog", {"p_products": products}
    )
    client.table.assert_not_called()


def test_credit_product_seed_rejects_wrong_price_before_database_access(
    monkeypatch,
):
    manager = stripe_manager.StripeManager()
    client = MagicMock()
    monkeypatch.setattr(
        stripe_manager,
        "supabase_config",
        SimpleNamespace(client=client, service_client=client),
    )
    products = _approved_credit_products()
    products[0]["price_amount"] = 1500

    assert manager.seed_credit_products(products) is False

    client.rpc.assert_not_called()
    client.table.assert_not_called()


def test_seed_database_rejects_empty_credit_catalog_even_with_plans(monkeypatch):
    manager = stripe_manager.StripeManager()
    monkeypatch.setattr(manager, "fetch_all_stripe_prices", lambda: [object()])
    monkeypatch.setattr(
        manager,
        "analyze_stripe_data",
        lambda _prices, verbose=False, include_subscriptions=True: (
            [{"name": "Starter"}], []
        ),
    )
    monkeypatch.setattr(manager, "seed_subscription_plans", MagicMock())

    assert manager.seed_database() is False
    manager.seed_subscription_plans.assert_not_called()


def test_seed_database_only_syncs_credit_catalog_by_default(monkeypatch):
    manager = stripe_manager.StripeManager()
    products = _approved_credit_products()
    monkeypatch.setattr(manager, "fetch_all_stripe_prices", lambda: [object()])
    monkeypatch.setattr(
        manager,
        "analyze_stripe_data",
        lambda _prices, verbose=False, include_subscriptions=True: (
            [{"name": "Legacy Starter"}], products
        ),
    )
    monkeypatch.setattr(
        manager, "check_tables_exist", MagicMock(return_value=True)
    )
    monkeypatch.setattr(manager, "seed_subscription_plans", MagicMock())
    monkeypatch.setattr(manager, "seed_credit_events", MagicMock())
    seed_products = MagicMock(return_value=True)
    monkeypatch.setattr(manager, "seed_credit_products", seed_products)

    assert manager.seed_database() is True

    manager.check_tables_exist.assert_called_once_with(["credit_products"])
    manager.seed_subscription_plans.assert_not_called()
    manager.seed_credit_events.assert_not_called()
    seed_products.assert_called_once_with(products, False)


def test_seed_database_rejects_combining_legacy_and_credit_pack_import(monkeypatch):
    manager = stripe_manager.StripeManager()
    plans = [{"name": "Legacy Starter"}]
    products = _approved_credit_products()
    monkeypatch.setattr(manager, "fetch_all_stripe_prices", lambda: [object()])
    monkeypatch.setattr(
        manager,
        "analyze_stripe_data",
        lambda _prices, verbose=False, include_subscriptions=True: (plans, products),
    )
    monkeypatch.setattr(
        manager, "check_tables_exist", MagicMock(return_value=True)
    )
    seed_plans = MagicMock()
    seed_events = MagicMock()
    seed_products = MagicMock(return_value=True)
    monkeypatch.setattr(manager, "seed_subscription_plans", seed_plans)
    monkeypatch.setattr(manager, "seed_credit_events", seed_events)
    monkeypatch.setattr(manager, "seed_credit_products", seed_products)

    assert manager.seed_database(include_legacy_billing_data=True) is False

    manager.check_tables_exist.assert_not_called()
    seed_plans.assert_not_called()
    seed_events.assert_not_called()
    seed_products.assert_not_called()


def test_seed_parser_requires_explicit_opt_in_for_legacy_data():
    default_args = stripe_manager.create_parser().parse_args(["seed"])
    legacy_args = stripe_manager.create_parser().parse_args(
        ["seed", "--include-legacy-billing-data", "--skip-credit-products"]
    )

    assert default_args.include_legacy_billing_data is False
    assert legacy_args.include_legacy_billing_data is True
    assert legacy_args.skip_credit_products is True


def test_default_seed_ignores_malformed_legacy_subscription_metadata(monkeypatch):
    manager = stripe_manager.StripeManager()
    malformed_legacy_product = SimpleNamespace(
        id="prod_stale_legacy",
        name="Stale subscription",
        description="",
        active=True,
        metadata={
            "included_credits": "not-an-integer",
            "max_users": "also-not-an-integer",
            "features": "not-json",
            "trial_period_days": "not-an-integer",
        },
    )
    malformed_legacy_price = SimpleNamespace(
        id="price_stale_legacy",
        product=malformed_legacy_product,
        type="recurring",
        unit_amount=2900,
        currency="usd",
        recurring=SimpleNamespace(interval="month", interval_count=1),
        metadata={},
    )
    prices = [malformed_legacy_price, *_stripe_credit_prices()]
    products = _approved_credit_products()
    monkeypatch.setattr(manager, "fetch_all_stripe_prices", lambda: prices)
    monkeypatch.setattr(
        manager, "check_tables_exist", MagicMock(return_value=True)
    )
    monkeypatch.setattr(manager, "seed_subscription_plans", MagicMock())
    monkeypatch.setattr(manager, "seed_credit_events", MagicMock())
    seed_products = MagicMock(return_value=True)
    monkeypatch.setattr(manager, "seed_credit_products", seed_products)

    assert manager.seed_database() is True

    manager.check_tables_exist.assert_called_once_with(["credit_products"])
    manager.seed_subscription_plans.assert_not_called()
    manager.seed_credit_events.assert_not_called()
    seed_products.assert_called_once_with(products, False)


def test_legacy_backfill_can_run_before_plan_version_migration(monkeypatch):
    manager = stripe_manager.StripeManager()
    plans = [{"name": "Legacy Starter"}]
    monkeypatch.setattr(manager, "fetch_all_stripe_prices", lambda: [object()])
    monkeypatch.setattr(
        manager,
        "analyze_stripe_data",
        lambda _prices, verbose=False, include_subscriptions=True: (plans, []),
    )
    monkeypatch.setattr(
        manager, "check_tables_exist", MagicMock(return_value=True)
    )
    seed_plans = MagicMock()
    seed_events = MagicMock()
    seed_products = MagicMock(return_value=True)
    monkeypatch.setattr(manager, "seed_subscription_plans", seed_plans)
    monkeypatch.setattr(manager, "seed_credit_events", seed_events)
    monkeypatch.setattr(manager, "seed_credit_products", seed_products)

    assert (
        manager.seed_database(
            include_legacy_billing_data=True, include_credit_products=False
        )
        is True
    )

    manager.check_tables_exist.assert_called_once_with(["subscription_plans"])
    seed_plans.assert_called_once_with(plans, False)
    seed_events.assert_not_called()
    seed_products.assert_not_called()


def test_legacy_backfill_fails_if_any_subscription_plan_cannot_be_imported(
    monkeypatch,
):
    manager = stripe_manager.StripeManager()
    monkeypatch.setattr(manager, "fetch_all_stripe_prices", lambda: [object()])
    monkeypatch.setattr(
        manager,
        "analyze_stripe_data",
        lambda _prices, verbose=False, include_subscriptions=True: (
            [{"name": "Legacy Starter"}],
            [],
        ),
    )
    monkeypatch.setattr(
        manager, "check_tables_exist", MagicMock(return_value=True)
    )
    seed_plans = MagicMock(return_value=False)
    seed_products = MagicMock(return_value=True)
    monkeypatch.setattr(manager, "seed_subscription_plans", seed_plans)
    monkeypatch.setattr(manager, "seed_credit_products", seed_products)

    assert (
        manager.seed_database(
            include_legacy_billing_data=True, include_credit_products=False
        )
        is False
    )

    seed_plans.assert_called_once_with([{"name": "Legacy Starter"}], False)
    seed_products.assert_not_called()


def test_setup_credit_products_does_not_clean_up_when_pack_reconciliation_fails(
    monkeypatch,
):
    manager = stripe_manager.StripeManager()
    old_product = SimpleNamespace(
        id="prod_old_pack",
        name="Old 100 Credits Pack",
        metadata={
            "catalog_owner": stripe_manager.CREDIT_CATALOG_OWNER,
            "credit_amount": "100",
        },
    )
    product_api = MagicMock()
    product_api.list.return_value = SimpleNamespace(data=[old_product], has_more=False)
    product_api.create.side_effect = [
        SimpleNamespace(id=f"prod_new_{pack['credit_amount']}")
        for pack in stripe_manager.CREDIT_PACKS
    ]
    price_api = MagicMock()
    price_api.list.side_effect = RuntimeError("price service unavailable")
    monkeypatch.setattr(
        manager,
        "stripe",
        SimpleNamespace(Product=product_api, Price=price_api),
    )

    assert manager.setup_credit_products() is False
    product_api.modify.assert_not_called()
    price_api.modify.assert_not_called()


def test_setup_credit_products_creates_launch_products_and_prices(monkeypatch):
    manager = stripe_manager.StripeManager()
    product_api = MagicMock()
    product_api.list.return_value = SimpleNamespace(data=[], has_more=False)
    product_api.create.side_effect = [
        SimpleNamespace(id=f"prod_{pack['credit_amount']}")
        for pack in stripe_manager.CREDIT_PACKS
    ]
    price_api = MagicMock()
    price_api.list.return_value = SimpleNamespace(data=[])
    price_api.create.side_effect = [
        SimpleNamespace(id=f"price_{pack['credit_amount']}")
        for pack in stripe_manager.CREDIT_PACKS
    ]
    monkeypatch.setattr(
        manager,
        "stripe",
        SimpleNamespace(Product=product_api, Price=price_api),
    )

    assert manager.setup_credit_products() is True

    assert product_api.create.call_count == len(stripe_manager.CREDIT_PACKS)
    assert price_api.create.call_count == len(stripe_manager.CREDIT_PACKS)
    assert [call.kwargs["unit_amount"] for call in price_api.create.call_args_list] == [
        int(pack["price_usd"] * 100) for pack in stripe_manager.CREDIT_PACKS
    ]
    price_api.modify.assert_not_called()
