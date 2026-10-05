# Master-data launch strategy

Research snapshot: 2026-08-13. This is a decision aid, not a final pricing
approval. Prices and plan limits must be recalculated from observed provider
costs and validated with pilot customers before paid catalog rows are seeded.

> **Superseded pricing hypothesis.** The Launch/Growth/Pro prices and minutes
> below are historical research only. Use the approved Starter/Pro/Scale
> catalog, number policy, and current runtime rates in
> [the pilot billing runbook](../09_launch_strategy/05-pilot-billing-runbook.md)
> and [plan publish spec](../09_launch_strategy/06-plan-publish-spec.md).

## Recommended initial market

The repository already has 15 well-structured platform skills in three
industries. That is a strong starting point because the content, reference-file
model, and tests are already aligned. The launch should remain intentionally
narrow:

### 1. Restaurants and hospitality — first wedge

Why it is attractive:

- High-volume, repetitive inbound requests: reservations, hours, menu and
  allergy questions, special requests, and follow-up calls.
- The workflows are easy to demonstrate and measure without asking the agent to
  make clinical or mechanical safety decisions.
- The National Restaurant Association projected **$1.5 trillion** in 2025
  restaurant and foodservice sales, **15.9 million** jobs, and more than **one
  million** outlets. That is a large, fragmented buyer pool, although the same
  source describes competition as intense. [National Restaurant Association:
  2025 industry outlook](https://restaurant.org/research-and-media/media/press-releases/restaurant-industry-poised-for-growth-in-2025-industry-expected-to-employ-15-9-million-people-and-r/)

Initial skills:

- reservation booking
- menu and information
- special requests
- reservation follow-up
- escalation

Launch proof points: answered-call rate, reservation completion rate, missed-
call recovery, after-hours coverage, and human handoff rate.

### 2. HVAC and home services — second wedge

Why it is attractive:

- High-value calls arrive outside office hours and callers need triage,
  scheduling, maintenance reminders, and service-plan information.
- ACCA's 2025 Contractor of the Future study emphasizes operational data,
  training, service plans, marketing, and leadership as contractor priorities.
  [ACCA study release](https://www.acca.org/news/release/acca-and-farmington-consulting-group-release-2025-contractor-of-the-future-study-results)
- ENERGY STAR's maintenance guidance supports recurring pre-season service
  reminders and concrete maintenance workflows. [ENERGY STAR maintenance
  checklist](https://www.energystar.gov/saveathome/heating-cooling/maintenance-checklist)

Initial skills:

- service appointment booking
- service information
- diagnosis and triage
- maintenance recall
- escalation

Guardrails: never diagnose gas, carbon-monoxide, electrical, or other dangerous
conditions; route emergencies to the appropriate human or emergency service;
make clear that the agent schedules and gathers information rather than
certifying a repair.

### 3. Dental — controlled pilot, not unrestricted launch

Why it is attractive:

- Appointment booking, new-patient intake, recall, FAQs, and escalation are
  repetitive and map directly to the current skill library.
- ADA HPI maintains current workforce and practice-economics research, and ADA
  reporting shows meaningful DSO and multi-location practice activity. [ADA
  Dentist Workforce](https://www.ada.org/resources/research/health-policy-institute/dentist-workforce)
  and [ADA practice modality data](https://adanews.ada.org/new-dentist/2024/web-exclusives/practice-modality-by-the-numbers/)

Initial skills:

- appointment booking
- FAQs
- new-patient intake
- recall and reminders
- escalation

Pilot gate: administrative scheduling only, no diagnosis or treatment advice,
minimum-data collection, explicit human handoff, and a separate compliance and
security review before handling sensitive patient information. The seeder must
not treat “dental” as evidence that the platform is ready for regulated
clinical workloads.

### Defer for the next wave

The existing onboarding templates also include salon, real estate, and
plumbing. They are useful expansion candidates, but adding them before the
first three wedges have measurable conversion and retention data would dilute
the content-review and sales motion. Plumbing can share much of the HVAC
operating model; salon and real estate should be added when a repeatable buyer
profile and channel are clear.

## Launch skill-authoring standard

Every launch skill should contain:

- concrete caller trigger phrases and a short activation description;
- a happy-path procedure with tool-agnostic user-visible actions;
- required data, validation, confirmation, and cancellation behavior;
- explicit escalation and safety boundaries;
- a Mermaid decision diagram;
- no provider-specific tool names in reusable skill prose;
- reference files only for data too large or volatile for the core skill;
- test coverage for structure, guardrails, handoff language, and forbidden
  coupling.

The current skill tests already enforce these rules for all 15 templates. The
market recommendation changes rollout order and guardrails; it does not replace
the existing authored content with generic industry labels.

## Competitive pricing signals

The market has three recognizable pricing shapes:

| Pattern | Public signal | Implication for 24x7 AI |
| --- | --- | --- |
| Developer infrastructure + pass-through | Vapi advertises $0.05/min hosting, includes 10 concurrency, and passes model-provider costs through | Transparent and attractive to technical builders, but customers carry cost variability and configuration burden. [Vapi pricing](https://vapi.ai/pricing) |
| All-in usage rate | Bland lists $0.14/min on Start, $0.12/min plus $299/month on Build, and $0.11/min plus $499/month on Scale; Retell publishes a broad $0.07–$0.31/min range and a current example around $0.11/min | Easy to understand for SMBs; the platform must actively manage provider and telephony margins. [Bland pricing](https://app.bland.com/pricing), [Retell pricing](https://www.retellai.com/pricing) |
| Bundled SaaS minutes | Synthflow lists $29/month for 50 minutes, $450/month for 2,000 minutes, and $900/month for 4,000 minutes on its BPO page, with overage rates and enterprise pricing | Bundles create predictable budgets and room for packaging, but unused minutes and concurrency must be modeled. [Synthflow BPO pricing](https://synthflow.ai/ai-agent-for-bpo) |

Underlying cost is not just the model. Twilio's US voice page lists local
receive at $0.0085/min, local outbound at $0.014/min, toll-free receive at
$0.022/min plus a monthly number charge, and separate recording/transcription
fees. [Twilio US Voice pricing](https://www.twilio.com/en-us/voice/pricing/us)
Google's Gemini pricing page also shows separate input/output audio and text
rates for Live API models. [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)

These public prices are directional benchmarks. Vendor rates, provider mix,
prompt/audio tokenization, call duration distribution, recording policy,
support, and concurrency can materially change actual contribution cost.

## Current pilot catalog proposal (not yet published)

Do not seed paid plan versions from a worktree fixture. Configure and review
them through the authenticated Plan Catalog admin following the
[plan publish spec](../09_launch_strategy/06-plan-publish-spec.md):

| Tier | Monthly price | Annual price | Included call minutes/month | Included credits/month |
| --- | ---: | ---: | ---: | ---: |
| Free | $0 | — | 10 | 100 |
| Starter | $49 | $490 | 250 | 2,500 |
| Pro | $149 | $1,490 | 1,000 | 10,000 |
| Scale | $299 | $2,990 | 2,100 | 21,000 |

Current runtime pricing is 10 credits per connected voice minute, 80 credits
per additional US local number-month, 200 credits per existing legacy non-US
local or mobile number-month, and 120 credits per toll-free number-month. New
platform number search and purchase are US-only and mobile inventory is
disabled in v1; imported customer-owned Twilio numbers have no platform rental
fee. These values are internal meters, not a claim that one credit should be
marketed as currency. Credit top-ups are $5/200, $10/400, and $25/1,000.

Recommended commercial presentation:

- Show included minutes and estimated remaining minutes to customers; keep
  credits as an internal metering mechanism.
- Annual billing charges 10 monthly payments for 12 months of service. Grant
  12 times the monthly credits so the annual call-minute allowance remains
  consistent.
- Do not enable or advertise a separate overage price until pilot COGS and the
  pricing decision are reviewed.
- Treat phone-number rental as a separate transparent line item or include a
  small allocation in the bundle and disclose it clearly.

## Unit economics and margin guardrails

Track the following per connected minute and per customer-month:

```text
variable COGS/minute = telephony + STT + LLM + TTS + media/recording
                       + metering/infra + variable support
contribution margin = (recognized revenue - variable COGS) / recognized revenue
required price/minute = variable COGS/minute / (1 - target margin)
```

Initial guardrails:

- Target at least **70% contribution margin** after direct variable voice costs
  for the standard self-serve tiers. This is a product target, not a forecast.
- Review any tier that falls below **55%** at P80 expected usage or at the
  platform's included-minute exhaustion point.
- Model P50, P80, and P95 call duration and concurrent-call usage; a monthly
  minute bundle without concurrency and overage analysis is incomplete.
- Keep a separate fully loaded view that adds sales, onboarding, payment,
  support, and compliance costs. Do not call contribution margin gross margin
  if those costs are included inconsistently.
- Reprice or reduce included minutes if provider COGS rises; never silently
  change the meaning of a credit already granted to a customer.

For example, if blended direct COGS is $0.05/minute, a 70% target requires at
least $0.167/minute before payment fees and other fixed costs. That calculation
is why the proposed table remains a hypothesis rather than an immediate paid
seed.

## Decisions required before paid seeding

1. Approve the first two production wedges and the dental pilot gate.
2. Measure real provider cost by call type, duration percentile, and transfer
   behavior in staging and the first pilot cohort.
3. Decide whether phone rentals are included, passed through, or priced as a
   separate line item.
4. Approve the contribution-margin floor and the overage policy.
5. Create Stripe products/prices and versioned plan entitlements through the
   existing Plan Catalog admin workflow.
6. Add an approved paid-plan source definition and tests before enabling paid
   plan seeding in `MasterDataService`.
