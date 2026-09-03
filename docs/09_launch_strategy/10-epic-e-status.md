# Epic E Status — Abuse & Auth Hardening (`codex/hardening`)

**Base:** `origin/codex/controlled-saas-launch` @ `6509719` → target same.
**Scope:** audit trail, backend password reset, Turnstile plumbing, and the
Epic A leftover (forwarding guides). SMS transport, outcome summaries, OTel
dashboards, and paid-catalog publish remain tracked follow-ups.

## What shipped

- `auth_audit_events` (migration `20260905000001`, append-only,
  service-role): `signup/signup_denied/signin/signin_denied/oauth_signin/
  oauth_denied/password_reset_requested` (+ unused constants for signout/
  invitation flows). Best-effort writer that never raises; platform-admin
  `GET /api/v1/auth/audit` reader.
- Backend `POST /api/v1/auth/password-reset` (3/min, fixed safe message,
  Supabase recovery link with `redirect_to` to `/auth/reset-password`,
  existing `user.password_reset` Resend template). Forgot-password dialog
  now uses it instead of direct Supabase calls.
- Turnstile: `src/security/turnstile.py` (8s timeout, fail-closed when
  configured, pass-through when not), enforced on public leads POST and
  email signup; `TurnstileWidget` (no new deps, renders nothing without a
  site key) wired into request-demo and signup forms; keys synced across
  all `.env.*.example`.
- `09-forwarding-guides.md`: conditional-forwarding concierge procedure
  with verify-don't-memorize carrier-code policy and test-call proof.

## Verification

| Layer | Result |
|---|---|
| Backend new (audit/reset/audit-list 8 + turnstile 5) | 13/13 pass |
| Frontend new (widget 2 + dialog 2) + auth dir | 37/37 pass |
| Regression (auth+security+notifications+leads) | 246 pass; 7 failures proven identical on stashed baseline |
| tsc / ESLint / flake8 / black on touched files | clean |
| Migration | single head, SQL rendered + verified |
| E2E full stack | 69 pass, 1 fail — same pre-existing skills `.prose` failure (proven on clean baseline) |

## Founder ops (no code)

Provision Cloudflare Turnstile keys (site + secret) into staging/prod;
confirm Supabase redirect allowlist includes `/auth/reset-password`;
review `GET /api/v1/auth/audit` weekly during pilots. Tracked in
`03-deferred-and-followups.md`.
