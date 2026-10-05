# Cloud Staging Environment

**Project:** [oc-dev-ai-voice-agent-platform](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx)  
**URL:** `https://gdzwiwukcwbqohfwxxrx.supabase.co`  
**Region:** `us-west-2`  
**Purpose:** Isolated cloud database for local Docker validation before production deploy.

This is a shared release-validation environment, not a database for concurrent
Git worktrees. Use a worktree-specific local Supabase stack for interactive
feature testing. See [Worktree Isolation and Release Promotion Strategy](deployment/worktree-and-release-strategy.md).

Production Supabase (`zymiyfilulmtrmyyhvzw`) powers **247ai.live** — never point local `.env.local` or `.env.staging` at production for feature testing.

---

## Environment files

| File | Supabase | Use when |
|------|----------|----------|
| `.env.local` | Local (`127.0.0.1:54321`) | Default day-to-day dev |
| `.env.staging` | Staging (`gdzwiwukcwbqohfwxxrx`) | Local Docker + cloud staging DB |
| `.env.prod` | Production (`zymiyfilulmtrmyyhvzw`) | Deploy / migrate production only |

Templates (committed):

- `.env.local.example` → copy to `.env.local`
- `.env.staging.example` → copy to `.env.staging`
- `.env.prod.example` → copy to `.env.prod`

The startup script selects the file for you. No file copying is needed:

```bash
./start.sh start dev                 # local Supabase (.env.local)
./start.sh start dev --env staging   # staging Supabase (.env.staging)
./start.sh start prod                # production Supabase (.env.prod)
```

Every application `start`/`restart` runs `alembic upgrade head` in the
backend container before Docker services start, and rebuilds images so runtime
dependencies stay synchronized with the checked-out requirements. A migration
failure prevents the app from starting. Because `.env.staging` is a shared
database, only one release candidate should run the staging startup or
validator at a time.

Use `./start.sh config --env staging` to verify the selected file and Supabase
URL without printing secrets.

### Shared-database rule

Compose project names and port offsets isolate application containers, but all
stacks using `.env.staging` still share this Supabase project. Do not run
branch-specific migrations or destructive test-data changes from multiple
worktrees against staging. Select one release candidate for staging validation;
run other worktrees against their own local Supabase instances.

---
## Staging migration state and bootstrap

The staging database must be checked read-only before a shared migration. The
validator performs that compatibility check, applies `alembic upgrade head`,
verifies data postconditions, and starts the local application stack. The
startup command also applies the idempotent migration gate, so a direct local
staging start cannot silently run against an older schema:

```bash
./scripts/validate-staging.sh           # check + migrate + sync usage meters/tools/demos + restart local stack
# Direct start is only for a database whose release catalogs were already synced.
./start.sh start dev --env staging
```

Check any future checkout before touching shared staging:
```bash
python3 scripts/deploy/check_alembic_compatibility.py --env-file .env.staging
```

The legacy bootstrap script is still available for a newly recreated or
intentionally reset staging project. Do not run it merely because the
database is at the current head.

### 1. Create `.env.staging`

```bash
cp .env.staging.example .env.staging
# or copy Stripe/OAuth from prod and swap Supabase refs:
python3 scripts/create-env-staging.py --from .env.prod
```

Supabase **renamed** the old API keys in newer projects. Use this mapping in `.env.staging`:

| What you need in `.env.staging` | Where in Supabase dashboard | Starts with |
|-------------------------|----------------------------|-------------|
| `SUPABASE_SERVICE_KEY` | **Settings → API Keys → Secret keys** | `sb_secret_...` (or legacy JWT on **Legacy API Keys** tab) |
| `SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Settings → API Keys → Publishable keys** | `sb_publishable_...` (or legacy `anon` JWT on **Legacy API Keys** tab) |
| `DATABASE_URL` | **Connect** button (top of project) → **Session pooler** | `postgresql://postgres.gdzwiwukcwbqohfwxxrx:...@aws-0-us-west-2.pooler.supabase.com:5432/postgres` |

#### API keys (Settings → API Keys)

Open: [API Keys — staging project](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx/settings/api-keys)

1. **Publishable key** → paste into both `SUPABASE_ANON_KEY` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
2. **Secret key** → paste into `SUPABASE_SERVICE_KEY`  
   (This is the replacement for the old **service_role** key — same elevated backend access.)

If you only see **Publishable keys** and **Secret keys** (no “service_role” label), that is expected on new projects.

Optional: on the **Legacy API Keys** tab you may still see `anon` / `service_role` JWT keys — either format works in this repo.

#### Database URL (Connect panel, not Settings → API)

Open: [Connect — staging project](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx?showConnect=true)

1. Click **Connect** at the top of the project page (green button near the project name)
2. Choose **Session pooler** (port **5432**) — best for Alembic migrations from your Mac
3. Copy the URI and set it as `DATABASE_URL` in `.env.staging`
4. Replace `[YOUR-PASSWORD]` with your **database password**

**Don't know the database password?**

- [Database Settings → Reset database password](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx/database/settings)
- This is **not** your Supabase login password — it is the Postgres `postgres` user password
- URL-encode special characters in the password when building the URI (`#` → `%23`, `@` → `%40`)

Example shape (yours will include the real password):

```bash
DATABASE_URL=postgresql://postgres.gdzwiwukcwbqohfwxxrx:YOUR_URL_ENCODED_PASSWORD@aws-0-us-west-2.pooler.supabase.com:5432/postgres
```

Copy Stripe keys from production `.env.prod` for now (same Stripe account). Split test keys later.

### 2. Run bootstrap

```bash
./scripts/bootstrap-staging-db.sh
```

When the staging project is empty or at an older known revision, this runs
four steps in order:

```mermaid
flowchart LR
  A["alembic upgrade 20260807000001"] --> B["alembic upgrade head"]
  B --> C["master-data apply (missing system-pricing meters)"]
  C --> D["stripe_manager seed (approved credit packs)"]
```

The head upgrade first runs the legacy `subscription_plans` backfill and creates
the atomic credit-catalog sync function. The default Stripe Manager seed then
syncs only the approved credit packs; it does not import Stripe subscription
prices or overwrite the admin-managed plan and usage catalogs. Bootstrap and
release fixture sync create missing code-owned system-pricing meters (including
new phone rental meters) while preserving existing rates.

Legacy Stripe plan imports are a separate, deliberate backfill. If one is
required, first preview it against the intended Stripe account and database
with `seed --include-legacy-billing-data --skip-credit-products --dry-run` at
revision `20260807000001`, review the imported plans, then run that command
without `--dry-run` before upgrading to `head`. After the migration backfills
those rows into plan versions, run the normal `seed` command to sync approved
credit packs. Do not use this legacy path to publish current paid plans; manage
those through the Plan Catalog admin UI.

Options:

```bash
./scripts/bootstrap-staging-db.sh --dry-run-seed   # preview system-pricing + Stripe seed
./scripts/bootstrap-staging-db.sh --skip-seed      # migrations only
```

After bootstrap (including `--skip-seed`), use `./scripts/validate-staging.sh`
to synchronize the release catalogs and start the local application. A direct
`start.sh` command does not synchronize system pricing, tools, or demos.

### 3. Point local app at staging

```bash
./scripts/validate-staging.sh
```

Open http://localhost:3000 — auth and data come from staging Supabase.

**CORS:** When running the frontend at `http://localhost:3000`, `CORS_ORIGINS` in `.env.staging` must include localhost (see `.env.staging.example`). If you generated `.env.staging` from `.env.prod` via `create-env-staging.py`, re-run the script or copy the `CORS_ORIGINS` line from the example — production-only origins (`https://www.247ai.live`) cause signup/API calls to fail with `OPTIONS 400 Disallowed CORS origin`.

### 4. Grant platform admin (first user)

After signup, grant `platform_admin` so `/platform/plans` and `/platform/entitlements` work:

```sql
-- Run in Supabase SQL editor (staging project)
INSERT INTO user_roles (user_id, role_id, organization_id)
SELECT u.id, r.id, NULL
FROM auth.users u
CROSS JOIN roles r
WHERE u.email = 'your-email@example.com'
  AND r.name = 'platform_admin'
ON CONFLICT DO NOTHING;
```

---

## Manual migration commands

The normal path is the validator:

```bash
./scripts/validate-staging.sh                 # check + migrate + verify + sync meters/tools/demos + restart
./scripts/validate-staging.sh --migrate-only  # check + migrate + verify; no catalog sync or app start
```

After `--migrate-only`, rerun the full validator before starting the staging
app. This applies the reviewed release catalogs, including any newly added
system-pricing meter.

For granular control:

```bash
# Staging — check first, then apply a specific revision only when necessary
python3 scripts/deploy/check_alembic_compatibility.py --env-file .env.staging
ENV_FILE=.env.staging REVISION=20260807000001 ./scripts/deploy/run-alembic.sh
./scripts/deploy/sync-release-fixtures.sh --env-file .env.staging --project-name 247ai-staging
ENV_FILE=.env.staging REVISION=head ./scripts/deploy/run-alembic.sh

# Production (247ai.live) — use with care
./scripts/deploy.sh migrate
```

---

## Stripe & OAuth (current policy)

| Integration | Staging today | Recommended later |
|-------------|---------------|-------------------|
| Stripe | Same keys as production (per team decision) | Stripe **test** mode + CLI webhooks |
| Google OAuth | Same client IDs as production | Separate OAuth client with localhost redirect |
| Supabase Auth providers | Configure on **staging** project dashboard | Keep separate from prod |

**Webhook note:** Stripe webhooks hit whatever URL is configured in the Stripe dashboard (usually `api.247ai.live`). Local staging validation covers UI, catalog, and entitlements — not full webhook-driven billing unless you add Stripe CLI forwarding.

---

## Verification checklist

After bootstrap, confirm in [Supabase SQL editor](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx/sql/new):

```sql
SELECT version_num FROM alembic_version;
-- expect: the selected release candidate's Alembic head

SELECT COUNT(*) AS plans FROM subscription_plans;
SELECT COUNT(*) AS products FROM plan_products;
SELECT COUNT(*) AS versions FROM plan_versions;
SELECT COUNT(*) AS entitlements FROM entitlement_definitions;
```

Expected after full bootstrap:

- `alembic_version` at head
- `subscription_plans` contains legacy rows only when the separate backfill was used
- `plan_products` includes Free and any paid products backfilled from existing legacy rows
- `entitlement_definitions` ≈ 11 rows (seeded in migration)

The default credit-pack sync does not populate paid subscription plans. Add
current paid plans through the authenticated Plan Catalog after bootstrap.

---

## Related docs

- [Environment configuration](./environment_configuration.md)
- [Deployment](./DEPLOYMENT.md)
- [Entitlements tracker](../03_implementation/ENTITLEMENTS_IMPLEMENTATION_TRACKER.md)
