# Navigation Redesign + Permission Contract (N1)

**Status:** Shipped 2026-07-11 (all 5 phases; product split between N1 follow-ups #1–#4 and the foundational RBAC work). See `docs/tw-drafts/n1-architecture-review.md` for the as-built audit and the design-vs-implementation drift it caught.
**Owner:** Platform
**Sprint board:** `docs/SPRINT-BOARD.md` (closed: was next-up item #1)
**Date:** 2026-07-11

---

## 1. Problem statement

The current left-nav (`frontend/src/components/layout/dashboard-layout.tsx`) is
coarse, hard-coded by name, and gets one major thing wrong: it treats org-user
and platform-admin items as siblings with no separator, filters them with a
literal `item.name === "Users"` check, and hides Phone Numbers / Skills / Org
admin / Settings behind an avatar dropdown or inside the org page's tab strip.

Today, the left-nav is the only permission gate — agents, phone
numbers, and skills are surfaced to every member, with write actions
also visible to everyone. When the proper RBAC system lands, we
don't want to re-plumb the nav, the layout, or the page-level
guards. The right move is to ship the **contract** (a permission
string format, a `/me/permissions` endpoint, and a `useHasPermission()`
hook) **now** with a stub resolver, so the Phase 2 work is a backend
change, not a refactor.

---

## 2. Goals

1. **Intuitive nav**: org-user workspace items, org admin items, and platform
   admin items each live in their own visual section.
2. **Org-as-primary-actor**: the org switcher moves from the avatar dropdown to
   the sidebar so the org context is the first thing the user sees.
3. **Top-level parity**: Phone Numbers and Skills become first-class routes
   (not org page tabs). The Org page collapses to a settings-only page.
4. **Permission-aware from day one**: the nav filters items by a
   `requiredPermission` field, evaluated by a `useHasPermission()` hook that
   hits a new `GET /me/permissions` endpoint. The endpoint returns a stub
   resolution today (role-based), with a real per-role resolver in Phase 2.
5. **Workspace read for members, write for org_admin/platform_admin**: regular
   org members see the workspace section (Home, Agents, Phone Numbers, Skills,
   Calls) but no write affordances. org_admin (and platform_admin) keep full
   CRUD. This is an intentional product rule — the RBAC migration is the
   place where the legacy "everyone can write" behavior is retired.

---

## 3. Non-goals

- Building the full RBAC per-role permission resolver (Phase 2). The stub
  resolver today encodes the same role→permission mapping that the canonical
  matrix in `docs/02_features/authentication_rbac/permission-matrix.md`
  defines; the Phase 2 work reads those rows from `role_permissions` rather
  than the stub.
- Per-resource permission resolution against `role_permissions` (Phase 2).
- Removing the duplicate avatar-menu entries (Settings, Members, Billing) on
  day one. They stay for one release as a fallback; removal is a follow-up.

---

## 4. Permission string contract

Format: `<resource>:<action>` — matches the existing `UserProfile.has_permission()` API.

Canonical reference: `docs/02_features/authentication_rbac/permission-matrix.md`.
The single source of truth for the resource × action matrix is the migration
`20260705000001_extend_org_admin_and_regular_user_grants.py`; the table
below mirrors the rows it grants.

| Resource       | Actions                                              | Example strings                       |
|----------------|------------------------------------------------------|---------------------------------------|
| `agent`        | `read`, `create`, `update`, `delete`                 | `agent:read`, `agent:create`          |
| `phone_number` | `read`, `create`, `update`, `delete`                 | `phone_number:read`                   |
| `skill`        | `read`, `create`, `update`, `delete`                 | `skill:read`                          |
| `call_log`     | `read`                                               | `call_log:read`                       |
| `member`       | `read`, `create`, `update`, `delete`                 | `member:create`                       |
| `billing`      | `manage`, `subscribe`                                | `billing:manage`, `billing:subscribe` |
| `organization` | `read`, `update`, `delete`                           | `organization:update`                 |
| `platform`     | `admin`                                              | `platform:admin`                      |
| `*` (wildcard) | any                                                  | `*:*` (granted only to `platform_admin`)|

**Reserved actions:** `write` / `invite` / `remove` are **not** valid action
names — the contract uses REST-style `create|update|delete`. `manage`,
`subscribe`, and `admin` are the composite actions for billing, the legacy
billing API seed, and the platform surface respectively. The canonical
validator lives at `frontend/src/lib/permissions.ts` and rejects any
permission string not in the matrix; new resources or actions must be
added to that allow-list, the migration, and the matrix doc together.

The contract is **scoped to the current org** for org resources. The endpoint
response is a `Record<resource, action[]>` for the current org context; the
frontend hook just checks membership. The `*:*` wildcard (granted to
`platform_admin` via the resolver) short-circuits every check.

---

## 5. Backend changes

### 5.1 `GET /me/permissions`

**File:** `backend/src/auth/routes.py` (the response is embedded on
`GET /api/v1/auth/me?org_id=<uuid>` so the user profile and the resolved
permissions land in a single round-trip on app boot — see Open Question 1
for the decision log).

**Response (200):**

```json
{
  "user_id": "uuid",
  "current_organization_id": "uuid-or-null",
  "permissions": {
    "agent": ["read", "create", "update", "delete"],
    "phone_number": ["read", "create", "update", "delete"],
    "skill": ["read", "create", "update", "delete"],
    "call_log": ["read"],
    "member": ["read", "create", "update", "delete"],
    "billing": ["manage"],
    "organization": ["read", "update"],
    "platform": ["admin"]
  }
}
```

For a regular org member, the same shape with `member: ["read"]` and
`billing: {}` and `organization: ["read"]` (read-only on every workspace
resource). The canonical role → grants mapping is documented in
`docs/02_features/authentication_rbac/permission-matrix.md` and is what the
resolver at `backend/src/auth/permissions_service.py` returns.

**Resolver shape:**

- `platform_admin` role → `{"*": ["*"]}` (the frontend hook short-circuits
  every check on the wildcard).
- `org_admin` role on the current org → full CRUD on every org-scoped
  resource plus `billing:manage`.
- Regular org member on the current org → read-only on every workspace
  resource. No `billing` entry. No `member:create|update|delete`.
- No current org context (or no matching role) → `{}`.

**Phase 2** replaces the in-code mapping with a lookup against the
`role_permissions` table joined with the user's roles on the current org.

### 5.2 Pydantic model

`backend/src/auth/permissions_models.py` (new file):

- `ResourcePermissions` (Dict[str, List[str]]).
- `MyPermissionsResponse` with `user_id`, `current_organization_id`,
  `permissions: ResourcePermissions`.

### 5.3 Tests (red→green)

`backend/tests/auth/test_me_permissions_route.py` (and
`backend/tests/auth/test_permissions_service.py` for the resolver unit
tests):

1. Platform admin gets `{"*": ["*"]}` (the wildcard that short-circuits
   every check).
2. Org admin on current org gets every org-scoped action including
   `billing:manage` and full CRUD on `member`.
3. Regular org member gets read-only on every workspace resource
   (`agent:read`, `phone_number:read`, `skill:read`, `call_log:read`,
   `member:read`, `organization:read`) and **no** `billing` entry.
4. User not in any org returns empty permissions object (no org context).
5. Unauthenticated → 401 (handled by `get_authenticated_user`).

---

## 6. Frontend changes

### 6.1 `useHasPermission()` hook

**File:** `frontend/src/hooks/use-has-permission.ts` (new).

Signature:

```typescript
function useHasPermission(perm: string): boolean | null;
function useHasAnyPermission(perms: string[]): boolean | null;
```

Where `perm` is `<resource>:<action>`. Returns `null` while loading, `true`
or `false` once resolved. The hook reads from a `useMyPermissions()` data
hook (TanStack Query) that hits `GET /me/permissions` and caches per
`currentOrganization.id`.

**Tests** (`frontend/src/hooks/__tests__/use-has-permission.test.ts`):

1. Returns `true` when the perm is in the resolved set.
2. Returns `false` when the perm is not in the set.
3. Returns `true` when `*` is present in the response.
4. Returns `null` while the query is loading.
5. `useHasAnyPermission` returns `true` if any of the perms is granted.

### 6.2 `nav-config.ts`

**File:** `frontend/src/components/layout/nav-config.ts` (new).

```typescript
export interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  requiredPermission: string | null;  // null = visible to all signed-in users
  section: "workspace" | "org_admin" | "platform_admin";
  exact?: boolean;
}
```

Initial entries (with permission strings):

| Section         | Name              | href                      | requiredPermission       |
|-----------------|-------------------|---------------------------|--------------------------|
| workspace       | Home              | `/dashboard`              | `null`                   |
| workspace       | Agents            | `/agents`                 | `agent:read`             |
| workspace       | Phone Numbers     | `/phone-numbers`          | `phone_number:read`      |
| workspace       | Skills            | `/skills`                 | `skill:read`             |
| workspace       | Calls             | `/calls`                  | `call_log:read`          |
| org_admin       | Members           | `/organization/members`   | `member:read`            |
| org_admin       | Billing           | `/organization/billing`   | `billing:manage`         |
| org_admin       | Organization      | `/organization`           | `organization:read`      |
| platform_admin  | All Users         | `/users`                  | `platform:admin`         |
| platform_admin  | Platform Skills   | `/platform/skills`        | `platform:admin`         |
| footer          | Settings          | `/settings`               | `null`                   |
| footer          | Sign out          | (action)                  | `null`                   |

**Tests** (`frontend/src/components/layout/__tests__/nav-config.test.ts`):

1. Every item has a `requiredPermission` field (null is allowed).
2. Every `requiredPermission` is one of the strings in the contract.
3. Sections are in the order: workspace → org_admin → platform_admin.

### 6.3 `dashboard-layout.tsx` refactor

Replace the hard-coded `item.name === "Users"` filter with a
permission-driven filter. Render three sections (workspace,
org_admin, platform_admin) with a visual separator between them.

**Section-level role gate (Option C).** A section's *heading* is
shown only if the current user holds the section's `requiredRole`
defined in `nav-config.ts` `SECTION_ROLES`. Items inside a section
remain permission-gated via `requiredPermission`. The mapping is:

| Section        | requiredRole      | Why                                                              |
| -------------- | ----------------- | ---------------------------------------------------------------- |
| `workspace`    | `null`            | Every signed-in user sees the base layer.                        |
| `org_admin`    | `org_admin`       | The section grants org admin powers; platform_admin inherits.    |
| `platform_admin` | `platform_admin` | Strictly platform-only; org_admin does NOT see this section.     |

A user with the underlying permissions but not the required role
(e.g. a future role that holds `member:read` but is not org_admin)
must NOT see the section heading or the items. The page-level
role check (`user.hasRole("platform_admin")`) on `/users` and
`/platform/skills` is the source of truth for those routes; the
nav section role gate is what prevents the nav from promising what
the page denies.

**Per-item permission gate.** Independent of the section role gate,
each item's `requiredPermission` (a `<resource>:<action>` string or
`null`) is checked via `useHasPermission()`. An item with
`requiredPermission: null` is visible to every signed-in user.
Items with a string permission render only when the user holds it
on the current org context. The wildcard `*:*` (granted to
platform admins via the Phase 1 RBAC seed) makes every item render.

**Component tests** (`frontend/src/components/layout/__tests__/dashboard-layout.test.tsx`):

1. Platform admin sees all three section headings + every item.
2. Org admin sees the workspace + org_admin section headings and
   items; no `platform_admin` heading or items.
3. Regular member sees only the workspace section heading and
   items; no `org_admin` heading or items; no `platform_admin`
   heading or items.
4. An item with a permission the user lacks is not rendered (even
   if the section role gate would allow it).
5. A user with the underlying org_admin permissions but not the
   org_admin role (e.g. a future granular role) still does NOT see
   the org_admin section heading or items (Option C lock-in test).

**Config tests** (`frontend/src/components/layout/__tests__/nav-config.test.ts`):

1. `SECTION_ROLES` maps every nav section key (`workspace`,
   `org_admin`, `platform_admin`) to a role or `null`.
2. `SECTION_ROLES.platform_admin === "platform_admin"`.
3. `SECTION_ROLES.org_admin === "org_admin"` (the inheritance for
   `platform_admin` is enforced in the layout, not in the config).
4. `SECTION_ROLES.workspace === null`.
5. Every nav item has a `requiredPermission` field (null allowed).
6. Every `requiredPermission` is either `null` or a valid
   `<resource>:<action>` string from the contract.

### 6.4 `OrganizationSwitcher`

**File:** `frontend/src/components/layout/organization-switcher.tsx` (new).

A clickable card at the top of the sidebar (below the logo) showing the
current org's name and role badge. Clicking opens a popover listing all
orgs the user belongs to, with a "Switch" action per row, plus a "Create
organization" entry at the bottom.

**Component tests** (`frontend/src/components/layout/__tests__/organization-switcher.test.tsx`):

1. Renders the current org name.
2. Renders the current org role badge.
3. Clicking opens the popover.
4. Popover lists every org the user belongs to.
5. Popover renders the "Create organization" entry.

### 6.5 Top-level route promotion

**New files:**

- `frontend/src/app/(dashboard)/phone-numbers/page.tsx` — renders the
  existing `PhoneNumberDashboard` component (currently embedded in
  `organization/page.tsx`).
- `frontend/src/app/(dashboard)/skills/page.tsx` — renders the existing
  `OrganizationSkillsTab` component (scoped to the current org).

**Write-action permission gates (N1 follow-ups #1–#4, shipped).**

The N1 browser validation surfaced write-action leaks on `/agents`,
`/skills`, `/phone-numbers`, `/organization/members`, and
`/organization/billing` for members who lacked the underlying permission.
All five fixes shipped on the `feature/improved-navigation` branch and
land in the same shape as the nav permission contract:

- `/agents` → page-level `canCreateAgent = isPlatformAdmin || isOrgAdmin`
  gates the 3 "New Agent" / "Create Your First Agent" buttons. Every
  `<AgentCard>` receives a per-agent `canDelete` / `canEdit` / `canConfigure`
  derived from the user's role on the **agent's** org, so a non-current-org
  agent shows no write affordances (this replaces the page-level flag the
  draft originally described — the per-agent check is the right model and
  was promoted in follow-up #1).
- `/skills` → `<OrganizationSkillsTab canCreate={…} canEdit={…}>` from the
  page. `<SkillEditor>` already consumes the flag for its per-row delete
  button and confirm dialog. A regular member sees no create, edit, or
  delete UI.
- `/phone-numbers` → `<PhoneNumberDashboard canManage={isPlatformAdmin ||
  isOrgAdmin}>` from the page. All 4 write buttons (Search & Purchase,
  Add Phone Number, Assign, Cancel) are gated on the prop.
- `/organization/members` → the columns factory accepts a `canManage` flag
  and returns `null` for the Actions column when false, so a regular member
  sees no per-row "Remove Member" dropdown.
- `/organization/billing` and `/agents/create` → page-level `AccessDenied`
  blocks for non-admins (and for the `/agents/create` direct-URL path).

**Out of scope (deferred, see n1-architecture-review.md):**

- **PhoneNumberDashboard dashboard-mode write prop audit** — the
  component still defaults `canCreate?` / `canDelete?` to `true` for
  back-compat. Every new call site must pass the page's `canManage`
  flag; the permissive default is a known tech-debt item (the audit
  flagged it as HIGH). Tracked under Epic C cleanup.
- **Per-agent write affordances on phone-numbers and skills** — the
  per-agent pattern promoted for `/agents` has not been propagated to
  the other two resource lists. Tracked under Epic C.
- **Backend write-endpoint audit** — frontend permission gates are a
  UX nicety, not a security boundary. The audit in
  `docs/tw-drafts/n1-followup-2-leak-audit.md` enumerated every
  endpoint that lacked a server-side check; fixes shipped for
  `tool_routes` (4 CRITs), `process-invitation`, the `member:invite`
  typo, 3 skill file/refresh IDORs, and 5 `has_permission`-without-org
  dead endpoints. Remaining `has_role` ladders (~27 across 5 route
  files) are tracked under task #41 / Epic C and migrate to
  `Depends(require_permission(…))` or `assert_has_permission(…)`
  depending on whether the org id is known at dep time or only after
  the resource is loaded.

**Route tests** (`frontend/src/app/(dashboard)/phone-numbers/__tests__/page.test.tsx`,
`frontend/src/app/(dashboard)/skills/__tests__/page.test.tsx`,
`frontend/src/app/(dashboard)/agents/__tests__/page.test.tsx`):

1. The new top-level page renders the dashboard/tab/component.
2. The component receives the current `orgId`.
3. Loading and error states match the embedded version.
4. **Permission gate (where applicable):** the "New Agent" / "Create
   Skill" / "Add Phone Number" buttons are not rendered for a
   regular member.

**Redirects:**

- `frontend/app/(dashboard)/organization?tab=phone-numbers` →
  `frontend/app/(dashboard)/phone-numbers`.
- `frontend/app/(dashboard)/organization?tab=skills` →
  `frontend/app/(dashboard)/skills`.
- `frontend/app/(dashboard)/organization?tab=ai-agent` →
  `frontend/app/(dashboard)/agents`.

The redirect **forwards deep-link query params** (everything except the
consumed `tab`): a legacy deep link like
`/organization?tab=skills&skill=appointment-booking&file=references/faq.md`
lands on `/skills?org_id=…&skill=…&file=…` so the `SkillEditor` can restore
the selected skill + file. `org_id` is always re-emitted. Implemented in
`legacy-tab-redirect.ts` (pure helper, unit-tested) and called from
`organization/page.tsx`'s `useEffect` watching `tabParam`.

### 6.6 `OrganizationPage` collapse

**File:** `frontend/src/app/(dashboard)/organization/page.tsx`.

Remove the `ai-agent`, `skills`, and `phone-numbers` tabs. Keep:

- `profile` (was `overview`) — name, description, website, slug, industry,
  location, business_details.
- `members` (already a separate page; keep the link).
- `billing` (already a separate page; keep the link).
- `danger-zone` (new; placeholder until org deletion lands).

---

## 7. TDD execution order

1. **Red — backend**: `backend/tests/test_me_permissions.py`. Write the five
   tests above. Run them; confirm they fail (route doesn't exist).
2. **Green — backend**: implement `MyPermissionsResponse`, the resolver
   stub in `backend/src/auth/permissions_service.py`, and the route in
   `backend/src/auth/routes.py`. Re-run; confirm pass.
3. **Red — frontend hook**: `use-has-permission.test.ts`. Confirm fail.
4. **Green — frontend hook**: implement `useMyPermissions` (TanStack Query)
   and `useHasPermission` / `useHasAnyPermission`.
5. **Red — nav-config**: `nav-config.test.ts`. Confirm fail.
6. **Green — nav-config**: write the config.
7. **Red — layout**: `dashboard-layout.test.tsx`. Confirm fail.
8. **Green — layout**: refactor `dashboard-layout.tsx`.
9. **Red — org switcher**: `organization-switcher.test.tsx`. Confirm fail.
10. **Green — org switcher**: implement.
11. **Red — route promotion**: `phone-numbers/page.test.tsx`,
    `skills/page.test.tsx`. Confirm fail.
12. **Green — route promotion**: create the routes with the existing
    components.
13. **Red — Org page collapse**: tab-redirect test. Confirm fail.
14. **Green — Org page collapse**: implement redirects, remove tabs.
15. **Browser validation** (per AGENTS.md): open
    `http://localhost:3000`, log in as `test@cogninets.local`, walk through
    the new nav, click every item, verify the switcher works, take
    screenshots. Then **clean up** all smoke-test artifacts (test data,
    screenshots, role grants) before merging.

---

## 8. Open questions

1. ~~**Endpoint shape**: extend `GET /me` (add a `permissions` field) or add a
   separate `GET /me/permissions`?~~ **Resolved (shipped):** the `permissions`
   and `current_organization_id` fields are embedded on `GET /api/v1/auth/me`
   with an `?org_id=` query param. The single round-trip on app boot won out
   over the separate endpoint — the `useMyPermissions` hook re-uses the same
   TanStack Query cache that the auth context already warms.
2. **Permission check on the Org page tabs (vs redirects)**: if a user
   navigates to `?tab=phone-numbers` directly, do we (a) redirect to
   `/phone-numbers`, or (b) render the tab? **Recommendation:** redirect —
   the new top-level routes are the canonical path. Confirm before
   implementing.
3. ~~**TanStack Query vs simpler cache**: the existing app uses TanStack
   Query (`useQuery`, `useMyAgents`, etc.) — confirm we should use
   `useQuery` for `useMyPermissions` and not introduce a new caching
   pattern.~~ **Resolved (shipped):** `useMyPermissions` is a `useQuery`
   keyed by the current `orgId`, with `staleTime` of 60s and an org-switch
   invalidation.

---

## 9. Out of scope (deferred to follow-up)

- Removing the duplicate avatar-menu entries (Settings, Members, Billing).
- Per-resource permission resolution against `role_permissions` (Phase 2).
- Org page "Danger zone" (delete org) — needs backend support first.
- URL refactor `?org_id=` → `/{resource}/{orgId}/` (task #27).
