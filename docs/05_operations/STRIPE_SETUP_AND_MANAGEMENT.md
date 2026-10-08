# Stripe Setup and Management

This document provides comprehensive guidance for setting up Stripe products and managing them using the consolidated Stripe management tool.

> **Canonical subscription setup:** New signups use the platform plan catalog,
> not Stripe product metadata as the entitlement source. Create or edit plan
> products and immutable versions in the platform-admin catalog, set explicit
> `billing_mode` and `credit_grant_policy`, save the Stripe Product ID for paid
> products, and publish the version. Publishing a paid version creates or binds
> its immutable Stripe Price and stores `stripe_price_id`; free versions do not
> require a Stripe Price. See [Subscription-Aware Onboarding and Credit Policy](../01_architecture/ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md).

The metadata examples later in this document describe the legacy Stripe seed
and compatibility path. They are not used to enforce current plan limits.

## Table of Contents

1. [Stripe Configuration](#stripe-configuration)
2. [Stripe Manager Tool](#stripe-manager-tool)
3. [Quick Start Guide](#quick-start-guide)
4. [Detailed Usage](#detailed-usage)
5. [Troubleshooting](#troubleshooting)

## Stripe Configuration

Before using the management tool, you need to properly configure your Stripe products with the required metadata.

### Environment Setup

Ensure your `STRIPE_SECRET_KEY` is set in your environment variables:

```bash
# In the selected root environment file (normally .env.local)
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
```

### 1. Subscription Plans (Recurring Prices)

For subscription plans, create **recurring prices** in Stripe with the following **product metadata**:

#### Required Metadata Fields:

- `included_credits` (string): Number of credits included with this plan
- `max_users` (string, optional): Maximum users allowed (omit for unlimited)
- `features` (JSON string): Plan features as JSON object
- `trial_period_days` (string, optional): Trial period in days

#### Example Product Metadata:

```json
{
  "included_credits": "1000",
  "max_users": "5",
  "features": "{\"api_calls\": 10000, \"storage_gb\": 10, \"support\": \"email\"}",
  "trial_period_days": "14"
}
```

#### Sample Plan Configurations:

**Starter Plan:**

```json
{
  "included_credits": "1000",
  "max_users": "5",
  "features": "{\"api_access\": true, \"basic_support\": true, \"storage_gb\": 10}",
  "trial_period_days": "14"
}
```

**Pro Plan:**

```json
{
  "included_credits": "5000",
  "max_users": "25",
  "features": "{\"api_access\": true, \"priority_support\": true, \"storage_gb\": 100, \"analytics\": true}",
  "trial_period_days": "14"
}
```

**Enterprise Plan:**

```json
{
  "included_credits": "10000",
  "max_users": "100",
  "features": "{\"api_access\": true, \"dedicated_support\": true, \"storage_gb\": 1000, \"analytics\": true, \"custom_integrations\": true}",
  "trial_period_days": "30"
}
```

### 2. Credit Products (One-time Prices)

For each managed credit product, add Product metadata and a matching one-time Price:

#### Required Metadata Fields:

- `catalog_owner` (string): `24x7-ai-credit-catalog-v1`, set on Product and Price
- `credit_amount` (string): Number of credits this product provides (Product metadata)

#### Example Product Metadata:

```json
{
  "catalog_owner": "24x7-ai-credit-catalog-v1",
  "credit_amount": "1000"
}
```

### Setting Up Products in Stripe Dashboard

#### For Subscription Plans:

1. Go to **Products** → **Add product**
2. Fill in product name and description
3. Create a **recurring** price (monthly/yearly)
4. In the **Product** section, add the metadata fields above
5. Make sure the product is **Active**

#### For Credit Products:

1. Go to **Products** → **Add product**
2. Fill in product name and description
3. Create a **one-time** price
4. In the **Product** section, add both `catalog_owner` and `credit_amount`; add the same ownership marker to the one-time Price metadata
5. Make sure the product is **Active**

## Stripe Manager Tool

The `stripe_manager.py` script consolidates all Stripe-related functionality into a single, easy-to-use command-line tool.

### Features

The script provides the following commands:

- **`diagnostic`** - Inspect Stripe account and show recommendations
- **`cleanup`** - Deactivate old "All Credit Packages" products
- **`setup-credits`** - Create individual credit products with proper metadata
- **`seed`** - Seed database with Stripe data using intelligent detection
- **`show-metadata`** - Display metadata setup instructions

### Benefits

✅ **Single Script**: One tool for all Stripe operations  
✅ **Consistent Interface**: Unified command-line experience  
✅ **Intelligent Detection**: Automatically detects subscription plans and credit products  
✅ **Pagination Support**: Handles large Stripe accounts with automatic pagination  
✅ **Smart Defaults**: Provides sensible fallbacks when metadata is missing  
✅ **Dry Run Support**: Preview changes before applying them  
✅ **Enhanced Error Handling**: Better error reporting and recovery  
✅ **Easy Maintenance**: Single file to update and maintain

## Quick Start Guide

### 1. Inspect Your Current Stripe Setup

```bash
cd backend
python scripts/stripe_manager.py diagnostic
```

This will show you all your current Stripe products and their metadata, plus recommendations.

### 2. Set Up Credit Products (if needed)

```bash
# Preview what would be created
python scripts/stripe_manager.py setup-credits --dry-run

# Create the credit products
python scripts/stripe_manager.py setup-credits
```

### 3. Clean Up Old Products (if needed)

```bash
# Preview what would be cleaned up
python scripts/stripe_manager.py cleanup --dry-run

# Perform the cleanup
python scripts/stripe_manager.py cleanup
```

### 4. Sync the Approved Credit Packs

```bash
# Preview the approved credit-pack sync (recommended first)
python scripts/stripe_manager.py seed --dry-run

# Sync only the approved credit packs to the database
python scripts/stripe_manager.py seed
```

The default `seed` command does not import subscription plans or usage rates
from Stripe. Configure plan versions in Plan Catalog and rates in the
system-pricing admin UI. `--include-legacy-billing-data` is an explicit opt-in
for a reviewed pre-migration backfill; it imports only legacy subscription-plan
rows.

## Detailed Usage

### View All Available Commands

```bash
python scripts/stripe_manager.py --help
```

### Inspect Your Stripe Account

```bash
python scripts/stripe_manager.py diagnostic
```

This command provides a comprehensive inspection of your Stripe account, showing:

- All active products and their metadata
- All active prices and their types
- Analysis of which products can be categorized
- Recommendations for improving your setup

### Clean Up Old Products

```bash
# Preview what would be cleaned up (safe)
python scripts/stripe_manager.py cleanup --dry-run

# Actually perform the cleanup
python scripts/stripe_manager.py cleanup
```

This command specifically targets old "All Credit Packages" products for deactivation.

### Set Up Credit Products

```bash
# Preview what would be created
python scripts/stripe_manager.py setup-credits --dry-run

# Create the credit products
python scripts/stripe_manager.py setup-credits
```

This creates standardized credit products:

- 200 Credits Pack ($5.00)
- 500 Credits Pack ($12.00)
- 1000 Credits Pack ($23.00)
- 2000 Credits Pack ($44.00)

Apply the reviewed catalog migration before database synchronization and follow
the [four-pack rollout procedure](stripe_management.md#four-pack-catalog-rollout).
Product setup alone does not switch the active database catalog.

### Sync Credit Packs; Import Legacy Billing Data Only by Exception

```bash
# Preview the approved credit-pack sync
python scripts/stripe_manager.py seed --dry-run

# Sync the approved credit packs
python scripts/stripe_manager.py seed

# A reviewed legacy plan backfill is a separate pre-migration step
python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run
```

The default command:

- Uses pagination to fetch all Stripe products
- Detects legacy subscription products but leaves those records unchanged
- Synchronizes only the four approved credit products
- Reports uncategorized items for manual review

Use `--include-legacy-billing-data --skip-credit-products` only for the
reviewed, pre-migration legacy backfill described in
[staging_environment.md](./staging_environment.md). The legacy rows must be
loaded after `20260807000001` and before `20260807000002`; run the normal
credit-pack seed after upgrading to `head`.

### Show Metadata Setup Instructions

```bash
python scripts/stripe_manager.py show-metadata
```

This displays detailed instructions for manually adding metadata to your Stripe products.

## Intelligent Detection Features

The tool includes smart detection capabilities:

### For Subscription Plans:

- **Smart Defaults**: Plans without metadata get 1000 included credits by default
- **Plan Naming**: Keeps customer-facing plan names separate from billing cadence
- **Metadata Parsing**: Safely parses JSON features with fallbacks

### For Credit Products:

- **Ownership detection** requires `catalog_owner=24x7-ai-credit-catalog-v1` on both Product and Price, plus a supported credit amount and approved USD price.
- `setup-credits` only edits marked products and prices and keeps existing Prices active. `seed` ignores unowned one-time products and uses `sync_credit_product_catalog` to atomically activate the full approved database catalog and deactivate stale rows. Older Stripe Prices may remain active, but the billing UI offers only the active database catalog.

## Troubleshooting

### "No data found in Stripe" error:

- Check that `STRIPE_SECRET_KEY` is set correctly
- Ensure products are marked as **Active** in Stripe
- Verify subscription metadata is set on products
- For credit products, ensure Product and Price both carry the ownership marker and Product has `credit_amount`

### Missing fields in database:

- Check that product metadata follows the exact field names above
- Ensure JSON in `features` field is valid JSON
- Verify numeric fields contain valid integers

### "Required database tables are missing":

- Run the billing migration: `alembic upgrade head`
- Ensure your database connection is properly configured

### Products not being categorized:

- Use the `diagnostic` command to inspect your Stripe setup
- Add proper metadata to your Stripe products
- Check that products are marked as **Active**
- Use `--verbose` flag with seed command to see detailed analysis

## Migration from Old Scripts

If you were using the old individual scripts, here's the mapping:

| Old Script                                                                 | New Command                                                 |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `python scripts/stripe_diagnostic.py`                                      | `python scripts/stripe_manager.py diagnostic`               |
| `python scripts/cleanup_old_stripe_products.py --dry-run`                  | `python scripts/stripe_manager.py cleanup --dry-run`        |
| `python scripts/setup_stripe_credit_products.py --setup-credits --dry-run` | `python scripts/stripe_manager.py setup-credits --dry-run`  |
| `python scripts/seed_billing_data.py --dry-run`                            | `python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run` |
| `python scripts/seed_billing_data_enhanced.py --dry-run`                   | `python scripts/stripe_manager.py seed --include-legacy-billing-data --skip-credit-products --dry-run --verbose` |

Run these legacy imports only after `20260807000001` and before
`20260807000002`; then apply the remaining migrations and run the normal
credit-pack seed. Routine setup uses the default credit-only seed.

## Best Practices

1. **Always use dry-run first**: Preview changes before applying them
2. **Use the diagnostic command**: Understand your current setup before making changes
3. **Add proper metadata**: This ensures the best detection and categorization
4. **Keep products active**: Inactive products won't be processed
5. **Use consistent naming**: Makes automatic detection more reliable
6. **Regular syncing**: Re-run the seed command when you update Stripe products
