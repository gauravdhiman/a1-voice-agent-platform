# Public Organization and Demo Agent Pages

## Overview

24x7 AI exposes two unauthenticated voice-agent surfaces:

- **Organization showcase**: `/o/{organization-slug}` lists agents that an
  organization explicitly publishes. An organization may optionally require a
  passphrase before visitors can see the list.
- **Demo showcase**: `/demo/{demo-slug}` exposes one active agent marked as a
  platform demo. Demo calls are intended for product showcasing and bypass
  voice credit and concurrency checks.

These are separate controls. Publishing an agent on an organization's page
does not make it a demo, and marking an agent as a demo does not require the
organization showcase to be enabled.

## Configuration and permissions

| Setting | Purpose | Who can change it | Public requirement |
| --- | --- | --- | --- |
| Organization `public_page_enabled` | Enables `/o/{slug}` | Organization admin or platform admin | Organization must be active and enabled |
| Agent `is_published_on_public_page` | Lists the agent on `/o/{slug}` | Organization admin or platform admin | Agent must also be active |
| Agent `is_demo` | Enables the dedicated demo surface and billing bypass | Platform admin only | Agent must have a unique `demo_slug` and be active |
| Agent `demo_slug` | Stable URL identifier for a demo | Platform admin only | Lowercase letters, numbers, and hyphens; unique across demo slugs |
| Agent `public_description` | Visitor-facing demo copy | Platform admin only | Optional; falls back to mission, then persona |

Safety rules are enforced in both the dashboard and API layer:

- Deactivating an agent clears `is_published_on_public_page`.
- Turning off `is_demo` clears `demo_slug`.
- An organization admin cannot set demo status, a demo slug, or demo copy by
  sending a direct API request.
- Public API responses contain only visitor-safe agent metadata.

## Visitor request flow

```mermaid
flowchart TD
    Visitor[Unauthenticated visitor] --> Surface{Which public surface?}
    Surface -->|Organization URL| OrgSummary[GET /api/v1/public/orgs/{slug}]
    OrgSummary --> Enabled{Active and enabled?}
    Enabled -->|No| NotFound[404 page unavailable]
    Enabled -->|Yes| Gate{Passphrase required?}
    Gate -->|Yes| Access[POST /api/v1/public/orgs/{slug}/access]
    Gate -->|No| AgentList[GET /api/v1/public/orgs/{slug}/agents]
    Access --> AgentList
    AgentList --> Published[Active + explicitly published agents]
    Published --> OrgToken[POST /api/v1/public/orgs/{slug}/agents/{id}/token]
    Surface -->|Demo URL| DemoLookup[GET /api/v1/public/demo/{demo_slug}]
    DemoLookup --> DemoState{Active demo agent?}
    DemoState -->|No| DemoNotFound[404 demo not found]
    DemoState -->|Yes| DemoToken[POST /api/v1/public/demo/{demo_slug}/call-token]
    OrgToken --> VoiceWS[Pipecat voice-ws session]
    DemoToken --> VoiceWS
```

## API contract

### Organization showcase

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/public/orgs/{slug}` | None | Returns safe organization metadata and `passphrase_required` |
| `POST` | `/api/v1/public/orgs/{slug}/access` | None | Verifies the passphrase and returns a short-lived access token |
| `GET` | `/api/v1/public/orgs/{slug}/agents` | Optional `X-Public-Access-Token` | Lists active, explicitly published agents |
| `POST` | `/api/v1/public/orgs/{slug}/agents/{agent_id}/token` | Optional `X-Public-Access-Token` | Issues a visitor voice-session token after organization and agent checks |

The frontend routes are `/o/{slug}` and `/o/{slug}/call/{agentId}`. A public
organization call still uses the normal credit and concurrency entitlement
check.

### Demo showcase

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/public/demo/{demo_slug}` | None | Returns safe metadata for an active demo agent |
| `POST` | `/api/v1/public/demo/{demo_slug}/call-token` | None | Issues a visitor voice-session token for the demo |

The frontend route is `/demo/{demo_slug}`. The page supports the two final
visualizer choices used during rollout:

- `?visualizer=radial` (default)
- `?visualizer=lk-bars`

Missing or obsolete visualizer values resolve to `radial`.

## Billing and call lifecycle

Demo behavior is applied at both sides of the call boundary:

1. The public demo token route passes `agent_is_demo=True` to the shared voice
   entitlement check, bypassing credit-headroom and concurrency admission.
2. `voice-ws` checks `voice_agents.is_demo` at call teardown and records
   `credits_consumed = 0` without creating a credit ledger debit.
3. Non-demo public organization calls continue through normal entitlement and
   final settlement rules.

The demo bypass is intentionally derived from the database agent flag rather
than from a caller-controlled query parameter.

## Database fields and migration history

The `voice_agents` table stores:

- `is_published_on_public_page` — organization showcase publish flag.
- `is_demo` — platform-admin-controlled demo flag, default `false`.
- `demo_slug` — nullable unique slug for demo lookup.
- `public_description` — nullable visitor-facing demo copy.

The schema details and migration history are maintained in
[`docs/DATABASE_SCHEMA.md`](../../DATABASE_SCHEMA.md):

- `20260731000001_add_public_org_page.py`
- `20260820000001_add_demo_flag_to_voice_agents.py`
- `20260820000002_add_public_description_to_voice_agents.py`

## Testing coverage

The feature is covered at each boundary:

- **Model tests** validate defaults, slug normalization/validation, and public
  description trimming.
- **Service tests** validate demo transitions, slug clearing, demo lookup, and
  active/published organization queries.
- **Route tests** validate public listing/token behavior, passphrase handling,
  demo token bypass, and platform-admin-only demo writes.
- **Frontend service tests** validate public metadata/token requests and safe
  error translation.
- **Playwright E2E tests** cover open and passphrase-protected organization
  pages, public demo rendering, visualizer selection/defaulting, and the
  dashboard workflow that publishes and marks an agent as a demo.

Run the focused backend and frontend suites with:

```bash
cd backend
pytest -q \
  tests/organization/test_public_routes.py \
  tests/voice_agents/test_demo_agent_routes.py \
  tests/shared/voice_agents/test_agent_service.py \
  tests/shared/voice_agents/test_models.py

cd ../frontend
npm run test:run -- \
  src/services/__tests__/demo-public-service.test.ts \
  src/services/__tests__/public-org-page-service.test.ts \
  src/components/agents-ui/__tests__/demo-visualizer-config.test.ts
```

Run the isolated browser suite from the repository root with
`./scripts/run-e2e.sh`. The suite applies all migrations to a disposable E2E
database and tears that stack down after the run.

## Related documentation

- [Voice Agents Overview](./overview.md)
- [Embed Call Button](./embed_button.md)
- [Testing Guidelines](../../04_development_guides/testing.md)
- [Database Schema](../../DATABASE_SCHEMA.md)
