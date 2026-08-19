# MCP tool integration (`shared.voice_agents.tools.mcp`)

The tool-integration path for **remote MCP servers** over Streamable HTTP, used by
`voice-ws` at runtime (via `voice-ws/src/tools/mcp_pipecat.py`) instead of
hand-rolling one `BaseTool` subclass per vendor. This package lives **alongside**
the legacy `BaseTool` mechanism (`shared/voice_agents/tools/base/`) — both paths
coexist. See
[`docs/03_implementation/mcp_integration_rfc.md`](../../../docs/03_implementation/mcp_integration_rfc.md)
§1.1 for the coexistence hard constraint.

## Modules

| Module | Purpose |
|---|---|
| `models.py` | `McpServerConfig`, `McpToolDef`, `McpToolResult` — data models decoupled from the `mcp` SDK. |
| `client.py` | `McpClient` — async client (`list_tools`, `call_tool`, `close`) over Streamable HTTP. |
| `dispatch.py` | Shared helpers: `mcp_server_config_from_agent_tool`, tool discovery and schema sanitization for LLM runtimes. |
| `schema_sanitize.py` | JSON Schema normalization for strict realtime models. |
| `reference_servers/google_calendar.py` | Deterministic in-memory plumbing fixture; not a production appointment connector. |
| `reference_servers/google_calendar_rest.py` | Platform-owned Google Calendar Appointment MCP connector backed by the GA REST API. |

Pipecat wiring lives in `voice-ws/src/tools/mcp_pipecat.py` (not in this package).

## How voice-ws routes a tool

For each session, `voice-ws` loads the agent's `agent_tools` and, per row:

- if `platform_tools.tool_source == 'mcp'` → **MCP path**: build an
  `McpServerConfig` from the row's `mcp_server_*` fields (injecting the per-user
  OAuth bearer from decrypted `agent_tools.sensitive_config`), open an
  `McpClient`, discover the server's tools, and register Pipecat-compatible
  function handlers. The client stays open for the session and is closed on teardown.
- otherwise → **legacy path**: resolve the `BaseTool` subclass via
  `platform_tool_registry` (unchanged).

A broken MCP server fails soft — it is skipped and logged, so the agent's other
tools (legacy or MCP) still load.

## Running the Google Calendar reference server

The reference server is a real, deployable MCP server (in-memory calendar):

```bash
# In the voice-ws container (or any image with `mcp` + `uvicorn` installed):
docker exec -e MCP_PORT=8000 -w /app a1-voice-agent-platform-voice-ws-dev-1 \
  python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar
# Serves Streamable HTTP at http://0.0.0.0:8000/mcp
```

Then point a `platform_tools` row at it (the Phase 2 migration is RUN; see
"Configuration" below for the seeded `Google_calendar_appointment_mcp` row):

```sql
INSERT INTO platform_tools
  (name, description, tool_source, mcp_server_url, mcp_server_name, is_active)
VALUES
  ('Google_calendar_appointment_mcp', 'Google Calendar Appointment via MCP', 'mcp',
   'http://<calendar-mcp-host>:8000/mcp', 'google-calendar', true);
```

Attach it to an agent via `agent_tools` (with the user's OAuth `access_token`
stored encrypted in `sensitive_config`, same as the legacy path). `voice-ws`
routes it through MCP automatically; agents still using the legacy
`Google_calendar` row are unaffected.

## Configuration — Google Calendar Appointment (the real thing)

There are **two** Google Calendar integration paths. The
`Google_calendar_appointment` row is the native adapter and the
`Google_calendar_appointment_mcp` row is the platform-owned MCP adapter. Both
call the same shared appointment service and expose the same six operations;
the catalog name selects the runtime path.

### Path A — REST connector (active; works with a personal Gmail today)

`shared/voice_agents/tools/mcp/reference_servers/google_calendar_rest.py` — a
platform-owned FastMCP server that wraps Google's plain **Calendar REST API**
(`www.googleapis.com/calendar/v3`). The REST API is GA and **not** gated by the
Workspace Developer Preview, so it works with a **personal Gmail** token. On
each tool call the connector reads the incoming `Authorization: Bearer <token>`
header (the per-user token the dispatch layer injects) and forwards it to the
REST API. Six appointment tools: `find_available_slots`,
`check_availability`, `find_appointments`, `create_appointment`,
`update_appointment`, and `cancel_appointment`.

This is the path the `Google_calendar_appointment_mcp` row points at. It is
also the better long-term design while Google's remote Calendar MCP remains
preview-gated: we own the appointment schemas and error handling, while the
Google REST API remains the provider boundary.

**Front-desk prompting lives in the tool descriptions.** `voice-ws` feeds the
model the live descriptions from this connector (via `tools/list`). Mutation
tools require one explicit confirmation flag, while the shared service performs
a fresh conflict check before writing. Caller email and phone are first-class
fields; organization policy decides which are required. DOB, insurance, and
other sensitive health data are not silently persisted to the calendar.

**The connector auto-starts with `voice-ws-dev`.**

`voice-ws-dev` runs [`voice-ws/entrypoint.dev.sh`](../../../voice-ws/entrypoint.dev.sh),
which launches the connector as a co-process and then `exec`s uvicorn.

Because the connector is a child of PID 1 in the same container, it:

- starts automatically whenever `voice-ws-dev` starts or restarts;
- binds `127.0.0.1:8733` inside that container — which is why the
  `Google_calendar_appointment_mcp` row points at `http://127.0.0.1:8733/mcp`;
- is torn down with the container (`exec` makes the app PID 1 and receives
  docker's `SIGTERM`).

No manual `docker exec -d …` is needed anymore. (If you ever need to run it by
hand, the command is
`MCP_HOST=127.0.0.1 MCP_PORT=8733 python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest`,
serving Streamable HTTP at `http://127.0.0.1:8733/mcp`.) Production uses the
same connector: the production Docker command uses
`entrypoint.prod.sh` to start this connector alongside voice-ws. Google's
remote Calendar MCP remains a future provider option (Path B).

### Path B — Google's remote Calendar MCP server (Workspace Preview-gated; GA target)

Google publishes an **official remote Calendar MCP server** at
`https://calendarmcp.googleapis.com/mcp/v1` (Streamable HTTP, **Developer
Preview**). It is gated by the **Google Workspace Developer Preview Program**,
which (currently) requires a **Workspace** account — a personal Gmail cannot
use it. This is the cause of the earlier "The caller does not have permission"
error. We will repoint the row at this server once Google grants Preview access
or the product reaches GA — **no platform change** beyond the row URL. The
in-memory `reference_servers/google_calendar.py` remains only as a deterministic
plumbing proof (no third-party OAuth); it is not on either real-Google path.

The remote server is a standard Google **resource server**: it does not host
its own OAuth. We run the ordinary Google OAuth 2.0 web-app flow ourselves
(consent → callback → token exchange), store the tokens encrypted in
`agent_tools.sensitive_config`, and the dispatch layer injects the decrypted
bearer as `Authorization: Bearer <token>` on every MCP call. This reuses the
platform's existing OAuth plumbing — `start_oauth` / `oauth_callback` are
DB-driven (read `platform_tools.auth_config`), and `TokenRefreshService`
auto-refreshes the tokens from the same `auth_config`. See RFC §6.4 for the
full sequence diagram and the one-time GCP setup checklist.

Refresh selection is provider-agnostic: an MCP tool with native provider
metadata such as Google keeps the native provider refresh payload, while
generic MCP metadata—or any unregistered provider with complete OAuth
metadata—uses the standard refresh-token payload with the connection's
encrypted client ID and resource. Discovery capabilities (token endpoint,
client-auth method, supported grants, client ID, and resource) are sanitized and
persisted as platform metadata, with the connection retaining an encrypted
endpoint fallback. The provider label is not used as an MCP allow-list. Public
clients, `client_secret_post`, and `client_secret_basic` are supported, as are
refresh-token rotation, expired-token recovery, and transient token-endpoint
retries. The connection still requires a durable
`refresh_token`, a token endpoint, and usable OAuth client metadata; revoked
tokens or proprietary client-auth schemes require reauthorization.

OAuth configuration is metadata-only. Access/refresh tokens are stored in the
encrypted `agent_tools.sensitive_config` connection, while confidential MCP
client secrets use the write-only `oauth_client_secret_input` field and the
encrypted `platform_tools.oauth_client_secret_encrypted` column. The platform
admin UI declares whether refresh is automatic, manual, or unknown and shows
Org Admins the corresponding reauthorization guidance. If a provider returns
no refresh token, the live connection is always reported as manual even when
the provider advertises the refresh grant.

Callback state is encrypted and short-lived, carries the PKCE verifier only
inside the opaque value, and is rejected when tampered with or expired. OAuth
and MCP endpoints require HTTPS, do not follow redirects, and never echo token
responses or provider exception bodies to the browser. MCP server URLs are
validated at discovery, save, and runtime dispatch; the final dispatch check
re-resolves the host before decrypting or merging credentials. Public MCP
headers are filtered for credential-like names; use the encrypted secret-header
field for server credentials. Authorization-server metadata, dynamic client
registration, callback token exchange, and background refresh also perform
DNS-aware private-address checks. Providers advertising only proprietary token
endpoint authentication are disclosed as manual and are not sent a guessed
`client_secret_post` request.

### The seeded `Google_calendar_appointment_mcp` row (all environments)

| Field | Value |
|---|---|
| `tool_source` | `mcp` |
| `mcp_server_url` | `http://127.0.0.1:8733/mcp` (REST connector; revert to `https://calendarmcp.googleapis.com/mcp/v1` for Path B) |
| `mcp_server_name` | `google-calendar-appointment` |
| `auth_type` / `requires_auth` | `oauth2` / `true` |
| `auth_config.scopes` | `calendar.events` + `calendar.readonly` (read/write appointment contract) |
| `auth_config.auth_url` / `token_url` | `https://accounts.google.com/o/oauth2/v2/auth` / `https://oauth2.googleapis.com/token` |
| `auth_config.access_type` / `prompt` | `offline` / `consent` (so Google returns a `refresh_token`) |
| `tool_functions_schema` | Six appointment tools (display-only — voice-ws discovers tools live via `tools/list`) |
| Token storage | `agent_tools.sensitive_config` (encrypted, auto-refreshed by `TokenRefreshService`). The dispatch layer decrypts and injects the bearer — the MCP server never handles refresh logic. |

**One-time GCP setup** (operator, both paths): enable
`calendar-json.googleapis.com` (Path A) and `calendarmcp.googleapis.com` (Path
B), add the four scopes + a test user to the OAuth consent screen, and add
`http://localhost:8000/api/v1/tools/callback` to the OAuth client's authorized
redirect URIs (must equal `GOOGLE_OAUTH_TOOL_REDIRECT_URI` in `.env`). Path B
additionally needs Workspace Developer Preview enrollment. Full checklist in
RFC §6.4.

## Running the tests

```bash
cd voice-ws
pytest tests/test_mcp_client.py tests/test_tool_runtime_reliability.py -v
```

Backend shared MCP tests:

```bash
cd backend
pytest tests/voice_agents/test_tool_oauth_mcp.py -v
```

All tests run against real in-process FastMCP servers over real localhost HTTP
(no external network, no third-party OAuth).
