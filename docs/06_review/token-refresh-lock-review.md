# Code Review: Token Refresh Distributed Lock

**Branch:** `fix/token-refresh-race-issue`
**Date:** 2026-06-23
**Reviewer:** AI Agent Review

---

## Overview

The change implements a **Postgres-backed distributed lease lock** to fix the multi-instance OAuth token-refresh race condition. The core idea is sound and well-documented.

- Migration `20260623000001` creates `token_refresh_leases` table + `claim_token_refresh`/`release_token_refresh` SQL functions.
- `ToolService` gains `claim_refresh_lock()` and `release_refresh_lock()` methods.
- `TokenRefreshService._check_and_refresh_token()` acquires the lease before the OAuth HTTP call and releases in a `finally` block.
- TDD tests cover claim/release/integration scenarios.

**Verdict:** The distributed lock design is correct and well-implemented. However, there are issues that should be addressed before merging.

---

## Critical Issues

### 1. Lost Refresh Token on DB Update Failure (Token Corruption)

**File:** `backend/src/services/token_refresh_service.py:299-333`

If the OAuth provider successfully refreshes and **rotates the refresh token**, but `_update_agent_tool` (line 320) fails afterward, the new refresh token is lost. The old refresh token in the DB is now invalid on the provider side. The next refresh cycle will use the old (invalid) token and fail permanently — user must re-authenticate.

```python
# Flow that causes corruption:
1. OAuth refresh succeeds → provider rotates refresh_token
2. new_tokens["refresh_token"] = "new_rotated_token"
3. _update_agent_tool() fails (DB timeout, etc.)
4. finally block releases the lock
5. Old refresh_token in DB is now INVALID on provider side
6. Next cycle tries old refresh_token → fails → user must re-auth
```

**Risk:** Silent, irreversible data loss. User experiences a broken tool with no obvious cause.

**Recommendation:**
- At minimum, log a **CRITICAL** level warning when DB update fails after a successful refresh.
- Consider caching the new tokens in-memory or a temp column as a fallback.
- Document this as a known limitation if the risk is accepted.

---

### 2. `get_all_agent_tools_with_auth` Doesn't Filter Disabled Tools

**File:** `shared/voice_agents/tool_service.py:590-595`

The query fetches **all** `agent_tools` rows without filtering `is_enabled`. Disabled tools are still processed in the refresh loop, wasting DB reads, decryption calls, and processing time.

```python
# Current: fetches everything
response = (
    self.supabase.table("agent_tools")
    .select("*, tool:platform_tools(*)")
    .execute()
)

# Then filters in Python:
if not tool_data or not tool_data.get("requires_auth", False):
    continue
```

**Recommendation:**
- Add `.eq("is_enabled", True)` to the database query, or
- At minimum, filter `is_enabled` in Python before the `requires_auth` check.

---

## Medium Issues

### 3. Lease TTL (120s) vs. Provider Response Time

**File:** `shared/voice_agents/tool_service.py:172`

The 120-second lease is hardcoded as `REFRESH_LOCK_LEASE_SECONDS = 120`. If a provider is slow or rate-limiting, the lease could expire mid-refresh. A second instance would then acquire the lease and start a concurrent refresh — the exact race this lock is meant to prevent.

**Recommendation:**
- Make `REFRESH_LOCK_LEASE_SECONDS` configurable via environment variable.
- Consider extending the lease before the HTTP call if the work is still in progress.

---

### 4. No Idempotency After Crash Recovery

If the process crashes after a successful OAuth refresh but before DB update, the next cycle will refresh again with the **old** refresh token (which may still be valid depending on the provider). Some providers allow reuse within a window; others don't. There is no mechanism to detect "this token was already refreshed" — it just retries blindly.

**Recommendation:**
- Consider adding a `last_refresh_attempt_at` timestamp to detect recent successful refreshes.
- Or accept the risk and document it as a known edge case.

---

### 5. Refresh Loop Processes All Tokens Sequentially

**File:** `backend/src/services/token_refresh_service.py:164`

With many tools, sequential processing could become slow. Not urgent for current scale, but worth noting.

**Recommendation:**
- Consider `asyncio.gather()` with a concurrency limit for parallel refreshes.
- Defer until the number of tools justifies it.

---

## Minor Issues

### 6. Excessive Logging at INFO Level

**File:** `backend/src/services/token_refresh_service.py:165`

```python
logger.info(f"Processing tool: {agent_tool.tool.name}, enabled: {agent_tool.is_enabled}")
```

This logs on every cycle for every tool. In production with many tools, this generates excessive log volume.

**Recommendation:** Move to `DEBUG` level.

---

### 7. No HTTP Timeout on OAuth Refresh Call

**File:** `backend/src/services/token_refresh_service.py:366-376`

```python
async with httpx.AsyncClient() as client:
    response = await client.post(token_url, data=oauth_data)
```

No timeout is set. A hung provider connection could block the entire refresh loop indefinitely.

**Recommendation:** Add `timeout=httpx.Timeout(30.0)` to the client.

---

### 8. `_check_and_refresh_token` Is Overly Long

**File:** `backend/src/services/token_refresh_service.py:191-340`

The method is ~150 lines with deeply nested logic (try/except, try/finally, multiple early returns). Could benefit from extraction into smaller methods for readability and testability.

---

## What's Good

- **SQL functions are atomic** — `claim_token_refresh` uses `INSERT ... ON CONFLICT DO UPDATE ... WHERE` correctly.
- **Fail-closed behavior** — if the lock cannot be acquired/verified, refresh is skipped rather than racing.
- **Claim-id based release** — prevents releasing a lease another instance re-acquired.
- **`finally` block** ensures lock release on both success and failure.
- **TDD tests** cover claim (granted/held/error), release (owned/not-owned/error), and integration (skip/refresh-then-release/release-on-failure).
- **Documentation** is thorough — migration doc, DATABASE_SCHEMA.md update, implementation doc all consistent.
- **OpenTelemetry spans** on lock methods for observability.

---

## Action Items

| # | Severity | Issue | Action |
|---|----------|-------|--------|
| 1 | **Critical** | Lost refresh token on DB failure | Add CRITICAL log + consider temp cache |
| 2 | **Critical** | Disabled tools not filtered | Filter `is_enabled` in query or Python |
| 3 | Medium | Hardcoded lease TTL | Make configurable via env var |
| 4 | Medium | No crash idempotency | Document or add timestamp guard |
| 5 | Medium | Sequential refresh loop | Consider parallel with concurrency limit |
| 6 | Minor | Excessive INFO logging | Move to DEBUG |
| 7 | Minor | No HTTP timeout | Add `httpx.Timeout(30.0)` |
| 8 | Minor | Long method | Extract smaller methods |

---

## Merge Recommendation

**Do not merge until #1 and #2 are addressed.** The remaining items can be deferred or tracked as follow-ups.

---

## Resolution (2026-06-23)

Addressed via TDD (red→green) in `backend/tests/services/test_token_refresh_review_fixes.py` (21 tests).

| # | Severity | Resolution |
|---|----------|------------|
| 1 | Critical | **Fixed.** `_update_agent_tool` now returns bool; the caller logs **CRITICAL** and returns `False` when the DB update fails after a successful (rotated) OAuth refresh. The lock is still released. The rotated token being lost is now an observable, alertable event (not silent). |
| 2 | Critical | **Fixed.** `get_all_agent_tools_with_auth` filters `is_enabled=True` at the DB (`.eq`) and again in Python (defense-in-depth). Disabled tools are no longer refreshed. |
| 3 | Medium | **Fixed.** Lease TTL is now configurable via `TOKEN_REFRESH_LOCK_LEASE_SECONDS` (default 120, 10–600) and is forwarded to `claim_refresh_lock`. Set it above your slowest provider round-trip. |
| 4 | Medium | **Documented** as a known edge case (crash between OAuth refresh and DB write). Fully closing it needs a temp token store; the CRITICAL log from #1 makes the failure observable. See `docs/03_implementation/token_refresh_lock.md`. |
| 5 | Medium | **Fixed.** `_refresh_expired_tokens` now uses `asyncio.gather` with a semaphore (`TOKEN_REFRESH_MAX_CONCURRENT_REFRESHES`, default 5, 1–20). Tokens are refreshed concurrently instead of sequentially. |
| 6 | Minor | **Fixed.** "Processing tool" log moved to DEBUG. |
| 7 | Minor | **Fixed.** OAuth refresh HTTP call now uses `httpx.Timeout(30.0)` so a hung provider cannot stall the loop/outlive the lease. |
| 8 | Minor | **Fixed.** `_check_and_refresh_token` extracted into 3 focused methods: `_is_token_expiring` (expiry check), `_resolve_oauth_config` (OAuth config resolution), `_perform_token_refresh` (lock → refresh → persist → release). Each is independently testable. |

**All items addressed.** Only #4 remains as a documented known edge case.
