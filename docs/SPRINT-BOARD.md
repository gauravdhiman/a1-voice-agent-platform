# 📋 Sprint Board

**Last Updated:** 2026-07-12 (N1 Epic C closed)
**Current branch:** `main`
**Product direction:** Voice-only — the platform focuses exclusively on phone-call
AI agents. Chat / multi-channel agents (F3, F14) are **deprioritized** and not on
the active roadmap.

> Reconciled with the actual code/commits. Source of truth for what's done vs
> pending. See also `docs/PRIORITY-LIST.md` (feature backlog) and
> `docs/FEATURE_REPORT.md`.

---

## 🟢 Done

### Skills system (F1) — complete through admin management
| Item | Completed | Notes |
|------|-----------|-------|
| Phase 1 — Markdown agent instructions (#18) | 2026-04-01 | Markdown system prompts. |
| Phase 2a — Progressive disclosure (#19) | 2026-04-02 | Skills + on-demand reference loading. |
| Phase 2b — CRUD / Import / Files / Assignment | 2026-05-03 | Skill CRUD, GitHub import, file mgmt, agent assignment. |
| Phase 2c — Platform skills fork/refresh | 2026-05-06 | Orgs fork platform skills + refresh; hidden-skills badge. |
| Elaborate `appointment-booking` skill | 2026-05-06 | First "exceptional capability" w/ rich reference files. |
| Built-in skill library (8 generic skills) | 2026-06-22 | Original generic library: appointment-booking, insurance-verification, dispatch-coordination, call-transfer, faq-responder, after-hours, lead-qualification, payment-collection. **Superseded** by the Phase 2c redesign. |
| Built-in skill library (15 industry-specific skills) | 2026-06-24 | Phase 2c re-design: 15 industry-specific skills, 5 per industry (dental, restaurant, HVAC), one per capability slot. Each skill is industry-tuned with its own decision tree, mermaid diagram, guardrails, and reference files. Skills are decoupled from specific tools — they describe user-visible actions. Library index in `docs/02_features/voice_agents/skills_library.md`. |
| Platform Skills Management (Admin UI) | 2026-06-22 | Platform-admin-only UI at `/platform/skills`: list/create/edit/hide-restore/files + import-from-URL. Backend RBAC on all routes; `include_inactive` admin list. |
| Shared `<SkillEditor>` + org skills tab migration | 2026-06-22 | Extracted shared master-detail editor (`frontend/src/components/skills/skill-editor.tsx`); org skills tab now renders it via `OrganizationSkillsTab`. Org + platform share one UI — no drift. |
| voice-ws token-refresh race condition (multi-instance) | 2026-06-23 | Postgres-backed per-tool lease lock (`token_refresh_leases` + `claim_token_refresh`/`release_token_refresh` SQL fns, migration `20260623000001`). `TokenRefreshService` claims before the OAuth call, releases in `finally`. Lease TTL auto-recovers from crashes; fail-closed. **Note:** used a row-lease via RPC rather than `pg_advisory_lock` because advisory locks need session affinity, which Supabase/PostgREST connection pooling breaks. TDD (red→green), 9 new tests. |
| Platform skills status enum (single source of truth) | 2026-06-24 | Consolidated `is_active` + `is_deleted` booleans into a single `status VARCHAR(20)` enum (draft / active / deprecated / deleted) with a CHECK constraint. Dedicated transition endpoints (`deprecate` / `reactivate` / `delete` / `restore`) enforce the state machine server-side. Frontend adapter passes `statuses` query param. Migration `20260624000001`. TDD red→green, 36+ tests across backend + frontend. |

### Platform foundations (shipped)
| Item | Completed | Notes |
|------|-----------|-------|
| Phone Number Management (F2) | 2026-03-15 | Twilio search/purchase/assign/release; credit pricing; full CRUD. |
| RBAC & Multi-tenancy | 2026-03-29 | Orgs, roles, permissions, invitations, Google OAuth. |
| Billing & Notifications | 2026-03-29 | Stripe subscriptions/credits; Resend email notifications. |
| Dynamic Tool System | 2026-01–2026-03 | Gmail, Google Calendar, Google Sheets, Cal.com; encrypted OAuth token storage + auto-refresh. |
| Embed / Call Button | 2026-02 | Embeddable call widget w/ API key config. |
| Observability (OpenTelemetry) | 2026-03-29 | Traces, metrics, logs across backend + worker. |
| Security Hardening | 2026-03-29 | Rate limiting, JWT signature verification, security headers, ES256 for local Supabase. |
| SMB 5-step Onboarding Wizard | 2026-03-29 | Template selection, validation, activation gating. |
| Landing Page Redesign | 2026-03-29 | Early-adopter CTA, 4-tier pricing, branding (24x7 AI). |
| 247ai.live production deploy (GCP + OCI) | 2026-08 | `scripts/deploy.sh`, `docs/05_operations/deployment/`, `.env.cloud.example`. |
| N1 Epic A — Permission vocabulary lock-in | 2026-07-11 | Canonical resource × action matrix in `docs/02_features/authentication_rbac/permission-matrix.md`; `frontend/src/lib/permissions.ts` exports the `P` namespace + `isCanonicalPermission` validator; `permissions.test.ts` pins the contract (14 tests); the legacy `agent:write` / `member:invite` / `member:remove` / `settings:*` names are now rejected by the validator. |
| N1 Epic B — Single FE permission API | 2026-07-11 | Page-level gates go through `useHasPermission(...)` (low-level) or `useUserPermissions()` (page facade); old role-only gates dropped where a permission is the right check; the `NODE_ENV === "development"` grant-all fallback removed (test `does NOT grant-all when NODE_ENV is development` guards the regression). `useMyPermissions` re-uses the auth context's `/me` query cache, invalidated on org switch. 17 facade tests + 14 `useHasPermission` tests pin the contract. |
| N1 Epic D (partial) — Doc & IA cleanup | 2026-07-11 | `docs/tw-drafts/navigation-redesign.md` brought to as-implemented: §1, §2, §3, §4, §5, §6, §8, §9 all reflect the shipped product (canonical CRUD names, composite actions, regular-user-is-read-only rule, deferred-items list). `docs/tw-drafts/n1-architecture-review.md` is the as-built audit; the `/me` + permission-string test files were renamed to match the embedded-on-`/me` decision. Epic D still owns the `?org_id=` → `/{orgId}/` URL refactor (task #27) and the `OrganizationSkillsTab` URL-noise cleanup (§4.5 of the review). |
| N1 Epic C — backend `has_role` ladder migration | 2026-07-12 | Replaced ~80 inline `has_role("org_admin", str(org_id))` ladders across 5 route files with the `assert_has_permission` / `assert_has_role` / `assert_platform_role` helpers from `src/auth/dependencies.py` (and the `require_permission` / `require_role` factory for path/body-scoped routes). The 3-way OR (platform_admin / org_admin / `billing:subscribe`) collapses to a single `assert_has_permission` because the canonical matrix already encodes the right grants per role. The platform-only routes (`platform_skill_routes.py`, `seed_platform_skills`, `sync_platform_skills`, billing plans CRUD) use the new `assert_platform_role` helper. Read-scope expansions (platform admin sees all orgs) and IDOR guards (`is_platform_admin` for cross-org ownership checks) stay inline — they're not 403 gates. All 682 tests pass, including the 8 new tests in `test_dependencies.py` (billing helper + `assert_platform_role`) and the 6 new tests in `test_routes.py` (organization platform-only 403 paths). `check_billing_permissions` consolidated from `auth/middleware.py` into `auth/dependencies.py`. Tracked as task #41. |

### Tooling / housekeeping
- `.gitignore` hardened: `.agents/`, `.codex/skills/graphify/`, `.codex/hooks.json`, `graphify-out/`; `.graphifyignore` added for code-only graphify runs.
- Branding consistency: sidebar + signin/signup pages drive the product name from `NEXT_PUBLIC_APP_NAME` (fallback `24x7 AI`). Website: https://247ai.live

---

## 🟡 In Progress / Next (priority order)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Industry-template onboarding (Phase B)** | Next | Schema + fork-injection: `organizations.industry` column + `industry_skill_templates` table; on org creation or industry change, fork the matching industry skills into the org library automatically. Supersedes the prior "soft-delete" line item — soft-delete / show-deleted / restore is now handled by the `status` enum (draft / active / deprecated / deleted) shipped in PR #25. |

---

## 🔴 Backlog (Voice-focused, ordered)

| ID | Feature | Effort | Priority | Rationale |
|----|---------|--------|----------|-----------|
| F7 | Call Recording & Transcription | Medium | P2 | High value; builds on `call_logs` + voice-ws recording tee. |
| F13 | Campaign Management (Outbound) | High | P3 | See [outbound_phone_calls.md](03_implementation/outbound_phone_calls.md). |
| F8 | CRM Integration | Medium | P2 | Reuses the dynamic-tool architecture. |
| F4 | Call Analytics Dashboard | Low | P3 | Leverages `call_logs` + OTEL metrics already collected. |
| F5 | Voice Templates (Industry) | Low | P3 | Preset system prompts per industry; complements skills. |
| F6 | SMS/Text Fallback | Medium | P3 | Twilio already integrated. |
| F9 | Multi-language Support | Medium | P3 | TTS/STT language switching. |
| F10 | Call Scoring / QA | Medium | P4 | Post-call quality analysis. |
| F11 | Custom Voice / TTS | High | P4 | Branding / voice selection. |
| F12 | IVR Menu System | Medium | P4 | Menu-driven call routing. |

### Low-priority housekeeping
- Prune merged/stale git branches (~7 fully-merged + several squash-merged remotes safe to delete) — deferred; needs per-branch confirmation.
- Minor TODO: `backend/src/billing/routes.py:187` placeholder `billing@{slug}.example.com` email.
- `OrganizationPage` (`frontend/src/app/(dashboard)/organization/page.tsx`) is a "god page" with 4 tabs that duplicates top-level routes (Agents, Skills, Phone Numbers). Targeted for refactor in N1: collapse to a settings-only page (Profile / Members / Billing / Danger Zone), promote the other tabs to top-level routes.

### 🟣 Deferred / Speculative (build only when a real need appears)

Not on the active roadmap. Documented so they don't get lost, but should not
be picked up speculatively. Each has a concrete trigger condition.

| Item | Trigger |
|------|---------|
| **Define roles & permissions** — let org admins (or platform admins) create custom roles in the UI, assign permissions to them, and assign users to those roles. Today the platform has three fixed roles (`platform_admin`, `org_admin`, `member`) with hardcoded permission sets. | A paying customer needs differentiated access for non-admin users (e.g. "this user can handle calls but not see billing"). Today, any non-admin user is `member` (read-only) — the middle ground doesn't exist. |
| **Phase 2 RBAC real resolver** — replace the coarse role-based `GET /me/permissions` stub with a resolver that joins `user_roles → role_permissions → permissions` to compute the actual effective permission set. The data model is already in place; the `require_permission` / `require_role` factory in `backend/src/auth/dependencies.py` already calls `has_permission(...)` so it would consume the resolver's output unchanged. | The "Define roles & permissions" feature ships. The resolver is dead weight without it — every role currently maps to a fixed permission set, so a join produces the same answer as a hardcoded map. |

**Why defer:** No paying customer yet, so no concrete user need. Both items
involve product decisions (who can manage roles, how to resolve role conflicts,
whether custom roles are org-scoped) that should be made with users in the room.
The data model and factory infrastructure are already in place — building later
costs the same as building now.

---

## ⚪ Deprioritized (not on active roadmap — voice-only)

| ID | Feature | Reason |
|----|---------|--------|
| F3 | Chat Agents with Long-term Memory | Out of voice-only scope; needs new channel surface + memory backend (Letta/Agno). PRD retained for reference. |
| F14 | Multi-channel (WhatsApp, Discord) | Out of voice-only scope. |
| — | Skills Marketplace | Re-evaluate when 50+ orgs use skills. |

---

## 📝 Next sprint (suggested)
- [x] voice-ws scaling: Postgres-backed lease lock implemented + tested (migration `20260623000001` — `alembic upgrade head` applied; DB head confirmed at `20260624000001`).
- [x] Platform skills `status` enum (single source of truth) — soft-delete, restore, and show-deleted are now backed by the enum + transition endpoints (PR #25, migration `20260624000001`).
- [x] **Navigation redesign + permission contract (N1)** — see `docs/tw-drafts/navigation-redesign.md`. All 5 phases shipped: (a) backend `GET /me/permissions` embedded on `/api/v1/auth/me?org_id=` (role-based set, with `*:*` wildcard for `platform_admin`), (b) frontend `useHasPermission()` + `useMyPermissions` hooks, (c) `nav-config.ts` with `requiredPermission` per item, (d) `OrganizationSwitcher` popover in the sidebar, (e) Phone Numbers & Skills promoted to top-level routes, (f) page-level + component-level frontend gates (N1 follow-ups #1–#4), (g) 4 backend tool_routes CRITs closed, (h) 5 surgical auth fixes, (i) `require_permission` / `require_role` factory + `assert_has_permission` / `assert_has_role` helpers. Architecture review at `docs/tw-drafts/n1-architecture-review.md`; per-endpoint PASS/FIXED audit at `docs/02_features/authentication_rbac/backend-endpoint-permission-audit.md`. Epics A + B + D-partial of the review are done. Org page collapse to settings-only is the remaining piece of the original N1 scope; the URL refactor (`?org_id=` → `/{orgId}/`) is filed as task #27.
- [ ] **N1 Epic C** — migrate the ~27 remaining inline `has_role` ladders to `Depends(require_permission(...))` / `assert_has_permission(...)` per context (task #41). Touches `voice_agents/routes.py`, `skill_routes.py`, `phone_numbers/routes.py`, `organization/routes.py`, `billing/routes.py`, `platform_skill_routes.py`.
- [ ] Industry-template onboarding (Phase B) — `organizations.industry` + `industry_skill_templates`; auto-fork on org create / industry change.
- [ ] Add 1–2 more built-in skills (e.g. `new-patient-intake`, `call-handling`).
- [ ] (Optional) prune stale branches.

---

## 🔗 Links
- **Feature backlog:** `docs/PRIORITY-LIST.md`
- **PRDs:** `docs/PRD-*.md`
- **Feature report:** `docs/FEATURE_REPORT.md`
- **DB schema:** `docs/DATABASE_SCHEMA.md`
- **Platform skills admin doc:** `docs/02_features/voice_agents/platform_skills_admin.md`
- **Skill definitions (seeded):** `backend/src/voice_agents/skill_seeds.py`
