#!/usr/bin/env python3
"""
Consolidated Stripe Management Script

This script combines functionality from multiple Stripe-related scripts into
a single, easy-to-use tool with intelligent detection capabilities.

For detailed documentation, see: docs/STRIPE_SETUP_AND_MANAGEMENT.md

Usage:
    python scripts/stripe_manager.py --help
    python scripts/stripe_manager.py diagnostic
    python scripts/stripe_manager.py cleanup --dry-run
    python scripts/stripe_manager.py setup-credits --dry-run
    python scripts/stripe_manager.py seed --dry-run
    python scripts/stripe_manager.py seed
    python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add repo root so ``shared.config`` resolves when run from the host (outside Docker).
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import stripe

from shared.config.settings import settings
from shared.config.supabase import supabase_config
from src.billing.credit_catalog import CREDIT_PACKS

if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key

CREDIT_CATALOG_OWNER = "24x7-ai-credit-catalog-v1"


class StripeManager:
    """Consolidated Stripe management functionality."""

    def __init__(self):
        self.stripe = stripe

    def diagnostic(self):
        """Comprehensive inspection of Stripe account."""
        print("🔍 STRIPE ACCOUNT DIAGNOSTIC")
        print("=" * 50)

        # 1. Fetch ALL products
        print("\n📦 ALL PRODUCTS:")
        print("-" * 30)

        try:
            products = self.stripe.Product.list(limit=100, active=True)
            print(f"Found {len(products.data)} active products:")

            for i, product in enumerate(products.data, 1):
                print(f"\n{i}. Product: {product.name}")
                print(f"   ID: {product.id}")
                print(f"   Type: {product.type if hasattr(product, 'type') else 'N/A'}")
                print(f"   Active: {product.active}")
                print(f"   Description: {product.description or 'No description'}")
                if product.metadata:
                    print(f"   Metadata: {dict(product.metadata)}")
                else:
                    print(f"   Metadata: None")

        except Exception as e:
            print(f"❌ Error fetching products: {e}")
            return

        # 2. Fetch ALL prices
        print(f"\n💰 ALL PRICES:")
        print("-" * 30)

        try:
            prices = self.stripe.Price.list(
                limit=100, active=True, expand=["data.product"]
            )
            print(f"Found {len(prices.data)} active prices:")

            recurring_count = 0
            one_time_count = 0

            for i, price in enumerate(prices.data, 1):
                print(f"\n{i}. Price: {price.id}")
                print(f"   Product: {price.product.name}")
                print(
                    f"   Amount: ${price.unit_amount / 100:.2f} {price.currency.upper()}"
                )
                print(f"   Type: {price.type}")

                if price.type == "recurring":
                    recurring_count += 1
                    print(f"   Billing: {price.recurring.interval}")
                    if price.recurring.interval_count > 1:
                        print(f"   Interval Count: {price.recurring.interval_count}")
                else:
                    one_time_count += 1

                # Check product metadata for special fields
                product_metadata = price.product.metadata or {}
                if product_metadata:
                    print(f"   Product Metadata: {dict(product_metadata)}")

                    # Check for subscription-related metadata
                    if any(
                        key in product_metadata
                        for key in ["included_credits", "max_users", "features"]
                    ):
                        print(f"   ✅ Has subscription metadata")

                    # Check for credit-related metadata
                    if "credit_amount" in product_metadata:
                        managed = (
                            product_metadata.get("catalog_owner")
                            == CREDIT_CATALOG_OWNER
                        )
                        print(
                            f"   {'✅ Managed' if managed else 'ℹ️  Unmanaged'} credit product "
                            f"(credit_amount: {product_metadata['credit_amount']})"
                        )
                else:
                    print(f"   ⚠️  No metadata")

            print(f"\nSUMMARY:")
            print(f"- Recurring prices (subscriptions): {recurring_count}")
            print(f"- One-time prices: {one_time_count}")

        except Exception as e:
            print(f"❌ Error fetching prices: {e}")
            return

        # 3. Recommendations
        self._show_recommendations()

    def _show_recommendations(self):
        """Show setup recommendations."""
        print(f"\n💡 STRIPE SETUP RECOMMENDATIONS:")
        print("=" * 50)

        print(
            """
🎯 FOR SUBSCRIPTION PLANS:
- Create Products for each plan tier (Starter, Pro, Enterprise)
- Create Prices for each billing interval (monthly, yearly)
- Add metadata to Products:
  * included_credits: "1000" (number of credits included)
  * max_users: "5" (maximum users allowed)
  * features: '{"api_access": true, "priority_support": false}'
  * trial_period_days: "14" (optional free trial)

💳 FOR CREDIT PRODUCTS (Pay-as-you-go):
- Run setup-credits to create the approved credit bundles
- Managed Products and one-time Prices use catalog_owner: "24x7-ai-credit-catalog-v1"
- The Product carries credit_amount; unmarked Stripe products are left untouched

📝 Example Product Metadata for "Pro Plan":
{
  "included_credits": "5000",
  "max_users": "25",
  "features": "{\\"api_access\\": true, \\"priority_support\\": true, \\"analytics\\": true}",
  "trial_period_days": "14"
}
        """
        )

    def cleanup_old_products(self, dry_run=False):
        """Deactivate only owned legacy aggregate credit products."""
        print("🧹 Cleaning up old 'All Credit Packages' products...")

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made to Stripe")

        try:
            products = self.stripe.Product.list(limit=100, active=True)
            old_products = [
                product
                for product in products.data
                if product.name == "All Credit Packages"
                and (product.metadata or {}).get("catalog_owner")
                == CREDIT_CATALOG_OWNER
            ]

            if not old_products:
                print("✅ No old 'All Credit Packages' products found")
                return

            print(f"Found {len(old_products)} old 'All Credit Packages' products")

            for i, product in enumerate(old_products, 1):
                print(f"\n{i}. Product: {product.name} ({product.id})")

                # Get prices for this product
                prices = self.stripe.Price.list(product=product.id, active=True)
                unmanaged_price_found = False
                print(f"   Has {len(prices.data)} active prices:")

                for price in prices.data:
                    print(f"     - ${price.unit_amount / 100:.2f} ({price.id})")
                    if (price.metadata or {}).get(
                        "catalog_owner"
                    ) != CREDIT_CATALOG_OWNER:
                        unmanaged_price_found = True
                        continue

                    if not dry_run:
                        # Deactivate price
                        self.stripe.Price.modify(price.id, active=False)
                        print(f"       ✅ Deactivated price")
                    else:
                        print(f"       [DRY RUN] Would deactivate price")

                if not dry_run and not unmanaged_price_found:
                    # Deactivate product
                    self.stripe.Product.modify(product.id, active=False)
                    print(f"   ✅ Deactivated product")
                elif not dry_run:
                    print(
                        "   ⚠️  Leaving product active because it has an unmanaged price"
                    )
                elif not unmanaged_price_found:
                    print(f"   [DRY RUN] Would deactivate product")
                else:
                    print(
                        "   [DRY RUN] Would leave product active because of an unmanaged price"
                    )

            if dry_run:
                print(f"\n🔍 DRY RUN COMPLETED")
                print("Only marked products and prices above are eligible for cleanup")
            else:
                print(f"\n✅ CLEANUP COMPLETED")
                print(f"Deactivated {len(old_products)} old products")

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    def setup_credit_products(self, dry_run=False):
        """Reconcile active Stripe credit products with the launch catalog."""
        credit_packs = [dict(pack) for pack in CREDIT_PACKS]

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made to Stripe")

        print("🏗️  Reconciling individual credit products in Stripe...")
        print("=" * 50)

        try:
            products = []
            starting_after = None
            while True:
                params = {"active": True, "limit": 100}
                if starting_after:
                    params["starting_after"] = starting_after
                page = self.stripe.Product.list(**params)
                products.extend(page.data)
                if not page.has_more:
                    break
                starting_after = page.data[-1].id
        except Exception as exc:
            print(f"❌ Could not read active Stripe products: {exc}")
            return False

        credit_products = [
            product
            for product in products
            if self._credit_amount_from_product(product) is not None
        ]
        reconciliation_errors: list[str] = []
        claimed_product_ids: set[str] = set()

        for pack in credit_packs:
            try:
                candidates = [
                    product
                    for product in credit_products
                    if self._credit_amount_from_product(product)
                    == pack["credit_amount"]
                    and product.id not in claimed_product_ids
                ]
                product = next(
                    (item for item in candidates if item.name == pack["name"]),
                    candidates[0] if candidates else None,
                )
                price_cents = int(pack["price_usd"] * 100)
                action = "reuse" if product else "create"
                print(
                    f"\n📦 {'[DRY RUN] Would' if dry_run else 'Will'} {action} "
                    f"{pack['name']}: {pack['credit_amount']} credits for "
                    f"${pack['price_usd']:.2f}"
                )

                if product is None:
                    if dry_run:
                        continue
                    product = self.stripe.Product.create(
                        name=pack["name"],
                        description=pack["description"],
                        metadata={
                            "catalog_owner": CREDIT_CATALOG_OWNER,
                            "credit_amount": str(pack["credit_amount"]),
                        },
                    )
                elif not dry_run:
                    self.stripe.Product.modify(
                        product.id,
                        name=pack["name"],
                        description=pack["description"],
                        metadata={
                            "catalog_owner": CREDIT_CATALOG_OWNER,
                            "credit_amount": str(pack["credit_amount"]),
                        },
                    )
                claimed_product_ids.add(str(product.id))
                active_prices = self.stripe.Price.list(
                    product=product.id, active=True, limit=100
                ).data
                matching_prices = [
                    price
                    for price in active_prices
                    if price.type == "one_time"
                    and price.currency.lower() == "usd"
                    and price.unit_amount == price_cents
                    and (price.metadata or {}).get("catalog_owner")
                    == CREDIT_CATALOG_OWNER
                ]
                keep_price = matching_prices[0] if matching_prices else None
                if keep_price:
                    print(f"   Active launch price: {keep_price.id}")
                elif dry_run:
                    print("   [DRY RUN] Would create the matching one-time USD price")
                else:
                    new_price = self.stripe.Price.create(
                        product=product.id,
                        unit_amount=price_cents,
                        currency="usd",
                        metadata={
                            "catalog_owner": CREDIT_CATALOG_OWNER,
                            "credit_amount": str(pack["credit_amount"]),
                        },
                    )
                    print(f"   ✅ Created price: {new_price.id}")

            except Exception as e:
                print(f"   ❌ Could not reconcile {pack['name']}: {e}")
                reconciliation_errors.append(pack["name"])

        if reconciliation_errors:
            print(
                "\n❌ Credit catalog reconciliation was incomplete; "
                "retired products were left unchanged."
            )
            return False

        print("\n✅ Credit products prepared in Stripe")
        print("\n💡 Next steps:")
        print("1. Review the Stripe products and prices")
        print("2. Run: python scripts/stripe_manager.py seed --dry-run")
        print("3. Run seed to atomically switch the active database catalog")
        print(
            "   Existing Stripe Prices stay active; the billing UI exposes only "
            "the approved active database catalog"
        )
        return True

    @staticmethod
    def _credit_amount_from_product(product):
        """Identify only products explicitly owned by this credit catalog."""
        metadata = product.metadata or {}
        if metadata.get("catalog_owner") != CREDIT_CATALOG_OWNER:
            return None
        try:
            amount = int(metadata.get("credit_amount", ""))
        except (TypeError, ValueError):
            amount = 0
        return amount if amount > 0 else None

    def fetch_all_stripe_prices(self):
        """Fetch ALL prices from Stripe with pagination."""
        print("🔍 Fetching all prices from Stripe (with pagination)...")

        all_prices = []
        starting_after = None

        try:
            while True:
                # Fetch prices in batches of 100
                params = {"limit": 100, "active": True, "expand": ["data.product"]}
                if starting_after:
                    params["starting_after"] = starting_after

                prices = self.stripe.Price.list(**params)
                all_prices.extend(prices.data)

                if not prices.has_more:
                    break

                starting_after = prices.data[-1].id
                print(f"  Fetched {len(prices.data)} prices, continuing...")

            print(f"✓ Found {len(all_prices)} total prices in Stripe")
            return all_prices

        except stripe.error.StripeError as e:
            print(f"❌ Stripe API error: {e}")
            return []
        except Exception as e:
            print(f"❌ Error fetching prices: {e}")
            return []

    def analyze_stripe_data(
        self, prices, verbose=False, include_subscriptions=True
    ):
        """Analyze Stripe data and categorize products with intelligent detection."""
        print("🔍 Analyzing Stripe data with intelligent detection...")

        subscription_plans = []
        credit_products = []
        uncategorized = []

        for price in prices:
            if not price.product.active:
                continue

            product = price.product
            metadata = product.metadata or {}

            if verbose:
                print(f"\nAnalyzing: {product.name} ({price.type})")
                print(
                    f"  Price: ${price.unit_amount / 100:.2f} {price.currency.upper()}"
                )
                if price.type == "recurring":
                    print(f"  Billing: {price.recurring.interval}")
                print(f"  Metadata: {dict(metadata) if metadata else 'None'}")

            if price.type == "recurring":
                if not include_subscriptions:
                    if verbose:
                        print(
                            f"  Skipping legacy subscription price {price.id}; "
                            "legacy billing import is disabled"
                        )
                    continue

                # This is a subscription plan
                plan_data = {
                    "name": product.name,
                    "description": product.description or "",
                    "stripe_price_id": price.id,
                    "stripe_product_id": product.id,
                    "price_amount": price.unit_amount,
                    "currency": price.currency.upper(),
                    "interval": (
                        "annual" if price.recurring.interval == "year" else "monthly"
                    ),
                    "interval_count": price.recurring.interval_count,
                    # Intelligent defaults - prefer metadata, fallback to sensible defaults
                    "included_credits": int(metadata.get("included_credits", 1000)),
                    "max_users": (
                        int(metadata.get("max_users"))
                        if metadata.get("max_users")
                        else None
                    ),
                    "features": (
                        json.loads(metadata.get("features", "{}"))
                        if metadata.get("features")
                        else {}
                    ),
                    "trial_period_days": (
                        int(metadata.get("trial_period_days", 0))
                        if metadata.get("trial_period_days")
                        else None
                    ),
                }
                subscription_plans.append(plan_data)
                if verbose:
                    print(f"  ✅ Categorized as: Subscription Plan")

            elif price.type == "one_time":
                # Only seed top-ups managed by this catalog. Other products
                # may also contain credit-like metadata and remain untouched.
                if (
                    metadata.get("catalog_owner") == CREDIT_CATALOG_OWNER
                    and (price.metadata or {}).get("catalog_owner")
                    == CREDIT_CATALOG_OWNER
                    and price.currency.lower() == "usd"
                ):
                    try:
                        amount = int(metadata.get("credit_amount", ""))
                    except (TypeError, ValueError):
                        amount = 0
                    pack = next(
                        (
                            item
                            for item in CREDIT_PACKS
                            if item["credit_amount"] == amount
                        ),
                        None,
                    )
                    expected_price = (
                        int(pack["price_usd"] * 100) if pack is not None else None
                    )
                    if amount <= 0 or price.unit_amount != expected_price:
                        uncategorized.append(
                            {
                                "name": product.name,
                                "price_id": price.id,
                                "type": price.type,
                                "reason": "Managed credit product price does not match the approved USD catalog",
                            }
                        )
                        continue
                    product_data = {
                        "name": product.name,
                        "description": product.description or "",
                        "stripe_price_id": price.id,
                        "stripe_product_id": product.id,
                        "credit_amount": amount,
                        "price_amount": price.unit_amount,
                        "currency": price.currency.upper(),
                    }
                    credit_products.append(product_data)
                    if verbose:
                        print(f"  ✅ Categorized as: Managed Credit Product")
                else:
                    uncategorized.append(
                        {
                            "name": product.name,
                            "price_id": price.id,
                            "type": price.type,
                            "reason": "One-time product is not owned by the managed credit catalog",
                        }
                    )
                    if verbose:
                        print("  ⚠️  Ignored: not owned by managed credit catalog")
            else:
                uncategorized.append(
                    {
                        "name": product.name,
                        "price_id": price.id,
                        "type": price.type,
                        "reason": f"Unknown price type: {price.type}",
                    }
                )
                if verbose:
                    print(f"  ⚠️  Uncategorized: Unknown price type")

        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"- Subscription plans: {len(subscription_plans)}")
        print(f"- Credit products: {len(credit_products)}")
        print(f"- Uncategorized: {len(uncategorized)}")

        if uncategorized and verbose:
            print(f"\n⚠️  UNCATEGORIZED ITEMS:")
            for item in uncategorized:
                print(f"  - {item['name']}: {item['reason']}")

        return subscription_plans, credit_products

    def seed_subscription_plans(
        self, plans_data: List[Dict[str, Any]], dry_run: bool = False
    ) -> bool:
        """Seed legacy subscription plans and report whether every row succeeded."""
        if not plans_data:
            print("⚠️ No subscription plans to seed")
            return False

        print(f"🌱 Seeding {len(plans_data)} subscription plans...")

        if dry_run:
            print("🔍 DRY RUN - Would seed the following subscription plans:")
            for plan in plans_data:
                print(
                    f"  - {plan['name']}: ${plan['price_amount'] / 100:.2f}/{plan['interval']} ({plan['included_credits']} credits)"
                )
            return True

        success_count = 0
        for plan in plans_data:
            try:
                # Check if plan already exists
                existing = (
                    supabase_config.client.table("subscription_plans")
                    .select("id")
                    .eq("stripe_price_id", plan["stripe_price_id"])
                    .execute()
                )

                plan_data = {
                    "name": plan["name"],
                    "description": plan["description"],
                    "stripe_price_id": plan["stripe_price_id"],
                    "stripe_product_id": plan["stripe_product_id"],
                    "price_amount": plan["price_amount"],
                    "currency": plan["currency"],
                    "interval": plan["interval"],
                    "interval_count": plan["interval_count"],
                    "included_credits": plan["included_credits"],
                    "max_users": plan["max_users"],
                    "features": plan["features"],
                    "trial_period_days": plan["trial_period_days"],
                }

                if existing.data:
                    # Update existing plan
                    supabase_config.client.table("subscription_plans").update(
                        plan_data
                    ).eq("stripe_price_id", plan["stripe_price_id"]).execute()
                    print(f"  ✅ Updated: {plan['name']}")
                else:
                    # Insert new plan
                    supabase_config.client.table("subscription_plans").insert(
                        plan_data
                    ).execute()
                    print(f"  ✅ Created: {plan['name']}")

                success_count += 1

            except Exception as e:
                print(f"  ❌ Error with {plan['name']}: {e}")

        print(
            f"✓ Subscription plans seeded: {success_count}/{len(plans_data)} successful"
        )
        return success_count == len(plans_data)

    def seed_credit_products(
        self, products_data: List[Dict[str, Any]], dry_run: bool = False
    ) -> bool:
        """Atomically reconcile the full approved credit product catalog."""
        expected_by_amount = {pack["credit_amount"]: pack for pack in CREDIT_PACKS}
        if len(products_data) != len(CREDIT_PACKS) or not all(
            isinstance(product, dict) for product in products_data
        ):
            print(
                "❌ Credit catalog is incomplete or malformed; expected exactly "
                "one product for each approved pack."
            )
            return False

        received_amounts = [product.get("credit_amount") for product in products_data]
        valid_amounts = all(
            isinstance(amount, int) and not isinstance(amount, bool)
            for amount in received_amounts
        )
        valid_products = valid_amounts
        if valid_products:
            valid_products = set(received_amounts) == set(expected_by_amount) and len(
                set(received_amounts)
            ) == len(expected_by_amount)
        if valid_products:
            valid_products = all(
                isinstance(product.get(field), str) and bool(product[field])
                for product in products_data
                for field in ("stripe_price_id", "stripe_product_id")
            )
        if valid_products:
            valid_products = len(
                {product["stripe_price_id"] for product in products_data}
            ) == len(CREDIT_PACKS) and len(
                {product["stripe_product_id"] for product in products_data}
            ) == len(
                CREDIT_PACKS
            )
        if not valid_products:
            print(
                "❌ Credit catalog is incomplete or contains duplicate packs; "
                "expected exactly one correctly priced active Stripe Price for "
                "each approved pack."
            )
            return False

        for product in products_data:
            pack = expected_by_amount[product["credit_amount"]]
            valid_products = valid_products and (
                product.get("name") == pack["name"]
                and product.get("price_amount") == int(pack["price_usd"] * 100)
                and str(product.get("currency", "")).upper() == "USD"
                and bool(product.get("stripe_price_id"))
                and bool(product.get("stripe_product_id"))
            )
        if not valid_products:
            print(
                "❌ Credit catalog is incomplete or contains duplicate packs; "
                "expected exactly one correctly priced active Stripe Price for "
                "each approved pack."
            )
            return False

        print(f"🌱 Seeding {len(products_data)} credit products...")

        if dry_run:
            print("🔍 DRY RUN - Would seed the following credit products:")
            for product in products_data:
                print(
                    f"  - {product['name']}: {product['credit_amount']} credits for ${product['price_amount'] / 100:.2f}"
                )
            return True

        try:
            client = getattr(supabase_config, "service_client", None) or (
                supabase_config.client
            )
            result = client.rpc(
                "sync_credit_product_catalog", {"p_products": products_data}
            ).execute()
            if result.data != len(products_data):
                raise RuntimeError("database did not confirm a complete catalog sync")
        except Exception as exc:
            print(f"❌ Credit product catalog sync failed atomically: {exc}")
            return False

        print(f"✅ Atomically activated all {len(products_data)} approved credit packs")
        return True

    def seed_credit_events(self, dry_run: bool = False):
        """Seed the finite system usage-pricing catalog."""
        credit_events = [
            {
                "name": "voice_call_minute",
                "description": "A connected voice call is charged for each whole minute, rounded up.",
                "credit_cost": 10,
                "category": "voice",
                "meter_type": "duration",
                "billing_unit": "minute",
            },
            {
                "name": "phone_number_local_month",
                "description": (
                    "Existing non-US local platform rentals retain their legacy "
                    "monthly rate."
                ),
                "credit_cost": 200,
                "category": "phone_number",
                "meter_type": "count",
                "billing_unit": "month",
            },
            {
                "name": "phone_number_us_local_month",
                "description": (
                    "Each additional platform-provided US local phone number "
                    "uses 80 credits per rental month."
                ),
                "credit_cost": 80,
                "category": "phone_number",
                "meter_type": "count",
                "billing_unit": "month",
            },
            {
                "name": "phone_number_mobile_month",
                "description": (
                    "Legacy active mobile rentals retain their monthly rate; "
                    "new mobile-number purchases are unavailable in v1."
                ),
                "credit_cost": 200,
                "category": "phone_number",
                "meter_type": "count",
                "billing_unit": "month",
            },
            {
                "name": "phone_number_toll_free_month",
                "description": (
                    "An active toll-free phone number uses 120 credits ($3 at 40 "
                    "credits per dollar) for each rental month."
                ),
                "credit_cost": 120,
                "category": "phone_number",
                "meter_type": "count",
                "billing_unit": "month",
            },
        ]

        print(f"🌱 Seeding {len(credit_events)} credit events...")

        if dry_run:
            print("🔍 DRY RUN - Would seed the following credit events:")
            for event in credit_events:
                print(
                    f"  - {event['name']}: {event['credit_cost']} credits ({event['category']})"
                )
            return

        success_count = 0
        for event in credit_events:
            try:
                # Check if event already exists
                existing = (
                    supabase_config.client.table("credit_events")
                    .select("id,credit_cost")
                    .eq("name", event["name"])
                    .execute()
                )

                if existing.data:
                    # These rates are editable by platform admins. A catalog
                    # seed may create missing known events, but must not reset
                    # a reviewed rate on every Stripe sync.
                    print(
                        f"  ⏭️  Preserved admin rate for {event['name']}: "
                        f"{existing.data[0].get('credit_cost')} credits"
                    )
                else:
                    # Insert new event
                    supabase_config.client.table("credit_events").insert(
                        event
                    ).execute()
                    print(f"  ✅ Created: {event['name']}")

                success_count += 1

            except Exception as e:
                print(f"  ❌ Error with {event['name']}: {e}")

        print(
            f"✓ Credit events seeded: {success_count}/{len(credit_events)} successful"
        )

    def check_tables_exist(self, required_tables=None):
        """Check whether the requested billing tables exist."""
        required_tables = required_tables or [
            "subscription_plans",
            "credit_events",
            "credit_products",
        ]

        for table in required_tables:
            try:
                supabase_config.client.table(table).select("id").limit(1).execute()
            except Exception as e:
                print(f"❌ Table '{table}' appears to be missing: {e}")
                return False

        return True

    def seed_database(
        self,
        dry_run=False,
        verbose=False,
        include_legacy_billing_data=False,
        include_credit_products=True,
    ):
        """Sync approved credit packs or import legacy subscription rows."""
        if not include_legacy_billing_data and not include_credit_products:
            print("❌ Nothing to sync; select a billing catalog operation")
            return False
        if include_legacy_billing_data and include_credit_products:
            print(
                "❌ Legacy plan import is a pre-migration step; run it separately "
                "with --skip-credit-products, then sync packs after Alembic head."
            )
            return False

        if dry_run:
            print("🔍 DRY RUN MODE - No data will be written to database")

        print("🌱 Starting intelligent billing data seeding...")
        print("=" * 60)

        # Always use the enhanced method with pagination and intelligent detection
        all_prices = self.fetch_all_stripe_prices()
        if not all_prices:
            print("❌ No prices found in Stripe")
            return False

        subscription_plans, credit_products = self.analyze_stripe_data(
            all_prices,
            verbose=verbose,
            include_subscriptions=include_legacy_billing_data,
        )

        if not include_legacy_billing_data and subscription_plans:
            print(
                f"ℹ️ Detected {len(subscription_plans)} legacy subscription plans; "
                "they will not be imported. Use --include-legacy-billing-data "
                "only for a reviewed legacy backfill."
            )

        if include_credit_products:
            expected_credit_amounts = {pack["credit_amount"] for pack in CREDIT_PACKS}
            observed_credit_amounts = [
                product.get("credit_amount") for product in credit_products
            ]
            if set(observed_credit_amounts) != expected_credit_amounts or len(
                observed_credit_amounts
            ) != len(expected_credit_amounts):
                print(
                    "❌ Stripe does not contain exactly one active price for each "
                    "approved credit pack; run setup-credits and review its result first."
                )
                return False
        elif not subscription_plans:
            print("❌ No valid subscription plans or credit products found")
            print(
                "💡 Consider adding metadata to your Stripe products or check the diagnostic output"
            )
            return False

        try:
            if not dry_run:
                required_tables = []
                if include_legacy_billing_data:
                    required_tables.append("subscription_plans")
                if include_credit_products:
                    required_tables.append("credit_products")
                if not self.check_tables_exist(required_tables):
                    print("❌ Required database tables are missing")
                    return False

            print(f"\n🌱 SEEDING DATA:")
            print("=" * 30)

            # Legacy plan imports are a pre-migration step. Current plan
            # versions and system usage rates remain admin-managed catalogs.
            if include_legacy_billing_data:
                if not self.seed_subscription_plans(subscription_plans, dry_run):
                    print("❌ Legacy subscription plan import was incomplete")
                    return False
            if include_credit_products and not self.seed_credit_products(
                credit_products, dry_run
            ):
                print("❌ Credit product synchronization failed")
                return False

            if dry_run:
                print(f"\n🔍 DRY RUN COMPLETED")
                if include_legacy_billing_data:
                    print(
                        f"Found {len(subscription_plans)} legacy subscription plans"
                    )
                elif include_credit_products:
                    print(f"Found {len(credit_products)} approved credit products")
            else:
                print(f"\n🎉 SEEDING COMPLETED!")
                if include_legacy_billing_data:
                    print(f"✅ {len(subscription_plans)} subscription plans")
                if include_credit_products:
                    print(f"✅ {len(credit_products)} credit products")

            return True

        except Exception as e:
            print(f"❌ Error during seeding: {e}")
            return False


def create_parser():
    """Create argument parser for CLI interface."""
    parser = argparse.ArgumentParser(
        description="Consolidated Stripe Management Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/stripe_manager.py diagnostic
  python scripts/stripe_manager.py cleanup --dry-run
  python scripts/stripe_manager.py setup-credits --dry-run
  python scripts/stripe_manager.py seed --dry-run
  python scripts/stripe_manager.py seed
  python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run
  python scripts/stripe_manager.py seed --verbose
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Diagnostic command
    diagnostic_parser = subparsers.add_parser(
        "diagnostic", help="Inspect Stripe account and show recommendations"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help='Deactivate only marked old "All Credit Packages" products'
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be cleaned up without making changes",
    )

    # Setup credits command
    setup_parser = subparsers.add_parser(
        "setup-credits", help="Reconcile only credit products marked as platform-owned"
    )
    setup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making changes",
    )

    # Seed command
    seed_parser = subparsers.add_parser(
        "seed", help="Sync approved credit packs; legacy billing import is opt-in"
    )
    seed_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be seeded without writing to database",
    )
    seed_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed analysis of each Stripe product during processing",
    )
    seed_parser.add_argument(
        "--include-legacy-billing-data",
        action="store_true",
        help=(
            "Import legacy subscription plans only as a deliberate pre-migration backfill"
        ),
    )
    seed_parser.add_argument(
        "--skip-credit-products",
        action="store_true",
        help=(
            "For a reviewed legacy backfill only: import old subscription rows "
            "before migration 20260807000002; sync approved credit packs after migrations"
        ),
    )

    # Show metadata instructions command
    metadata_parser = subparsers.add_parser(
        "show-metadata",
        help="Show instructions for adding metadata to subscription products",
    )

    return parser


def show_metadata_instructions():
    """Show instructions for adding metadata to existing subscription products."""
    print(f"\n📝 SUBSCRIPTION PLAN METADATA SETUP:")
    print("=" * 50)
    print(
        f"""
To optimize your existing subscription plans, add this metadata to each product in Stripe Dashboard:

🎯 Starter Plan:
{{
  "included_credits": "1000",
  "max_users": "5",
  "features": "{{'api_access': true, 'basic_support': true, 'storage_gb': 10}}",
  "trial_period_days": "14"
}}

🚀 Pro Plan:
{{
  "included_credits": "5000",
  "max_users": "25",
  "features": "{{'api_access': true, 'priority_support': true, 'storage_gb': 100, 'analytics': true}}",
  "trial_period_days": "14"
}}

🏢 Enterprise Plan:
{{
  "included_credits": "10000",
  "max_users": "100",
  "features": "{{'api_access': true, 'dedicated_support': true, 'storage_gb': 1000, 'analytics': true, 'custom_integrations': true}}",
  "trial_period_days": "30"
}}

📍 How to add metadata:
1. Go to Stripe Dashboard → Products
2. Click on each product (Starter Plan, Pro Plan, Enterprise Plan)
3. Scroll down to "Metadata" section
4. Add the key-value pairs shown above
5. Save the product
"""
    )


def main():
    """Main CLI entry point."""
    if not settings.stripe_secret_key:
        print("❌ STRIPE_SECRET_KEY not found in environment variables")
        sys.exit(1)

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize Stripe manager
    manager = StripeManager()

    print("🔧 STRIPE MANAGER")
    print("=" * 40)

    try:
        if args.command == "diagnostic":
            manager.diagnostic()

        elif args.command == "cleanup":
            manager.cleanup_old_products(dry_run=args.dry_run)

        elif args.command == "setup-credits":
            if not manager.setup_credit_products(dry_run=args.dry_run):
                sys.exit(1)

        elif args.command == "seed":
            success = manager.seed_database(
                dry_run=args.dry_run,
                verbose=args.verbose,
                include_legacy_billing_data=args.include_legacy_billing_data,
                include_credit_products=not args.skip_credit_products,
            )
            if not success:
                sys.exit(1)

        elif args.command == "show-metadata":
            show_metadata_instructions()

    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
