# Phone-number lifecycle and Twilio integration

This document describes the implemented v1 phone-number contract. The
customer-facing experience is intentionally provider-neutral for platform
purchase and assignment.

## Source of truth

`phone_numbers` owns the phone-to-agent relationship. A row is routable only
when all of the following are true:

- `status` is `purchased` or `active`;
- `assigned_agent_id` points to an active agent;
- `is_incoming_enabled` is true;
- `billing_status` is `active`; and
- `configuration_status` is `configured`.

`is_incoming_enabled` is a property of the number mapping. Agent activation is
checked separately during routing, so an inactive agent can retain its mapping
and become callable immediately when reactivated.

The legacy `voice_agents.phone_number` column is not used for inbound routing.
This allows one agent to be changed without leaving stale routing values on the
agent record and makes customer-owned numbers behave exactly like purchased
numbers after verification.

For compatibility, agent list/detail API responses still expose a
`phone_number` field. The backend populates that response field from the
assigned `phone_numbers` row, so cards, search, and older clients see the same
current assignment without treating the legacy database column as authoritative.
If the assignment lookup is temporarily unavailable during a rolling deploy,
the service can fall back to the legacy value for read availability; inbound
routing never uses that fallback.

## Two ownership modes

| Mode | How it enters the platform | Platform billing | Twilio API authority | Release action |
| --- | --- | --- | --- | --- |
| `platform_managed` | Search and purchase | Monthly credits | Purchase, configure, release | Release the provider number |
| `customer_managed` | Connect existing number | None | No purchase or release | Disconnect local routing only |

### Platform purchase

The backend first checks the organization entitlement and consumes the current
monthly rental price. It then inserts a `provisioning` row and calls Twilio's
incoming-phone-number create API with both canonical callbacks:

```text
https://api.247ai.live/api/v1/voice/twilio/incoming
https://api.247ai.live/api/v1/voice/twilio/status
```

If Twilio fails, the local row is cancelled and the credit debit is refunded.
If Twilio created a number but the local finalization fails, the service attempts
to release the provider SID. A failed compensation is persisted as
`release_pending` for the scheduler.

The `Idempotency-Key` request header is accepted for retries. The key is stored
on the provisioning row and also in the credit ledger metadata so a client
retry does not debit twice or purchase a second number.

### Customer-owned import

The Connect Existing Number dialog accepts an existing E.164 number and an
optional agent. The backend creates a `verification_required` row and returns
tokenized URLs once containing an opaque `connection_token`. Only its SHA-256
hash is stored; the raw token cannot be recovered later. The user configures
both URLs in the Twilio console once. The first signed webhook verifies the
number and enables routing, after which the same token protects future
callbacks. The platform never asks for or stores the customer's Twilio auth
token in v1.

The later “Connect Twilio account” capability can remove this manual callback
configuration, but it is intentionally out of scope for v1.

## Agent configuration experience

Agent settings expose a single phone-number dropdown backed by
`phone_numbers`. Existing organization numbers can be selected or cleared
without releasing them. Selecting **Connect a custom number** opens a right
drawer where the user enters an already-owned number; after the record is
created, the drawer displays the tokenized voice and status callback URLs plus
step-by-step provider instructions. The create-agent wizard defers this step
until an agent ID exists, so it never creates a new legacy-only mapping.

## Search

The UI exposes US only. The backend is country-aware and passes the selected
country to Twilio. Search is a generic `contains` search: punctuation and a
leading `+` are removed before the provider request. There is no separate
starts-with or ends-with API because both are represented by a contains pattern
at the selected position.

## Billing and release scheduler

Platform-owned numbers are charged using the enabled monthly system pricing
event for their type. The default grace period is seven days. Platform
administrators can configure the grace period and both scheduler intervals
from **Platform → Phone Number Settings**. Environment variables remain safe
deployment defaults and fallbacks. On a failed renewal:

1. `billing_status` becomes `past_due`.
2. Incoming calls are disabled immediately.
3. The number remains provider-owned during grace.
4. After grace, release is attempted.
5. Provider failures remain `release_pending` and are retried automatically.

The scheduler cadence is the lower of:

- `PHONE_NUMBER_BILLING_CHECK_INTERVAL_HOURS`; and
- `PHONE_NUMBER_RELEASE_RETRY_INTERVAL_HOURS`.

This gives one daily loop by default. The scheduler reads the persisted values
at each iteration, so a settings change takes effect without a process restart.
The broader platform-admin area for managing every cron job remains a future
separate request. The current per-instance scheduler risks and the shared
Postgres lease design are documented in
[Maintenance jobs and horizontal scaling](maintenance_jobs.md); that work is
scheduled immediately after this Twilio integration.

<!-- TODO: Extend the platform-admin settings area to cover all cron jobs,
including pause/resume, last-run status, and per-job health diagnostics. -->

## Webhook security

Inbound and status endpoints validate `X-Twilio-Signature` using the configured
Twilio auth token. Customer-owned URLs additionally validate the connection
token against the stored hash. Missing or invalid signatures/tokens receive
HTTP 403. Duration parsing is defensive, and a malformed duration cannot turn a
status callback into a server error.

## Verification and test plan

The repository includes:

- unit tests for normalization, lifecycle transitions, provider request fields,
  billing refunds, entitlement counting, and signature rejection;
- service/route integration tests with mocked Supabase and Twilio boundaries;
- frontend component/service tests for query-string organization scoping and
  management actions;
- Playwright browser smoke coverage for the phone-number dashboard; and
- a live Twilio test gate that must be run later with a real test number. Live
  testing is intentionally not part of the no-cost validation stage.
