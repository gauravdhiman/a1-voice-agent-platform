# Plan Publish Spec — Free / Starter / Pro / Scale (Approved Pilot Catalog)

> **Approved pricing direction.** Configure paid plans through the authenticated
> Plan Catalog admin after Stripe Test prices are created and reviewed. Paid
> plans are not seeded from code or worktree fixtures. Repeat the object and
> price-ID mapping in Stripe Live mode and the Production Plan Catalog before
> charging a customer. See `05-pilot-billing-runbook.md` for the exact steps.

## Design constraints (locked)

- Metering engine untouched: `ceil(min) × 10 credits/min`, settle order
  plan → bonus → purchased.
- Minutes in marketing, credits inside: bundles convert at 10 cr/min.
- 40 credits equal $1 of purchased-credit value. One extra US local number
  consumes 80 credits/month ($2 equivalent) from the shared balance.
- Platform-provided number search and purchase are US-only in v1. Existing
  non-US local rentals retain the legacy 200-credit rate; customer-owned Twilio
  imports remain a separate, non-rental flow. Mobile numbers are not offered
  for new purchases; existing mobile rentals retain their legacy rate until
  vendor cost and margin are reviewed.
- Reconcile actual per-minute provider and infrastructure cost after the first
  2–3 customers; the current free-tier deployment is not a concurrency SLA.

## Proposed catalog (USD)

| Tier | Monthly price | Annual price¹ | Included credits | Up to call minutes² |
|---|---:|---:|---:|---:|
| Free | $0 | — | 100/month | 10/month |
| Starter | $49/month | $490/year | 2,500/month | 250/month |
| Pro | $149/month | $1,490/year | 10,000/month | 1,000/month |
| Scale | $299/month | $2,990/year | 21,000/month | 2,100/month |

¹ Annual plans charge the price of 10 monthly payments for 12 months of service
(two months free) and grant 12 times the monthly credits.

² 10 credits/minute, rounded up per connected call; numbers and other paid
usage reduce the same available credit balance. Minutes are a maximum
equivalent, not a promise of uninterrupted utilization.

Feature flags: `credit_topup_enabled=true` all paid tiers;
`embed_widget=true` all; `custom_branding` Pro+; `premium_tools`
Scale only. The pilot premium integrations are Gmail, Google Sheets, HubSpot
lead capture, and Cal.com scheduling; these are the integrations marked premium
in the platform catalog and shown in the entitlement description.

Plan highlights for the published cards:

- **Free:** one voice agent, one member, 100 monthly credits, and one standard
  voice profile. It has no platform-provided phone-number purchase allowance.
- **Starter:** 2,500 monthly credits, embed widget, credit top-ups, one US local
  platform number on request, and additional US local numbers at 80 credits per
  month each.
- **Pro:** Starter features plus custom branding and 10,000 monthly credits.
- **Scale:** Pro features plus Gmail, Google Sheets, HubSpot lead capture,
  Cal.com scheduling, and 21,000 monthly credits.

Customer-facing plan-card descriptions:

| Tier | Description |
|---|---|
| Starter | For solo owners and small shops handling a steady flow of calls. |
| Pro | For busy teams with higher call volumes and custom branding needs. |
| Scale | For larger, multi-location teams handling high call volumes. |

All paid tiers include one standard voice profile. Optional provider voices use
BYOK (bring your own keys); provider usage is billed directly by that provider.
The platform credit meter applies to connected call minutes and platform phone
number rentals, not the customer's provider account usage.

Annual versions, when offered, charge exactly 10 monthly payments for 12 months
of service (two months free). Their included-credit entitlement must equal 12
times the monthly allowance so the call-minute allowance remains consistent
throughout the year. At the approved monthly prices, the annual prices are
$490 Starter, $1,490 Pro, and $2,990 Scale.

## Pilot safeguards

- No fourth public fixed plan. Higher call volume, multiple locations, and
  tailored onboarding go through `/contact` while pilot economics are
  measured.
- One standard voice profile is included. Optional provider voices use BYOK
  (bring your own keys); the provider bills the customer directly for its
  service, and 24x7 AI does not add a provider usage charge.
- Set `max_phone_numbers` to unlimited on paid plans and zero on Free. One US
  local DID is included on request. Customer-owned Twilio numbers remain
  at no platform rental cost; existing carrier numbers need call forwarding to
  a connected number, with carrier fees confirmed by the customer.
- The included number stays free while paid-plan access is active. If retained
  after the plan ends, it renews at 80 credits/month from the shared balance;
  the cancellation dialog discloses this and the normal rental grace applies.
- Keep auto-reload off. Review credit use, top-up rates, call duration,
  provider spend, infrastructure, support, and failed payments after 2–3
  customer pilots before revising price or announcing concurrency capacity.

## Publish checklist (founder + reviewer)

- [ ] Pilot COGS/min and peak concurrency reviewed from actual call traces
- [ ] Stripe Products/Prices created (test → live), price ids recorded
- [ ] `plan_versions` drafted via Plan Catalog admin, `preview` reviewed
- [ ] Only Free, Starter, Pro, and Scale are current for signup; retire older public signup versions such as Enterprise without changing existing subscriptions
- [ ] Migration mode `new_signups_only`; grandfathering note for Trial
- [ ] Top-up credit products match $5/200, $10/400, and $25/1,000
- [ ] System pricing shows 10 credits per call minute, 80 credits per extra US local number-month, and preserves the legacy non-US local rate at 200 credits/month
- [ ] Existing mobile rental rate remains clearly marked legacy; new mobile inventory is disabled pending a vendor cost review
- [ ] Onboarding + billing pages show minutes-equivalence (Epic C1 done)
- [ ] Phone-number setup explains the included line, credit add-on, Twilio import, and carrier forwarding
- [ ] Live Price IDs and webhook settings are verified in production separately from Test mode
- [ ] Staging checkout → webhook → grant verified end-to-end (Epic C gate)
