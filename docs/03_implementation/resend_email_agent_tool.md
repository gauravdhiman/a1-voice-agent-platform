# Resend Agent Email Tool

## Purpose

`Resend_email` is a native platform tool for an agent to send a plain-text
follow-up email to business staff after a caller requests help, a callback, or
another action that cannot be completed during the call. It is intentionally a
small outbound capability, not a Gmail replacement and not a durable case or
notification workflow.

The tool is available to any agent when a platform administrator publishes the
code-owned tool and an organization administrator attaches and configures it.
The organization chooses logical routes such as `customer_support`, `sales`,
or `front_desk`; the model chooses a route, while the platform keeps the raw
recipient addresses out of the model-facing tool result.

## Boundary and ownership

| Concern | Owner | Behavior |
| --- | --- | --- |
| Tool contract and validation | `shared/voice_agents/tools/implementations/resend_email.py` | Defines route selection, argument validation, response codes, and retry guidance. |
| Provider adapter | `shared/notifications/email_providers.py` | Wraps the synchronous Resend SDK behind an async, provider-neutral contract. |
| Voice runtime | `voice-ws/src/tools/assembly.py` | Discovers the native tool, injects trusted `ToolContext`, and serializes results for the model. |
| Route configuration | `agent_tools.config` | Stores organization-admin-managed logical route IDs, labels, and recipients as public tool configuration. |
| Organization credential | Encrypted `organizations.provider_credentials` | Stores the organization's Resend API key under the `resend` key. It is decrypted only in the voice runtime and is never returned to the frontend or model. |
| Sender identity | `agent_tools.config` | Stores the attachment's verified `from_email` and optional `from_name`, allowing different agents in one organization to use different approved sender identities. |
| Platform notifications | Platform environment | The event-driven notification service continues to use `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and `RESEND_FROM_NAME` for platform-owned messages such as verification and billing emails. |
| UI | `frontend/src/components/tools/resend-email-config.tsx` | Provides the route editor and client-side validation; the backend remains authoritative. |

The tool does not create a new database table, persist a callback request, or
send through the existing event-driven notification processor. The provider
adapter is shared with that processor so both paths use one Resend boundary.

## Configuration

An organization administrator configures the attachment in the agent's Tools
drawer. The persisted shape is:

```json
{
  "from_email": "noreply@example.com",
  "from_name": "Example Business",
  "routes": [
    {
      "route_id": "customer_support",
      "label": "Customer Support",
      "recipients": ["support@example.com", "manager@example.com"]
    }
  ]
}
```

Rules enforced by the backend and mirrored by the UI:

- 0–50 routes per agent attachment; an empty list leaves the attached tool
  available but reports that an administrator must configure a route;
- route IDs are unique, lowercase, and use letters, numbers, hyphens, or
  underscores (maximum 64 characters);
- labels are required and limited to 100 characters;
- every route has 1–10 unique, syntactically valid recipient addresses;
- `from_email` is required, limited to 254 characters, and must belong to a
  domain verified in the organization's Resend account; and
- the model never supplies a raw recipient address.

The organization administrator enters the Resend API key under Organization →
Credentials. The backend encrypts it in the existing organization credential
blob. The native tool does not accept an API key in its public configuration,
function arguments, prompt, or `ToolContext`. The voice runtime resolves the
organization key at assembly time and supplies it only to the in-process tool
instance. Legacy per-agent API-key values are ignored at runtime and removed
when the attachment configuration is next saved.

The agent Tools tab shows the attachment as `Configuration required` with a red
card until the organization credential is present, the sender identity is
valid, and at least one route has at least one valid recipient. It shows
`Connected` only after all three prerequisites are confirmed by the UI read
model. The backend remains authoritative when the attachment is saved and the
runtime remains authoritative when delivery is attempted.

Sender identity is attachment configuration rather than a platform default.
Resend authorizes sending against the API key's account and verified domains, so
hard-coding a `247ai.live` sender would not be reliable for an organization's
own Resend account. The configured address must be verified by that account;
the optional display name is validated as a single line.

## Model-facing contract

Native function names are converted to the readable names shown in the tool
catalog. Their docstrings are the model-facing guidance; the generic platform
prompt does not mention Resend or any other specific tool.

| Function | Arguments | Result |
| --- | --- | --- |
| `list_resend_email_routes` | No model arguments; runtime injects `ToolContext`. | `status=ok`, with route IDs and labels only. |
| `send_resend_email` | `route_id: string`, `subject: string`, `body: string`. | `status=accepted` only after Resend accepts every configured recipient. |

The model should list routes when it does not already know a valid route ID,
collect the details required by the agent's instructions, then send to the
selected route. The result means provider acceptance, not delivery, inbox
placement, or reading. The model must not claim any of those stronger outcomes.

## Error and retry contract

Every recoverable error has a stable `code`, concise `message`, `next_action`,
and `retryable` flag. Argument errors identify the bad field and expected
format. Examples include:

| Code/status | Meaning | Model action |
| --- | --- | --- |
| `route_not_configured` / `error` | Route is unknown or a raw email was supplied. | List routes or tell the caller an administrator must configure one. |
| `invalid_argument` / `error` | Subject or body is empty, malformed, or too long. | Correct the named argument and retry. |
| `organization_provider_not_configured` / `unavailable` | The organization has no Resend API key. | Do not retry repeatedly; tell the caller the follow-up cannot be sent and ask an organization administrator to configure Resend. |
| `sender_not_configured` / `unavailable` | This agent has no verified sender identity. | Do not retry repeatedly; ask an organization administrator to configure the sender in the tool attachment. |
| `provider_authentication_failed` / `error` | Resend rejected the organization's key or sender/domain. | Do not retry unchanged; ask an organization administrator to verify the key and sender domain. |
| `provider_timeout` / `error` | Resend outcome is unknown after the bounded timeout. | Retry later with the same operation; the session-scoped idempotency key prevents duplicate provider requests when supported. |
| `provider_temporary_failure` / `error` | Resend returned a rate-limit or server failure. | Retry later with the same request. |
| `partial_delivery` / `partial` | Some route recipients were accepted and another recipient failed or timed out. | Do not claim full delivery; follow `error.next_action` and avoid changing the request content on retry. |

The tool sends one provider request per configured recipient so that each
request has a stable idempotency key. These requests are bounded concurrent
fan-out, so one slow recipient does not delay independent recipients. A retry
of the same route, subject, and body within one voice session reuses those
keys. The provider adapter runs the synchronous Resend SDK in a worker thread
and the tool applies an eight-second per-recipient timeout.

## Operational lifecycle

1. Add or change the native implementation and its tests in the same change.
2. Run the explicit master-data preview and apply for `platform_tools` in the
   target environment. This upserts the code-owned catalog row; it does not
   publish it automatically.
3. A platform administrator publishes the new `Resend_email` row. New org
   users then see it in the tool catalog.
4. An organization administrator configures the organization's `Resend` API
   key under Organization → Credentials. It is stored encrypted.
5. The organization administrator attaches the tool to an agent and saves a
   verified sender identity plus one or more routes in the Tools drawer, or
   leaves the route list empty until a destination is approved.
6. Add agent-specific instructions describing when to capture a follow-up and
   which route label to use. The tool remains usable by agents with different
   workflows because route configuration is per attachment.

Platform-owned notification workflows still require the platform environment
variables documented in the notification runbook; those credentials are not a
fallback for the native organization follow-up tool.

From the backend runtime, the review-gated catalog operation is:

```bash
python -m src.master_data.cli preview \
  --domain platform_tools \
  --format json \
  --output /tmp/platform-tools-plan.json
python -m src.master_data.cli apply --plan /tmp/platform-tools-plan.json
```

Review the generated plan before applying it. The normal local worktree
launcher performs the same operation for its isolated database; shared staging
and production require the documented release approval path.

No migration is required: routes use the existing `agent_tools.config` JSONB
field. Do not copy route configuration or provider credentials between
organizations or environments.

## Scope and follow-ups

Current scope deliberately excludes:

- arbitrary caller-supplied recipients;
- HTML/template authoring;
- durable callback cases, delivery webhooks, bounce tracking, or a retry queue;
- email composition/search in a user's mailbox; and
- Telegram or WhatsApp delivery.

If a customer needs guaranteed follow-up tracking or delivery status, add a
durable domain workflow rather than silently expanding this tool. If an
organization needs multiple Resend accounts, add an explicit connection
contract and authorization model rather than placing credentials in the agent
prompt or route configuration.

## Validation

Focused contract and provider tests:

```bash
pytest -q backend/tests/shared/voice_agents/tools/test_resend_email.py \
  backend/tests/notifications/test_email_providers.py \
  backend/tests/voice_agents/test_native_tool_config_validation.py
```

Deterministic provider-independent evaluation:

```bash
python scripts/run-agent-evals.py --suite resend
python scripts/run-agent-evals.py  # all registered deterministic suites
```

The suite uses a fake provider and never sends a real email. Live Resend
delivery, DNS/domain verification, mailbox placement, and provider latency
belong in staging or a separately approved integration lane.
