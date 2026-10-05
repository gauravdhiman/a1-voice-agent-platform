# Stripe Management Tool

The `stripe_manager.py` script provides a unified command-line interface for managing Stripe products, prices, and billing setup.

## Overview

The Stripe Manager Tool consolidates all Stripe-related functionality into a single, easy-to-use CLI tool for:

- Creating credit products with proper metadata
- Cleaning up outdated products
- Diagnosing Stripe account configuration
- Seeding database with Stripe data
- Viewing metadata requirements

> **Current subscription design:** New founder signups use immutable platform
> plan versions and explicit `billing_mode`; plan entitlements are resolved from
> Supabase, not inferred from Stripe metadata. Use the platform-admin plan
> catalog to publish paid versions and create/bind their Stripe Prices. This CLI
> remains useful for diagnostics, one-time credit-product setup, and legacy
> compatibility seeding. See [Subscription-Aware Onboarding and Credit Policy](../01_architecture/ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md).

## Location

**File**: `backend/scripts/stripe_manager.py`

## Features

### Diagnostic Capabilities

- Inspect Stripe account and show recommendations
- Display all active products and their metadata
- Analyze product categorization
- Provide setup guidance

### Product Management

- **`diagnostic`** - Inspect Stripe account and show recommendations
- **`cleanup`** - Deactivate old "All Credit Packages" products
- **`setup-credits`** - Create individual credit products with proper metadata
- **`seed`** - Seed database with Stripe data using intelligent detection
- **`show-metadata`** - Display metadata setup instructions

## Prerequisites

### Environment Setup

Ensure your `STRIPE_SECRET_KEY` is set:

```bash
# In the selected root environment file (normally .env.local)
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
```

### Required Metadata Fields

For subscription plans, products must have:

- `included_credits` (string): Number of credits included with this plan
- `max_users` (string, optional): Maximum users allowed (omit for unlimited)
- `features` (JSON string): Plan features as JSON object
- `trial_period_days` (string, optional): Trial period in days

For credit products, Product and Price must have:

- `catalog_owner` (string): `24x7-ai-credit-catalog-v1`
- `credit_amount` (string): Number of credits this product provides (Product metadata)

## Usage

### 1. Diagnose Your Stripe Setup

```bash
cd backend
python scripts/stripe_manager.py diagnostic
```

This shows:

- All active products and their metadata
- All active prices and their types
- Analysis of which products can be categorized
- Recommendations for improving your setup

### 2. Set Up Credit Products

```bash
# Preview what would be created
python scripts/stripe_manager.py setup-credits --dry-run

# Create credit products
python scripts/stripe_manager.py setup-credits
```

This creates standardized credit products:

- 200 Credits Pack ($5.00)
- 400 Credits Pack ($10.00)
- 1000 Credits Pack ($25.00)

### 3. Clean Up Old Products

```bash
# Preview what would be cleaned up
python scripts/stripe_manager.py cleanup --dry-run

# Perform cleanup
python scripts/stripe_manager.py cleanup
```

This specifically targets old "All Credit Packages" products for deactivation.

### 4. Sync the Approved Credit Packs

```bash
# Preview the approved credit-pack sync (recommended first)
python scripts/stripe_manager.py seed --dry-run

# Sync only the three approved credit packs to the database
python scripts/stripe_manager.py seed
```

The default `seed` command does not import subscription plans or usage rates
from Stripe. Configure plan versions in Plan Catalog and usage rates in the
system-pricing admin UI. `--include-legacy-billing-data` is an explicit opt-in
for a reviewed pre-migration backfill; it imports only legacy subscription-plan
rows.

The seed command:

- Uses pagination to inspect Stripe prices
- Syncs only the three approved credit products by default
- Parses and imports legacy subscriptions only when explicitly requested
- Reports uncategorized items for manual review

**Cloud staging:** `./scripts/bootstrap-staging-db.sh` upgrades the schema to
head first, then syncs approved credit packs. It does not import legacy Stripe
plans or publish paid plan versions; those remain an authenticated Plan Catalog
task. See [staging_environment.md](./staging_environment.md) for the separate
pre-migration legacy backfill sequence.

### 5. View Metadata Setup Instructions

```bash
python scripts/stripe_manager.py show-metadata
```

This displays detailed instructions for manually adding metadata to your Stripe products.

## Intelligent Detection

### For Subscription Plans

- **Smart Defaults**: Plans without metadata get 1000 included credits by default
- **Flexible Naming**: Automatically appends billing interval to plan names
- **Metadata Parsing**: Safely parses JSON features with fallbacks

### For Credit Products

- **Ownership detection** requires `catalog_owner=24x7-ai-credit-catalog-v1` on Product and Price, plus an approved credit amount and USD price.
- `setup-credits` only edits marked products and prices. `seed` ignores unowned one-time products and deactivates stale database top-ups only after every current managed price sync succeeds.

## Best Practices

1. **Always use dry-run first**: Preview changes before applying them
2. **Use diagnostic command**: Understand your current setup before making changes
3. **Add proper metadata**: This ensures best detection and categorization
4. **Keep products active**: Inactive products won't be processed
5. **Use consistent naming**: Makes automatic detection more reliable
6. **Regular syncing**: Re-run seed command when you update Stripe products

## Troubleshooting

### "No data found in Stripe" error

- Check that `STRIPE_SECRET_KEY` is set correctly
- Ensure products are marked as **Active** in Stripe
- Verify subscription metadata is set on products
- For credit products, ensure Product and Price both carry the ownership marker and Product has `credit_amount`

### Missing fields in database

- Check that product metadata follows exact field names above
- Ensure JSON in `features` field is valid JSON
- Verify numeric fields contain valid integers

### Products not being categorized

- Use `diagnostic` command to inspect your Stripe setup
- Add proper metadata to your Stripe products
- Check that products are marked as **Active**
- Use `--verbose` flag with seed command to see detailed analysis

## Migration from Old Scripts

If you were using old individual scripts, here's the mapping:

| Old Script                                                                 | New Command                                                 |
| -------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `python scripts/stripe_diagnostic.py`                                      | `python scripts/stripe_manager.py diagnostic`               |
| `python scripts/cleanup_old_stripe_products.py --dry-run`                  | `python scripts/stripe_manager.py cleanup --dry-run`        |
| `python scripts/setup_stripe_credit_products.py --setup-credits --dry-run` | `python scripts/stripe_manager.py setup-credits --dry-run`  |
| `python scripts/seed_billing_data.py --dry-run`                            | `python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run` |
| `python scripts/seed_billing_data_enhanced.py --dry-run`                   | `python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run --verbose` |

These legacy commands run only after migration to `20260807000001` and before
`20260807000002`; run the normal credit-pack seed after upgrading to `head`.
For routine setup, use the default credit-only `seed` command instead.

## Example Product Metadata

### Subscription Plan (Monthly)

```json
{
  "included_credits": "1000",
  "max_users": "5",
  "features": "{\"api_access\": true, \"basic_support\": true, \"storage_gb\": 10}",
  "trial_period_days": "14"
}
```

### Credit Product

```json
{
  "catalog_owner": "24x7-ai-credit-catalog-v1",
  "credit_amount": "1000"
}
```

## Additional Resources

- [Billing System](../02_core_systems/billing_system.md) - Complete billing system documentation
- [Stripe Integration](../03_implementation/stripe_integration.md) - Stripe integration details
- [Payment Flow](../03_implementation/payment_flow.md) - Complete payment workflow

## Getting Help

```bash
python scripts/stripe_manager.py --help
```

This will display all available commands and their options.
