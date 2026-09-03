# Deferred & Follow-up Tracker (cross-epic)

Single list of everything deliberately postponed, with the epic that owns
the pickup. Review this file at the start of every epic; delete lines as
they land (with the PR number that closed them).

## From Epic A (open)

- [ ] Carrier forwarding guides (T-Mobile/AT&T/Verizon star-codes, landline,
  RingCentral-style VoIP) + concierge screen-share script + test-call proof
  checklist → owner: **Epic B concierge appendix or Epic D pilot kit**
  (needed before the first real pilot, not before code merge).
- [ ] `docs/SUMMARY.md` cross-links for `docs/09_launch_strategy/` (plan +
  decisions + statuses) → owner: **next docs-touching epic**.
- [ ] Native HTML5 validation also gates older forms (signup/signin) before
  RHF/zod runs — audit and add `noValidate` where styled errors are
  authoritative → owner: **Epic E** (auth hardening).
- [ ] E2E skills `.prose` locator failure (`test_organization_skills_page_shows_skills`)
  — pre-existing, reproduced on clean baseline → owner: **whoever touches
  skills UI next** (not launch-blocking: dashboard path unaffected).

## From Epic B (open)

- [ ] PostHog project key provisioning + dashboard/funnel setup in PostHog
  Cloud (code ships keyless-safe; events flow once env is set) → owner:
  **founder (5-minute ops task, no code)**.
- [ ] Vertical ROI numbers on SEO pages are illustrative ("50 missed
  bookings/mo") — replace with measured pilot data after 10 pilots →
  owner: **Epic D**.
- [ ] Multilingual (ES) landing + demo copy → owner: **backlog**
  (English-only until a pilot demands it).

## Backlog (explicitly not launch)

Per-call metering engine · real PSTN warm transfer · annual plans ·
tax/invoice portal · SAML/SSO · MFA/passkeys · standalone CRM ·
transcript search · outbound campaigns at scale.
