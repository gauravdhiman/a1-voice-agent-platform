# Leads module (Epic A: gated entry + interest funnel)

Private interest-lead capture for the controlled-SaaS funnel. The
`interest_leads` table is the source of truth for follow-up; demo-safe
subsets are forwarded to public proof destinations (shared Sheet/Calendar)
by the demo workflow, never the reverse.

## Boundary

- Public, unauthenticated: `POST /api/v1/public/leads` (5/min rate limit,
  fixed ack envelope — no email oracle).
- Platform admins only: `GET /api/v1/leads[?status=]` and
  `PATCH /api/v1/leads/{id}` (follow-up state machine
  `new → contacted → invited → converted`/`dropped`).
- Storage is service-role only (RLS enabled, no public policy); see
  migration `20260903000001_add_interest_leads.py` and
  `docs/DATABASE_SCHEMA.md` (`interest_leads`).

After a successful insert, the route queues a platform-admin alert in the
FastAPI background task. Email and Telegram delivery are independent and use
the recipient, sender, Resend, and Telegram settings documented in
`backend/src/notifications/README.md`; incomplete channels are skipped and
delivery failures do not change the public acknowledgement or remove the
stored lead.

## Tests

`backend/tests/leads/test_lead_routes.py` — route gating (regular users
denied, missing lead → 404) plus service persistence/error-hiding, all
against a fake Supabase chain (no database required).
