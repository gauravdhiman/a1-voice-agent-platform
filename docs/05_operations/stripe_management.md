# Stripe Management Tool

The `stripe_manager.py` script provides a unified command-line interface for managing Stripe products, prices, and billing setup.

## Overview

The Stripe Manager Tool consolidates all Stripe-related functionality into a single, easy-to-use CLI tool for:
- Creating credit products with proper metadata
- Cleaning up outdated products
- Diagnosing Stripe account configuration
- Seeding database with Stripe data
- Viewing metadata requirements

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
# In your .env file
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
```

### Required Metadata Fields

For subscription plans, products must have:
- `included_credits` (string): Number of credits included with this plan
- `max_users` (string, optional): Maximum users allowed (omit for unlimited)
- `features` (JSON string): Plan features as JSON object
- `trial_period_days` (string, optional): Trial period in days

For credit products, products must have:
- `credit_amount` (string): Number of credits this product provides

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
- 100 Credits Pack ($15.00)
- 1000 Credits Pack ($25.00)
- 2500 Credits Pack ($50.00)
- 5000 Credits Pack ($90.00)

### 3. Clean Up Old Products

```bash
# Preview what would be cleaned up
python scripts/stripe_manager.py cleanup --dry-run

# Perform cleanup
python scripts/stripe_manager.py cleanup
```

This specifically targets old "All Credit Packages" products for deactivation.

### 4. Seed Database

```bash
# Preview what would be seeded (recommended first)
python scripts/stripe_manager.py seed --dry-run

# Seed database with intelligent detection
python scripts/stripe_manager.py seed
```

The seed command:
- Uses pagination to fetch all Stripe products
- Intelligently detects subscription plans and credit products
- Provides smart defaults when metadata is missing
- Reports uncategorized items for manual review

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
- **Metadata Detection**: Prefers explicit `credit_amount` metadata
- **Name-based Inference**: Extracts credit amounts from product names like "100 Credits Pack"
- **Price-based Inference**: Infers credits from common pricing patterns:
  - $15.00 → 100 credits
  - $25.00 → 1000 credits
  - $50.00 → 2500 credits
  - $90.00 → 5000 credits

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
- Verify metadata fields are set on products (not prices)
- For credit products, ensure they have `credit_amount` metadata

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

| Old Script | New Command |
|------------|-------------|
| `python scripts/stripe_diagnostic.py` | `python scripts/stripe_manager.py diagnostic` |
| `python scripts/cleanup_old_stripe_products.py --dry-run` | `python scripts/stripe_manager.py cleanup --dry-run` |
| `python scripts/setup_stripe_credit_products.py --setup-credits --dry-run` | `python scripts/stripe_manager.py setup-credits --dry-run` |
| `python scripts/seed_billing_data.py --dry-run` | `python scripts/stripe_manager.py seed --dry-run` |
| `python scripts/seed_billing_data_enhanced.py --dry-run` | `python scripts/stripe_manager.py seed --dry-run --verbose` |

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
