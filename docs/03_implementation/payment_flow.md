# Payment Flow Implementation

This document describes the payment flows currently implemented for 24x7 AI.
The organization billing page and founder signup use the same versioned,
subscription-aware customer catalog documented below. The original flat
`subscription_plans` checkout remains available only as a compatibility path
for grandfathered records and webhook fallback handling; it is not used to
render or start new customer subscriptions.

> **Current source of truth:** [Subscription-Aware Onboarding and Credit Policy](../01_architecture/ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md)
> defines the decisions. This page is an implementation reference; it should
> not be read as permission to infer free/paid status from a price or Stripe
> metadata.

## Current founder activation flow

```text
Authenticate → provision organization → save organization details
→ select published/current plan version
→ free activation without Stripe OR backend-created paid Checkout
→ Stripe webhook binds the plan version and subscription
→ onboarding polls for active/trial → dashboard
```

Agent creation, phone purchase, tool configuration, and test calls are deferred
to the dashboard. Invited users join the inviting organization and bypass the
founder plan gate.

The versioned customer endpoints are:

- `GET /api/v1/billing/plans/available`
- `POST /api/v1/billing/subscription/free`
- `POST /api/v1/billing/checkout/versioned-subscription`
- `POST /api/v1/billing/subscription/plan-change/preview`
- `POST /api/v1/billing/subscription/plan-change/confirm`
- `GET /api/v1/billing/subscription/status/{organization_id}`
- `POST /api/v1/organizations/{organization_id}/complete-onboarding`

Free activation requires a published version with `billing_mode = free` and
stores null Stripe identifiers. Paid checkout requires `billing_mode = paid`
and a Stripe Price. The authenticated user's email is used for the Stripe
customer. A successful browser return is not payment confirmation; the UI waits
for the webhook-backed activation status. Active subscriptions use the
plan-change preview/confirm pair so a target internal plan is validated before
Stripe is changed.

## 🚀 What Was Implemented

### Backend Enhancements

#### 1. **Billing API Endpoints** (`backend/src/billing/routes.py`)

- `POST /api/v1/billing/checkout/versioned-subscription` - Versioned founder checkout
- `POST /api/v1/billing/subscription/free` - Free plan activation without Stripe
- `POST /api/v1/billing/credit-products/checkout` - Credit top-up checkout
- `POST /api/v1/billing/subscription/portal` - Stripe Customer Portal session
- `POST /api/v1/billing/subscription/cancel` - Cancel at period end
- `POST /api/v1/billing/subscription/reactivate` - Reactivate before period end
- `POST /api/v1/billing/subscription/plan-change/preview` - Preview an internal plan transition
- `POST /api/v1/billing/subscription/plan-change/confirm` - Confirm an internal plan transition

The older non-versioned subscription checkout endpoints remain for grandfathered
legacy records and webhook fallback handling. The organization billing page and
new signup must use the versioned endpoints above.

#### 2. **Enhanced Stripe Service** (`backend/src/billing/stripe_service.py`)

- `create_subscription_checkout_session()` - Handles subscription checkout creation
- `create_credits_checkout_session()` - Handles credit purchase checkout creation
- `create_customer_portal_session()` - Creates customer portal for self-service
- `reactivate_subscription()` - Reactivates cancelled subscriptions

#### 3. **Cleaned Migration** (`backend/alembic/versions/b1c2d3e4f5g6_add_billing_and_subscription_tables.py`)

- Removed data seeding from migration (pure schema focus)
- Follows best practices for database migrations

#### 4. **Stripe-Integrated Seed Script** (`backend/scripts/seed_billing_data.py`)

- Fetches subscription plans directly from Stripe
- Fetches credit products from Stripe with metadata validation
- Dry-run support for testing
- Ensures database stays in sync with Stripe

### Frontend Implementation

#### 1. **Plan Selection Component** (`frontend/src/components/billing/plan-selection.tsx`)

- Loads published internal `plan_products`/`plan_versions` through
  `GET /api/v1/billing/plans/available`
- Displays entitlements authored in the platform catalog
- Monthly vs Annual plan separation
- Tier-rank ordering with current-plan highlighting and unrestricted eligible target selection
- Preview dialog showing effective timing, proration, price/credit deltas, and purchased-credit preservation
- Trial period metadata when supplied by the catalog
- Free activation or backend-created Stripe Checkout for paid versions

#### 2. **Credit Purchase Component** (`frontend/src/components/billing/credit-purchase.tsx`)

- Credit package comparison
- Best value highlighting
- Cost per credit calculation
- Usage tips and guidance
- Optional navigation focus when opened from the Overview tab's Buy credits action

#### 3. **Subscription Management** (`frontend/src/components/billing/subscription-management.tsx`)

- Current subscription overview
- Overview-level Change plan action
- Cancellation/reactivation controls
- Customer Portal integration
- Billing date information
- Status indicators

#### 4. **Enhanced Billing Service** (`frontend/src/services/billing-service.ts`)

- `getAvailablePlanVersions()` - Loads the internal published plan catalog
- `activateFreePlan()` - Activates a free internal plan without Stripe
- `createVersionedSubscriptionCheckout()` - Resolves the internal version to its Stripe Price
- `createCreditsCheckout()` - Initiates credit purchase
- `cancelSubscription()` - Cancels subscription
- `reactivateSubscription()` - Reactivates subscription

#### 5. **Post-Checkout Pages**

- `/billing/success` - Payment success confirmation
- `/billing/cancel` - Payment cancellation handling

#### 6. **Updated Main Billing Page** (`frontend/src/app/(dashboard)/organization/billing/page.tsx`)

- Integrated all new components
- Tabbed interface (Overview, Plans, Credits); Overview contains the current
  subscription controls plus Change plan and Buy credits actions
- Credits tab renders the balance summary first, credit purchase packages second,
  and detailed usage and the full ledger after the purchase action
- Free subscriptions do not open Stripe Customer Portal because they have no
  Stripe customer; the UI explains this inline and the API rejects portal
  requests with a clear conflict response
- Responsive design
- Real-time data refresh

## 🔄 Complete User Journey

### 1. **Founder Plan Activation Flow**

```
User saves organization details → Views published plan versions →
Free activation without Stripe OR backend creates paid Checkout →
Stripe webhook binds subscription → onboarding polls activation status →
onboarding completion guard → dashboard
```

### 2. **Post-Onboarding Billing Flow**

```
User visits /organization/billing → Views internal plan/credit management →
Selects a published internal plan version → free activation or backend-created
Stripe Checkout → webhook updates billing state →
Billing UI refreshes subscription and credit balances
```

### 3. **Credit Purchase Flow**

```
User visits /billing → Overview Buy credits action or Credits tab →
Selects credit package →
Redirected to Stripe Checkout → Completes payment →
Credits added to account → Success confirmation
```

### 4. **Subscription Management Flow**

```
User with active subscription → Overview tab →
Can cancel/reactivate → Access Customer Portal →
Self-service billing management
```

## 🔧 Environment Requirements

### Required Environment Variables

**Each selected root environment file needs:**

```bash
# Stripe Configuration (Backend)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret_here

# Stripe Configuration (Frontend)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here
```

Use `.env.local` for local Supabase, `.env.staging` for cloud staging, and
`.env.prod` for production. Do not copy any environment file into a root
`.env`; see [Environment Configuration](../05_operations/environment_configuration.md).

**Note:** The publishable key is needed for the frontend Stripe integration.

## 📋 Setup Checklist

### 1. **Stripe Setup** (Required)

- [ ] Configure products and prices in Stripe Dashboard
- [ ] Add required metadata to Stripe products (see `backend/scripts/README_STRIPE_SETUP.md`)
- [ ] Set up webhook endpoints for subscription events

### 2. **Database Setup**

- [ ] Run migration: `alembic upgrade head`
- [ ] Run seed script: `python backend/scripts/seed_billing_data.py`
- [ ] Verify data: `python backend/scripts/seed_billing_data.py --dry-run`

### 3. **Frontend Setup**

- [ ] Ensure all billing components are imported correctly
- [ ] Test plan selection redirects to Stripe
- [ ] Verify success/cancel page routes work

## Credit and entitlement behavior

Plan versions declare `billing_mode` and `credit_grant_policy`. Paid recurring
credits come from successful invoice webhooks; free recurring credits come from
the application scheduler. Plan credits expire at the period boundary and are
consumed before non-expiring purchased credits. Grants and debits use atomic,
idempotent PostgreSQL functions so retries and concurrent voice sessions do not
double-apply balance changes. Pay-as-you-go is not part of the current model.

## Key Benefits Achieved

✅ **Complete Payment Integration** - Users can now actually subscribe and pay  
✅ **Stripe Data Validation** - Database stays in sync with Stripe pricing  
✅ **Self-Service Management** - Users can manage subscriptions independently  
✅ **Professional UI/UX** - Beautiful, responsive billing interface  
✅ **Error Handling** - Proper error states and user feedback  
✅ **Mobile Responsive** - Works on all device sizes  
✅ **Type Safety** - Full TypeScript integration

## 🚨 What Was Missing Before

❌ No frontend payment forms  
❌ No Stripe Checkout integration  
❌ No subscription upgrade/downgrade flows  
❌ No credit purchase capability  
❌ No customer portal access  
❌ Data seeding mixed with migrations  
❌ Manual pricing sync with Stripe

## 🔗 Flow Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Plan Selection │────│ Stripe Checkout  │────│ Payment Success │
│    (Frontend)    │    │   (Stripe UI)    │    │   (Frontend)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Checkout Session│────│   Webhook Event  │────│  Update Database│
│    (Backend)    │    │    (Stripe)      │    │    (Backend)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🔮 Next Steps

1. **Test the complete flow** with Stripe test cards
2. **Set up webhook handling** for subscription lifecycle events
3. **Configure Customer Portal** settings in Stripe Dashboard
4. **Add analytics tracking** for conversion metrics
5. **Implement plan upgrade/downgrade** workflows
6. **Add invoice download** functionality
7. **Set up email notifications** for billing events

This implementation provides the baseline payment and entitlement flows. Cloud
Stripe billing, staging validation, and production operational readiness remain
environment-specific validation activities rather than assumptions made by the
local test suite.
