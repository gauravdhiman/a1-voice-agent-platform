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

## From Epic D (open)

- [ ] SMS owner alerts (Twilio sender transport does not exist yet;
  callback email works). Add SMS channel to the notification path and a
  per-trigger channel config → owner: **Epic D part 2 or Epic E**.
- [ ] Cheap LLM call-outcome summaries (owner value proof without
  Twilio transcription) → owner: **Epic D part 2**.
- [ ] Callback seed prompt snippet for the dental/HVAC/restaurant skill
  packs (tool docstring carries the contract today; skills reference it
  at pilot setup) → owner: **first pilot setup**.

## From Epic E (open)

- [x] Public demo token issuance is limited to five attempts per source IP per
  hour across demo slugs; calls remain free with the existing 15-minute
  duration cap. This is an abuse-control layer, not a complete spend cap —
  monitor provider cost and retain an operational kill switch.
- [x] Closed-signup invitation claims are email-bound and atomic; failed
  invitation processing cannot fall back to a personal organization. The
  production admin allowlist remains deployment configuration, not source
  code.
- [ ] Cloudflare Turnstile keys (site + secret) provisioned into
  staging/prod; code enforces automatically once set → owner: **founder
  (5-minute ops task)**.
- [ ] Supabase redirect allowlist includes `/auth/reset-password`
  (recovery links point there) → owner: **founder (dashboard check)**.
- [x] OTel dashboards/alerts (service readiness, API/voice/tool failures,
  persistence and AI latency): implementation, local dashboards, cloud
  collector profile and deterministic alert tests are checked in. Production
  still needs one Grafana Cloud stack, one Langfuse project and an owned
  contact point provisioned from the operator guide → owner: **founder (release
  configuration task)**.
- [x] Carrier forwarding guides → closed by `09-forwarding-guides.md`
  (Epic E PR).

## From live-call incident 2026-09-04 (Fish TTS empty audio → dropped call)

- [ ] TTS-empty-audio resilience: a single Fish synthesis returning zero
  bytes currently raises a Pipecat error frame that kills the whole call
  (`voice_pipeline_error`, ~30s in — observed live). Wanted: one retry,
  then a spoken fallback line, then graceful close — never a hard drop
  on a transient TTS blip. Lives in/around the pinned Pipecat Fish
  service; do not hack around it — evaluate on the pinned runtime
  deliberately → owner: **voice reliability pass, before any paid SLA**.
- [ ] TTS provider A/B: Cartesia is already integrated as a pipeline TTS
  option; run Fish vs Cartesia on empty-audio rate + latency before
  committing pilots to one voice → owner: **same pass as above**.

## From UX polish (open)

- [x] Callback queue is visible in the signed-in workspace navigation, and
  public marketing copy no longer promises SMS, on-call transfer, or automated
  recall workflows that are not part of the launch surface.
- [ ] Restaurant demo agent + `/restaurants` return (route removed: it
  demoed the wrong agent). Needs tuned instructions, tested booking
  flow, and evals — not a copy job → owner: **after 2 live verticals
  prove out**.
- [x] Materialize the `# Closing` rating line in every environment's code-owned
  demo agents → closed by the release fixture bootstrap. Provider connections
  remain founder setup.
- [ ] Vertical strategy stays 2-polished-over-5-thin until pilot data
  says otherwise → owner: **product decision, revisit post-pilots**.

## Backlog (explicitly not launch)

Per-call metering engine · real PSTN warm transfer · annual plans ·
tax/invoice portal · SAML/SSO · MFA/passkeys · standalone CRM ·
transcript search · outbound campaigns at scale.
