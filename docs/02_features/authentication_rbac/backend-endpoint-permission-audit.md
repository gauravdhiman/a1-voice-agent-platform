# Backend Write-Endpoint Permission Audit (2026-07-07; Epic C sweep 2026-07-13)

**Scope**: Every backend write endpoint must independently enforce the role/permission
server-side, regardless of frontend gates. Frontend permission gates are a UX
nicety, not a security boundary. This audit documents which endpoints enforce
access control correctly, which were missing checks, and which were fixed in
2026-07.

**Trigger**: N1 navigation redesign surfaced UI permission leaks. The user
explicitly required: "we must also validate permissions on the back end. That
is how the code systems are built, which do the right checks at both the
front end and back end."

**2026-07-13 update (N1 Epic C)**: The remaining inline `has_role("org_admin", str(org_id))`
ladders across all route files were migrated to the typed helpers in
[`src/auth/dependencies.py`](../../../backend/src/auth/dependencies.py):

- `require_permission(resource, action, ...)` / `require_role(role, ...)` —
  FastAPI dependency factory for path/body-scoped org ids.
- `assert_has_permission(user_profile, resource, action, org_id)` — post-load
  helper for routes that resolve the org id after loading a resource.
- `assert_has_role(user_profile, role, org_id)` — post-load role helper.
- `assert_platform_role(user_profile, role)` — org-agnostic helper for
  platform-only routes (no sentinel UUID).
- `assert_billing_access(user_profile, organization_id)` — the four-way OR
  (platform_admin / org_admin / `billing:manage` / `billing:subscribe`)
  used by every billing route; `check_billing_permissions` is a thin async
  dependency wrapper over it.

The 3-way OR ladders (platform_admin / org_admin / regular_user) collapse to
a single `assert_has_permission` because the canonical
[permission matrix](./permission-matrix.md) already encodes the right grants
per role (`regular_user` has `*:read`, `org_admin` has full CRUD, `platform_admin`
wildcard). See the Epic C row in [`docs/SPRINT-BOARD.md`](../../SPRINT-BOARD.md).

**Verdict legend**:
- **PASS** — endpoint enforces the correct role/permission server-side.
- **FIXED** — endpoint was missing or had wrong check; now fixed.
- **DEFERRED** — endpoint has a known gap; tracked as a follow-up task.

## RBAC catalog (platform-wide)

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/permissions/` | POST | `platform_admin` | PASS | Always required platform admin. |
| `/api/v1/permissions/{id}` | GET | `platform_admin` | FIXED | Was `has_permission("permission:read")` without org scoping — a non-platform-admin org role with `permission:read` would have been allowed. Switched to `has_role("platform_admin")`. |
| `/api/v1/permissions/` | GET | `platform_admin` | FIXED | Same as above. |
| `/api/v1/permissions/{id}` | PUT | `platform_admin` | PASS | |
| `/api/v1/permissions/{id}` | DELETE | `platform_admin` | PASS | |
| `/api/v1/permissions/roles/{role_id}/permissions/{perm_id}` | POST | `platform_admin` | PASS | |
| `/api/v1/permissions/roles/{role_id}/permissions/{perm_id}` | DELETE | `platform_admin` | PASS | |
| `/api/v1/permissions/roles/{role_id}/permissions` | GET | `platform_admin` | FIXED | Same as the other GET. |
| `/api/v1/roles/` | POST | `platform_admin` | PASS | |
| `/api/v1/roles/{id}` | GET | `platform_admin` | FIXED | Same as the permission GETs. |
| `/api/v1/roles/` | GET | `platform_admin` | FIXED | Same. |
| `/api/v1/roles/{id}` | PUT | `platform_admin` | PASS | |
| `/api/v1/roles/{id}` | DELETE | `platform_admin` | PASS | |

## Voice agents — agent tools (CRIT)

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/tools/agent/{agent_tool_id}` | PUT | `agent:update` on the tool's org (or `platform_admin`) | FIXED | Was **no check at all** — any logged-in user could rewrite an agent tool config. Now loads the tool, resolves its org, asserts `agent:update` via `_assert_agent_tool_admin` (tool config is an agent mutation). |
| `/api/v1/tools/agent/{agent_tool_id}` | DELETE | same | FIXED | Same. |
| `/api/v1/tools/agent/{agent_tool_id}/logout` | POST | same | FIXED | Same. |
| `/api/v1/tools/agent/{agent_tool_id}/api-key` | PUT | same | FIXED | Same — most dangerous: could overwrite a real user's Google API key. |
| `/api/v1/tools/agent/{agent_id}` (configure / list) | POST, GET | `agent:update` / `agent:read` on the agent's org | PASS | Migrated to `assert_has_permission` in the Epic C sweep. |
| `/api/v1/tools/platform` (create) | POST | `platform_admin` | PASS | Migrated to `assert_platform_role`. |

## Voice agents — skills (cross-org IDOR + Epic C sweep)

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/organizations/{org_id}/skills/{skill_id}/files/{file_id}` | PUT | `skill:update` on `{org_id}` AND file's `organization_id == org_id` | FIXED | Was org-admin on path only; allowed an org admin to edit a file that *belonged* to a *different* org. Now loads the file, asserts `file.organization_id == org_id`. Epic C: role ladder → `assert_has_permission("skill", "update")`. |
| `/api/v1/organizations/{org_id}/skills/{skill_id}/files/{file_id}` | DELETE | `skill:delete` on `{org_id}` AND file's `organization_id == org_id` | FIXED | Same. |
| `/api/v1/organizations/{org_id}/skills/{skill_id}/refresh` | POST | `skill:update` on `{org_id}` AND skill's `organization_id == org_id` | FIXED | Same — cross-org skill refresh was possible. |
| `/api/v1/organizations/{org_id}/skills` | GET, POST, PUT, DELETE | `skill:read` / `skill:create` / `skill:update` / `skill:delete` on `{org_id}` | PASS | Epic C sweep. |
| `/api/v1/agents/{agent_id}/skills` (assign / unassign) | POST, DELETE | `skill:update` on the agent's org | PASS | Epic C sweep (org id resolved from the loaded agent). |
| `/api/v1/skills/seed-platform`, `/api/v1/skills/sync-platform` | POST | `platform_admin` | PASS | Migrated to `assert_platform_role`. |
| `/api/v1/organizations/{org_id}/skills/import`, `/skills/fork` | POST | `skill:create` on `{org_id}` | PASS | Epic C sweep. |

## Billing

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/billing/plans` (create / update) | POST, PUT | `platform_admin` | PASS | Migrated to `assert_platform_role`. Reads (list / get) are public. |
| `/api/v1/billing/subscription/{organization_id}` (get) | GET | `assert_billing_access` (platform_admin / org_admin / `billing:manage` / `billing:subscribe`) | PASS | `Depends(check_billing_permissions)`. |
| `/api/v1/billing/subscription/checkout`, `/credits/consume`, `/checkout/*`, `/portal`, `/subscription/cancel`, `/subscription/reactivate` | POST | `assert_billing_access` on the body's `organization_id` | PASS | Epic C sweep: the bare `org_admin` role check was replaced by `billing:manage` (Phase 2 custom billing-manager role now passes); `billing:subscribe` kept as the documented legacy fallback. |

## Phone numbers

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/phone-numbers/available` | GET | authenticated | PASS | Provider catalog is not org-scoped. |
| `/api/v1/phone-numbers/purchase` | POST | `phone_number:create` on `organization_id` (or `platform_admin`) | FIXED | Previously gated on `check_billing_permissions`, which let a `billing:subscribe`-only holder purchase numbers while the frontend `canManagePhoneNumbers` gate hid the UI — an API/UI consistency gap. Now gates on `phone_number:create`. Credit deduction is a separate 402 in the service layer. |
| `/api/v1/phone-numbers` (list) | GET | `phone_number:read` on `organization_id` | FIXED | Same §6 fix. |
| `/api/v1/phone-numbers/{phone_number_id}/assign` | POST | `phone_number:update` on `organization_id` | FIXED | Same. |
| `/api/v1/phone-numbers/{phone_number_id}` (cancel) | DELETE | `phone_number:delete` on `organization_id` | FIXED | Same. |

## Voice agents — agents

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/agents/` | POST | `agent:create` on body's `organization_id` (or `platform_admin`) | PASS | Migrated to `Depends(require_permission("agent", "create", org_id_source="body", body_field="organization_id"))` as the reference example for the new factory. |
| `/api/v1/agents/{agent_id}` | PUT | `agent:update` on the agent's org (or `platform_admin`) | PASS | Migrated to `assert_has_permission` (post-load; org id resolved from the loaded agent). |
| `/api/v1/agents/{agent_id}` | DELETE | `agent:delete` on the agent's org (or `platform_admin`) | PASS | Same. |
| `/api/v1/agents/{agent_id}` (GET, test-token, system-prompt, embed-config/token) | GET, POST | `agent:read` on the agent's org (or `platform_admin`) | PASS | Migrated in the Epic C sweep. `create_embed_config` / `delete_embed_config` gate on `agent:update` (config mutation). |
| Other `/api/v1/agents/...` writes | various | `agent:<action>` via `assert_has_permission` | PASS | Epic C sweep replaced the former inline `has_role` ladders. |

**Open follow-up (task #17)**: page-level `canDelete` on the `/agents` page is
"good enough" with a TODO. The proper fix is per-agent `can_delete` (option B
in the task). Currently an org admin viewing a non-current-org agent card
sees no trash icon (cross-org delete is correctly blocked by the backend).

## Organization / members

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/auth/process-invitation` | POST | authenticated user, body `user_id` must match `current_user_id` | FIXED | Was **no check at all** — caller could pass *any* `user_id` and impersonate the invitee. Now requires auth and rejects mismatched `user_id` with 403. |
| `/api/v1/organizations/{org_id}/members` (invite) | POST | `org_admin` OR `member:create` on the org | FIXED | Was checking `member:invite` — a typo, no such permission exists. The migration grants `member:create`. Epic C: `try assert_has_role("org_admin") / except assert_has_permission("member", "create")`. |
| `/api/v1/organizations/{org_id}/members` (list), `/api/v1/organizations/{org_id}` (get) | GET | `org_admin` OR `organization:read` on the org | PASS | Epic C sweep. |
| `/api/v1/organizations/{org_id}` (update, complete-onboarding) | PATCH, POST | `org_admin` on the org (or `platform_admin`) | PASS | Migrated to `assert_has_role`. |
| `/api/v1/organizations/` (create), `/{org_id}` (delete) | POST, DELETE | `platform_admin` | PASS | Migrated to `assert_platform_role`. |
| `/api/v1/platform/skills/...` | various | `platform_admin` | PASS | `_require_platform_admin` helper → `assert_platform_role`. |

## Out of scope (not audited this round)

- `/api/v1/calls/...` — read-only by spec; no write paths.
- RBAC catalog `/api/v1/permissions/...` and `/api/v1/roles/...` —
  platform-admin-only APIs; intentionally role-gated (not permission-gated).
  The N1 `has_permission("permission:read")` org-blind bug was fixed earlier
  (see table above); the rest stay role-based by design.

## Follow-up tasks

- **#17** — Per-agent `can_delete` on `/agents` (Option B: backend returns
  per-agent `can_delete` boolean, or a `canDeleteAgent(agent_id)` API).
- **#15** — Phone-number backend audit. **Done 2026-07-13** (Epic C §6):
  routes now gate on `phone_number:<action>`; see the Phone numbers table
  above. The `TestPurchasePhoneNumberPermission` / `TestList...` /
  `TestAssign...` / `TestCancel...` suites in
  `tests/phone_numbers/test_routes.py` pin the contract (11 tests,
  including the `billing:subscribe`-only → 403 behavior change).
- **#27** — URL refactor `?org_id=` → `/{orgId}/` would eliminate an
  entire class of "missing query param" bugs at the cost of a wide
  mechanical refactor. Deferred.

## How to extend this doc

When you add a new write endpoint:
1. Add a row to the table above.
2. Mark **PASS** if it requires the correct role/permission, **FIXED**
   if you had to add a check, or **DEFERRED** if the gap is filed as
   a follow-up.
3. The audit is the source of truth for "this endpoint enforces server-side
   access control" — referenced by code review.
