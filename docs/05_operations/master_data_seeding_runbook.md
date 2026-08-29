# Master-data seeding runbook

This is the copy-paste operating guide for reviewing and explicitly applying
platform master data. The workflow is intentionally separate from application
startup: preview is read-only, JSON is the apply artifact, and normal apply is
idempotent and non-destructive.

For the domain inventory, source ownership, and launch decisions, see
[Master-data catalog and seeding](../03_implementation/master_data_seeding.md)
and [Master-data launch strategy](master_data_launch_strategy.md).

## Quick reference: isolated Docker stack

The currently configured review stack uses this backend container:

```bash
SEED_CONTAINER=247ai-master-data-seeding-backend-dev-1
```

Check that the stack is running and healthy:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | grep 247ai-master-data-seeding
curl -s http://localhost:8010/health
```

## 1. Generate a human-readable review report

This command performs no database writes. It prints a Markdown report containing
the storage model, current counts, seed status, and the actual source values.
Platform skills include their complete instructions and reference files inside
expandable sections.

```bash
docker exec "$SEED_CONTAINER" \
  python -m src.master_data.cli preview --format markdown \
  > /tmp/master-data-review.md
```

Open `/tmp/master-data-review.md` in a Markdown-capable editor. To review one
domain at a time:

```bash
docker exec "$SEED_CONTAINER" \
  python -m src.master_data.cli preview \
  --domain platform_skills \
  --format markdown \
  > /tmp/platform-skills-review.md
```

Supported seedable domains are:

- `platform_skills`
- `platform_tools`
- `system_pricing`
- `notification_events`

Use `--domain` more than once to select multiple domains.

## 2. Generate the exact apply plan

The Markdown report is for people. The JSON plan is for the apply command. Both
are read-only previews, but only JSON is accepted by `apply`.

```bash
docker exec "$SEED_CONTAINER" \
  python -m src.master_data.cli preview --format json \
  > /tmp/master-data-plan.json
```

Optional machine-oriented inspection:

```bash
jq '.catalog[] | {
  domain: .key,
  status,
  seedable,
  expected: .expected_count,
  current: .current_count
}' /tmp/master-data-plan.json
```

Do not use the JSON output as the human review document. Use the Markdown
report for that purpose.

## 3. Apply the reviewed plan

Copy the reviewed JSON plan into the backend container, then apply it:

```bash
docker cp /tmp/master-data-plan.json \
  "$SEED_CONTAINER:/tmp/master-data-plan.json"

docker exec "$SEED_CONTAINER" \
  python -m src.master_data.cli apply \
  --plan /tmp/master-data-plan.json
```

Before writing, the CLI checks that the source-definition hashes and reviewed
payloads in the plan still match the running release. If source code changed or
the JSON catalog was edited after the review, the command stops and asks for a
new preview. This prevents applying data that was not reviewed.

## 4. What normal apply does

Normal apply:

- creates missing platform-owned rows;
- skips unchanged platform skills using content hashes;
- synchronizes platform tool schemas and keeps code-owned native rows published;
- leaves the MCP draft/publish lifecycle unchanged;
- creates missing notification events without replacing existing rows;
- creates missing system-pricing rows and skips unchanged rows while preserving
  existing administrator-set credit rates and activation state;
- writes an audit record to `master_data_seed_runs` for each selected domain;
- does not delete organization skills, agents, subscriptions, balances, logs,
  credentials, or other customer-owned data.

Normal platform-skill apply does not prune old platform rows. It is safe to run
again when a deployment is repeated or when a previous apply partially failed.

## 5. Reset behavior

Reset is a separate recovery operation. It is not part of normal deployment and
is accepted only when `ENVIRONMENT` is explicitly `development`, `dev`, `local`,
`test`, or `staging`. Production values, an unset variable, and unknown values
fail closed.

First generate and review a fresh JSON plan, then use:

```bash
docker exec "$SEED_CONTAINER" \
  python -m src.master_data.cli apply \
  --plan /tmp/master-data-plan.json \
  --reset --yes
```

Reset can restore source defaults for supported providers and prune obsolete
platform-skill rows. It still does not reset customer-owned data or unrelated
database tables. Production corrections must be implemented as reviewed,
forward-only data changes or migrations.

## 6. Where the data lives

The database is not the only place master data exists. The source of truth
depends on the domain:

| Domain | Source definition | Runtime database storage |
| --- | --- | --- |
| Platform skills | `backend/src/voice_agents/skill_seeds.py` | `platform_skills`, `platform_skill_files` |
| Platform tools | `shared/voice_agents/tools/implementations` and the tool registry | `platform_tools` |
| System pricing | `backend/src/billing/system_pricing.py` | `credit_events` |
| Notification events | `backend/src/notifications/templates.py` | `notification_events` |
| Plans and entitlements | Alembic migrations plus review-gated catalog definitions | `plan_products`, `plan_versions`, `entitlement_definitions` |
| Voice templates and presets | Alembic migrations | Corresponding runtime tables |
| Seed audit history | CLI service | `master_data_seed_runs` |

Python modules and migrations are version-controlled source definitions. The
database contains materialized rows used at runtime. Markdown and JSON files in
`/tmp` are temporary review artifacts and are not loaded automatically.

## 7. Troubleshooting

### The report only shows counts

Use the Markdown format explicitly:

```bash
docker exec "$SEED_CONTAINER" \
  python -m src.master_data.cli preview --format markdown \
  > /tmp/master-data-review.md
```

The JSON format is intentionally optimized for the apply command, not for
human navigation.

### Apply says the source definition changed

Regenerate both artifacts from the same running release, review the new Markdown
file, and copy the new JSON plan into the container before applying again.

### Apply says a domain is review-gated or migration-managed

That domain is intentionally not handled by this seeder. Paid plans and credit
products require an approved source catalog, pricing decision, cost model, and
Stripe configuration. Migration-managed data must be changed through a new
version-controlled migration.

### The application starts normally without seeding

That is expected. Application startup has no master-data write path. Run this
runbook as an explicitly approved bootstrap or release task instead.

### Shared staging shortcut

The canonical shared-staging validator runs the narrower native-tool sync after
the migration and before starting the local application:

```bash
./scripts/validate-staging.sh
```

It materializes every native implementation currently present in the checked-
out release under `platform_tools`, including new tools such as
`Resend_email`. `--migrate-only` intentionally skips this Docker-backed seed;
run `scripts/deploy/sync-native-tools.sh --env-file .env.staging` separately
when a migration-only validation also needs to refresh the catalog.

## Production deployment pattern

Run schema migrations through the normal release pipeline. Then run the JSON
apply command as a separately approved one-off task using the exact release
image or artifact that produced the reviewed plan. Do not add seeding to the
application startup hook and do not treat staging rows as the production source
of truth.
