# ADR: Subscription-Aware Onboarding and Credit Policy

**Status:** Accepted; baseline implemented
**Date:** 2026-08-08
**Deciders:** Platform architecture
**Related:** [Plan Versioning & Entitlements](./ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md), [Plan Entitlements & Limits](../03_implementation/plan_entitlements_and_limits.md), [Billing Overview](../02_features/billing/overview.md), [Database Schema](../DATABASE_SCHEMA.md)

## Context

Founder onboarding previously mixed organization setup with agent creation,
phone purchasing, test calls, and implicit subscription assumptions. That made a
new organization depend on billing data that might not exist yet and made the
free plan indistinguishable from a paid plan with a zero price.

The platform also needs to support recurring paid subscriptions, a usable free
plan, immutable plan versions, expiring plan credits, non-expiring purchased
credits, and future credit sources such as administrator grants and referrals.
These concerns must be explicit and server-owned so the browser cannot select a
stale plan, bypass a billing gate, or create duplicate credit grants.

## Decision

### 1. Founder onboarding is organization setup plus plan activation

The founder flow is:

1. Authenticate and provision the organization and organization administrator.
2. Save organization details, including the IANA timezone.
3. Select a currently published plan version.
4. Activate a free version locally or complete paid Stripe Checkout.
5. Confirm the resulting subscription is active or trialing.
6. Mark onboarding complete and enter the dashboard.

Agent creation, phone-number purchase, tool configuration, and test calls are
dashboard workflows. They are intentionally not part of founder onboarding.
Invited users join the inviting organization and bypass the founder plan gate;
they do not create a second organization or complete founder onboarding.

### 2. Plan selection uses immutable, versioned catalog entries

New signups may select only a published `plan_versions` row marked
`is_current_for_signup`. An organization subscription stores
`plan_version_id`, so runtime entitlements continue to use the exact version
the organization selected. Published versions are not edited in place; a
catalog change creates and publishes a new version.

`plan_versions.billing_mode` is the authoritative payment classification:

- `free`: activate in the application without Stripe.
- `paid`: require a non-null Stripe Price and use Stripe Checkout.

The application must not infer billing mode from plan names, slugs, zero prices,
Stripe metadata, or the presence of a Stripe identifier. Stripe metadata is a
debugging and webhook-resolution aid, not the entitlement source of truth.

### 3. Free activation is a first-class, idempotent operation

Free activation creates or reactivates an active organization subscription with
null Stripe customer, subscription, and payment identifiers. It validates that
the selected version is published, current for signup, and explicitly marked
`billing_mode = free`.

The operation is safe to retry. If the subscription row was written but the
initial grant failed, replaying activation reuses the same grant key and repairs
the credit state without creating a second subscription or double-crediting the
organization.

### 4. Paid activation is webhook-confirmed

Paid checkout validates `billing_mode = paid`, the published/current version,
and the Stripe Price before creating Checkout. The authenticated billing user's
email is supplied by the server when creating the Stripe customer; it is never
trusted from the browser request.

Stripe webhooks bind the subscription to the selected `plan_version_id`. The
onboarding return page polls the server after a successful Checkout return,
because the browser can return before the webhook has committed the subscription.
Only an `active` or `trial` activation state can complete founder onboarding;
cancelled, failed, incomplete, or past-due states return the user to plan
selection or show a retry state. The plan picker presents the catalog's monthly
and annual intervals and handles loading, cancellation, failure, and webhook
polling states; these are UI representations of the server contract, not a
second billing decision layer.

### 5. Credit grants are policy-driven and idempotent

`plan_versions.credit_grant_policy` explicitly distinguishes:

- `recurring`: grant plan credits for each eligible billing period.
- `one_time`: grant the plan allocation once, with no recurring refresh.

Paid recurring grants are driven by successful invoice processing. Free recurring
grants have no Stripe event, so the application scheduler advances them using
the subscription period and the same shared grant service. A stable grant key
and the `grant_subscription_credits` PostgreSQL function make each grant
atomic and idempotent.

The current implementation deliberately uses two pools:

- plan credits: period-bound and expiring;
- purchased credits: non-expiring top-up balance.

Consumption is centralized and drains plan credits before purchased credits.
The `debit_organization_credits` function locks the organization row and updates
both pools atomically, preventing concurrent voice sessions from overspending
prepaid balance. Pay-as-you-go credit headroom is not part of the current model.

The long-term direction is a source-aware grant/lot ledger with explicit
`plan`, `purchase`, `admin_grant`, and `referral` sources plus allocation
references. That richer ledger, administrator grant UI, and referral rewards are
future scope; the current two-pool model must not be documented as if those
features already exist.

### 6. Entitlements are enforced from the bound version

`EntitlementService` resolves the organization subscription's bound plan
version and applies registered handlers. Enforcement includes:

- `max_agents` when creating agents;
- `max_concurrent_calls` before voice sessions;
- `premium_tools` when attaching premium tools; and
- `credit_topup_enabled` before top-up checkout.

The seeded free version is intentionally usable after onboarding: it allows one
agent and includes 100 credits per recurring period. The exact values remain
catalog data and must be changed through a new plan version, not hard-coded into
the onboarding UI.

### 7. Grandfathering and cancellation remain explicit

Existing subscribers remain on their bound version when a newer version is
published. Migration policy, grace periods, migration rows, and the daily
migration scheduler handle any later move. Voluntary cancellation is
cancel-at-period-end with no refund; the bound version and its entitlements remain
available until `current_period_end`.

### 8. Renewal policy is period-based

The initial scheduler does not attempt historical catch-up for missed free-plan
periods. It grants the current eligible period once and advances the period
boundary. If future products require catch-up, carry-over, annual billing with
monthly credits, or more complex grant schedules, those policies must be added
to the credit-grant contract and covered by idempotency tests before changing the
scheduler.

## Current implementation map

| Concern | Implementation |
|---|---|
| Customer plan catalog | `GET /api/v1/billing/plans/available` |
| Free activation | `POST /api/v1/billing/subscription/free` |
| Paid checkout | `POST /api/v1/billing/checkout/versioned-subscription` |
| Activation polling | `GET /api/v1/billing/subscription/status/{organization_id}` |
| Completion guard | `POST /api/v1/organizations/{organization_id}/complete-onboarding` |
| Plan-version admin catalog | `backend/src/billing/admin_plan_routes.py` and `/platform/plans` |
| Entitlement catalog admin UI | `/platform/entitlements` |
| Free recurring renewal | `backend/src/billing/free_plan_renewal_scheduler.py` |
| Paid recurring renewal | Stripe invoice webhook → shared credit-grant service |
| Atomic credit grant | `grant_subscription_credits` PostgreSQL function |
| Atomic credit debit | `debit_organization_credits` PostgreSQL function |

The supporting schema changes are recorded in migrations
`20260807000002` through `20260808000012` and in
[DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md).

## Consequences

Positive consequences:

- onboarding no longer depends on agent, phone, or test-call side effects;
- free and paid billing flows are explicit and independently testable;
- published terms are grandfathered and runtime enforcement is version-bound;
- Stripe retries, browser refreshes, scheduler retries, and webhook redelivery
  cannot create duplicate subscriptions or credit grants when the same
  idempotency keys are used.

Trade-offs:

- activation completion is asynchronous for paid plans because webhooks are the
  source of payment truth;
- free recurring credit renewal requires an application scheduler;
- the current two-pool model is simpler than the planned source-aware ledger but
  must eventually be extended before admin grants or referral rewards are added;
- catalog administration and migration require more schema and operational
  tooling than a mutable flat plan table.

## Validation requirements

The behavior is covered by focused tests for:

- free activation versus paid Checkout and explicit billing mode;
- version selection, plan-version binding, and webhook resolution;
- onboarding completion guards, paid return polling, cancellation, and the
  absence of agent creation during founder onboarding;
- recurring versus one-time credit policy;
- idempotent subscription grants and atomic plan-first credit consumption;
- max-agent, premium-tool, top-up, and voice-session entitlement gates.

Run the focused suites with:

```bash
(cd backend && pytest -q tests/billing)
(cd frontend && npm run test:run -- src/app/onboarding/page.test.tsx src/components/onboarding/__tests__/step-plan-selection.test.tsx)
```
