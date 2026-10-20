# Production readiness review — October 19, 2026

**Remediation:** See the [implementation and remaining launch gates](production-readiness-remediation-2026-10-19.md). This report preserves the original observed state.

**Decision: NO-GO for paid customer onboarding in the current state.**
The most urgent issue is direct database access, ahead of Stripe configuration.
The platform is running, but several security, customer, and operational
contracts have not been met or demonstrated in production.

Target: launch on or before **November 1, 2026**, with an earlier controlled
launch when the gates below pass. Dates use America/Phoenix. This is a dated
engineering assessment, not a claim that every code path is defect-free.

## Scope and evidence

- Reviewed remote `main` at `b7f8fc402893e9d1e2756ca0c04a251ecaa17a55` in the
  dedicated `codex/production-readiness-20261019` worktree.
- Both serving Cloud Run image tags matched that SHA. Backend revision:
  `backend-247ai-00061-fhq`; frontend: `frontend-247ai-00049-qps`, each at 100%
  traffic at observation time.
- Compared four critical files in the running voice container with this source:
  WebSocket entry point, bot pipeline, call tracking, and shared voice
  entitlements. All matched. This does not establish identical installed
  dependencies or complete image provenance.
- Inspected deployment, authentication, permissions, schema grants/RLS/RPCs,
  billing, notifications, integrations, voice/recording lifecycle, and runbooks.
  Ran broad automated suites, a clean frontend build, and dependency scans.
- Used authenticated **read-only** GCP, GitHub, database, Resend, Telegram, and
  Twilio queries. Database transactions were read-only. Anonymous Data API
  probes requested zero rows. Browser checks covered the homepage, lead form,
  sign-in, signup routing, and privacy page.
- No production signup, lead, payment, invitation, email, Telegram message,
  browser voice call, or PSTN call was created. No production data change,
  deployment, migration, plan change, commit, push, or PR was performed.
- Plan configuration remains owned by the other workstream requested by the
  founder. It is a launch dependency here, not duplicated implementation.
- [Sanitized evidence](production-readiness-2026-10-19.evidence.json) contains
  operational metadata, permission assertions, and aggregate outcomes only.
  Credentials, customer rows, recipient addresses, phone numbers, and message
  content are excluded.

Evidence: **CONFIRMED** = observed in production; **CODE** = verified from the
reviewed source; **UNVERIFIED** = an acceptance gate remains open. Credential
presence or a passing mock test does not prove live delivery.

Priority: **P0** = immediate security containment; **P1** = resolve before the
affected paid launch path; **P2** = scheduled improvement or an explicitly
bounded launch risk. Suggested owners below are responsibilities, not accepted
assignments. All register entries remain open at publication.

## Ordered remediation register

| ID | Priority | Finding / gate | Evidence | Suggested owner |
| --- | --- | --- | --- | --- |
| R01 | P0 | Client CRUD on 17 tables without RLS; global authenticated agent/tool reads | CONFIRMED | Database/security engineer |
| R02 | P0 | Privileged invitation/demo RPCs executable by client roles | CONFIRMED + CODE | Database/security engineer |
| R03 | P1 | Direct Supabase signup bypasses the intended invite-only boundary | CONFIRMED configuration + CODE | Auth engineer/operator |
| R04 | P1 | Platform notification destinations incomplete; verification disabled by configuration | CONFIRMED + CODE | Backend engineer/operator |
| R05 | P1 | Resend domain and actual inbox delivery not established | UNVERIFIED; historical failures confirmed | Domain/email operator |
| R06 | P1 | Default Twilio account is Trial; number callbacks target another host | CONFIRMED | Telephony operator |
| R07 | P1 | Terms and Privacy documents are not published | CONFIRMED | Founder/legal operator |
| R08 | P1 | Stripe remains test-only; live account/payment acceptance open | CONFIRMED + UNVERIFIED | Billing operator |
| R09 | P1 | Application telemetry disabled; alert delivery unproven | CONFIRMED + UNVERIFIED | Operations owner |
| R10 | P1 | Backup coverage and isolated restore drill unproven | UNVERIFIED | Database/operations owner |
| R11 | P1 | Bot protection absent; HTTP limits are per process | CONFIRMED + CODE | Security/backend engineer |
| R12 | P1 | Vulnerable dependency pins, including the public webhook form parser | CODE + scans | Backend/frontend engineers |
| R13 | P1 | Production approval and check enforcement incomplete | CONFIRMED + CODE | Repository/release owner |
| R14 | P1 | Failed call tracking/settlement lacks durable recovery | CODE | Voice/billing engineer |
| R15 | P1 | Call admission check and tracking insert are not atomic | CODE | Voice/database engineer |
| R16 | P1 | No recording expiry worker found; storage lifecycle unverified | CODE + UNVERIFIED | Storage/privacy owner |
| R17 | P1 | Two enabled tool connections need reauthorization; provider approval unknown | CONFIRMED + UNVERIFIED | Integration/operator owner |
| R18 | P1 | Raw console logs contain email/phone PII despite safe OTLP export | CODE | Backend/privacy engineer |
| R19 | P1 | Live customer journey and cross-tenant acceptance gates open | UNVERIFIED | Release owner |
| R20 | P1 | Broad suites are red and not required by current CI | TEST + CODE | Engineering/release owner |
| R21 | P2 | Public frontend lacks a security-header baseline | CONFIRMED + CODE | Frontend engineer |
| R22 | P2 | Blocking I/O remains in async paths | CODE | Backend/voice engineers |
| R23 | P2 | Single voice VM and unproven concurrency/recovery capacity | CONFIRMED topology + UNVERIFIED | Operations owner |
| R24 | P2 | Runtime reproducibility and health-probe hardening | CODE + CONFIRMED | Release/operations owner |
| R25 | P1 scope decision | Onboarding, support, privacy, costs, and public promises need signoff | UNVERIFIED | Founder/product owner |
| R26 | External dependency | Approved plan/catalog work must land and pass acceptance | Separate founder-requested workstream | Existing billing workstream |

### R01 — Close direct table access immediately

Production has RLS disabled on these 17 tables. Each grants `SELECT`, `INSERT`,
`UPDATE`, and `DELETE` to **both** `anon` and `authenticated`:

```text
agent_skills                       alembic_version
call_artifacts                     call_logs
entitlement_definitions            organization_skill_files
organization_subscription_migrations
pipeline_presets                   plan_products
plan_version_entitlements          plan_version_publish_events
plan_versions                      platform_skill_files
platform_skills                    platform_tools
skill_update_logs                 voice_templates
```

Anonymous zero-row REST reads succeeded for six representative tables,
including call logs, recording metadata, and organization skill files. Combined
with the database grants, this establishes an access-control exposure without
retrieving private rows or exercising writes. Backend permissions do not
protect direct Supabase requests. This does **not** establish exploitation;
available access logs need a separate assessment.

The policy inventory also found **RLS enabled but tenant isolation absent**
for `voice_agents` and `agent_tools`: each has an authenticated `SELECT`
policy with `USING (true)`, described as allowing Realtime subscriptions.
These policies apply to ordinary Data API reads too. Realtime access must not
be implemented by allowing every signed-in user to read every tenant's agent
or tool configuration. Include these two tables in containment and regression
tests, even after the 17 RLS-disabled tables are fixed. No cross-tenant records
were retrieved during this audit.

**Action:** preserve access evidence; inventory exposed tables, views, functions,
and default privileges; explicitly revoke unnecessary client grants; enable
RLS and narrowly allow intended tenant/public operations. Preserve service-role
behavior. Implement the durable change through Alembic with schema docs and
regression tests. Check staging independently.

**Acceptance:** direct Data API tests for anonymous, org A member/admin, and
org B prove intended allow/deny behavior for all four operations, including
billing catalogs and tool/skill configuration. Exercise mutations against
disposable data in an isolated DB, then verify production permissions read-only.
Add a migration gate for newly exposed objects. Supabase documents the need
to control both [grants and RLS](https://supabase.com/docs/guides/database/postgres/row-level-security).

### R02 — Remove unintended privileged RPC access

Client-role execute access is confirmed for three `SECURITY DEFINER` functions:
`claim_invitation`, `reserve_demo_voice_call`, and `consume_demo_voice_call`.
Their migrations revoke `PUBLIC`, then grant the service role, without
explicitly removing default/direct `anon` and `authenticated` grants.

`claim_invitation` accepts the target user ID and email as arguments and trusts
the backend identity boundary. The demo functions mutate budget/reservations.
Direct execution bypasses backend identity validation and rate limiting. The
claim function still requires a valid invitation token; this is not evidence
that arbitrary tokens can be guessed. No mutating RPC was called in the audit.

**Action/acceptance:** revoke unintended grants explicitly, correct default
function privileges, and test client-role denial plus successful service-role
invitation/demo flows. Inspect live signatures/definitions before remediation.
Sources: [demo migration](../../backend/alembic/versions/20260827000001_add_demo_call_limits.py),
[invitation migration](../../backend/alembic/versions/20260909000001_add_invitation_roles.py).

### R03 — Make the signup boundary consistent

The running backend has `PUBLIC_SIGNUP_ENABLED=false`; the browser redirects
noninvited signup to `/request-demo`. Supabase Auth reports
`disable_signup=false`, with email, Google, and LinkedIn OIDC enabled. The
[signup gate](../../backend/src/auth/signup_gate.py) documents the direct-provider
bypass. This audit did not create an account to exercise it.

**Action/acceptance:** choose concierge/invite-only or open signup deliberately.
For concierge launch, enforce the choice at Supabase and the backend while
preserving existing-user login and the supported OAuth broker. Test direct
Auth/provider signup, valid/expired/mismatched invitations, founder provisioning,
and active-org selection. Do not disable providers blindly and break login.
Disabled open signup alone is **not** a defect if concierge onboarding is the
intended launch mode.

### R04–R05 — Validate notifications and verification end to end

Production observations:

- Platform recipient email, verification sender address, and sender name are
  empty. Telegram bot/chat exist, but alert opt-in is disabled.
- Telegram token decryption, `getMe`, and `getChat` succeed. This proves bot/chat
  access, not message delivery or receipt.
- There are no saved organization notification-settings rows. Org-admin
  account emails can still receive some alerts; no settings row does not mean
  all org email delivery is disabled.
- Verification is inactive. [Auth signup](../../backend/src/auth/service.py)
  creates users with `email_confirm=true` when sender fields do not activate
  verification. This is a security setting, not cosmetic sender branding.
- Thirteen failed email records concern verification/invitations. They are
  historical **2025** domain-verification failures with no idempotency keys;
  the current retry pass excludes them. They do not prove the domain remains
  unverified today.
- Nineteen OAuth attention rows show all Telegram/SMS channels skipped. Two
  enabled tool connections currently need reauthorization.
- Resend domain inspection returned `restricted_api_key`. A scoped sending
  key is reasonable; do not broaden runtime access merely for this audit.

**Action:** verify the exact sending domain/DNS in Resend's dashboard; confirm
key/domain permissions; configure platform recipients and verification identity;
enable the chosen Telegram alerts; configure a test org's contacts and own bot.
Keep platform and org settings independent. Add safe admin test-delivery/status
functionality if needed. Make production verification an explicit fail-closed
policy instead of silently following empty sender fields. Handle historical
failed records deliberately; do not replay expired links or old invitations.

**Acceptance:** complete the notification matrix later in this report, including
actual inbox/chat receipt, outages, retries, tenant denial, and safe errors.
Domain verification, DNS authentication, API acceptance, and inbox placement
are separate checks. Resend requires a
[verified domain](https://resend.com/docs/dashboard/domains/introduction).
Bounce/complaint handling, quotas, and an owned support mailbox also need signoff.

### R06 — Establish a real production PSTN path

The platform Twilio account is active but **Trial**. Its single number has
the expected incoming/status paths on a host other than `api.247ai.live`,
without TwiML application or SIP trunk indirection. This establishes a default
account routing mismatch, not the state of every customer-owned account.
Platform number purchasing and SMS use the configured
[Twilio service](../../backend/src/phone_numbers/twilio_service.py).

**Action/acceptance:** activate the intended paid account, funding, allowed
destinations, and production incoming/status callbacks. Place a real inbound
call through public `/twilio`; verify routing, agent, two-way audio, recording,
final call status, and one usage debit. Separately validate customer-owned
numbers if offered. Review [trial restrictions](https://www.twilio.com/docs/usage/tutorials/how-to-use-your-free-trial-account).
SMS/WhatsApp need their own sender/template/registration checks if included;
they can remain explicitly disabled at initial launch.

### R07 — Publish Terms and Privacy before onboarding

Legal version and acceptance tables are empty. Both legal APIs return 404.
The privacy route serves a 200 shell, then displays that the policy is
unavailable. A successful page-shell response is insufficient evidence.

**Action/acceptance:** finalize appropriate business terms/privacy text and
publish through the existing [legal service](../../backend/src/legal/service.py).
Verify visible text/version/date and signup/invitation acceptance capture.
Approve recording consent, retention/deletion, subprocessors, AI limitations,
support/refunds, and permitted use for the actual launch market. Legal adequacy
is a business/legal signoff, not established by this engineering review.

### R08 / R26 — Stripe live cutover and plan dependency

The runtime secret is a test key; the registered webhook is `livemode=false`;
versioned config uses a test publishable key. The account response under that
test credential reports charges/payouts/details false. Verify activation in
the **live** account context rather than inferring live capability solely from
that test response.

**Action:** let the other workstream finalize plans, then bind the correct live
products/prices, matching browser/server keys, and live endpoint signing secret.
Rebuild the frontend. Reconcile prelaunch test customer/subscription/purchase
references without indiscriminate deletion. Test/live objects are separate in
[Stripe](https://docs.stripe.com/keys).

**Acceptance:** checkout, credit purchase, receipt, portal, cancellation,
renewal, payment failure, duplicate/out-of-order webhooks, and ledger
reconciliation. Use a founder-approved small real payment/refund before taking
customer money. Confirm taxes, invoice identity, payment methods, and dispute
ownership. The handler supports delayed checkout success, but that event is
absent from the current test endpoint's subscriptions; validate the event set
for the enabled methods. Follow Stripe's
[go-live checklist](https://docs.stripe.com/get-started/checklist/go-live).

### R09–R10 — Detect failures and demonstrate recovery

`OTEL_ENABLED=false` in the serving backend and voice container. A host Alloy
container runs, but this does not establish application telemetry or alert
receipt. Backend minimum instances=1 and CPU throttling=false support the
in-process maintenance workers. A bounded seven-day error-log sample was
counted without exporting payloads; it is not an availability/SLO measurement.

**Action/acceptance:** use the existing [observability runbook](observability.md)
to enable the approved application pipeline and prove operator alert receipt.
Cover calls/audio, 5xx/provider failures, settlement, outbox backlogs, OAuth,
recordings, VM resources, quotas, and stalled workers. Include independent
uptime/alert delivery, named primary/backup responders, and an incident drill.

Supabase backup/PITR coverage, latest recovery point, off-site retention, R2
recovery, and a completed restore drill remain **UNVERIFIED**. No database cron
backup job does not imply managed backups are absent. Inspect control-plane
backup settings; restore to a separate environment and verify Auth, schema,
tenant state, ledger, and encrypted credential/key recovery. Approve RPO/RTO.
A database backup does not restore recording objects; see
[Supabase's backup boundary](https://supabase.com/docs/guides/platform/backups).

### R11–R12 — Protect public cost and parsing boundaries

The backend has no Turnstile secret reference; the versioned frontend site
key is empty. [Verification](../../backend/src/security/turnstile.py) accepts
requests when its secret is absent. The
[HTTP limiter](../../backend/src/security/rate_limiter.py) uses in-memory state
while Cloud Run can scale to ten instances, so it is not a shared request
budget. Demo reservations already have useful database budget/duration controls.

**Action/acceptance:** enforce the chosen bot protection on public forms,
test missing/invalid/expired tokens, and use a shared or equivalent edge/backend
rate budget. Check proxy/IP trust and actual ingress; DNS-only Cloudflare
records do not supply a proxied WAF. Test multiple instances and provider-cost
caps in isolation, without load-testing production.

Dependency findings:

- Production-only npm audit reports 22 affected package entries: 2 high,
  17 moderate, 3 low. Transitive chains are included; these are not 22 proven
  independent exploits.
- High entries include `sharp@0.35.4` and transitive `source-map-js`. The sharp
  advisory's RCE conditions involve glibc Linux; this frontend uses Alpine/musl.
  Do not claim proven image RCE. Patch/triage against the
  [maintainer advisory](https://github.com/advisories/GHSA-wq5f-xc86-pv6w).
- Next `15.5.26` matches advisory ranges. The inspected cache-poisoning
  advisory concerns Pages Router; this application uses App Router. Assess
  applicability and update the compatible maintenance line.
- A fresh backend requirements resolution reports eight affected Python
  packages, including dev-only Black/pytest. Runtime packages include
  `cryptography`, `PyJWT`, `python-dotenv`, `python-multipart`, `requests`, and
  `starlette`. Deduplicate advisory aliases before counting issues.
- The clearest reachable issue is `python-multipart==0.0.12`: the
  [Twilio webhook](../../backend/src/voice_agents/voice_routes.py) calls
  `request.form()` before rejecting a missing signature. The maintainer
  documents a [form-parsing DoS](https://github.com/Kludex/python-multipart/security/advisories/GHSA-59g5-xgcq-4qw3).
  No malicious parser payload was sent to production.

**Action/acceptance:** update FastAPI/Starlette/parser as a compatible set,
bound body sizes/content types, reject obviously unauthenticated webhooks
early, and preserve signature validation. Triage other advisories against
installed image versions/reachability. Scan backend, frontend, voice, and base
OS images; a fresh local resolution is not a deployed-image SBOM.

### R13 — Enforce the promised release gates

GitHub production environment metadata contains no protection rules or branch
policy. Main branch protection inspection returns 403 with a repository-plan
upgrade requirement; enforced protection was not established. Promotion checks
SHA shape, not staging attestation or full-suite success. Recent promotions
include failures despite the narrower CI checks passing.

Voice deployment may be skipped with a successful job when SSH config is
missing. **The latest audited run actually executed voice deployment**; this
is a future failure mode, not a claim that latest voice deployment was skipped.

**Action/acceptance:** choose an available protected release mechanism, require
review/checks and recorded staging evidence for the exact candidate, fail
closed on missing required voice deployment, add functional post-deploy gates,
and rehearse rollback/migration compatibility. Record service image identities.
Sources: [workflow](../../.github/workflows/promote-production.yml),
[audited promotion](https://github.com/gauravdhiman/a1-voice-agent-platform/actions/runs/39318381270).

### R14–R15 — Preserve accounting under faults and concurrency

[Call tracking](../../voice-ws/src/call_tracking.py) returns no log ID after
persistence failure; the [bot](../../voice-ws/src/bot.py) continues. Finalization
returns immediately without an ID. It otherwise marks the call finished before
attempting billing, then logs/swallows settlement exceptions. No durable
settlement reconciliation worker was found. Crashes or transient database
failure can leave incomplete/unbilled work without automatic recovery.

[Admission](../../shared/billing/voice_session_entitlement.py) counts active
calls before the later tracking insert. Concurrent requests can pass the same
slot check. Atomic credit debit does not make admission atomic. Normal calls
have no general duration cap in this WebSocket path; demo caps do exist.
Completing admitted calls into overdraft is an explicit current credit policy.

**Action/acceptance:** atomically reserve an expiring admission lease; refuse
or explicitly recover paid calls without durable tracking; persist completion
and idempotent settlement work; reconcile stale leases/calls/missing debits.
Test simultaneous starts at limit one, duplicate tokens/callbacks, worker death,
and failures before/after debit. Decide maximum normal-call cost exposure and
test that policy. Preserve intended overdraft semantics unless deliberately
changed. Inject faults only in isolated environments.

### R16–R18 — Protect stored data and integration continuity

Recording code writes a 90-day expiry. No application code consuming
`retention_expires_at` to remove recordings was found; external R2 lifecycle is
unverified. Existing private playback/deletion paths are useful, but metadata
does not enforce retention. Verify lifecycle rules or add an observable worker;
coordinate DB tombstones; test expiry/deletion, missing objects, tenant denial,
and signed-link expiry. Review transcript, notification, and backup retention
separately. No expired available recordings were observed, which does not
prove cleanup works.

Two enabled tools have `reauth_required`. Reconnect through the supported UI;
do not copy tokens. Google consent publishing, approval/scopes, quotas/billing,
and LinkedIn app production state remain unverified. Gmail requests
`gmail.readonly`, `gmail.modify`, and `gmail.compose`, which Google calls
[restricted scopes](https://developers.google.com/workspace/gmail/api/auth/scopes).
External use may require verification and a
[security assessment](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification).
Check actual approval immediately. If it cannot meet the deadline, explicitly
reduce launch integration scope instead of promising unapproved functionality.

OTLP has an attribute allowlist and sanitized log copies, but intentionally
leaves console handlers unchanged. [Auth](../../backend/src/auth/service.py)
logs email addresses, and [incoming calls](../../backend/src/voice_agents/voice_routes.py)
log caller/called numbers. Cloud Run collects stdout with OTLP disabled.
Redact at source/console boundaries and verify cloud logs and OTLP contain no
email/phone/token/message payloads. Review existing log access/retention too.

### R19–R20 — Close executable and live acceptance gaps

| Check | Result | Interpretation |
| --- | --- | --- |
| Backend + shared, Python 3.11 | 2,546 passed, 1 failed, 40 skipped | Analytics test uses a fixed September timestamp outside today's rolling window |
| Voice, Python 3.11 | 142 passed | Includes local MCP connector round trips; not live provider acceptance |
| Deterministic agent evaluations | 34/34 passed | Calendar 16, callback 7, lead capture 4, Resend 7 |
| Frontend Vitest | 1,287 passed, 2 failed, 206 files | Sitemap/SEO assertions omit newly added blog URLs |
| Frontend TypeScript | Passed | `tsc --noEmit` |
| Frontend lint | 0 errors, 10 warnings | Existing unused symbol/directive warnings |
| Clean production frontend build | Passed | Turbopack; isolated worktree; no production secrets used |
| Migration graph | Passed | Single head `20261012000001`; live revision matches |
| Latest configured CI | Passed | Agent evals, migrations, observability contracts; not full app coverage |
| Live browser/PSTN calls | UNVERIFIED | No calls placed |
| Authenticated admin/customer workflows | UNVERIFIED | No real admin/customer sessions used |
| Full disposable browser E2E lifecycle | NOT RUN | No existing application stack was replaced or torn down |
| Whole-repo pre-commit autofix | NOT RUN | Audit did not autoformat source; document/link/diff checks separate |

Frontend checks used host Node `v26.7.0`; deployment uses Node 20. Repeat
required gates in the supported release runtime. Initial fixture socket errors
disappeared when loopback access was allowed. Initial backend import/env
effects were separated from the final results and are not production defects.
The three remaining assertions are still red evidence even if stale tests.

Repair deterministic dates and expected route lists. Add required backend,
frontend, and durable browser gates for the customer journey. Do not count
skipped database tests as passing. The current CI/promotion does not enforce
these broader suites.

### R21–R25 — Bound launch risk and promises

- **Frontend headers:** sampled `www` pages lack CSP, HSTS, nosniff,
  Referrer-Policy, and framing policy; the API has its own headers. Add/test
  a frontend policy preserving microphone, WebSockets, Stripe, providers,
  Turnstile, media, and intended embeds. Consider report-only CSP first.
  One nonbrowser apex probe got 403 while a real browser redirected correctly;
  verify crawler/edge behavior rather than calling the apex universally broken.
- **Async I/O:** synchronous Stripe operations run inside async services;
  synchronous DB calls remain in admission/auth; JWKS refresh uses synchronous
  HTTP. Use bounded async/executor adapters and timeouts. Test latency while
  providers stall. Payment retries still require explicit idempotency.
- **Capacity/availability:** one OCI voice VM, with a configured 2-CPU worker.
  Idle disk/RAM headroom is healthy, but no concurrency capacity was proven.
  Establish initial admission limits, overload behavior, quotas, recovery, and
  customer fallback. Full active-active redundancy can be a documented later
  improvement for a small concierge cohort; unowned recovery cannot.
- **Reproducibility/probes:** Cloud Run uses TCP startup probes and no observed
  liveness probes. Add useful probes and stuck-worker alerts. Python ranges,
  on-host OCI builds, and mutable image/base tags weaken reproduction. Record
  immutable image/dependency identities; source equality is insufficient.
- **Admin access:** no verified native Supabase MFA factors were observed;
  external IdP MFA was not assessed. Establish strong-auth/recovery ownership
  for platform admins and cloud/provider accounts. Decide whether application
  step-up is required before adding it.
- **Customer scope:** approve onboarding, support contacts/response ownership,
  refunds/cancellation, incident messaging, and deletion procedures. Promise
  supported escalation: the callback tool is not proof of live call transfer.
  Validate each agent's hours/timezone, tools, permissions, and safe failure
  guidance. Confirm recording notice/consent; avoid regulated-data promises
  until the relevant provider/business review is complete.
- **Cost:** verify production model/STT/TTS/telephony funding, quotas, alerts,
  spending limits, and actual billed-minute economics against approved credit
  prices. Cloud budgets, provider budgets, and customer credits differ.
- **Funnel:** sign-in advertises “Sign up for free” while noninvited signup
  redirects to a demo request. Align copy with the launch mode. Keep analytics
  and marketing polish behind security, delivery, calls, and payments.

## Notification acceptance matrix

Use dedicated controlled accounts/destinations. All **live delivery** entries
remain UNVERIFIED until exercised. Store sensitive message/provider identifiers
in the private operational system, not in this document.

| Scenario | Expected destination / behavior | Required proof |
| --- | --- | --- |
| New email signup | User verification; unverified user denied | Receipt, correct public link, expiry/replay, no auto-confirm bypass |
| Resend verification | Same user; throttled safe response | Receipt, no account-existence disclosure |
| Password reset | One usable user recovery link | Existing/nonexistent response parity, expiry/single-use |
| Organization invitation | Invited email, selected org/role | Email match; revoked/expired/replayed token denial; no dummy org |
| Platform lead email | Configured platform recipient | Lead persists during outage; retry after failure; acknowledged channels not resent |
| Platform lead Telegram | Platform bot/chat with opt-in | Actual receipt, correct payload, channel independence |
| Platform signup Telegram | Platform bot/chat | Actual receipt; currently best-effort code without durable signup retry |
| Org OAuth attention email | Admin accounts and optional org inbox | Correct recipients, dedup/retry, no cross-org details |
| Org OAuth attention Telegram | That org's own bot/chat | Independent from platform bot; invalid/removed bot gives recoverable pending work |
| Platform OAuth attention | Platform contacts | Actual receipt and actionable reconnect guidance |
| Low credits | Correct org admins at configured thresholds | Durable delivery; threshold/dedup/reset behavior |
| Payment/subscription event | Correct billed org/user | Correct template; webhook retries do not duplicate business effects |
| Human callback | Agent-configured owner route | Persisted callback and owner receipt; accurate failure response |
| SMS/WhatsApp, if enabled | Approved sender/destination | Required registration/templates/opt-in, actual receipt; otherwise explicitly excluded |
| Authorization | Org A, org B, regular member, platform admin | API and direct DB allow/deny checks; secrets never returned |
| Outage/restart | Only failed channel retried | Invalid credentials, timeouts, 429, provider outage, worker restart; no lost durable event |

Org settings currently govern critical OAuth recovery channels. Saving an org
Telegram bot does not subscribe it to every business event. Define the
event/channel contract before extending it. Low-credit email, callback-owner
email, platform signup Telegram, and org OAuth Telegram have different runtime
boundaries and must be tested separately.

## Whole-platform coverage and remaining signoffs

| Area | Assessed | Still required |
| --- | --- | --- |
| DNS/TLS/site | Browser canonical redirect, HTTPS, pages, robots/sitemap | Independent-region/crawler checks, certificate monitoring, mobile smoke |
| Authentication | Routes, provider settings, verification configuration, tests | Controlled email/OAuth/invite/reset journeys |
| Tenant/RBAC | API test coverage; live table/RPC permissions and policies | R01/R02 plus direct Data API tenant matrix |
| Platform administration | Settings boundaries, release settings, MFA metadata | Admin browser gating and strong-auth/recovery signoff |
| Org onboarding/membership | Source/tests and invitation contracts | Two clean orgs, role denials, active-org switching, founder selection |
| Billing/plans/credits | Stripe account/webhook, ledger code/tests | Approved catalog integration, real payment/refund, ledger reconciliation |
| Notifications/leads | Settings, outbox/failure aggregates, provider probes | Matrix above, bounce/complaint/queue ownership |
| Browser/embed/demo voice | JWT/transports, budgets, tests, deployed source match | Real audio, cross-origin embeds, duration/abuse/failure scenarios |
| PSTN/phone lifecycle | Default account/routing, signatures, lifecycle tests | Paid account, purchase/import/release, real incoming call |
| Tools/MCP/OAuth | Assembly, evals, refresh states, local connector tests | Reconnects, provider approval, real controlled workflow |
| Recordings/transcripts | Storage/deletion authorization, expiry metadata, policies | Real R2 write/read/delete, retention enforcement, consent |
| Database/migrations | Live head alignment, grants/RLS, compatibility | Backup/PITR/control-plane proof, restore, security migration postconditions |
| Deployment/rollback | Workflow, revisions, actual latest job steps | Enforced gates, staged candidate, functional rollback rehearsal |
| Monitoring/background workers | Flags, CPU/min-instance config, host health | App telemetry, alert receipt, worker failure/restart evidence |
| Security/dependencies/privacy | Scans, parsing boundary, headers/logs | Image/OS scan, fixes/triage, log redaction, secret/IAM access review |
| Capacity/cost | Admission/settlement review, idle resources | Isolated load/fault tests, quotas, explicit service limits/unit economics |
| Legal/customer operations | Live publication/acceptance and public claims | Published docs, approved scope/support/deletion/refunds |

Cloud IAM least privilege, historical secret exposure, every provider account's
MFA, backup control-plane settings, and complete production capacity were not
established as passing. This audit is not an independent penetration test,
provider compliance assessment, or legal approval.

### Business-workflow acceptance boundary

The deterministic calendar/callback/lead/email evaluations passed at their
mocked tool boundary. **Integrated production workflow verdict: UNVERIFIED.**
No tool-enabled business behavior was changed in this audit. Before enabling
each launch integration, record its semantic fit, runtime boundary, integrated
and safety evidence, and PASS/FAIL/UNVERIFIED verdict under the repository's
[integration-function acceptance gate](../04_development_guides/testing.md#integration-function-acceptance-gate).

Required release journeys include:

1. Lead → platform alert → invitation → verification/login → correct invited
   org and role → approved plan → funded account.
2. Founder signup → own org provisioning → onboarding completion, with no
   dummy organization or accidental platform role.
3. Agent creation/configuration → approved tool connection → browser call →
   correct business action → finalized log/recording → exactly one usage debit.
4. Phone assignment/import → verified signed incoming webhook → public voice
   socket → audio/action → status callback and billing reconciliation.
5. Org A member/admin and org B denial checks across agents, tools, skills,
   numbers, logs, recordings, billing, notifications, and direct database APIs.
6. Provider/DB failure and restart → safe caller response → durable retry or
   operator action → no duplicate booking, email, payment, debit, or lost lead.

Do not exercise chargeable or customer-visible scenarios until their exact
test account/destination and action have been authorized. Historical calls or
health endpoints cannot replace evidence on the final release candidate.

## Launch sequence and dates

Suggested sequencing; estimates depend on implementation findings and external
approval. Start Google verification, Twilio activation, domain, and backup
checks immediately rather than saving them for the final week.

| Window | Work | Exit gate |
| --- | --- | --- |
| October 19–20 | R01/R02 containment/regression migration; signup boundary; provider/legal checks begin | Exposed objects closed and directly verified; preserve access evidence |
| October 20–22 | Auth/notifications/legal/provider configuration; bot controls; dependencies; release safeguards | Published legal text; controlled auth and notification matrix pass; live account blockers resolved |
| October 22–24 | Admission/accounting recovery; retention; monitoring; restore; OAuth reconnects | Fault/retry/concurrency gates pass; operator receives alerts; restore evidence exists |
| October 24–26 | Full isolated E2E and staging; approved catalog integration; capacity/cost tests | One immutable candidate passes complete agreed customer journey |
| October 26–28 | Approved production release and controlled payment/refund, browser/PSTN, notification gates | Production signoff; first concierge cohort may onboard |
| October 29–31 | Release defects only; repeat affected gates; observe controlled traffic | Stable evidence and staffed launch support |
| November 1 | Launch deadline | Open only the scope that passed; no security/payment bypass |

An earlier launch is reasonable when gates pass. External approvals cannot be
promised for a particular date. A practical initial scope is a small concierge
cohort with verified voice, calendar/approved tools, Resend email, and Telegram
admin alerts. SMS/WhatsApp, unapproved Gmail scopes, regulated workloads, and
complex integrations can be explicitly excluded until ready. Multi-region
voice infrastructure need not become a prerequisite for this bounded launch
if the founder accepts documented capacity/recovery limits.

## Final release record

For the selected release, retain exact SHA/image identities, suite outcomes,
staging signoff, approved catalog version, migration revision, backup/restore
reference, live transaction/refund reconciliation, browser/PSTN outcomes,
recording checks, notification receipts, and the named incident owner. Store
sensitive evidence only in private operational systems.

**Go only when** R01/R02 are closed, affected P1 paths pass acceptance,
unverified launch dependencies have evidence, and remaining P2 risks have a
named owner and explicit launch decision. Never mark these gates green merely
because HTTP health or mocked unit tests pass.
