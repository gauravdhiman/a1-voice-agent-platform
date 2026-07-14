# N1 Architecture Review — Implementation Status Report

**Date:** 2026-07-13  
**Reviewed against:** [`n1-architecture-review.md`](./n1-architecture-review.md)  
**Changes assessed:** Current working-tree diff (34 files, ~2,768 insertions) — **not yet committed**  
**Verdict:** **Mostly done for Epics A & B; Epic C partially done; Epic D partly done; Epic E correctly deferred.**

---

## 1. Executive summary

The follow-up work from the N1 architecture review has made **substantial progress**. The highest-risk items — permission vocabulary drift and the dual frontend permission systems — are largely addressed. Backend migration to declarative permission checks is **underway but incomplete**.

| Area | Review finding | Status today |
|------|----------------|--------------|
| Permission vocabulary lock-in (Epic A) | 🔴 High | ✅ **Done** |
| Single frontend permission API (Epic B) | 🔴 High | ✅ **Mostly done** (intentional role exceptions remain) |
| Backend auth migration (Epic C) | 🟠 Medium | 🟡 **In progress** (~50–60% of targeted routes) |
| Doc & IA cleanup (Epic D) | 🟠/🟡 Lower | 🟡 **Partial** |
| Custom roles / Phase 2 resolver (Epic E) | Deferred | ✅ **Correctly not started** |
| Security fixes from N1 branch | Already shipped | ✅ **Still in place** |
| Bug #35 (`basePath` skills flash) | Ship fix | ✅ **Fixed in code** |
| Bug #36 (local billing plan seed) | Separate track | ❌ **Not addressed** |

**Bottom line:** The review’s primary mitigation (Epics A → B → C before custom RBAC) is on track, but **Epic C is not finished**. Shipping custom roles before completing Epic C would still force rework.

---

## 2. Acceptance criteria (from review §14)

| # | Criterion | Met? | Notes |
|---|-----------|------|-------|
| 1 | One canonical permission matrix matches DB + call sites | ✅ Yes | [`permission-matrix.md`](../02_features/authentication_rbac/permission-matrix.md) + [`frontend/src/lib/permissions.ts`](../../frontend/src/lib/permissions.ts) |
| 2 | Page gates use `/me.permissions` (not dead ad-hoc strings) | 🟡 Mostly | `useUserPermissions` is now a facade over `useMyPermissions`; a few pages still gate on **role booleans** (see §5) |
| 3 | Dev grant-all fallback removed | ✅ Yes | Fail-closed; covered by [`use-user-permissions.test.tsx`](../../frontend/src/hooks/__tests__/use-user-permissions.test.tsx) |
| 4 | Majority of write endpoints use `require_permission` / helpers | 🟡 Partial | Agents + skills heavily migrated; phone numbers, tool routes, RBAC catalog, notifications still role-based |
| 5 | Design doc is as-implemented | ✅ Yes | [`navigation-redesign.md`](./navigation-redesign.md) updated (members read-only, REST vocabulary, matrix reference) |
| 6 | Bug #35 `basePath` committed + URL nit | 🟡 Code done | Fix present; **`tab=skills` omitted on `/skills`**; default `basePath` is now `/skills`. **Not committed yet.** |
| 7 | Bug #36 local billing seed documented/verified | ❌ No | Still only documented as hypothesis in review §12 |

**Overall:** **4/7 fully met**, **2/7 mostly met**, **1/7 not started**.

---

## 3. Epic-by-epic checklist

### Epic A — Vocabulary lock-in ✅ Done

| Task | Status |
|------|--------|
| Canonical permission matrix document | ✅ [`permission-matrix.md`](../02_features/authentication_rbac/permission-matrix.md) |
| Update design doc §4 | ✅ `navigation-redesign.md` |
| Fix `use-user-permissions.ts` dead strings | ✅ Uses `P.member.create`, `P.organization.*`, etc. |
| Fix tests with old names | ✅ Updated; forbidden names only in negative tests |
| Align billing `manage` vs `subscribe` | 🟡 Documented as composite; API still checks both separately |
| Shared constants (Python + TS) | 🟡 TS only (`permissions.ts`); **no Python mirror module** |

**Evidence:** Grep shows no production usage of `agent:write`, `member:invite`, `member:manage`, or `settings:*` outside comments/tests.

---

### Epic B — Single frontend permission API ✅ Mostly done

| Task | Status |
|------|--------|
| Page write gates from permission map | 🟡 **Main workspace pages yes**; some admin pages still role-only |
| Deprecate role-only gates (except platform surfaces) | 🟡 Intentional exceptions documented in matrix |
| Remove `NODE_ENV === "development"` grant-all | ✅ Removed |
| Invalidate `/me` on org switch | ✅ `queryKey` includes `orgId` in `use-has-permission.ts` |

**Migrated to permission-derived flags:**

- `/agents` — `canCreateAgent`
- `/skills` — `canManageSkills`
- `/phone-numbers` — `canManagePhoneNumbers`
- `/organization/members` — `canManageMembers`

**Still using role booleans for page gates:**

| Page | Gate | Impact today | Phase 2 impact |
|------|------|--------------|----------------|
| `/agents/create` | `isPlatformAdmin \|\| isOrgAdmin` | Same as `canCreateAgent` for current roles | Custom role with `agent:create` only would be **blocked** |
| `/organization/billing` | `isPlatformAdmin \|\| isOrgAdmin` | Same as `canManageBilling` today | Custom billing manager role would be **blocked** |
| `/organization` | `isPlatformAdmin \|\| isOrgAdmin` | Stricter than nav (org item is in org_admin section anyway) | Low for current product rules |
| `/users` | `hasRole("platform_admin")` | Correct for platform-only surface | OK to keep role-based |
| Cross-org agent card actions | `hasRole("org_admin", agent.org_id)` | **Documented intentional** — permissions map is current-org scoped | Needs per-resource API or expanded resolver |

**Architectural note:** Nav still uses **dual gate** (section role + item permission). That matches the review’s Option C and is **intentional**, not a regression — but it means Phase 2 custom roles need both layers updated.

---

### Epic C — Backend auth migration 🟡 In progress

| Module | Before (review) | Now | Remaining |
|--------|-----------------|-----|-----------|
| `voice_agents/routes.py` | Mostly `has_role` ladders | ✅ `require_permission` + many `assert_has_permission` | ~2 inline `has_role` (list/filter paths) |
| `voice_agents/skill_routes.py` | Mostly `has_role` | ✅ Heavy `assert_has_permission` use | ~3 `has_role` (platform_admin bypass checks) |
| `organization/routes.py` | Mixed | 🟡 Mix of `assert_has_permission` + `assert_has_role` | Member/org writes partially migrated |
| `billing/routes.py` | Role ladders | 🟡 `assert_has_role` OR `assert_has_permission("billing","subscribe")` | Not unified on `billing:manage` |
| `phone_numbers/routes.py` | Inline `has_role` (per audit) | ❌ Still uses `check_billing_permissions` | **Wrong semantic** — not `phone_number:*` (see §6) |
| `voice_agents/tool_routes.py` | Role ladder (post-security fix) | ❌ Still **8× `has_role`** | Should use `agent:update` or tool-specific permission |
| `platform_skill_routes.py` | Platform admin | 🟡 Uses `assert_platform_role` helper | Acceptable (role-only surface) |
| RBAC catalog / notifications / call_logs | Platform admin ladders | ❌ Unchanged | Expected for platform-admin-only APIs |

**Consolidation win:** `check_billing_permissions` moved from `middleware.py` → `dependencies.py` (single implementation).

**Sprint board** still lists **N1 Epic C / task #41** as open — consistent with this assessment.

**Tests:** 53 backend auth/org tests pass; frontend permission tests pass.

---

### Epic D — Doc & IA cleanup 🟡 Partial

| Task | Status |
|------|--------|
| `navigation-redesign.md` as-implemented | ✅ |
| Deferred Phase 2 wording | ✅ Sprint board + design doc clarified |
| Replace NeuraSaaS branding | ✅ `NEXT_PUBLIC_APP_NAME ?? "CogniNets"` in layout |
| Fix Platform Skills icon | ✅ `Layers` (was `CreditCard` in review) |
| Remove duplicate avatar-menu org links | ❌ Still present (Overview, Members, Billing in avatar dropdown) |
| Skills: drop `tab=skills` on `/skills` | ✅ |
| Rename `OrganizationSkillsTab` | ❌ Still named “tab” |
| Breadcrumbs from `nav-config` | ❌ Still pathname hard-code in `dashboard-layout.tsx` |
| Stronger `PermissionString` type | 🟡 Allow-lists in `permissions.ts`; template literal type still loose |

---

### Epic E — Do not start ✅ Correct

Custom roles UI and speculative resolver rewrite remain deferred per sprint board and design doc.

---

## 4. What was already good (unchanged)

These review “keep” items remain valid:

- Nav as data (`nav-config.ts`) with invariant tests
- `GET /me?org_id=` embedded permissions resolver
- Security fixes: tool routes auth, invitation `user_id` binding, skill ownership, RBAC catalog restriction, `member:create` typo fix
- Org switcher in sidebar; Phone Numbers & Skills as top-level routes
- TDD coverage for nav, hooks, and dependency factories

---

## 5. Remaining gaps (prioritized)

### High — finish before custom RBAC

1. **Epic C incomplete** — `tool_routes.py` and `phone_numbers/routes.py` are the clearest gaps. Tool writes should align with agent/org permissions; phone numbers should use `phone_number:create|update|delete`, not billing OR-checks.
2. **Page gates on roles** — `/agents/create` and `/organization/billing` should use `canCreateAgent` / `canManageBilling` for Phase 2 readiness (one-line changes).
3. **Backend audit doc stale** — [`backend-endpoint-permission-audit.md`](../02_features/authentication_rbac/backend-endpoint-permission-audit.md) predates Epic C work and still says agent/skill writes are “inline has_role PASS”. Update after Epic C completes.

### Medium — product / consistency

4. **Billing permission duality** — UI/nav uses `billing:manage`; several API paths use `billing:subscribe` OR `org_admin`. Documented in matrix but not unified in code.
5. **Dual gate model** — Nav section roles + item permissions + some page role gates. Coherent for three fixed roles; needs a written “Phase 2 alignment” note when custom roles ship.
6. **Changes uncommitted** — All assessed fixes live in the working tree only. Review acceptance should be re-checked after commit/merge.

### Lower — polish

7. Avatar dropdown duplicates org-admin links (design said “one release fallback”).
8. `OrganizationSkillsTab` rename; breadcrumb derivation from nav config.
9. No generated/shared Python permission constants (TS-only for now).
10. **Bug #36** — local `subscription_plans` empty; seed path not verified or documented in setup guide.

---

## 6. Additional finding — phone numbers backend permission model

The frontend correctly gates phone-number UI with `canManagePhoneNumbers` (`phone_number:create|update|delete`).

The backend still depends on `check_billing_permissions` for **all** phone-number routes (search, list, purchase, assign, unassign). That helper allows:

- `platform_admin`, **or**
- `org_admin` on the org, **or**
- `billing:subscribe` on the org

So a future user granted `billing:subscribe` without phone-number permissions could pass the API while failing the UI gate (or vice versa if grants diverge). This is a **consistency and security-boundary gap** called out in Epic C but not yet fixed.

---

## 7. Test & validation posture

| Suite | Result |
|-------|--------|
| `tests/auth/test_dependencies.py` | ✅ Pass |
| `tests/auth/test_permissions_service.py` | ✅ Pass |
| `tests/organization/test_routes.py` | ✅ Pass |
| `frontend/src/lib/__tests__/permissions.test.ts` | ✅ Pass |
| `frontend/src/hooks/__tests__/use-user-permissions.test.tsx` | ✅ Pass (includes no dev grant-all) |
| E2E role matrix across new routes | ⚠️ Not re-run for this report |
| Browser smoke / agent-browser | ⚠️ Not re-run for this report |

---

## 8. Recommended next steps (ordered)

1. **Commit** the current crunch changes as one or more focused commits (vocabulary + frontend facade + partial Epic C).
2. **Finish Epic C** for `tool_routes.py` and `phone_numbers/routes.py`; sweep billing routes to prefer `billing:manage` where appropriate.
3. **Switch** `/agents/create` and `/organization/billing` page gates to permission flags.
4. **Update** `backend-endpoint-permission-audit.md` to reflect migrated endpoints.
5. **Epic D cleanup** when convenient: avatar menu dedup, component rename, breadcrumbs.
6. **Bug #36** — run `stripe_manager.py seed` locally and document in setup guide (optional acceptance criterion).

---

## 9. Document history

| Date | Change |
|------|--------|
| 2026-07-13 | Initial implementation status report vs `n1-architecture-review.md` and working-tree diff |
