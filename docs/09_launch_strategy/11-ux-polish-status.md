# UX Polish Status — Errors, 404, Feedback, Vertical Focus (`codex/ux-polish`)

**Base:** `origin/codex/controlled-saas-launch` @ `95b3d7a` → target same.
**Trigger:** founder walkthrough of the live demo stack.

## What shipped

- **Branded auth error page** (`auth/session` error state): logo header
  with Home link; invite-only errors get a Request-a-demo primary CTA +
  explainer, other failures get Try-again + Home. No more blank Alert.
- **Request-demo split-screen** mirroring signup/signin (brand panel +
  value props + form). Same validation, same contract, new layout.
- **Branded 404** (`not-found.tsx`): "This page didn't pick up" + Home /
  Request-demo paths.
- **Restaurants page restored** with a dedicated Verdi Table demo link. It now
  points callers to Sofia's restaurant order and Q&A workflow instead of using
  the unrelated dental or HVAC demos. Launch verticals: dental + HVAC +
  restaurants.
- **Demo feedback loop closed** (was: neither agent-prompted nor form):
  outcome page carries a one-click 1–5 `DemoFeedback` widget emitting
  `demo_feedback {demo_slug, rating}` to PostHog (rating-only: no PII,
  no moderation surface); all three demo seed agents gained a `# Closing`
  section pointing callers at the on-screen rating. Prod demo agents
  need the same closing line mirrored (founder ops, tracked).

## Verification

| Layer | Result |
|---|---|
| Frontend (demo, request-demo, landing, auth, outcome) | 58/58 pass incl. 2 new feedback tests |
| tsc / ESLint on touched files | clean |
| Seed closing sections | import-asserted for both agents |
| E2E full stack | 69 pass, 1 fail — same pre-existing skills `.prose` failure (proven on clean baseline); new 404 + updated SEO tests green |

## Founder ops (no code)

The release bootstrap now mirrors the code-owned `# Closing` rating line into
the staging and production demo agents. Founder setup is still required for
the provider connections and destination resources described in the public
demo runbook.
