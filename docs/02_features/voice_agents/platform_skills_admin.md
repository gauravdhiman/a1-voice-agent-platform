# Platform Skills Management (Admin)

**Audience:** Platform administrators.
**Scope:** Voice-only platform. Platform skills are immutable built-in skill
templates that org admins can **fork** into their own editable libraries.

## Overview

Platform admins manage the built-in skill templates available to all
organizations. The UI is a **master-detail editor** shared with the organization
skills tab — `<SkillEditor>` in `frontend/src/components/skills/skill-editor.tsx`,
driven by a mode (`"platform"` | `"organization"`) and a data-access adapter.
Both the platform page (`/platform/skills`) and the org skills tab
(`OrganizationSkillsTab` in `frontend/src/components/skills/organization-skills-tab.tsx`)
render the same component, so the two surfaces stay consistent by construction.
Platform-admin-only, enforced on both the frontend (Access Denied + hidden nav
item) and the backend (defense in depth).

## UX

- **Left panel:** skill list with a filter and an **Add** menu
  (Create Skill / Import from URL). Each skill row expands into a file tree
  (SKILL.md entry + reference files grouped by folder).
- **Right panel:** skill/file view with inline **Edit**, **Add File**, and
  content rendering (markdown / code / JSON).
- **Create:** dialog (slug + name + description + markdown content). Slug is
  lowercase kebab-case, **globally unique, and read-only after creation** — it is
  matched by the seeder (`GET platform_skills?slug=eq.<slug>`), so renaming
  would create duplicates on re-seed.
- **Import from URL:** `POST /api/v1/platform/skills/import` fetches a skill
  package (SKILL.md + reference files) from GitHub / skills.sh and stores it as
  a **platform skill template** (not an org custom skill).

## Endpoints (`/api/v1/platform/skills…`, `platform_skill_router`)

| Action | Endpoint | Auth |
|--------|----------|------|
| List (active) | `GET /platform/skills` | any authenticated user (default filter `statuses=active`) |
| List by status(es) | `GET /platform/skills?statuses=active&statuses=deprecated&statuses=deleted` | platform admin (any non-active filter) |
| Get full skill + files | `GET /platform/skills/{id}` | platform admin |
| Create | `POST /platform/skills` | platform admin (status defaults to `active`) |
| Update | `PUT /platform/skills/{id}` | platform admin (bumps version; status is NOT settable here — use transition endpoints) |
| Deprecate | `POST /platform/skills/{id}/deprecate` | platform admin (`active` → `deprecated`) |
| Reactivate | `POST /platform/skills/{id}/reactivate` | platform admin (`deprecated` → `active`) |
| Soft delete | `DELETE /platform/skills/{id}` | platform admin (`*` → `deleted`; rejects already-deleted) |
| Restore | `POST /platform/skills/{id}/restore` | platform admin (`deleted` → `active`; rejects other states) |
| Import from URL | `POST /platform/skills/import` | platform admin |
| Files CRUD | `/platform/skills/{id}/files…` | platform admin |

**Status state machine**

```
DRAFT ──(publish, future)──► ACTIVE ──deprecate──► DEPRECATED ──reactivate──► ACTIVE
                                       │              │
                                       │              ▼
                                       └──────────► DELETED ──restore──► ACTIVE
```

The transition endpoints are the only way to change status. `PUT` only edits
`name` / `description` / `content`. Invalid transitions return 400 (e.g.,
deprecating a `deleted` skill). `restore` always lands on `active`; admins
can re-deprecate if needed.

## Authorization (defense in depth)

- **Frontend:** page early-returns `<AccessDenied>` when
  `user.hasRole("platform_admin")` is false; sidebar item filtered out for
  non-admins (`dashboard-layout.tsx`).
- **Backend:** every management route calls `_require_platform_admin` → `403
  {"detail":"Platform admin access required"}` for non-admins, independent of
  the frontend.

## Reuse status

- Both the **platform skills page** and the **organization skills tab** now render
  the shared `<SkillEditor>` (via `OrganizationSkillsTab` for org mode). The
  organization page's previous inline skills UI has been removed in favor of the
  shared component. Feature flags preserve org-only concepts (Platform/Custom
  badge, `is_visible` library toggle, fork-from-platform-library, refresh, hard
  delete with an agents-using pre-check) without affecting the platform page.

## Implemented

- **Soft delete (`status=deleted`) + show-deleted filter + restore** is live.
  The platform page exposes delete via the trash icon on each row and restore
  via the rotate-ccw icon next to deleted skills. Admins also see deprecate
  (archive icon, active → deprecated) and reactivate (rotate-ccw, deprecated
  → active) controls.
- **Dedicated transition endpoints** enforce the state machine: invalid
  transitions (e.g. deprecate a deleted skill, restore an active skill)
  return 400 with a descriptive message.

## Testing

- Backend: `backend/tests/voice_agents/test_platform_skill_routes.py` — 403 for
  non-admins and success for platform admins across all CRUD + file + import
  routes, including the `include_inactive` admin gate.
- Frontend: `frontend/tests/services/test-skill-service.test.ts` —
  `Platform Skills (admin CRUD)` block covers list (incl. inactive), get, create,
  update, delete, file CRUD, and import-from-URL.
- Frontend (component): `frontend/tests/components/test-skill-editor.test.tsx` —
  renders the shared `<SkillEditor>`, and covers the content-hydration regression
  (platform summaries carry no content; selecting a skill must hydrate via
  `adapter.hydrateSkill` and render SKILL.md).
