# Billing System Overview

## Overview

This document provides a comprehensive overview of the billing system implemented for the multi-tenant SaaS platform, including Stripe integration, subscription management, and credit-based usage tracking.

> **Current architecture:** New signups use immutable `plan_versions` and
> subscription-aware onboarding. `subscription_plans` remains for compatibility
> and grandfathered data; it is not the source of truth for new plan selection.
> See [Subscription-Aware Onboarding and Credit Policy](../01_architecture/ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md)
> and [Plan Versioning & Entitlements](../01_architecture/ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md).

## Architecture

### Database Schema

The billing system uses the following database tables:

#### Core Tables

- **plan_products / plan_versions**: Admin-managed catalog and immutable terms for new signups.
- **organization_subscriptions**: Organization subscription status and bound plan version.
- **subscription_plans**: Legacy compatibility catalog used by older records and APIs.
- **credit_events**: Fixed system activities that consume credits; rates are
  global rather than plan-version-specific.
- **credit_transactions**: All credit movements (earned, consumed, purchased).
- **credit_notification_outbox**: Durable, transaction-linked low-credit
  evaluation tasks processed by the notification scheduler.
- **platform_credit_grants**: Immutable audit records for platform-admin bonus
  allocations, including actor, reason, and idempotency key.
- **credit_products**: Standalone credit packages for purchase.
- **billing_history**: Payment history and invoices.

#### Key Features

- Multi-tiered subscription plans (monthly/annual).
- Credit-based usage system with configurable events.
- Independent credit purchases with no expiry.
- Platform-admin bonus credits with no expiry and a dedicated balance pool.
- Subscription credits that expire per billing period.
- Comprehensive audit trail for all transactions.

### Current pricing and enforcement policy

The platform has a deliberately small, system-wide usage catalog. Platform
admins edit rates in **Plan Catalog → Usage pricing**; rates are not copied into
plan versions. The supported activities are voice calls per connected whole
minute and local, mobile, and toll-free phone numbers per active rental month.
The runtime owns the meter and billing interval, and a rate of zero means free.
Call recording is currently a plan feature with one month of free retention,
not a storage charge.

New calls require enough balance for one billable minute. An admitted call is
allowed to complete, then its full rounded duration is settled atomically. If
the final debit crosses zero, the plan pool can temporarily be negative; the
next call is blocked until the organization restores credits. This prevents
undercharging while avoiding mid-conversation call drops.

Phone-number renewal failures enter a seven-day grace period. The daily rental
scheduler retries the current system rate and releases the Twilio number when
grace expires. A failed initial purchase debit releases the provider number
immediately.

The first US local platform number is included while the organization has
active paid-plan access. If it is kept after that access ends, the number
converts to the configured US local rental rate at its next renewal. The
customer is told about the 80-credit/month rate in the subscription-cancel
dialog; the same credit-balance and renewal grace rules then apply.

#### Platform usage pricing

Platform admins manage activity pricing from **Plan Catalog → Usage pricing**;
it is intentionally consolidated with plans and entitlements rather than added
as another left-navigation destination. The catalog contains four predefined
system activities: voice calls per connected minute, and local, mobile, and
toll-free phone numbers per active rental month. The admin changes only the
credit rate; the runtime-owned meter and interval are not arbitrary choices.
Setting a rate to zero makes that activity free. Call recording is currently a
plan feature with a free one-month retention policy, not a metered charge.

Phone-number rentals are charged at purchase and again at each monthly due
date using the current system rate. If a renewal debit fails, the number stays
owned for seven days while the organization can add credits. The daily rental
worker retries the charge and releases the Twilio number when that grace period
expires. A new call is blocked when the organization cannot cover at least one
billable minute; a call already in progress is allowed to finish and is billed
at teardown.

### Backend Implementation

#### Services

1.  **Stripe Service** (`backend/src/billing/stripe_service.py`)

    - Stripe API integration.
    - Customer management.
    - Subscription lifecycle.
    - Payment processing.
    - Webhook verification.

2.  **Billing Service** (`backend/src/billing/service.py`)

    - Core business logic.
    - Credit management.
    - Subscription handling.
    - Usage tracking.
    - Billing summaries.

3.  **Webhook Handler** (`backend/src/billing/webhook_handler.py`)
    - Stripe webhook processing.
    - Event-driven subscription updates.
    - Automatic credit allocation.
    - Payment status synchronization.

#### API Endpoints (`backend/src/billing/routes.py`)

- Subscription plan management.
- Organization subscription operations.
- Credit balance and consumption.
- Billing history retrieval.
- Stripe checkout sessions.
- Customer portal access.
- Platform-admin credit allocation for any organization through the platform
  organization controls.

### Frontend Implementation

#### Components

1.  **Billing Page** (`frontend/src/app/(dashboard)/billing/page.tsx`)

    - Comprehensive billing dashboard.
    - Subscription management interface.
    - Credit purchase and tracking.
    - Billing history display.

2.  **Platform Organization Credits**
    (`frontend/src/app/(dashboard)/organizations/credits/page.tsx`)

    - Platform-admin-only organization credit controls.
    - Credit usage and ledger reporting for the selected organization.
    - Audited, non-expiring platform credit allocations.
    - Future home for organization-specific entitlement overrides.

3.  **Billing Service** (`frontend/src/services/billing-service.ts`)

    - API integration layer.
    - Stripe checkout handling.
    - Data formatting utilities.

4.  **Type Definitions** (`frontend/src/types/billing.ts`)
    - TypeScript interfaces.
    - Utility functions.
    - Status enumerations.

## Configuration

### Environment Variables

Add the following to the selected root environment file. Use `.env.local` for
local Supabase, `.env.staging` for cloud staging, and `.env.prod` for production.
Do not copy an environment file into a root `.env`.

```bash
# Stripe Configuration
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Database Migration

Run the billing tables migration:

```bash
cd backend
alembic upgrade head
```

Migrations `20260811000004` and `20260811000005` seed the billing warning event,
create the credit notification outbox, and install the final-call settlement
RPC. Migrations `20260812000001` and `20260812000002` harden the outbox and
ensure regular debits preserve any negative plan balance created by a completed
call while still consuming positive admin or purchased pools. The outbox is
processed by the notification retry scheduler every five minutes by default;
email-provider failures do not fail credit consumption.

## Stripe Setup

### 1. Create Stripe Products and Prices

Create products and prices in Stripe Dashboard or via API:

```bash
# Example: Create a subscription plan
stripe products create \
  --name "Professional Plan" \
  --description "Perfect for growing teams"

stripe prices create \
  --product prod_xxx \
  --unit_amount 4900 \
  --currency usd \
  --recurring[interval]=month
```

### 2. Configure Webhooks

Set up webhook endpoint in Stripe Dashboard:

- URL: `https://yourapp.com/api/billing/webhook/stripe`
- Events to listen for:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
  - `payment_intent.succeeded`
  - `payment_intent.payment_failed`

### 3. Update Subscription Plans

Update the default plans in the migration file with your actual Stripe price IDs.

## Usage Examples

### Backend Usage

#### Create a Subscription

```python
from src.billing.service import billing_service
from src.billing.models import OrganizationSubscriptionCreate

subscription_data = OrganizationSubscriptionCreate(
    organization_id="org-uuid",
    subscription_plan_id="plan-uuid"
)

subscription = await billing_service.create_organization_subscription(subscription_data)
```

#### Consume Credits

```python
from src.billing.models import CreditConsumptionRequest

consumption = CreditConsumptionRequest(
    organization_id="org-uuid",
    event_name="voice_call_minute",
    quantity=10
)

result = await billing_service.consume_credits(consumption)
```

### Frontend Usage

#### Initialize Subscription

```typescript
import { billingService } from "@/services/billing-service";

// Redirect to Stripe checkout
await billingService.initializeSubscription(organizationId, planId);
```

#### Purchase Credits

```typescript
// Redirect to Stripe checkout for credit purchase
await billingService.purchaseCredits(organizationId, productId);
```

## Credit System Architecture

### Credit Events

Only runtime-supported activities are configured as credit events. The admin UI
manages the rate and description while the handler owns the measurement:

```sql
INSERT INTO credit_events
    (name, description, credit_cost, category, meter_type, billing_unit)
VALUES
('voice_call_minute', 'Connected voice-call minute', 10, 'voice', 'duration', 'minute'),
('phone_number_local_month', 'Existing non-US local number rental', 200, 'phone_number', 'count', 'month'),
('phone_number_us_local_month', 'Additional US local number rental', 80, 'phone_number', 'count', 'month'),
('phone_number_mobile_month', 'Mobile number rental', 200, 'phone_number', 'count', 'month'),
('phone_number_toll_free_month', 'Toll-free number rental', 120, 'phone_number', 'count', 'month');
```

### Credit Precedence

Credits are consumed in the following order:

1.  **Plan Credits** (expire at the plan period boundary) - consumed first.
2.  **Platform Bonus Credits** (non-expiring platform-admin allocations) -
    consumed second.
3.  **Purchased Credits** (no expiry) - consumed third.

The order is enforced by the shared billing service and the atomic
`debit_organization_credits` PostgreSQL function. This prevents concurrent voice
sessions from overspending any prepaid pool. Pay-as-you-go headroom is not part
of the current model.

### Credit Allocation

- **Plan Credits**: Allocated according to the plan version's explicit
  `credit_grant_policy`; paid recurring grants come from invoice webhooks and
  free recurring grants come from the application scheduler.
- **Purchased Credits**: Added immediately upon successful payment.
- **Platform Bonus Credits**: Added only through
  `POST /api/v1/billing/credits/{organization_id}/admin-grants`. The route is
  platform-admin-only and requires a positive amount plus an audit reason. The
  database function records the actor, reason, ledger row, and audit row
  atomically; it does not change the subscribed plan or purchased pool.
- **Expiry**: Only subscription credits expire at the end of billing period.

### Future entitlement overrides

Credit allocations are deliberately separate from plan entitlements. A future
platform-admin override should be implemented as an audited, time-bounded
overlay on resolved plan entitlements, with precedence `active override →
immutable plan version → catalog default`. It should never edit a published
plan version or mutate the subscription row.

## Subscription Lifecycle

### Status Flow

1.  **Trial** → **Active** (when trial ends and payment succeeds).
2.  **Active** → **Past Due** (when payment fails).
3.  **Past Due** → **Active** (when payment is retried successfully).
4.  **Active** → **Pending cancel** (user cancels — `cancel_at_period_end=true`; **still active**, full access until period end, **no refund**).
5.  **Pending cancel** → **Active** (user reactivates before period end).
6.  **Pending cancel** → **Cancelled** (when `current_period_end` is reached — Stripe `customer.subscription.deleted`).
7.  **Active** → **Cancelled** (immediate only via admin/Stripe dashboard exception — not self-service).

### Cancellation policy

- **No refunds** on voluntary cancellation — simplifies billing; customer keeps what they paid for through period end.
- **Entitlements unchanged** until `current_period_end` when user cancels (same plan version, limits, features, usable credits).
- Implementation: `POST /api/billing/subscription/cancel` sets Stripe `cancel_at_period_end=true` (see `backend/src/billing/stripe_service.py`).

Full spec: [Plan Entitlements §8.1](../03_implementation/plan_entitlements_and_limits.md#81-subscription-cancellation-policy-no-refund-active-until-period-end).

### Webhook-Driven Updates

All subscription status changes are handled via Stripe webhooks to ensure data consistency.

## Security Considerations

### Row Level Security (RLS)

All billing tables have RLS enabled with appropriate policies:

- Organizations can only access their own billing data.
- Platform admins have full access.
- Proper user role validation.

### Webhook Security

- Webhook signature verification using Stripe signature.
- Idempotency handling for duplicate events.
- Error handling and retry logic.

## Monitoring and Alerts

### Key Metrics to Monitor

1.  **Subscription Health**

    - Active subscriptions.
    - Churn rate.
    - Trial conversions.

2.  **Credit Usage**

    - Average credits per organization.
    - Credit consumption trends.
    - Low balance alerts.

3.  **Payment Processing**
    - Payment success rates.
    - Failed payment recovery.
    - Revenue tracking.

### Recommended Alerts

- Credit balance below threshold (< 1000 credits).
- Failed payments requiring attention.
- Subscription cancellations.
- Unusual credit consumption patterns.

## Testing & Validation

### Test Data

The migration includes sample subscription plans and credit products for testing.

### Test Webhooks

Use Stripe CLI for local webhook testing:

```bash
stripe listen --forward-to localhost:8000/api/billing/webhook/stripe
```

### Test Credit Consumption

```bash
# Test API endpoint
POST /api/billing/credits/consume
{
  "organization_id": "uuid",
  "event_name": "voice_call_minute",
  "quantity": 1
}
```

## Troubleshooting

### Common Issues

1.  **Webhook Failures**

    - Verify webhook secret configuration.
    - Check webhook URL accessibility.
    - Review webhook event logs in Stripe Dashboard.

2.  **Credit Consumption Errors**

    - Ensure credit events are properly configured.
    - Verify organization has sufficient credit balance.
    - Check for inactive credit events.

3.  **Subscription Sync Issues**
    - Manually trigger webhook replay from Stripe Dashboard.
    - Verify customer metadata includes organization_id.
    - Check subscription status mapping.

### Debug Tools

- Stripe Dashboard webhook logs.
- Application logs for billing operations.
- Database queries for credit transactions.
- Customer portal for subscription management.

## Future Enhancements

### Planned Features

1.  **Usage Analytics**

    - Detailed usage reports.
    - Cost optimization recommendations.
    - Predictive analytics.

2.  **Advanced Billing**

    - Usage-based billing.
    - Tiered pricing models.
    - Enterprise custom pricing.

3.  **Credit Management**

    - Credit gifting/transfers.
    - Bulk credit operations.
    - Credit expiry notifications.

4.  **Integration Enhancements**
    - Multiple payment methods.
    - International payment support.
    - Tax calculation integration.

## Support

For issues related to the billing system:

1.  Check the application logs for error details.
2.  Review Stripe Dashboard for payment/webhook issues.
3.  Verify environment variable configuration.
4.  Consult this documentation for common solutions.

## API Reference

### Subscription Management

- `GET /api/billing/plans` - List subscription plans.
- `POST /api/billing/subscription/checkout` - Create subscription checkout.
- `GET /api/billing/subscription/{org_id}` - Get organization subscription.
- `POST /api/billing/subscription/portal` - Access customer portal.

### Credit Management

- `GET /api/billing/credits/{org_id}` - Get credit balance.
- `POST /api/billing/credits/consume` - Consume credits.
- `GET /api/billing/credit-products` - List credit products.
- `POST /api/billing/credit-products/checkout` - Purchase credits.

### Billing Information

- `GET /api/billing/summary/{org_id}` - Get billing summary.
- `GET /api/billing/history/{org_id}` - Get billing history.
- `POST /api/billing/webhook/stripe` - Stripe webhook endpoint.

## Deployment Notes

### 1. Stripe Account Setup

- Create subscription products and prices.
- Configure webhook endpoints.
- Set up customer portal settings.
- Test payment flows.

### 2. Database Migration

```bash
cd backend
alembic upgrade head
```

### 3. Environment Configuration

- Set Stripe API keys.
- Configure webhook secrets.
- Update Supabase connection.

### 4. Production Considerations

- Set up monitoring and alerting.
- Configure payment method settings.
- Implement tax calculation if needed.
- Set up backup and recovery.

## Benefits Delivered

- **Complete Stripe Integration** - Production-ready payment processing.
- **Flexible Credit System** - Configurable usage-based billing.
- **Multi-Tenant Architecture** - Organization-scoped billing management.
- **Real-time Synchronization** - Webhook-driven state management.
- **Comprehensive UI** - User-friendly billing dashboard.
- **Audit Trail** - Complete transaction history and compliance.
- **Scalable Design** - Built for growth and feature expansion.

The billing system is now fully functional and ready for production deployment with proper Stripe configuration! 🚀
