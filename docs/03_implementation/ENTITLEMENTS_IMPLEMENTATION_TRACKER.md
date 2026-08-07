# Entitlements Implementation Tracker

**Started:** 2026-08-07  
**Last updated:** 2026-08-07  
**Spec:** [plan_entitlements_and_limits.md](./plan_entitlements_and_limits.md)  
**ADR:** [ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md](../01_architecture/ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md)

## Current status (read this first)

| | |
|---|---|
| **Completed** | Phases 0–5 (through credits, PAYG, voice-ws pre-call checks) |
| **Committed** | CP-1 ✅, CP-2 ✅, CP-3 ✅, CP-4 ✅ (user confirmed earlier) |
| **Ready to commit** | CP-5 — credits/PAYG/voice-ws entitlement enforcement |
| **Next up** | Post-feature validation on cloud; optional Stripe Billing Meters |
| **Deferred validation** | Local billing UI smoke; full E2E on 24x7 AI cloud after feature complete |

### Validation notes (local vs cloud)

| Area | Local dev | Cloud (24x7 AI) | Notes |
|------|-----------|-----------------|-------|
| Plans / Credits tabs | Often empty | Works (Stripe catalog) | **Pre-existing** local setup gap — not caused by entitlements work |
| Manage tab | Hidden without active/trial sub | Same rule | Manage only renders when `subscription.status ∈ {active, trial}` |
| Phase 3 UI (legacy badge, migration banner, cancel copy) | Not visible without sub + migration state | Validate after Phase 4 or end-of-feature | Code shipped in CP-3; UI is conditional |

**Decision (2026-08-07):** Defer local billing UI validation until Phase 4+ or final pass on deployed environment.

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
| Draft / clone / full admin CRUD | ⏸ | Phase 4 admin UI |

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

## Phase 5 — Credits, PAYG, voice-ws

| Item | Status | Notes |
|------|--------|-------|
| Credit grant from version on renewal | ✅ | `credit_entitlement_service` + invoice webhook |
| PAYG handlers / consumption | ✅ | `evaluate_consumption` in `consume_credits` |
| voice-ws concurrent + credit pre-check | ✅ | `shared/billing/voice_session_entitlement.py` |
| `max_concurrent_calls` handler | ✅ | `ConcurrentCallsHandler` + call log tracking |
| Tests | ✅ | credit entitlement, PAYG consume, shared precheck |

---

## Post-feature / optional

| Item | Status | Notes |
|------|--------|-------|
| Stripe Billing Meters (optional PAYG) | ⏸ | Spec optional |
| Cloud E2E billing + voice validation | ⏸ | Deferred per user |

---

## Test coverage (Phase 1 modules)

| Module | Target | Current |
|--------|--------|---------|
| `entitlement_models.py` | ≥90% | **100%** |
| `entitlement_service.py` | ≥90% | **94%** |
| `entitlement_handlers.py` | ≥90% | **88%** |
| **Combined** | ≥90% | **94%** |

Full billing suite: **68 passed**, 6 skipped (2026-08-07).

Additional Phase 2–3 tests: `test_plan_version_service.py` (6), `test_webhook_plan_version.py` (2), `test_plan_migration_service.py` (6), cancel-dialog vitest (1).

---

## Key files (by phase)

| Phase | Backend | Frontend |
|-------|---------|----------|
| 0–1 | `entitlement_service.py`, `entitlement_handlers.py`, migration `20260807000002` | — |
| 2 | `plan_version_service.py`, `admin_plan_routes.py`, `webhook_handler.py` | — |
| 3 | `plan_migration_service.py`, `plan_migration_scheduler.py`, `routes.py` (migrate) | `plan-migration-banner.tsx`, `subscription-management.tsx`, `cancel-subscription-dialog.tsx` |
| 4 | TBD admin plan CRUD routes | TBD `/admin/plans`, `/admin/entitlements` |

---

## Commits / review checkpoints

| Checkpoint | Ready for commit when | User testing needed? |
|------------|----------------------|---------------------|
| **CP-1** ✅ | Phase 0 migration + Phase 1 code + tests green | Migration applied locally |
| **CP-2** ✅ | Publish API + webhook binding | Committed |
| **CP-3** ✅ | Migration scheduler + billing UX | Committed or ready — **local UI validation deferred** |
| **CP-4** ⏳ | Admin UI (Phase 4) | After implementation; validate on cloud |

### CP-1 — Before you commit / test

1. Review changed files (migration + backend entitlement modules + tests).
2. **Run migration** (requires your approval per project rules):
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
| 2026-08-07 | **CP-5 complete:** Credit grant from plan version, PAYG consumption, voice-ws pre-call + concurrent tracking |
