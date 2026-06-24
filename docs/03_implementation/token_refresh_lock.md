# Token Refresh Distributed Lock

**Problem:** `TokenRefreshService` runs a background loop in every backend
instance that refreshes OAuth tokens before they expire. With multiple backend
instances, two can refresh the **same** token at once. Most OAuth providers
**rotate the refresh token** on each refresh, so concurrent refreshes invalidate
each other, and the last DB write can persist a stale refresh token — the tool
then silently breaks until the user re-authenticates.

**Solution:** a Postgres-backed per-tool **lease lock** so only one instance
refreshes a given token at a time.

## Why a row-lease (not `pg_advisory_lock`)

`pg_advisory_lock` requires the **same Postgres session** to acquire *and*
release (or hold across the work). This app talks to Postgres through
Supabase/PostgREST, which pools connections — each RPC call may land on a
different session, so an advisory lock acquired in one call can't be reliably
released or held across the external OAuth HTTP call. A row-based lease
(`token_refresh_leases`) works with pooling: acquisition and release are
independent atomic SQL statements, and the lease row survives across calls. It
is still a Postgres-level lock (atomic conditional write), just pooling-friendly.

## How it works

- Migration `20260623000001` creates `token_refresh_leases(agent_tool_id pk,
  locked_at, claim)` and two plpgsql functions:
  - `claim_token_refresh(p_tool_id, p_claim, p_lease_seconds=120) → jsonb`
    — `INSERT … ON CONFLICT DO UPDATE … WHERE locked_at < now()-lease`.
    Returns `{"claimed": true, "claim": <id>}` when this caller wins, else
    `{"claimed": false, "claim": ""}`. Atomic, so only one concurrent caller
    wins; the lease TTL means a crashed holder is re-acquirable after
    `p_lease_seconds`.
  - `release_token_refresh(p_tool_id, p_claim) → jsonb` — deletes the row only
    if `claim` matches this caller (avoids releasing a lease another instance
    re-acquired after this one's expired).

- `ToolService.claim_refresh_lock(agent_tool_id)` generates a `uuid4` claim id,
  calls the RPC, returns the claim id on success or `None` on failure
  (**fail-closed**: skip refresh rather than race).
- `ToolService.release_refresh_lock(agent_tool_id, claim_id)` releases only its
  own lease.
- `TokenRefreshService._check_and_refresh_token` claims **just before** the
  external OAuth HTTP call and releases in a **`finally`** (success or failure).

## Tests (TDD, red→green)

`backend/tests/services/test_token_refresh_lock.py` — 9 tests covering claim
(granted / held-by-another / fail-closed on error), release (owned / not-owned /
error), and the refresh integration (skip when locked; refresh-then-release on
success; release even on refresh failure). The existing
`test_check_and_refresh_token_success` was updated to mock + assert the lock.

## Applying

```bash
alembic upgrade head   # applies 20260623000001
```

The lock is internal; only the backend service role (which bypasses RLS) uses
the table/functions.

## Post-review hardening

After the code review (`docs/06_review/token-refresh-lock-review.md`):

- **Lost-rotated-token is now observable.** If the DB write fails after a
  successful OAuth refresh, `_update_agent_tool` returns `False` and the caller
  logs **CRITICAL** (the stored refresh_token is now invalid → user must
  re-auth). It does not silently report success.
- **Disabled tools are skipped.** `get_all_agent_tools_with_auth` filters
  `is_enabled = true` (DB + Python) so disabled integrations aren't refreshed.
- **Lease TTL is configurable** via `TOKEN_REFRESH_LOCK_LEASE_SECONDS`
  (default 120). Set it above your slowest OAuth round-trip so the lease can't
  expire mid-refresh.
- **HTTP call is bounded** — `_refresh_oauth_token` uses `httpx.Timeout(30.0)`.
- **Log noise reduced** — per-tool "Processing" log is DEBUG.
- **Parallel refresh** — `_refresh_expired_tokens` uses `asyncio.gather` with a
  semaphore (`TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES`, default 5) to refresh
  multiple tokens concurrently instead of one-by-one.
- **Method decomposition** — `_check_and_refresh_token` (~150 lines) was split
  into 3 focused methods:
  - `_is_token_expiring(agent_tool)` — checks whether the token is within the
    expiry window
  - `_resolve_oauth_config(agent_tool)` — resolves provider, token URL and
    builds the refresh payload
  - `_perform_token_refresh(agent_tool, oauth_data, token_url, ...)` — acquires
    the lease, refreshes, persists, and releases

### Known limitations (accepted)

- **Crash between OAuth refresh and DB write:** if the process dies after the
  provider rotates the refresh_token but before the DB write, the new token is
  lost and the next cycle retries with the old (possibly invalid) token. The
  CRITICAL log makes this observable; a temp-token store would fully close it.
