# Canonical Permission Matrix (N1)

**Status:** As-implemented (2026-07-11)  
**Source of grants:**  
- Initial seed: `backend/alembic/versions/91759229c32b_add_initial_rbac_tables.py`  
- N1 extension: `backend/alembic/versions/20260705000001_extend_org_admin_and_regular_user_grants.py`  
**Frontend constants:** `frontend/src/lib/permissions.ts`  
**Resolver:** `backend/src/auth/permissions_service.py` (buckets role.permissions for the current org; platform_admin → `{"*":["*"]}`)

## Format

`<resource>:<action>` — REST-style actions.

| Style | Examples | Status |
|-------|----------|--------|
| **Canonical** | `agent:create`, `member:delete`, `billing:manage` | Use everywhere |
| **Forbidden / dead** | `agent:write`, `member:invite`, `member:manage`, `settings:*` | Never grant; never check |

## Composite permissions

| Name | Meaning |
|------|---------|
| `billing:manage` | Nav + billing UI gate (N1). Covers subscribe/manage subscription in the product sense. |
| `billing:subscribe` | Older seed permission still checked on some billing API routes. Treat as equivalent to manage for org admins until routes are unified. |
| `platform:admin` | Platform admin section (nav). Pages also require `platform_admin` **role**. |
| `*:*` | Wildcard encoded as `permissions: {"*": ["*"]}` for platform admins only. |

## Role → grants (product rules)

| Role | Grants |
|------|--------|
| `platform_admin` | Wildcard `*:*` (resolver short-circuit). Not org-scoped. |
| `org_admin` (on org) | All N1 org-scoped permissions **except** `platform:admin`. Includes agent/phone/skill CRUD, member CRUD, `billing:manage`, organization update, etc. |
| `regular_user` (on org) | **Read only** on org-scoped resources: `agent:read`, `phone_number:read`, `skill:read`, `call_log:read`, `member:read`, `organization:read`. **No** billing. **No** writes. |

## Resource × action matrix (N1 + seed)

| Resource | read | create | update | delete | other |
|----------|------|--------|--------|--------|-------|
| `agent` | ✓ | ✓ | ✓ | ✓ | |
| `phone_number` | ✓ | ✓ | ✓ | ✓ | |
| `skill` | ✓ | ✓ | ✓ | ✓ | |
| `call_log` | ✓ | | | | |
| `member` | ✓ | ✓ (invite) | ✓ (roles) | ✓ (remove) | |
| `organization` | ✓ | ✓ | ✓ | ✓ | |
| `billing` | ✓ (seed) | | ✓ (seed) | | `manage`, `subscribe` |
| `platform` | | | | | `admin` |

## Frontend usage

| Concern | API |
|---------|-----|
| Nav item visibility | `useHasPermission("agent:read")` + section role gate |
| Page write CTAs | `useUserPermissions()` flags derived from the **same** `/me.permissions` map (or `useHasPermission` directly) |
| Cross-org agent card actions | Still `hasRole("org_admin", agent.organization_id)` — permissions map is **current-org scoped** |

## Backend usage

| Concern | API |
|---------|-----|
| Path/body org known at dependency time | `Depends(require_permission("agent", "create", ...))` |
| Org known only after loading a resource | `assert_has_permission(profile, "agent", "update", agent.organization_id)` |
| Role-only platform surfaces | `require_role("platform_admin")` / `has_role("platform_admin")` |

## Phase 2 (deferred)

Custom roles UI and differentiated non-admin grants. Do **not** invent new permission names without updating this matrix, the migration, and `frontend/src/lib/permissions.ts`.
