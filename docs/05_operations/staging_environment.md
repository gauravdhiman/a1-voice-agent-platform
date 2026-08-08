# Cloud Staging Environment

**Project:** [oc-dev-ai-voice-agent-platform](https://supabase.com/dashboard/project/gdzwiwukcwbqohfwxxrx)  
**URL:** `https://gdzwiwukcwbqohfwxxrx.supabase.co`  
**Region:** `us-west-2`  
**Purpose:** Isolated cloud database for local Docker validation before production deploy.

Production Supabase (`zymiyfilulmtrmyyhvzw`) powers **247ai.live** — never point local `.env` at production for feature testing.

---

## Environment files

| File | Supabase | Use when |
|------|----------|----------|
| `.env.local` | Local (`127.0.0.1:54321`) | Default day-to-day dev |
| `.env.staging` | Staging (`gdzwiwukcwbqohfwxxrx`) | Local Docker + cloud staging DB |
| `.env.cloud` | Production (`zymiyfilulmtrmyyhvzw`) | Deploy / migrate production only |

Templates (committed):

- `.env.staging.example` → copy to `.env.staging`
- `.env.cloud.example` → copy to `.env.cloud`

Switch local Docker to staging:

```bash
cp .env.staging .env
./start.sh restart dev
```

Switch back to local Supabase:

```bash
cp .env.local .env
./start.sh restart dev
```

---

## First-time staging bootstrap

The staging project starts **empty** and **behind** on Alembic (was at `20260127000001`). Run the bootstrap script once after filling credentials.

### 1. Create `.env.staging`

```bash
cp .env.staging.example .env.staging
# or copy Stripe/OAuth from prod and swap Supabase refs:
python3 scripts/create-env-staging.py --from .env.cloud
```

Supabase **renamed** the old API keys in newer projects. Use this mapping in `.env.staging`:

| What you need in `.env` | Where in Supabase dashboard | Starts with |
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

Copy Stripe keys from production `.env.cloud` for now (same Stripe account). Split test keys later.

### 2. Run bootstrap

```bash
./scripts/bootstrap-staging-db.sh
```

This runs three steps in order:

```mermaid
flowchart LR
  A["alembic upgrade 20260807000001"] --> B["stripe_manager seed"]
  B --> C["alembic upgrade head"]
```

**Why this order?** Migration `20260807000002` backfills `plan_products` / `plan_versions` from rows in `subscription_plans`. Seeding must happen **before** that migration on an empty database.

Options:

```bash
./scripts/bootstrap-staging-db.sh --dry-run-seed   # preview Stripe seed
./scripts/bootstrap-staging-db.sh --skip-seed      # migrations only
```

### 3. Point local app at staging

```bash
cp .env.staging .env
./start.sh restart dev
```

Open http://localhost:3000 — auth and data come from staging Supabase.

**CORS:** When running the frontend at `http://localhost:3000`, `CORS_ORIGINS` in `.env.staging` must include localhost (see `.env.staging.example`). If you generated `.env.staging` from `.env.cloud` via `create-env-staging.py`, re-run the script or copy the `CORS_ORIGINS` line from the example — production-only origins (`https://www.247ai.live`) cause signup/API calls to fail with `OPTIONS 400 Disallowed CORS origin`.

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

```bash
# Staging — specific revision
ENV_FILE=.env.staging REVISION=20260807000001 ./scripts/deploy/run-alembic.sh
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
-- expect: 20260807000002 (or current head)

SELECT COUNT(*) AS plans FROM subscription_plans;
SELECT COUNT(*) AS products FROM plan_products;
SELECT COUNT(*) AS versions FROM plan_versions;
SELECT COUNT(*) AS entitlements FROM entitlement_definitions;
```

Expected after full bootstrap:

- `alembic_version` at head
- `subscription_plans` > 0 (from Stripe seed)
- `plan_products` includes `free` + backfilled paid products
- `entitlement_definitions` ≈ 11 rows (seeded in migration)

---

## Related docs

- [Environment configuration](./environment_configuration.md)
- [Deployment](./DEPLOYMENT.md)
- [Entitlements tracker](../03_implementation/ENTITLEMENTS_IMPLEMENTATION_TRACKER.md)
