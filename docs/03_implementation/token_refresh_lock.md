# OAuth Token Refresh and Recovery

`TokenRefreshService` runs from the FastAPI lifespan and scans enabled OAuth
connections on a configurable interval. Cloud Run backend deployments keep one
minimum instance and use `--no-cpu-throttling` so the in-process loop can run
between HTTP requests. The loop runs in every backend instance; Postgres
coordinates work per connection.

## Refresh concurrency and credential fencing

The `token_refresh_leases` row and `claim_token_refresh` / `release_token_refresh`
functions prevent two workers from refreshing one connection concurrently.
This uses a row lease because Supabase/PostgREST pools database sessions, so a
session-scoped advisory lock cannot safely span an external HTTP call.

The worker uses the initial scan only to find candidates. Once it claims a
lease, it reloads the current connection and checks expiry and OAuth metadata
again. It marks the refresh in progress through `begin_token_refresh`, which
requires the current lease claim and credential generation.

Each `agent_tools` row has an `oauth_credential_version`. A database trigger
increments it and resets refresh failure state whenever `sensitive_config`
changes, including an OAuth callback. `complete_token_refresh` atomically writes
rotated credentials only when both the claim and source generation are still
current. A stale worker therefore cannot replace credentials from a newer
authorization or from a later lease holder.

The scheduler scan paginates `agent_tools`; every page is filtered to enabled
OAuth connections with stored encrypted credentials. Refreshes run concurrently
under `TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES` (default 5). The lease defaults
to 180 seconds and rejects values below that minimum. DNS validation is bounded
to 10 seconds; HTTPX network-inactivity timeouts are 30 seconds, and the entire
provider request/retry sequence has a 105-second wall-clock deadline. Only
connection-establishment or local-pool failures known to have happened before
request delivery are retried.

## Provider outcomes and recovery

OAuth refresh tokens can rotate when used. A read/write timeout, provider 5xx,
malformed success response, or process crash while a row is marked
`refreshing` can leave the outcome ambiguous. The worker does not replay the old
refresh token in those cases. After the lease expires, the next worker marks
`outcome_unknown`, stops automatic refresh, and sends an immediate admin alert.
This conservative policy can require reauthorization if the process crashed
after marking the attempt but before sending the request; that rare false
positive is safer than replaying a possibly rotated refresh token.

The internal `oauth_refresh_status` values are:

| State | Meaning | Recovery |
| --- | --- | --- |
| `ready` | No unresolved refresh failure | Normal scheduled refresh continues |
| `refreshing` | Provider request may be in flight | Wait for the lease; a later owner classifies an abandoned attempt as unknown |
| `outcome_unknown` | Provider may have rotated the grant but persistence is unconfirmed | Reconnect the tool; do not reuse the old refresh token |
| `reauth_required` | Provider returned `invalid_grant` | Reconnect the tool to grant permission again |
| `configuration_error` | Provider rejected client or endpoint configuration | Platform admin checks client ID, secret, and registered callback URL, then reconnects |
| `credentials_unreadable` | Stored ciphertext cannot be decrypted with the active/fallback Fernet keys | Restore the previous key or add it to `ENCRYPTION_KEY_FALLBACKS`; the next scan clears the state once decryption succeeds, otherwise reconnect |

An explicit HTTP 429 is deferred to the next normal scan. Connection failures
known to occur before request delivery can be retried with bounded backoff.
Provider revocation, account policy, outages, and expired grants cannot be
recovered automatically; the recorded state and alerts tell an administrator
what to do next.

## Administrator notifications

`OAuthAttentionNotifier` sends the seeded
`tools.oauth_reauthorization_required` email event to each organization admin
and the configured platform-admin email. Email delivery uses the existing
`NotificationService` and notification-log retry loop.

The platform Telegram chat receives OAuth alerts when the existing Telegram
notifications are enabled and configured. Optional platform-admin SMS requires
an E.164 destination and explicit opt-in in Platform Notification Settings,
plus backend Twilio credentials and `TWILIO_SMS_FROM_NUMBER`. Organization
admins currently receive email; the product has no organization-level
Telegram or SMS destination setting.

Telegram/SMS alerts are inserted into `oauth_attention_outbox` with safe display
fields and action instructions. The existing notification scheduler claims
rows with `FOR UPDATE SKIP LOCKED`, attempts new alerts immediately, and retries
failed channels with bounded exponential backoff. Delivery is at-least-once if
a provider accepts a message but its database acknowledgment is lost. Alerts
never contain OAuth tokens, client secrets, endpoint URLs, or raw provider
responses.

## Schema and tests

Migration `20260924000001` adds refresh generation/status fields, database
fencing functions, optional platform SMS settings, and the service-role-only
OAuth channel outbox. See [Database Schema](../DATABASE_SCHEMA.md) and the
[notification system guide](../02_core_systems/notification_system.md).

Regression coverage lives in:

- `backend/tests/services/test_token_refresh_service.py`
- `backend/tests/services/test_token_refresh_lock.py`
- `backend/tests/services/test_token_refresh_review_fixes.py`
- `backend/tests/services/test_oauth_attention_notifications.py`
- `backend/tests/notifications/test_oauth_attention_outbox.py`
- `backend/tests/notifications/test_platform_settings_service.py`
- `backend/tests/phone_numbers/test_twilio_service.py`
