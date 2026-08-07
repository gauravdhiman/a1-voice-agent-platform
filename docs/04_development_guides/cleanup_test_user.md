# Test / Sandbox User Cleanup

## Overview

The `backend/scripts/cleanup_test_user.py` dev helper deletes a test or
sandbox user from the database together with **every resource they own**. It is
meant for local development and test environments ("I created a test user, now
remove everything").

It is a **destructive** script. Always run it in dry-run mode first and review
the plan before applying.

## Usage

Run from the `backend` directory (inside the `backend-dev` container or with
the project virtual environment active):

```bash
# 1. Show the plan without changing anything (dry-run, the default)
python scripts/cleanup_test_user.py --email test@cogninets.local

# 2. Identify by id instead of email
python scripts/cleanup_test_user.py --user-id <auth.users-uuid>

# 3. Apply, answering the confirmation prompt
python scripts/cleanup_test_user.py --email test@cogninets.local --apply

# 4. Apply without a prompt (CI / scripts)
python scripts/cleanup_test_user.py --user-id <uuid> --apply --yes
```

The script is also directly executable (it has a shebang and the executable
bit), so `backend/scripts/cleanup_test_user.py --help` works from the repo root.
Anything beyond `--help` (i.e. an actual run) additionally needs `psycopg2` in
the active Python environment, so prefer the venv/container form for real runs:

### Options

| Option | Description |
|---|---|
| `--email EMAIL` | Target user email (case-insensitive). Mutually exclusive with `--user-id`. |
| `--user-id UUID` | Target user's `auth.users` id. Mutually exclusive with `--email`. |
| `--database-url URL` | Postgres connection string. Defaults to `DATABASE_URL` env, then `settings.database_url`. |
| `--apply` | Apply the deletions. **Default is dry-run** (prints the plan only). |
| `--yes` | Skip the confirmation prompt. Only meaningful with `--apply`. |

## What It Deletes

1. **Organizations where the user is the SOLE member** — the organization and
   its full resource subtree (voice agents, agent tools, embed configs, embed
   call logs, call logs, phone numbers, organization skills and their files,
   agent skill assignments, skill update logs, subscriptions, billing history,
   credit transactions, notification logs, invitations, memberships). This
   relies on the database `ON DELETE CASCADE` chain rooted at `organizations`,
   so the whole tenant subtree is removed atomically.
2. **Shared organizations** (more than one member) — **left intact**. Only the
   target user's membership row is removed (plus invitations they sent and
   their notification logs, via the `auth.users` cascade).
3. **The user row itself** — `auth.users` deletion cascades to `identities`,
   `sessions`, `refresh_tokens`, `user_roles`, and invitations the user sent.
4. **Non-cascading user rows** — `notification_logs` and
   `email_verification_tokens` have no FK to `auth.users`, so they are deleted
   explicitly before the auth row.

### What It NEVER Touches

Global/system catalogs shared across tenants are always left in place:
`platform_tools`, `pipeline_presets`, `platform_skills`, `platform_skill_files`,
`roles`, `permissions`, `role_permissions`, `notification_events`,
`notification_templates`, `credit_events`, `credit_products`,
`subscription_plans`, `voice_templates`.

## Safety Guarantees

- **Dry-run by default**: nothing is mutated unless `--apply` is passed.
- **Confirmation prompt** before applying (skippable with `--yes`).
- **Single transaction**: all deletions commit only after the last one
  succeeds; any failure rolls everything back.
- **Sole-member check**: an organization is deleted only when the target user
  is the only member in `user_roles`. Shared orgs are never deleted.

## Notes

- The script connects with `DATABASE_URL` (or `--database-url`), which points
  at the local Supabase Postgres instance. Run it inside the `backend-dev`
  container or from the host with the env loaded.
- Deleting from `auth.users` requires a connection with sufficient privileges
  (the local `postgres` superuser works; a restricted service role may not).
- Related: [Database Migrations](database_migrations.md) for schema changes,
  and [Database Schema](../../DATABASE_SCHEMA.md) for the FK/cascade graph the
  deletion relies on.
