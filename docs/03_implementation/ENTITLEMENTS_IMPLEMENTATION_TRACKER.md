# Entitlements Implementation Tracker

**Started:** 2026-08-07  
**Spec:** [plan_entitlements_and_limits.md](./plan_entitlements_and_limits.md)  
**ADR:** [ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md](../01_architecture/ADR_PLAN_VERSIONING_AND_ENTITLEMENTS.md)

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
| `/admin/entitlements` catalog CRUD | ⏸ | |
| `/admin/plans` product + version editor | ⏸ | |
| Publish dialog + migration policy | ⏸ | |

---

## Phase 5 — Credits, PAYG, voice-ws

| Item | Status | Notes |
|------|--------|-------|
| Credit grant from version on renewal | ⏸ | |
| PAYG handlers | ⏸ | |
| voice-ws pre-call entitlement check | ⏸ | |
| `max_concurrent_calls` | ⏸ | |

---

## Test coverage (Phase 1 modules)

| Module | Target | Current |
|--------|--------|---------|
| `entitlement_models.py` | ≥90% | **100%** |
| `entitlement_service.py` | ≥90% | **94%** |
| `entitlement_handlers.py` | ≥90% | **88%** |
| **Combined** | ≥90% | **94%** |

Full billing suite: **68 passed**, 6 skipped (2026-08-07).

---

## Commits / review checkpoints

| Checkpoint | Ready for commit when | User testing needed? |
|------------|----------------------|---------------------|
| **CP-1** ✅ | Phase 0 migration + Phase 1 code + tests green | Migration applied locally |
| **CP-2** ✅ | Publish API + webhook binding | |
| **CP-3** 🚧 | Migration scheduler + billing UX | Ready for review |
| CP-4 | Admin UI + browser validation | Yes — plan editor + checkout |

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
| 2026-08-07 | **CP-2 in progress:** PlanVersionService publish/grandfathering, admin publish route, webhook plan_version_id binding, 8 new tests (63 billing passed) |
| 2026-08-07 | **CP-3 complete:** Plan migration scheduler, self-service migrate API, billing UI legacy/grace banner, cancel dialog policy copy, 68 billing tests + vitest |
