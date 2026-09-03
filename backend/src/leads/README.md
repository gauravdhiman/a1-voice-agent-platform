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

## Tests

`backend/tests/leads/test_lead_routes.py` — route gating (regular users
denied, missing lead → 404) plus service persistence/error-hiding, all
against a fake Supabase chain (no database required).
