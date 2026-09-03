# Epic B Status — Messaging, SEO & Analytics (`codex/messaging-seo`)

**Base:** `origin/codex/controlled-saas-launch` @ `8291a06` → target same.
**State:** implemented + verified. Not committed (awaiting the standing
launch-line authorization: commit → PR → squash-merge).

## What shipped

- **Honest landing copy (business-voiced):** concierge hero
  ("live in 48 hours, we set it up with you"), outcome trust bullets,
  corrected escalation claim (was: seamless human handoff — not built;
  now: callback offer + instant team alert), concierge 3-step How It Works,
  pilot-framed pricing ("from $79/mo", CTAs → `/request-demo`), industry
  cards for dental/HVAC/restaurants link to new pages.
- **SEO pages:** `/dental`, `/hvac`, `/restaurants` from one shared
  `IndustryPage` template (pain → live demo → setup → outcomes → pricing
  anchor → FAQ + JSON-LD), per-page metadata + canonicals, sitemap extended.
- **PostHog (keyless-safe):** `posthog-js` + `lib/analytics/posthog.ts`
  (typed events, PII-key stripping, no-op without key, marketing/demo
  surfaces only) + provider with per-route pageviews + env sync across all
  three examples. Events: `demo_played`, `demo_completed`,
  `interest_submitted`, `invite_accepted`, `pilot_activated`.
- **Wiring:** demo call active/outcome, request-demo success, invited
  signup success, onboarding completion.
- **Tracker:** `03-deferred-and-followups.md` (cross-epic postponed list).

## Verification

| Layer | Result |
|---|---|
| New tests (analytics 4 + template 2 + sitemap 1) | 7/7 pass |
| Touched suites (landing, demo, auth incl. google-flow, onboarding, request-demo, services) | 68/68 pass |
| tsc / ESLint on touched files | clean |
| E2E full stack | 68 pass, 1 fail — same pre-existing skills `.prose` failure (proven on clean baseline); 3 new SEO + 3 gated-funnel tests green |

## Contract updates (intended, not regressions)

- `landing-page.test.tsx` pricing test → pilot-anchored contract ($79
  anchor, no price table); header comment updated.
- `seo-routes.test.ts` sitemap → exact 5-URL list.
- `auth-google-flow.test.tsx`: fixed pre-existing incomplete
  `next/navigation` mock (missing `useRouter`; failed on clean baseline).

## Ops follow-up (founder, no code)

Provision the PostHog Cloud project, set `NEXT_PUBLIC_POSTHOG_KEY`
(+ host) in staging/prod envs, build the demo→interest→invite→pilot
funnel dashboard. Tracked in `03-deferred-and-followups.md`.
