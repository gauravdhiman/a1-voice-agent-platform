# Production readiness remediation — October 19, 2026

This branch prepares fixes; it does **not** establish that production is ready.
No production/staging migration, deployment, paid call, payment or notification
was performed. Worktree: `.worktrees/codex-production-readiness-fixes`, branch
`codex/production-readiness-fixes`, based on main commit `5eef740f`.
The [original audit](production-readiness-2026-10-19.md) preserves the observed
production state. Approved plan/catalog changes remain in the separate workstream.

## Launch scope correction: a small customer pilot

The original register mixes confirmed defects, missing evidence and later
hardening. Its full completion is **not** a requirement for the first customer.
The founder has explicitly chosen a decent, controlled initial launch over
enterprise completeness. Keep the implemented fixes; defer work that does not
protect customer data, correct charging or the core journey being sold.

For the pilot, require protection of private data and privileged actions, a
working onboarding/call journey for the offered channel, correct payment and
usage accounting when charging, and the basic customer-facing policies and
recovery coverage appropriate to the data collected. Validate only integrations
used by the first customers. Public self-service needs stronger abuse controls
than a manually onboarded pilot with known customers and restricted access.

Advanced telemetry, large-scale load testing, a formal restore rehearsal,
additional image pinning, async-path optimization and enterprise GitHub approval
controls can follow the pilot unless a concrete failure makes one necessary.
Confirm basic backups and keep manual error/usage checks; deferring a formal
exercise does not mean accepting unprotected customer data or unlimited spend.

**First task: deploy and verify the prepared database access fix.** The audit
found direct client access that bypasses application permissions. This is a
real security defect, independent of customer count. The implementation and
isolated regression evidence are ready. Release it through the repository's
authorized Git/staging/production process, then verify live access restrictions
read-only and smoke-test the affected application flows. Do not ask the founder
to edit permissions manually in the database dashboard.

A same-day read-only recheck after this scope correction confirmed production
is still at revision `20261012000001`, with 17 public tables lacking RLS,
116 unsafe client-role/table grant combinations, six unsafe privileged-RPC
role grants and two private agent publication members. These are metadata
counts, not customer record reads or evidence of exploitation. The live
permissions therefore remain the first task; this is not a hypothetical risk.

## Prepared implementation

| Audit items | Change | Launch closure still required |
| --- | --- | --- |
| R01–R02 | Revoke client table/sequence/RPC grants and global/schema defaults, enable RLS, replace private Realtime feeds with tenant-scoped IDs, add a read-only security release gate | Review/apply coordinated migrations and frontend/backend/voice release; repeat direct Data API checks in staging/production |
| R04–R05 | Require production email verification independently of sender completeness; add platform and org saved-destination email/Telegram tests with backend role/tenant enforcement and safe provider errors | Configure sender/destinations; prove domain verification and actual receipts for both roles |
| R11 | Share HTTP quotas through backend Redis, protect Redis URL as a managed secret, clear copied Redis settings in isolated worktrees | Provision authenticated TLS Redis and Turnstile widget/keys; prove distributed limits and challenge behavior in deployed environments |
| R12 | Patch Python runtime/migration dependencies, Next/sharp, vulnerable transitive frontend packages and OpenTelemetry SDK; patch pytest/Black; bound Twilio URL-encoded parsing and reject unsigned/multipart/oversized traffic before parsing | Rebuild/deploy all runtimes; retain scans with the release SHA |
| R13/R20 | Broad application CI, real migration/concurrency fixtures, immutable-main promotion with successful exact-SHA checks, Data API postcondition gate, fail release when voice SSH config is missing; repair stale tests and runtime test-package isolation | Enable account-level protection/reviewers; successful CI and staging evidence for the integrated SHA |
| R14–R15 | Fail closed before provider startup if tracking fails; atomic slot admission and single-use sessions; worker leases/crash recovery; durable pending settlement with atomic ledger linkage and concurrent retry safety | Drain before rollout; run browser/PSTN faults and live accounting checks; choose normal-call duration cap |
| R16 | Deny expired playback/links/availability; bounded idempotent deletion with audited tombstones and retry; expiry index | Verify private bucket policy, lifecycle/backups and actual cleanup on deployed storage |
| R18 | Content-free console handlers even with OTLP disabled, including safe Uvicorn access formatting; retain only allowlisted events/fields | Inspect deployed logs and verify the chosen operational alerts still contain useful safe signals |
| R21 | HSTS, nosniff, referrer/permissions policy and CSP framing/object/base restrictions; preserve microphone access and call iframes | Verify deployed headers and customer embed/audio/OAuth flows |
| R22/R24 | Move Stripe SDK, JWT/JWKS verification and entitlement reads off the event loop; bounded Stripe timeout; pin compatible Node 22 Docker manifest and use lockfile installs | Other async database paths and production capacity/probes remain operational validation work |

Changes are regression-tested in isolated environments. Detailed final results
are recorded below; passing deterministic tests does not prove live provider
availability, voice latency, external delivery or production account settings.

## Release procedure and compatibility

1. Review and integrate this branch through the authorized Git workflow. Recheck
   against main and the separate plan/catalog work; preserve one Alembic head.
   Do not promote this uncommitted worktree or a moving branch.
2. Drain active voice sessions. Migrations `20261019000001` through
   `20261019000005` change the browser feed, admission RPCs and recovery contract.
   Deploy backend, frontend and voice-ws from the same reviewed SHA. The old
   browser's private subscriptions intentionally stop after lockdown.
3. After explicit release ownership/approval, run the documented staging
   validator, then `python scripts/deploy/verify_data_api_security.py --env-file
   .env.staging`. The validator now includes this read-only guard.
4. Run the staging release journey: invitation/verification, founder onboarding,
   tenant-denial matrix, browser audio, PSTN ingress/audio, recordings, billing,
   notification probes/receipt, credit limits and provider failure/recovery.
5. Promote only the exact main SHA whose application and agent workflows passed
   and whose staging evidence has been reviewed. Missing voice SSH configuration
   fails promotion. Repeat release-critical production checks before onboarding.

The security/financial migrations intentionally refuse unsafe downgrade. Keep
source images/configuration and a reviewed database recovery plan. A rollback
must not restore exposed grants, lose queued settlement or replay consumed
sessions; use a reviewed forward repair. Historical `billing_status=legacy`
calls are not automatically charged. Newly tracked calls become `pending` and
settle only from their persisted authoritative data.

The 90-second voice lease renews every 20 seconds. A renewal error/timeout stops
provider work rather than allowing an untracked call to continue. Crash recovery
uses last confirmed activity and retains the existing minimum-minute policy;
it does not bill the unknown outage interval. Pricing is resolved when settlement
runs, and any already-existing ledger debit retains its original amount.

Recording cleanup uses the stored per-artifact expiry, deletes objects before
metadata, and retries idempotently after failures. Null legacy expiry dates are
unchanged. Deployed cleanup requires the backend scheduler to be running and
private storage credentials with delete permission.

## Reference backlog — schedule only what the pilot needs

This is a reference list, not the next-cycle task list. Work one item at a time,
starting with database access containment. Some items require account access;
others are engineering follow-ups that the agent should handle independently.

| Priority | Needed action | Evidence to finish |
| --- | --- | --- |
| Next | Authorize the reviewed integration/release operations once checks pass | Exact approved SHA, staging owner, protected production approval |
| Before exposing signup | Align invitation-only policy and Supabase Auth, including email and new OAuth users | A fresh uninvited direct Auth signup is denied while a valid invited email/OAuth signup works. Do not blindly disable all signup and break invited OAuth registration; use a verified server-side Auth boundary. |
| Before email-dependent onboarding | Verify the sending domain in Resend, complete DNS/sender settings and save platform alert recipient plus verification From email/name | Actual verification email and platform/org test email received; provider dashboard confirms accepted/delivered state; domain API access or dashboard evidence |
| When used by the pilot | Save/enable platform Telegram bot+chat; save organization bot+chat and shared email inbox | Platform and org Telegram tests received; wrong/missing credentials produce actionable failure, never a success claim |
| Before offering PSTN | Upgrade/approve the production Twilio account and number route | Actual PSTN call reaches production webhook and `/twilio`, returns audio and completes one accounted call log |
| Before charging | Complete Stripe live activation in the separate billing workstream | Approved plans and prices in staging/production; live webhook, successful payment, failed payment, replay/idempotency and portal checks |
| Before customer onboarding | Approve and publish Terms/Privacy versions and support identity/contact | Public documents load, signup acceptance persists, customer promises match product behavior |
| Before public self-service | Provision TLS Redis and Turnstile keys/widget; opt REDIS_URL into managed deployment config | Two deployed instances share one quota; bot challenge validates server-side and denies invalid tokens |
| Later; manual checks for pilot | Choose telemetry backend credentials, enable application export and own actionable alert destinations | A synthetic service/voice/provider/queue failure is visible and the alert is received |
| Basic backups before customer data; drill later | Confirm backup/PITR coverage and schedule an isolated restore drill | Verified backup coverage initially; timestamped restore/application results and recovery expectations in the later drill |
| Later; retain manual review | Configure GitHub environment reviewers and main protection (may require an account-plan change) | Wrong/no approvals and failing/missing required checks demonstrably block promotion |
| Before sale | Reauthorize affected Google tool connections and resolve OAuth app approval/restricted-scope requirements | Approved tenant completes the intended Calendar/Gmail/CRM workflow without unverified-app blockers |
| Small limits now; scale testing later | Set supported pilot concurrency, bound spending and keep support promises modest | Known customer/usage limits, practical cost controls and an owner; validate wider capacity before selling it |
| Before offering the affected journey | Run controlled production acceptance with a synthetic test organization | Only the offered browser/PSTN journey, credits, required notifications, storage, legal acceptance and payment paths need initial live evidence |

## Explicit residual engineering/validation work

- Complete the invitation-only Supabase Auth boundary against the selected launch
  policy; backend invite checks alone do not contain direct provider signup.
- Remaining synchronous database operations need measured event-loop/load review.
  This branch removes identified Stripe/JWKS/entitlement blocking, not every
  synchronous Supabase call in the platform.
- Normal-call duration caps need an approved policy; active-credit overdraft is
  intentionally unchanged. Validate burst capacity and worker recovery on the
  production-sized VM before promising concurrency or an uptime SLA.
- Pin/review the remaining mutable runtime images and dependency ranges and add
  application liveness/readiness probes appropriate to production topology.
- Browser telemetry is disabled in the audited deployment. Enabling it requires
  reviewing browser log/span content and endpoint access separately from the
  server-side content-free log fixes.
- The final frontend production dependency scan has zero findings. The full npm
  development scan still flags the braces 3.0.3 build/test glob chain; npm's
  registry has no patched braces release at this check. Do not downgrade Next
  or force incompatible replacements merely to hide it. CI consumes trusted
  repository glob patterns; reassess when upstream publishes a fix.
- The copied audit/evidence describe the pre-remediation production deployment;
  they must never be relabeled as proof these local fixes are live.

## Validation record

Validated on October 19, 2026, in this worktree; no shared staging or production
database was used for mutation.

| Check | Result and boundary |
| --- | --- |
| Backend, shared and deployment Python suites | **2,650 passed, 57 skipped**; includes real shared-Redis quota checks. Optional provider/database lanes do not become PASS from a skip. |
| Voice runtime suite | **145 passed**, in its separate Python environment with the patched pytest/asyncio dependencies |
| Frontend suite | **209 files / 1,296 tests passed** |
| Fresh PostgreSQL migration/security tests | **6 passed** against the preceding schema; all five new migrations then applied to head `20261019000005`; all five read-only security violation counts were zero |
| Real SQL financial/admission tests | **11 passed** against the final migration chain, including concurrent debit/admission, replay rejection, rollback, leases and recovery |
| Deterministic agent evaluations | **34/34 passed**, across Calendar, callback, lead capture and Resend; no live provider delivery/latency claim |
| Notification browser regression | **1 Playwright journey passed** for organization settings, saved reload, email/Telegram test requests and mobile layout; Auth/API/provider boundaries were mocked |
| Interactive browser smoke | Signed into the isolated stack as platform admin and exercised the saved-destination validation error; no external notification was sent. Actual provider acceptance and receipt remain UNVERIFIED. |
| TypeScript / frontend lint | Typecheck passed; lint had **zero errors and 14 existing warnings** |
| Production frontend builds | Host Next build and clean Docker production build passed; built image runs **Node 22.23.3** |
| Dependency audit | Installed backend environment, including development dependencies: **zero known advisories**. Frontend production dependency graph: **zero findings**; full development graph retains the upstream braces advisory described above. This is not a complete deployed OS/image vulnerability attestation. |
| Changed Python formatting/lint | Black, isort and Flake8 passed for **51 changed Python files** |
| Isolated worktree launcher | Shell configuration regression suite passed, including clearing a copied external Redis URL |
| Repository/document checks | `git diff --check`, changed Python AST/YAML/JSON, shell syntax and changed Markdown relative links passed; updated database Mermaid diagram parsed successfully; no added credentials matched the checked token/private-key patterns |

The repository-wide non-mutating pre-commit check remains **not green** because
of existing Flake8 violations, a video script syntax error caught by the
debug-statement hook, and JSONC skill templates checked as JSON. Mutating
formatters ran only on changed files, preserving unrelated
code. Those baseline failures and the warnings above remain visible; the new
application CI workflow has been validated locally but has not yet run on GitHub
for an integrated commit.

The worktree application/Supabase stack was stopped with its data preserved.
The two separately labeled disposable PostgreSQL/Redis test containers and their
temporary storage were removed. Browser test sessions were closed. Source
changes were validated before publication; the branch and pull request record
the subsequent commit/review status. No shared-environment migration or
deployment has been performed. Launch status remains
**NO-GO** while the confirmed database access exposure remains uncontained.
After containment, assess the small-pilot criteria above against the offered
customer journey; the entire hardening backlog is not a launch gate.
