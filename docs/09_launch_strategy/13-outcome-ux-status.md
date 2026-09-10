# Outcome UX Status — Summary First, Interest Has a Home (`codex/outcome-ux`)

**Base:** `origin/codex/controlled-saas-launch` @ `80a03d3` → target same.
**Trigger:** founder walkthrough — tool internals buried the lede, feedback
and interest sat below the fold, ratings/interest had no platform home,
and the interest form lacked a free-text field.

## What shipped

- **Outcome relayout:** status banner → side-by-side rating + interest
  grid → collapsible "Call details" (`<details>`, shut by default) →
  receipt footer. Visitors see success + captured facts + next actions
  without scrolling past provider internals.
- **Interest form gains free text:** business/use-case/requirements box
  (`message`) on the outcome form; request-demo already had it.
- **Platform Interest page** (`/platform/interest`, nav item, admin-only
  both sides): attributed lead table (contact, business, source, demo
  slug, message preview) + status filter + one-click advance down the
  new → contacted → invited → converted chain. Ratings stay in the
  PostHog funnel by design (no PII duplication); the page says so. Demo
  and request-form submissions belong here; they are intentionally separate
  from the callback queue, which is reserved for callers asking an agent for
  a person. Platform admins see a link to this queue from Callbacks to make
  the distinction explicit.
- **Real bug fixed along the way:** the page depended on the `user`
  object identity in its fetch effect, which refetches in a loop
  whenever context identity churns. Now depends on the stable
  `isPlatformAdmin` boolean.

## Verification

| Layer | Result |
|---|---|
| New tests (interest page 3) + neighbors | green |
| tsc / ESLint on touched files | clean |
| E2E full stack | 71 pass, 1 fail — same pre-existing skills `.prose` failure (proven on clean baseline); outcome tests updated to open the Call-details disclosure first |
