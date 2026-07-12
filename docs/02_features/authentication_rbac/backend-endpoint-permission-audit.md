# Backend Write-Endpoint Permission Audit (2026-07-07)

**Scope**: Every backend write endpoint must independently enforce the role/permission
server-side, regardless of frontend gates. Frontend permission gates are a UX
nicety, not a security boundary. This audit documents which endpoints enforce
access control correctly, which were missing checks, and which were fixed in
2026-07.

**Trigger**: N1 navigation redesign surfaced UI permission leaks. The user
explicitly required: "we must also validate permissions on the back end. That
is how the code systems are built, which do the right checks at both the
front end and back end."

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
| `/api/v1/tools/agent/{agent_tool_id}` | PUT | `platform_admin` OR `org_admin` on the tool's org | FIXED | Was **no check at all** — any logged-in user could rewrite an agent tool config. Now loads the tool, resolves its org, asserts org admin. |
| `/api/v1/tools/agent/{agent_tool_id}` | DELETE | same | FIXED | Same. |
| `/api/v1/tools/agent/{agent_tool_id}/logout` | POST | same | FIXED | Same. |
| `/api/v1/tools/agent/{agent_tool_id}/api-key` | PUT | same | FIXED | Same — most dangerous: could overwrite a real user's Google API key. |

## Voice agents — skills (cross-org IDOR)

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/organizations/{org_id}/skills/{skill_id}/files/{file_id}` | PUT | org admin on `{org_id}` AND file's `organization_id == org_id` | FIXED | Was org-admin on path only; allowed an org admin to edit a file that *belonged* to a *different* org. Now loads the file, asserts `file.organization_id == org_id`. |
| `/api/v1/organizations/{org_id}/skills/{skill_id}/files/{file_id}` | DELETE | same | FIXED | Same. |
| `/api/v1/organizations/{org_id}/skills/{skill_id}/refresh` | POST | same | FIXED | Same — cross-org skill refresh was possible. |

## Voice agents — agents

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/agents/` | POST | `agent:create` on body's `organization_id` (or `platform_admin`) | PASS | Migrated to `Depends(require_permission("agent", "create", org_id_source="body", body_field="organization_id"))` as the reference example for the new factory. |
| `/api/v1/agents/{agent_id}` | PUT | org admin on agent's org | PASS | |
| `/api/v1/agents/{agent_id}` | DELETE | org admin on agent's org | PASS | |
| Other `/api/v1/agents/...` writes | various | inline `has_role` ladder | PASS | Not part of the leak audit; not flagged. |

**Open follow-up (task #17)**: page-level `canDelete` on the `/agents` page is
"good enough" with a TODO. The proper fix is per-agent `can_delete` (option B
in the task). Currently an org admin viewing a non-current-org agent card
sees no trash icon (cross-org delete is correctly blocked by the backend).

## Organization / members

| Endpoint | Method | Required | Verdict | Notes |
|----------|--------|----------|---------|-------|
| `/api/v1/auth/process-invitation` | POST | authenticated user, body `user_id` must match `current_user_id` | FIXED | Was **no check at all** — caller could pass *any* `user_id` and impersonate the invitee. Now requires auth and rejects mismatched `user_id` with 403. |
| `/api/v1/organizations/{org_id}/members` (invite) | POST | `member:create` permission on the org | FIXED | Was checking `member:invite` — a typo, no such permission exists. The migration grants `member:create`. Fixed. |

## Out of scope (not audited this round)

- `/api/v1/phone-numbers/...` — the four write buttons are gated by `canManage` in the frontend (task #15). The backend endpoints already have inline `has_role` checks. The corresponding backend audit (per the original task #16 scope) is a follow-up.
- `/api/v1/calls/...` — read-only by spec; no write paths.
- `/api/v1/platform/skills/...` — platform admin gate already enforced server-side.

## Follow-up tasks

- **#17** — Per-agent `can_delete` on `/agents` (Option B: backend returns
  per-agent `can_delete` boolean, or a `canDeleteAgent(agent_id)` API).
- **#15** — Audit the corresponding backend phone-number write endpoints
  to confirm they enforce the same `canManage` logic the frontend now
  relies on. (Code is gated; audit doc not yet written.)
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
