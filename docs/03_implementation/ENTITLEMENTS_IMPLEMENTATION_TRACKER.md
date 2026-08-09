# Entitlements Implementation Tracker

**Started:** 2026-08-07
**Last updated:** 2026-08-08
**Spec:** [plan_entitlements_and_limits.md](./plan_entitlements_and_limits.md)
**ADR:** [ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md](../01_architecture/ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md)
**Onboarding ADR:** [ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md](../01_architecture/ADR_SUBSCRIPTION_AWARE_ONBOARDING_AND_CREDIT_POLICY.md)

## Current status (read this first)

| | |
|---|---|
| **Completed** | Phases 0–5 plus subscription-aware founder onboarding and explicit free/paid activation |
| **Implemented** | CP-1 ✅ through CP-5 ✅, including atomic grant/debit RPCs and admin catalog UI |
| **Current focus** | Keep focused tests and operational documentation aligned; validate billing flows against the selected local/staging data set |
| **Deferred / future** | Cloud billing E2E, full source-aware credit-lot ledger, admin/referral grants, and optional Stripe Billing Meters |

### Validation notes (local vs cloud)

| Area | Local dev | Cloud (24x7 AI) | Notes |
|------|-----------|-----------------|-------|
| Plans / Credits tabs | Often empty | Works (Stripe catalog) | **Pre-existing** local setup gap — not caused by entitlements work |
| Manage tab | Hidden without active/trial sub | Same rule | Manage only renders when `subscription.status ∈ {active, trial}` |
| Phase 3 UI (legacy badge, migration banner, cancel copy) | Not visible without sub + migration state | Validate after Phase 4 or end-of-feature | Code shipped in CP-3; UI is conditional |

**Decision (2026-08-08):** The implementation is complete enough for focused local
validation. Cloud billing and voice validation remains a separate environment
activity because it depends on Stripe and the staging/production data sets.
Empty local billing catalog data is an environment/seed issue, not a reason to
reintroduce plan logic into onboarding.

## Status legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Done |
| 🚧 | In progress |
| ⏳ | Pending |
| ⏸ | Blocked / deferred |

---

## Phase 0 — Schema & catalog

| Item | Status | Notes |
|------|--------|-------|
| Alembic migration (`plan_products`, `plan_versions`, …) | ✅ | `20260807000002` — **applied on local dev** |
| Seed `entitlement_definitions` catalog | ✅ | In migration |
| Backfill `subscription_plans` → `plan_versions` v1 | ✅ | In migration |
| Add `organization_subscriptions.plan_version_id` | ✅ | In migration |
| Seed default **free** plan product/version | ✅ | In migration |
| Update `DATABASE_SCHEMA.md` | ✅ | Planned tables section added |

---

## Phase 1 — EntitlementService core

| Item | Status | Notes |
|------|--------|-------|
| Pydantic models (`entitlement_models.py`) | ✅ | |
| Handler registry (`entitlement_handlers.py`) | ✅ | `limit.max_count`, `limit.max_agents`, `feature.flag` |
| `EntitlementService` | ✅ | Resolve via `plan_version_id` |
| Cancel-at-period-end: full access while `active` | ✅ | Tested in `test_entitlement_service.py` |
| Unit tests (`test_entitlement_service.py`) | ✅ | 10 tests |
| Handler tests (`test_entitlement_handlers.py`) | ✅ | |
| Free plan DB resolution test | ✅ | `test_entitlement_service_free_plan.py` |
| `GET /api/v1/billing/entitlements/{org_id}` | ✅ | |
| Enforce `max_agents` on `POST /agents` | ✅ | 403 + `entitlement_denied` payload |
| Route tests for agent limit | ✅ | `TestAgentCreateEntitlementLimits` |
| `plan_version_id` on Pydantic subscription models | ✅ | `billing/models.py` |

---

## Phase 2 — Publish & grandfathering

| Item | Status | Notes |
|------|--------|-------|
| `plan_version_service.py` (publish, resolve, migration rows) | ✅ | |
| `POST /api/v1/admin/plan-versions/{id}/publish` | ✅ | `admin_plan_routes.py` |
| `stripe_service.create_price()` | ✅ | Called on publish when draft has no price |
| Webhook: bind `plan_version_id` from Stripe price | ✅ | `webhook_handler.py` |
| Tests: publish grandfathering + webhook binding | ✅ | 8 new tests |
| Draft / clone / full admin CRUD | ✅ | `admin_plan_catalog_service.py`, `admin_plan_routes.py` |

---

## Phase 3 — Migration scheduler & UX

| Item | Status | Notes |
|------|--------|-------|
| Daily migration job | ✅ | `plan_migration_scheduler.py` (24h loop, started in `main.lifespan`) |
| `plan_migration_service.py` | ✅ | Auto-migrate on grace expiry + self-service migrate |
| `POST /api/v1/billing/subscription/migrate` | ✅ | |
| Entitlements API: migration + legacy version info | ✅ | Extended `OrgEntitlements` |
| Billing UI: legacy badge, grace countdown | ✅ | `plan-migration-banner.tsx` + subscription header badge |
| Fix cancel dialog copy (access until period end) | ✅ | No refund; full access until period end |
| Self-service migrate CTA | ✅ | Confirm dialog in `PlanMigrationBanner` |
| Tests | ✅ | 6 migration service tests + cancel dialog vitest |

---

## Phase 4 — Admin UI

| Item | Status | Notes |
|------|--------|-------|
| Admin API: entitlement catalog list/update | ✅ | `admin_plan_catalog_service.py`, routes |
| Admin API: plan products + draft CRUD + clone | ✅ | `admin_plan_routes.py` |
| `/platform/entitlements` catalog editor | ✅ | `platform-entitlements-manager.tsx` |
| `/platform/plans` product + version editor | ✅ | `platform-plans-manager.tsx` |
| Publish dialog + migration policy | ✅ | `plan-publish-dialog.tsx` → existing publish API |
| Nav entries (Plan Catalog, Entitlements) | ✅ | `nav-config.ts` |
| Tests | ✅ | `test_admin_plan_catalog_service.py`, `test_admin_plan_routes.py`, vitest publish dialog |

---

## Phase 5 — Credits, credit pools, voice-ws

| Item | Status | Notes |
|------|--------|-------|
| Credit grant from version on renewal | ✅ | `credit_entitlement_service` + invoice webhook |
| Two-pool consumption (plan → purchased) | ✅ | `allocate_consumption` in `consume_credits`; PAYG removed (migration `20260807000004`) |
| Low-balance alerts (20/10/5%) | ✅ | `_maybe_notify_low_balance` + `low_credit_threshold_notified` |
| `credit_topup_enabled` checkout gates | ✅ | both credit checkout routes → 403 when off |
| `premium_tools` attach gate | ✅ | `POST /tools/agent` → 403 when off; `platform_tools.is_premium` |
| voice-ws concurrent + credit pre-check | ✅ | `shared/billing/voice_session_entitlement.py` |
| `max_concurrent_calls` handler | ✅ | `ConcurrentCallsHandler` + call log tracking |
| Tests | ✅ | credit entitlement, two-pool consume, shared precheck |

---

## Post-feature / optional

| Item | Status | Notes |
|------|--------|-------|
| Stripe Billing Meters (optional) | ⏸ | Spec optional |
| Cloud E2E billing + voice validation | ⏸ | Deferred per user |

---

## Test coverage (Phase 1 modules)

| Module | Target | Current |
|--------|--------|---------|
| `entitlement_models.py` | ≥90% | **100%** |
| `entitlement_service.py` | ≥90% | **94%** |
| `entitlement_handlers.py` | ≥90% | **88%** |
| **Combined** | ≥90% | **94%** |

Focused billing suite: **150 passed**, 6 skipped (2026-08-08); this includes
plan versioning, free/paid activation contracts, admin catalog routes, credit
grants/debits, two-pool consumption, webhook handling, and entitlement gates.

Focused onboarding UI suite: **10 passed** across the onboarding page and plan
selection tests (2026-08-08). Additional migration and cancellation tests remain
in their module-specific suites.

---

## Key files (by phase)

| Phase | Backend | Frontend |
|-------|---------|----------|
| 0–1 | `entitlement_service.py`, `entitlement_handlers.py`, migration `20260807000002` | — |
| 2 | `plan_version_service.py`, `admin_plan_routes.py`, `webhook_handler.py` | — |
| 3 | `plan_migration_service.py`, `plan_migration_scheduler.py`, `routes.py` (migrate) | `plan-migration-banner.tsx`, `subscription-management.tsx`, `cancel-subscription-dialog.tsx` |
| 4 | `admin_plan_catalog_service.py`, `admin_plan_routes.py` | `/platform/plans`, `/platform/entitlements`, `platform-plans-manager.tsx`, `platform-entitlements-manager.tsx` |
| Onboarding | `versioned_subscription_service.py`, `free_plan_renewal_scheduler.py`, organization completion guard | `onboarding/page.tsx`, `step-plan-selection.tsx` |

---

## Commits / review checkpoints

| Checkpoint | Ready for commit when | User testing needed? |
|------------|----------------------|---------------------|
| **CP-1** ✅ | Phase 0 migration + Phase 1 code + tests green | Migration applied locally |
| **CP-2** ✅ | Publish API + webhook binding | Committed |
| **CP-3** ✅ | Migration scheduler + billing UX | Committed or ready — **local UI validation deferred** |
| **CP-4** ✅ | Admin UI (Phase 4) | Focused service/route/UI tests; cloud catalog smoke remains separate |
| **Onboarding** ✅ | Free activation, paid return polling, completion guard | Focused Vitest/backend tests; Stripe cloud E2E deferred |

### CP-1 — Before you commit / test

1. Review changed files (migration + backend entitlement modules + tests).
2. **Run migration** against the intended environment (requires approval per project rules):
   ```bash
   cd backend && alembic upgrade head
   ```
3. Re-run tests in Docker or `.venv-backend`:
   ```bash
   pytest tests/billing/test_entitlement_service.py tests/billing/test_entitlement_handlers.py \
     tests/billing/test_entitlement_service_free_plan.py \
     tests/voice_agents/test_agent_routes.py::TestAgentCreateEntitlementLimits -v
   ```
4. Optional smoke (after migration + dev stack up): create agents until limit blocks with 403.
5. For onboarding behavior, run the focused free/paid plan-selection and onboarding page tests.

## Current credit-model boundary

The shipped implementation uses two prepaid pools: period-bound plan credits
and non-expiring purchased credits. Consumption is plan-first and is protected
by an atomic database function. `credit_transactions` records the movement and
grant metadata, but this is not yet the long-term source-aware credit-lot ledger
described in the architecture plan. Do not add administrator or referral grant
UI until grant ownership, authorization, idempotency, and ledger allocation
references are designed and tested.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-07 | Tracker created; Phase 0–1 implementation started |
| 2026-08-07 | **CP-1 complete:** migration file, EntitlementService, max_agents enforcement, 21 new tests, 94% coverage on entitlement modules |
| 2026-08-07 | Migration `20260807000002` applied on local dev Docker stack |
| 2026-08-07 | **CP-2 complete:** PlanVersionService publish/grandfathering, admin publish route, webhook `plan_version_id` binding, 8 new tests |
| 2026-08-07 | **CP-3 complete:** Plan migration scheduler, self-service migrate API, billing UI legacy/grace banner, cancel dialog policy copy, 68 billing tests + vitest |
| 2026-08-07 | Local billing UI validation deferred (empty Plans/Credits locally is pre-existing; Manage tab requires active sub) |
| 2026-08-07 | **Next:** Phase 4 Admin UI |
| 2026-08-07 | **CP-4 complete:** Admin catalog UI + draft CRUD routes |
| 2026-08-07 | **CP-5 complete:** Credit grant from plan version, two-pool consumption (PAYG removed), low-balance alerts, premium-tools + top-up gates, voice-ws pre-call + concurrent tracking |
| 2026-08-08 | **Atomic debit:** `debit_organization_credits` Postgres RPC (`SELECT … FOR UPDATE`) so concurrent consumption cannot overspend prepaid balance; low-balance CTA uses `/organization/billing` |
| 2026-08-08 | **Subscription-aware onboarding:** organization details → explicit plan selection → free activation or paid Checkout → webhook-confirmed completion; agent creation moved to the dashboard and invited users retain their onboarding bypass |
| 2026-08-08 | **Credit policy hardening:** explicit `billing_mode` and `credit_grant_policy`; free plans activate without Stripe, free recurring grants use the application scheduler, and grant retries use `grant_subscription_credits` idempotency |
