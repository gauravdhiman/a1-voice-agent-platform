# Epic A Status — Gated Entry + Interest Funnel (`codex/gated-entry`)

**Base:** `origin/main` @ `fe9f30f` → target `codex/controlled-saas-launch` (never `main` directly).
**State:** implemented + verified. Not committed (awaiting explicit approval per repo rules).

## What shipped

- Closed-signup gate: `PUBLIC_SIGNUP_ENABLED=false` default + `PLATFORM_ADMIN_ALLOWLIST`
  (`shared/config/settings.py`; synced across all three `.env.*.example`).
- Enforcement: `POST /auth/signup` → 403 `signup_disabled`; Google/LinkedIn
  callbacks redirect to the invite-only error page after provider exchange;
  new public `GET /auth/signup-status` for UX redirect (backend authoritative).
  New module `backend/src/auth/signup_gate.py` (read-only invitation check —
  no token-validity oracle, no side effects).
- Interest funnel: `interest_leads` table (migration `20260903000001`, single
  Alembic head verified + SQL rendered + compat checker green),
  `backend/src/leads/` (public POST + admin GET/PATCH, service-role only),
  `/request-demo` page (RHF+zod, `noValidate`, fixed success copy), landing
  CTAs retargeted (`/auth/signup` → `/request-demo`), signup page redirects
  when closed (invitation `?token=` bypasses).
- Demo third-party writes untouched (public Sheet/Calendar proof stays, per
  locked decision 6c).

## Verification (all recorded)

| Layer | Result |
|---|---|
| New backend tests (gate 17 + leads 10) | 27/27 pass |
| New frontend tests (service 4 + form 3) | 7/7 pass |
| Full E2E stack (`run-e2e.sh`) | 65 pass, 1 fail — the failure (`test_organization_skills_page_shows_skills`) reproduced on stashed baseline (62 pass/1 fail there): pre-existing, unrelated |
| Alembic | single head `20260903000001`, compat checker green |
| tsc / ESLint on touched files | clean (repo has 445 pre-existing jest-dom typing errors in older test files; new tests avoid those matchers) |
| flake8 on touched files | clean (routes.py/main.py hits are pre-existing) |
| black/isort | new code clean; 3 black + import-order hits in old code left untouched |

## Pre-existing failures documented (not introduced here)

- `backend/tests/auth/test_service.py` (5) + `test_email_availability.py` (1):
  mocked-Supabase shape drift (500s where 409/200 expected).
- `backend/tests/organization` + `test_lead_capture_suite`: 12 fail identically
  on stashed baseline.
- E2E skills `.prose` locator (above).
- Frontend `tsc --noEmit`: jest-dom matcher types missing repo-wide.

## Issues found and fixed during implementation

1. slowapi-decorated routes need a real Starlette `Request` in direct-invocation
   tests (plain `Mock()` raises) — established `_request()` helper pattern.
2. Route handlers read `organization_service.supabase` eagerly → tests must
   patch `organization_service` (existing pattern).
3. Native HTML5 validation (`type="email"`) blocks submit before RHF/zod in
   browsers too — `noValidate` added (also latent in older forms; backlog).
4. Test Supabase-chain fakes must emulate the full fluent chain
   (`.update().eq().execute()`), not just terminal `.execute()`.

## Backlog / follow-ups (not in Epic A)

- Epic E hardening: Turnstile, auth audit table, backend password-reset
  endpoint, frontend-direct Supabase OAuth gap (Supabase dashboard provider
  lockdown documented in `signup_gate.py`).
- Forwarding carrier guides + concierge checklist (Epic A planned, pending).
- `docs/SUMMARY.md` cross-links for the `09_launch_strategy` docs (live in
  `codex/launch-foundation`; link when both land on the integration branch).
