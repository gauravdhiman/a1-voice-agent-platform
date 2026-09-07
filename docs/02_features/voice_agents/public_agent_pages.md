# Public Organization and Demo Agent Pages

## Overview

24x7 AI exposes two unauthenticated voice-agent surfaces:

- **Organization showcase**: `/o/{organization-slug}` lists agents that an
  organization explicitly publishes. An organization may optionally require a
  passphrase before visitors can see the list.
- **Demo showcase**: `/demo/{demo-slug}` exposes one active agent marked as a
  platform demo. Demo calls are intended for product showcasing and bypass
  voice credit and concurrency checks, while optional call-count and
  per-call-duration limits protect the public surface.

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
| Agent `demo_public_result_url` | External destination shown by the receipt CTA | Platform admin only | Optional HTTPS URL; shown only after a successful provider handoff |
| Agent `demo_calls_remaining` | Number of trial call reservations left | Platform admin only | `0` disables new calls; positive values decrement at token issuance; `-1` is unlimited |
| Agent `demo_max_call_duration_seconds` | Maximum duration of each demo call | Platform admin only | Positive seconds cap the call; `-1` is unlimited; `0` is invalid |

Safety rules are enforced in both the dashboard and API layer:

- Deactivating an agent clears `is_published_on_public_page`.
- Turning off `is_demo` clears `demo_slug`.
- An organization admin cannot set demo status, a demo slug, or demo copy by
  sending a direct API request.
- An organization admin cannot set the demo receipt destination URL by sending
  a direct API request. The URL is platform-admin-only metadata and must be a
  credential-free HTTPS link.
- An organization admin cannot change either demo budget. Platform admins can
  set a new positive count at any time to re-enable an exhausted demo, or use
  `-1` to remove the count limit. The duration setting also uses `-1` for no
  per-call cap.
- Public API responses contain only visitor-safe agent metadata.

## Visitor request flow

```mermaid
flowchart TD
    Visitor[Unauthenticated visitor] --> Surface{Which public surface?}
    Surface -->|Organization URL| OrgSummary["GET /api/v1/public/orgs/{slug}"]
    OrgSummary --> Enabled{Active and enabled?}
    Enabled -->|No| NotFound[404 page unavailable]
    Enabled -->|Yes| Gate{Passphrase required?}
    Gate -->|Yes| Access["POST /api/v1/public/orgs/{slug}/access"]
    Gate -->|No| AgentList["GET /api/v1/public/orgs/{slug}/agents"]
    Access --> AgentList
    AgentList --> Published[Active + explicitly published agents]
    Published --> OrgToken["POST /api/v1/public/orgs/{slug}/agents/{id}/token"]
    Surface -->|Demo URL| DemoLookup["GET /api/v1/public/demo/{demo_slug}"]
    DemoLookup --> DemoState{Active demo agent?}
    DemoState -->|No| DemoNotFound[404 demo not found]
    DemoState -->|Yes| DemoToken["POST /api/v1/public/demo/{demo_slug}/call-token"]
    OrgToken --> Reservation{Reserve demo slot when applicable}
    DemoToken --> Reservation
    Reservation -->|Available| VoiceWS[Pipecat voice-ws session]
    Reservation -->|Exhausted| TrialEnded[429 DEMO_TRIAL_EXHAUSTED]
    VoiceWS --> ToolAction[Allowlisted provider action]
    ToolAction --> Receipt[Signed demo outcome receipt]
    Receipt --> OutcomePage[GET /demo/{slug}/outcome?token=...]
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
check unless the selected agent is a demo agent, in which case the demo
reservation policy applies.

### Demo showcase

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v1/public/demo/{demo_slug}` | None | Returns safe metadata for an active demo agent |
| `POST` | `/api/v1/public/demo/{demo_slug}/call-token` | None | Issues a visitor voice-session token for the demo |
| `GET` | `/api/v1/public/demo/{demo_slug}/outcome?token=...` | Signed receipt token | Returns the visitor's allowlisted provider outcome |

The outcome endpoint is intentionally a receipt, not a public CRM or calendar
view. The call-token response contains a short-lived, session-bound receipt
token. The frontend uses it to open `/demo/{demo_slug}/outcome`; the endpoint
returns only the actions performed by that call and sets `Cache-Control:
private, no-store`. Receipt tokens expire after 24 hours and stored receipt
rows are retained for seven days. Provider credentials, raw transcripts,
internal session identifiers, and other visitors' records are never exposed.
When `demo_public_result_url` is configured, the response includes that URL on
successful actions only. The receipt page uses it for an `Open … result`
button; failed or incomplete handoffs never receive the URL and therefore
never show that CTA. If the field is blank, no external result CTA is shown,
even when a provider returns an internal record URL.

The outcome allowlist currently contains the two seeded showcase workflows:

- `pleasant-pediatric-appointments` uses the native Google Calendar
  appointment tool. A successful new booking returns the calendar event
  summary. The public fixture exposes availability lookup and new booking only;
  existing-event search, update, and cancellation functions are disabled.
- `copper-ridge-service-request` uses the focused native Google Sheets
  lead-capture tool. It appends one complete, confirmed service row with a
  session id, timestamp, caller details, service context, urgency, and callback
  preference. A same-session retry is deduplicated before append.

The seeded prompts carry the business context that is intentionally absent from
the shared demo organization. Alex identifies as an AI assistant for the
fictional Pleasant Pediatric practice at 1234 Sunbeam Way, Peoria, AZ 85383,
open Monday-Friday 8:00 AM-5:00 PM and Saturday 9:00 AM-1:00 PM. Jordan
identifies as an AI assistant for the fictional Copper Ridge Heating & Air at
4550 N Copper Ridge Way, Phoenix, AZ 85032, open Monday-Friday 7:00 AM-6:00 PM
and Saturday 8:00 AM-2:00 PM. Alex can describe the fictional demo services
and prices: a new-patient exam with standard X-rays ($95), routine pediatric
cleaning ($85), fluoride treatment ($25), and dental sealants ($45 per tooth).
Jordan can describe the fictional demo services and prices: an HVAC diagnostic
or inspection visit ($89), an air-conditioning tune-up ($129), a heating-system
tune-up ($129), and an indoor-air-quality assessment ($79). Both prompts
identify the agent as a helpful AI assistant, spell names and email addresses
back for confirmation, redirect unrelated requests, require explicit
confirmation before provider mutations, and prohibit unsupported claims. Prices
are clearly presented as illustrative demo rates, not binding quotes. The HVAC
prompt also handles out-of-hours requests and immediate gas, carbon-monoxide,
fire, or smoke hazards. The dental prompt is limited to new bookings and does
not expose or modify existing appointment records. The prompt content is grouped
into short sections and bullets for disclosure, business facts, services and
prices, workflow, email follow-up, and safety rules. The public-data notice is
intentionally a one-time opening reminder; after the caller acknowledges it or
starts sharing details, the agent moves on unless the caller asks or appears
confused.

The allowlist also records an independently attached `send_email`,
`send_email_reply`, or `send_resend_email` call as a separate `email_delivery`
action. The receipt includes only the provider, safe delivery status, and a
provider message identifier; it never includes the recipient, subject, or body.
The primary Calendar, Sheets, and HubSpot tools do not send email or know that
an email tool exists. For the seeded demos, when the caller provides and confirms
an email address and an independent email-sending tool is attached, the agent's
instructions tell it to invoke that tool automatically after the primary
provider confirms success, unless the caller declines. The agent reports the
tool's actual result: it says the confirmation was sent or accepted only after
success, and otherwise says that the primary action succeeded but the email was
not sent. The email tool's own contract decides how recipients or configured
routes are handled. Gmail sends to caller-confirmed recipients; Resend sends
only to its administrator-configured business routes.

The agents call those provider tools directly, just like customer agents do.
The receipt is a presentation boundary added after an allowlisted tool result;
it is not an intermediate write queue or a replacement for the provider
integration. If credentials are missing or a provider rejects the request, the
demo shows an honest needs-attention result rather than claiming success.

Before a visitor can start a demo call, the page displays a public-data notice
and requires an acknowledgement. The notice explains that the configured demo
data store is public, recommends dummy names, email addresses, phone numbers,
and addresses, and tells visitors that providing an email will cause the agent
to attempt a confirmation through any independently attached email tool. It also
links to Google's Gmail alias
guidance. This is an explicit demo-use disclosure; it is not a privacy or
row-level access control mechanism. The seeded demo spreadsheet must remain a
dedicated platform-admin-owned demo store and must not contain internal or
customer data.

### Google Sheets lead-demo setup

The seeded lead demo already has `Google_Sheets_lead_capture` attached. An
administrator must connect the organization's Google account to that agent and
set its spreadsheet id (an id or full Sheets URL) in the agent-tool settings.
The target spreadsheet should contain a tab named `Lead submissions` with this
header row in columns A:L:

```text
Submission ID | Captured at | Lead source | Caller name | Caller email | Caller phone | Service needed | Issue summary | Service address | Urgency | Preferred callback window | Status
```

Use `Lead submissions!A:L` as the append range and
`Lead submissions!A:A` as the deduplication range. The demo action performs a
read-only submission-id check first, appends the row once, and reports a
retryable provider error without automatically repeating a mutation. The
general-purpose `Google_Sheets` tool remains a separate platform capability;
it is deliberately not attached to this public agent.

To show the sheet after a successful capture, set the demo agent's **Public
result URL (optional)** field to the public share URL for this dedicated demo
spreadsheet. This URL is a presentation CTA, not an access-control boundary:
every visitor who can open the sheet can see its rows. Use a platform-admin-
owned demo sheet containing synthetic data only, and leave the field blank if
the external destination should not be shown.

The agent Tools drawer shows an information tooltip beside each configuration
field. The tooltip stays available after a value is entered and mirrors the
tool schema's setup guidance, including accepted URL/range formats and required
permissions.

Demo metadata includes `demo_calls_remaining` and
`demo_max_call_duration_seconds`. Successful token responses include the
post-reservation remaining count and the duration captured for that call.
When the count is exhausted, token endpoints return HTTP `429` with the safe
error code `DEMO_TRIAL_EXHAUSTED`; public clients should show that the demo has
used its available trial calls and direct visitors to contact the platform
administrator for further details or to have the demo re-enabled, rather than
exposing internal billing details or suggesting a retry window.

When calls remain, the public surfaces label the two independent settings
explicitly on separate lines. Once a demo is exhausted, those details are
hidden because the exhausted message already explains the state and next step:

- `Calls: 3 trial calls remaining`
- `Duration: Maximum 15 minutes per call`

These rows are omitted when the demo has no calls remaining because the
exhausted message already explains the state and directs visitors to the
platform administrator.

The duration is the maximum length of each individual call; it does not add to
or subtract from the number of calls remaining. When either setting is `-1`,
the corresponding public summary identifies it as unlimited.

The frontend route is `/demo/{demo_slug}`. The page supports the two final
visualizer choices used during rollout:

- `?visualizer=radial` (default)
- `?visualizer=lk-bars`

Missing or obsolete visualizer values resolve to `radial`.

## Billing and call lifecycle

Demo behavior is applied at both sides of the call boundary:

1. Every demo token path atomically decrements `demo_calls_remaining` when a
   call reservation is issued. The count is decremented for a call attempt,
   so concurrent public requests cannot oversubscribe the configured budget.
2. The reservation id and `demo_max_call_duration_seconds` are signed into the
   short-lived voice-session JWT. `voice-ws` consumes the reservation exactly
   once before admitting the WebSocket, preventing token replay.
3. A positive duration cap starts when the WebSocket client connects and
   cancels the Pipecat pipeline at the limit. `-1` leaves the duration
   unlimited. Changing settings affects new reservations; active calls keep
   their captured duration.
4. The shared entitlement check bypasses credit-headroom and concurrency
   admission for demo agents, and `voice-ws` checks `voice_agents.is_demo` at
   call teardown and records
   `credits_consumed = 0` without creating a credit ledger debit.
5. Non-demo public organization calls continue through normal entitlement and
   final settlement rules.

The demo bypass is intentionally derived from the database agent flag rather
than from a caller-controlled query parameter.

## Database fields and migration history

The `voice_agents` table stores:

- `is_published_on_public_page` — organization showcase publish flag.
- `is_demo` — platform-admin-controlled demo flag, default `false`.
- `demo_slug` — nullable unique slug for demo lookup.
- `public_description` — nullable visitor-facing demo copy.
- `demo_calls_remaining` — remaining reservations or `-1` for unlimited calls;
  `0` makes new token requests unavailable.
- `demo_max_call_duration_seconds` — positive per-call duration cap or `-1`
  for unlimited duration.

The internal `demo_call_reservations` table records the session id and one-time
`reserved` → `consumed` transition used by `voice-ws`. It is protected by RLS;
only the service role can execute the reservation RPCs.

The schema details and migration history are maintained in
[`docs/DATABASE_SCHEMA.md`](../../DATABASE_SCHEMA.md):

- `20260731000001_add_public_org_page.py`
- `20260820000001_add_demo_flag_to_voice_agents.py`
- `20260820000002_add_public_description_to_voice_agents.py`
- `20260827000001_add_demo_call_limits.py` (merge migration for the existing
  `20260820000002` and `20260821000001` heads)
- `20260830000001_add_demo_outcome_receipts.py` (short-lived, service-role-only
  visitor outcome receipts)
- `20260901000001_add_demo_public_result_url.py` (platform-admin-configured
  external-result CTA destination)
- `20260901000002_add_demo_email_outcome_action.py` (independent email actions
  in visitor outcome receipts)

The isolated worktree stack and the explicit release bootstrap materialize both
showcase agents and their native tool configurations. The seeded demos use
unlimited calls and a 15-minute cap. A deployed environment must configure
Google OAuth credentials for the
appointment and lead demos, connect the relevant Google account to each agent,
and set the lead agent's spreadsheet id plus its `Lead submissions` sheet
ranges. The lead demo uses the focused Sheets action rather than the
general-purpose `Google_Sheets` toolbox, so the model cannot browse or mutate
unrelated spreadsheets. Email is optional and must be attached/configured as
its own Gmail or Resend tool. When a caller provides and confirms an email, the
seeded instructions automatically attempt the email action after the primary
provider succeeds and report whether that action succeeded. HubSpot remains
available as a separately configurable platform integration for customer
agents; it is not a dependency of this public demo.

## Testing coverage

The feature is covered at each boundary:

- **Model tests** validate defaults, slug normalization/validation, and public
  description trimming.
- **Service tests** validate demo transitions, slug clearing, demo lookup, and
  active/published organization queries.
- **Route tests** validate public listing/token behavior, passphrase handling,
  demo token bypass, reservation/error handling, outcome receipt access, and
  platform-admin-only demo writes and budget overrides.
- **Runtime tests** validate reservation claim signing, one-time WebSocket
  admission, and duration-timer cancellation.
- **Frontend service tests** validate public metadata/token requests, signed
  outcome retrieval, and safe error translation. Component tests validate the
  disabled exhausted-demo state, finite/unlimited limit copy, and successful
  or failed outcome rendering.
- **Tool contract and deterministic evaluation tests** cover the focused
  Google Sheets row contract, confirmation and dedupe behavior, provider
  failures, independent Gmail/Resend receipt actions, the separately
  supported HubSpot contact/note integration, and the appointment/lead
  workflows without writing to real providers.
- **Playwright E2E tests** cover open and passphrase-protected organization
  pages, public demo rendering, exhausted-demo messaging, visualizer
  selection/defaulting, visitor outcome receipts, and the dashboard workflow
  that publishes and marks an agent as a demo with a finite call budget.

Run the focused backend and frontend suites with:

```bash
cd backend
pytest -q \
  tests/organization/test_public_routes.py \
  tests/voice_agents/test_demo_agent_routes.py \
  tests/voice_agents/test_embed_routes.py \
  tests/voice_agents/test_test_token_transport.py \
  tests/voice_agents/test_voice_routes.py \
  tests/shared/voice_agents/test_agent_service.py \
  tests/shared/voice_agents/test_models.py \
  tests/shared/voice_agents/test_voice_session_service.py

cd ../shared
pytest -q tests/test_demo_call_reservations.py tests/test_voice_session_entitlement.py

cd ../frontend
npm run test:run -- \
  src/services/__tests__/demo-public-service.test.ts \
  src/app/demo/[slug]/outcome/page.test.tsx \
  src/services/__tests__/public-org-page-service.test.ts \
  src/components/public-org/__tests__/public-agent-card.test.tsx \
  src/components/agents-ui/__tests__/demo-visualizer-config.test.ts \
  src/lib/__tests__/demo-call-limits.test.ts \
  src/lib/__tests__/voice-call-messages.test.ts
```

Run the isolated browser suite from the repository root with
`./scripts/run-e2e.sh`. The suite applies all migrations to a disposable E2E
database and tears that stack down after the run.

Run the provider-independent agent evaluations from the repository root with:

```bash
python scripts/run-agent-evals.py --suite calendar
python scripts/run-agent-evals.py --suite lead_capture
```

## Related documentation

- [Voice Agents Overview](./overview.md)
- [Embed Call Button](./embed_button.md)
- [Testing Guidelines](../../04_development_guides/testing.md)
- [Database Schema](../../DATABASE_SCHEMA.md)
