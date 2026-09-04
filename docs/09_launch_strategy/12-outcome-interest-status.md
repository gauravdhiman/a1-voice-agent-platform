# Outcome Interest Status — Closing the Demo Loop (`codex/outcome-interest`)

**Base:** `origin/codex/controlled-saas-launch` @ `ac71467` → target same.
**Trigger:** founder redial — outcome page had rating only, no interest
capture, although the funnel design promised a form fallback.

## What shipped

- `OutcomeInterest` on the demo outcome page: name/email/business →
  private leads funnel with `source=outcome-form` + `demo_slug` +
  vertical attribution, Turnstile-aware, fixed success copy. Sits below
  the rating widget; request-demo remains the standalone path.
- Clarified division (documented here, not just in chat): the agent
  captures *demo-business* data on the call (Sheets/Calendar); the
  outcome page captures *product interest* after the call. The agent
  never mixes the two — roleplay data and real contact data stay apart
  by construction.

## Verification

| Layer | Result |
|---|---|
| New component tests | 4/4 across demo components dir |
| tsc / ESLint on touched files | clean |
| E2E (new outcome-interest test) | (record after run) |
