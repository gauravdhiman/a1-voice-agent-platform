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

- [x] SMS owner alerts → closed by night batch: `shared/notifications/sms.py`
  (keyless-safe Twilio HTTPS transport, no SDK), callback tool
  `sms_recipients`/`sms_from_number` config + `twilio_account_sid`/
  `twilio_auth_token` sensitive config, `notified_channels` result,
  contract tests + `callback.sms_only_request_notifies_owner` eval.
  Config fields render automatically in the tool drawer (generic schema
  form); Twilio creds flow through the existing encrypted
  `sensitive_config` update path. Remaining: founder Twilio creds +
  a drawer credential input for the Twilio SID/token (API path works).
- [ ] Cheap LLM call-outcome summaries (owner value proof without
  Twilio transcription) → owner: **Epic D part 2**.
- [ ] Callback seed prompt snippet for the dental/HVAC/restaurant skill
  packs (tool docstring carries the contract today; skills reference it
  at pilot setup) → owner: **first pilot setup**.

## From Epic E (open)

- [ ] Cloudflare Turnstile keys (site + secret) provisioned into
  staging/prod; code enforces automatically once set → owner: **founder
  (5-minute ops task)**.
- [ ] Supabase redirect allowlist includes `/auth/reset-password`
  (recovery links point there) → owner: **founder (dashboard check)**.
- [ ] OTel dashboards/alerts (deny-spike, webhook-lag, COGS-breach):
  collector exists, no Grafana in repo — needs a home decision →
  owner: **founder + next observability pass**.
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
  Night-batch progress (2026-09-04): verified against pinned Pipecat
  1.8.1 source — a `finish/reason=error` frame reaches us as "Fish Audio
  server error during synthesis"; `classify_pipeline_failure` now returns
  distinct `tts_empty_audio` with retry/credits guidance instead of the
  generic code (tested, incl. rule ordering vs auth errors). Known
  upstream limit: Pipecat silently drops Fish audio chunks ≤1024 bytes,
  so zero-audio can also pass with silence and no error at all — the
  retry/fallback design still needs a live repro on the pinned runtime.
- [ ] TTS provider A/B: Cartesia is already integrated as a pipeline TTS
  option; run Fish vs Cartesia on empty-audio rate + latency before
  committing pilots to one voice → owner: **same pass as above**.

## From UX polish (open)

- [ ] Restaurant demo agent + `/restaurants` return (route removed: it
  demoed the wrong agent). Needs tuned instructions, tested booking
  flow, and evals — not a copy job → owner: **after 2 live verticals
  prove out**.
- [ ] Mirror the `# Closing` rating line into production demo agents'
  instructions → owner: **founder (config edit)**.
- [ ] Vertical strategy stays 2-polished-over-5-thin until pilot data
  says otherwise → owner: **product decision, revisit post-pilots**.

## Backlog (explicitly not launch)

Per-call metering engine · real PSTN warm transfer · annual plans ·
tax/invoice portal · SAML/SSO · MFA/passkeys · standalone CRM ·
transcript search · outbound campaigns at scale.
