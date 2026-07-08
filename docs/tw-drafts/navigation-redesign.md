# Navigation Redesign + Permission Contract (N1)

**Status:** In progress (TDD, red→green)
**Owner:** Platform
**Sprint board:** `docs/SPRINT-BOARD.md` (next-up item #1)
**Date:** 2026-07-04

---

## 1. Problem statement

The current left-nav (`frontend/src/components/layout/dashboard-layout.tsx`) is
coarse, hard-coded by name, and gets one major thing wrong: it treats org-user
and platform-admin items as siblings with no separator, filters them with a
literal `item.name === "Users"` check, and hides Phone Numbers / Skills / Org
admin / Settings behind an avatar dropdown or inside the org page's tab strip.

Today, every org member has full CRUD on agents, phone numbers, and skills —
there is no per-resource permission gate. When the proper RBAC system lands,
we don't want to re-plumb the nav, the layout, or the page-level guards. The
right move is to ship the **contract** (a permission string format, a
`/me/permissions` endpoint, and a `useHasPermission()` hook) **now** with a
stub resolver, so the Phase 2 work is a backend change, not a refactor.

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
5. **Zero behavior regression for current users**: an org member today still
   sees every workspace item and every action they're used to.

---

## 3. Non-goals

- Building the full RBAC per-role permission resolver (Phase 2).
- Hiding the create/edit buttons inside individual pages when the user lacks
  write permission (Phase 2). The current contract is **visibility only** at
  the nav level.
- Removing the duplicate avatar-menu entries (Settings, Members, Billing) on
  day one. They stay for one release as a fallback; removal is a follow-up.

---

## 4. Permission string contract

Format: `<resource>:<action>` — matches the existing `UserProfile.has_permission()` API.

| Resource       | Actions                       | Example strings                       |
|----------------|-------------------------------|---------------------------------------|
| `agent`        | `read`, `write`, `delete`     | `agent:read`, `agent:write`           |
| `phone_number` | `read`, `write`, `delete`     | `phone_number:read`                   |
| `skill`        | `read`, `write`, `delete`     | `skill:read`                          |
| `call_log`     | `read`                        | `call_log:read`                       |
| `member`       | `read`, `invite`, `remove`    | `member:invite`                       |
| `billing`      | `manage`                      | `billing:manage`                      |
| `organization` | `read`, `update`, `delete`    | `organization:update`                 |
| `platform`     | `admin`                       | `platform:admin`                      |
| `*` (wildcard) | any                           | `*` (platform admins only today)      |

The contract is **scoped to the current org** for org resources. The endpoint
response is one flat list per org context (resolved server-side); the
frontend hook just checks set membership.

---

## 5. Backend changes

### 5.1 `GET /me/permissions`

**File:** `backend/src/auth/routes.py` (extend existing `/me` route, OR add a new
`/me/permissions` route — see open question below).

**Response (200):**

```json
{
  "user_id": "uuid",
  "current_organization_id": "uuid-or-null",
  "permissions": {
    "agent": ["read", "write", "delete"],
    "phone_number": ["read", "write", "delete"],
    "skill": ["read", "write", "delete"],
    "call_log": ["read"],
    "member": ["read", "invite", "remove"],
    "billing": ["manage"],
    "organization": ["read", "update"],
    "platform": ["admin"]
  }
}
```

For a regular org member, the same shape with `member: []` and
`billing: []` and `organization: ["read"]`.

**Stub resolution (Phase 1):**

- `platform_admin` role → full `*` (encoded as the literal `"*"` entry in
  the `platform` key — the frontend hook treats it as "all permissions").
- `org_admin` role on the current org → every org-scoped permission.
- Any other org member → every org-scoped **read** permission, plus
  `agent:write`, `phone_number:write`, `skill:write` (today everyone has
  CRUD; this preserves the current behavior exactly).

**Phase 2** replaces the stub with a lookup against the
`role_permissions` table joined with the user's roles on the current org.

### 5.2 Pydantic model

`backend/src/auth/permissions_models.py` (new file):

- `ResourcePermissions` (Dict[str, List[str]]).
- `MyPermissionsResponse` with `user_id`, `current_organization_id`,
  `permissions: ResourcePermissions`.

### 5.3 Tests (red→green)

`backend/tests/test_me_permissions.py` (new file, TDD):

1. Platform admin gets `platform: ["*"]` and every resource with every action.
2. Org admin on current org gets every org-scoped action.
3. Regular org member gets `agent:read|write|delete`, `phone_number:read|write|delete`,
   `skill:read|write|delete`, `call_log:read`, `member:read`,
   `organization:read`, but NOT `member:invite|remove`, NOT `billing:manage`,
   NOT `organization:update|delete`.
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

**Write-action permission gates (follow-up, N1 follow-up #1).**

The N1 browser validation surfaced write-action leaks on `/agents` and
`/skills`: the per-row delete button and the page-level "New Agent"
/"Create Your First Agent" buttons rendered for regular members who
lacked the underlying permission. The fix is consistent with the nav
permission contract:

- `/skills` → `<OrganizationSkillsTab canCreate={isPlatformAdmin || isOrgAdmin} canEdit={isPlatformAdmin || isOrgAdmin} />`.
  The tab already passes `canDelete={canCreate}` to `<SkillEditor>`.
  The editor's per-row delete button consults `canDelete` (the
  permission gate dominates the adapter capability check) so a
  regular member sees no delete UI. The editor's confirm dialog
  remains `canDelete`-gated (defence in depth).
- `/agents` → page-level `canCreateAgent = isPlatformAdmin || isOrgAdmin`.
  The 3 "New Agent" / "Create Your First Agent" buttons are gated on
  this flag. Every `<AgentCard>` receives `canDelete={canCreateAgent}`,
  and the card gates its trash icon on that prop.
- `<AgentCard>` accepts optional `canDelete?` / `canEdit?` /
  `canConfigure?` props (default `true` for back-compat with pre-N1
  call sites). The page is the strict gate; the card is permissive by
  default.

**Out of scope (follow-up tasks):**

- **PhoneNumberDashboard write-action leak**: the dashboard is a
  controlled component that does not currently gate its 4 write
  buttons (Search & Purchase, Add Phone Number, Assign, Cancel) on
  user permissions. The page shows a "read-only access" message for
  non-admins but does not actually pass any permission props. The
  fix is to add optional `canCreate?` / `canDelete?` props to
  `PhoneNumberDashboard` and pass them from the page.
- **Cross-org delete on `/agents`**: the page lists agents across
  all orgs; a page-level `canDelete` derived from the current org
  is wrong for non-current-org agents. For now, the simple
  page-level flag (matching the org-scoped `/skills` pattern) is
  acceptable because the backend re-validates per-org. The proper
  fix is a per-agent "can I delete this" check.
- **Backend write-endpoint audit**: the frontend permission gates
  are a UX nicety, not a security boundary. Every write endpoint
  must independently enforce the role/permission. Audit
  `/agents` (POST/DELETE/PATCH), `/skills` (POST/PATCH/DELETE/file
  CRUD), `/phone-numbers` (purchase/assign/cancel), and
  `/platform/skills` for the matching server-side checks.

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

Handled in `organization/page.tsx` itself (a `useEffect` watching
`tabParam`), or via Next.js `redirects()` in `next.config.js`. TBD in
implementation — pick whichever the project already uses. (Check the
existing config; if neither, use the `useEffect` approach in the page to
keep this change self-contained.)

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

1. **Endpoint shape**: extend `GET /me` (add a `permissions` field) or add a
   separate `GET /me/permissions`? Pro separate: lets the frontend cache
   permissions independently of the user profile. Pro extend: one fewer
   network round-trip on app boot. **Recommendation:** separate endpoint —
   permissions are queried by `useHasPermission` on every nav render, and
   we don't want to re-fetch the entire user profile for that. Confirm
   before implementing.
2. **Permission check on the Org page tabs (vs redirects)**: if a user
   navigates to `?tab=phone-numbers` directly, do we (a) redirect to
   `/phone-numbers`, or (b) render the tab? **Recommendation:** redirect —
   the new top-level routes are the canonical path. Confirm before
   implementing.
3. **TanStack Query vs simpler cache**: the existing app uses TanStack
   Query (`useQuery`, `useMyAgents`, etc.) — confirm we should use
   `useQuery` for `useMyPermissions` and not introduce a new caching
   pattern.

---

## 9. Out of scope (deferred to follow-up)

- Removing the duplicate avatar-menu entries (Settings, Members, Billing).
- Hiding create/edit buttons on individual pages when the user lacks write
  permission (page-level guards).
- Per-resource permission resolution against `role_permissions` (Phase 2).
- Org page "Danger zone" (delete org) — needs backend support first.
