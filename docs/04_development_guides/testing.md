# Testing Guidelines

Testing is a maintained product surface. A code change is incomplete when
its tests, fixtures, evaluation scenarios, or browser workflows still describe
the old behavior.

## Test layers

| Layer                 | Tools                                        | Purpose                                                                    |
| --------------------- | -------------------------------------------- | -------------------------------------------------------------------------- |
| Unit/component        | pytest, Vitest, React Testing Library, MSW   | Fast deterministic logic and UI coverage                                   |
| API/integration       | pytest with mocked or dedicated dependencies | Route, service, authz, persistence, and provider boundaries                |
| Agent/tool evaluation | evals/, pytest, trace replay                 | Tool contract, ordering, arguments, side effects, and recovery             |
| Browser E2E           | Python Playwright and isolated Docker stack  | Critical user journeys across frontend/backend                             |
| Browser smoke         | Browser automation skill                     | Focused user-perspective validation when UI risk warrants it               |
| Live voice            | Staging browser/PSTN calls                   | Transport, realtime provider, latency, recording, and entitlement behavior |

No layer proves the others. Deterministic tests cannot prove Gemini Live
responsiveness; a successful manual call cannot replace a regression test.

## Change-to-test rules

- New or changed behavior gets a test in the nearest layer and coverage for
  success, validation, failure, and cleanup paths that are relevant.
- New routes and permissions require happy-path, denial, and tenant-isolation
  tests. Never rely on UI hiding to enforce authorization.
- Contract changes update existing assertions first, then implementation and
  dependent callers. Do not weaken an assertion merely to make a suite pass.
- Schema changes add migration compatibility/postcondition coverage and update
  docs/DATABASE_SCHEMA.md.
- Tool or MCP changes add contract tests and a deterministic evaluation
  scenario/trace when model-facing selection, arguments, ordering,
  confirmation, idempotency, or errors can change.
- Realtime tool-schema changes also run the voice-ws schema compatibility tests.
  Gemini Live optional arguments are represented by omission, never by an empty
  string inside an enum; provider validation happens before model audio starts.
- UI changes update component/service tests and the durable E2E journey. Keep
  loading, empty, error, accessibility, and permission states covered.
- Production incidents become redacted replay traces or deterministic
  regression scenarios before the fix is considered complete.

## Integration-function acceptance gate

Use this gate when a change can alter a user-visible business workflow that
uses one or more tools. This includes changes to tool selection, descriptions or
schemas, agent instructions, tool enablement, runtime assembly, provider
adapters, result handling, or provider-side effects. For a docs-only change,
pure refactor, or internal change that cannot affect those boundaries, run the
ordinary checks and record why this gate is not applicable.

This is an agent execution and review contract, not a replacement for unit,
contract, deterministic evaluation, browser, or live-provider checks. A tool can
be contract-compatible and still be the wrong tool for the job. The implementing
agent gathers the evidence; the reviewing agent checks that the evidence matches
the changed boundary and does not infer PASS from missing evidence.

### Agent protocol

Follow these steps for an applicable change:

1. Define the requested use case and map each selected tool to it before
   changing code.
2. Identify the intended entrypoint and runtime, then choose the narrowest
   realistic fixture and stateful provider fake that can prove the behavior.
3. Run the nearest unit, route, contract, and deterministic evaluation tests.
4. Run an integrated trace through the intended configured-agent, API, browser,
   or voice-runtime boundary when that boundary changed.
5. Exercise the relevant no-tool, duplicate/retry, and dependency-unavailable
   paths. Mark a check not applicable only with a concrete reason.
6. Report the evidence and PASS, FAIL, or UNVERIFIED verdict in the PR/task
   response. Link durable artifacts and redact secrets, tokens, PII, and
   sensitive recordings.

### Semantic fit

Before running the integrated trace, map the requested use case to every
selected tool. For each tool, include:

| Required mapping | Evidence to record |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Purpose | What real user need this tool satisfies and why this tool is the intended one |
| Inputs | Realistic values, required/optional fields, accepted values, and the source of each value |
| Outputs | The result shape and how the runtime/user will use it |
| Side effects | Records, messages, external mutations, or other state changes expected |
| Configuration | Agent instructions, enabled tool/function, tenant, permissions, timezone, credential binding/reference (never secret values), and provider settings |

Reject a tool that is only schema- or contract-compatible but semantically
wrong for the requested use case. For example, an HVAC lead-capture tool must
not be reused to take restaurant orders merely because both accept contact
details. A semantic mismatch is a **FAIL**, even when the invocation and unit
tests pass.

### Integrated trace and safety paths

Use a realistic use-case fixture through the intended entrypoint and runtime
(for example, the configured agent surface, API, or voice runtime). The trace
must show all of the following:

- **Selection and invocation:** the user/request context, selected tool, exact
  realistic arguments, and the runtime entrypoint that invoked it.
- **Provider or stateful fake behavior:** the provider request and response, or
  a stateful fake that persists and exposes the relevant reads/writes. A direct
  unit mock or a contract-only schema assertion is not sufficient.
- **Read-back and result handling:** the returned value is read by the runtime,
  mapped to the user-visible/result contract, and errors are classified safely.
- **Expected side effects:** verify the resulting records/state and ownership.
  For a mutating operation, repeat the same request or simulate a timeout and
  prove an idempotent outcome: the same logical result and no duplicate
  committed mutation. Demonstrate the idempotency key, provider lookup, unique
  constraint, or documented reconciliation mechanism. Do not claim exactly-once
  behavior across an external network boundary unless the provider explicitly
  guarantees it.
- **No-tool path:** for a user-facing tool workflow, run a realistic request
  that does not require a tool and verify that no tool is selected, invoked, or
  allowed to create a side effect. Record why this is not applicable for a
  non-conversational or internal workflow.
- **Dependency-unavailable path:** make the provider, stateful fake, or relevant
  dependency unavailable and verify safe, actionable failure handling, no false
  success, no unintended partial/duplicate write, and the documented retry
  classification. If the workflow has no such dependency, record that fact.

If the provider is external, use an authorized non-production provider or the
repository's stateful fake. Live-provider evidence is required when the
release lane or acceptance criteria call for provider-specific behavior; its
absence is **UNVERIFIED**, never PASS by implication. A stateful fake can prove
deterministic application behavior, but it cannot prove provider-specific
behavior that the acceptance criteria require.

### Evidence record and verdict

Evidence must be reproducible by another agent and contain:

| Field | Required content |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Scope | Use case, changed boundary, selected tool(s), acceptance criteria, and semantic-fit map |
| Environment | Branch/commit, environment/config, entrypoint/runtime, tenant, and fixture/seed identifier |
| Commands and trace | Exact commands or user steps; selection, arguments, provider/fake interactions, read-back, and results |
| Side-effect checks | Before/after state, expected records, duplicate/retry result, and no-tool result |
| Failure paths | Dependency-unavailable result, safe error, retry classification, and cleanup outcome |
| Raw evidence | Redacted logs, trace IDs, API responses, and browser/voice artifacts only when relevant; link durable test artifacts |
| Verdict | PASS, FAIL, or UNVERIFIED, with unresolved risks and the next action |

Use these rules:

- **PASS:** semantic fit is accepted, every applicable trace item above is
  evidenced with expected results, and no unresolved acceptance failure remains.
- **FAIL:** the tool is semantically wrong or the observed behavior violates
  the expected invocation, result, side-effect, idempotency, no-tool, or
  dependency-unavailable contract. Record the smallest reproduction and the
  affected boundary.
- **UNVERIFIED:** required applicable evidence is missing, redacted beyond
  reviewability, or could not run. Do not call the change fully verified or
  approve it by implication; list the exact missing check and next action.
- **Not applicable:** allowed only with a concrete reason tied to the changed
  boundary. It must not be used to avoid a relevant safety check.

An AI agent must not silently waive an UNVERIFIED check. If task constraints
prevent the check, report that limitation and leave the release or scope
decision explicit for the next authorized owner.

### Reviewing-agent checklist

The reviewing agent should:

- classify whether the gate applies and challenge an unsupported exemption;
- compare the semantic-fit map with the actual tool schema, instructions,
  registration, permissions, tenant, and runtime wiring;
- confirm that tests and traces exercise the changed boundary, not only a
  lower-level adapter or direct unit mock;
- verify side effects, idempotent retry behavior, no-tool behavior, and
  dependency-unavailable handling when applicable; and
- return FAIL or UNVERIFIED with a concrete missing check or reproduction.

### Copyable issue-description blocks

An implementing agent can include this compact record in its task or PR:

```markdown
## Integration-function acceptance gate

Follow [the canonical gate](https://github.com/gauravdhiman/a1-voice-agent-platform/blob/main/docs/04_development_guides/testing.md#integration-function-acceptance-gate).

- Gate applicability and changed boundary:
- Use case and acceptance criteria:
- Selected tool(s) and semantic-fit map (purpose, inputs, outputs, side effects, configuration):
- Environment/branch/commit and entrypoint/runtime:
- Agent/tenant/permission/timezone/provider configuration (credential reference only; no secret values):
- Realistic fixture/seed and test account (no secrets or PII):
- Exact commands or user steps:
- Selection/invocation and realistic arguments:
- Provider or stateful-fake behavior and read-back/result handling:
- Expected side effects and idempotent duplicate/retry result:
- No-tool path and result, or reason not applicable:
- Dependency-unavailable path, safe error, and retry classification, or reason not applicable:
- Redacted logs/traces and relevant artifacts:
- Verdict (PASS / FAIL / UNVERIFIED):
- Missing evidence, defect, or next action:

Direct unit or contract mocks alone do not satisfy this gate.
```

A reviewing agent can use this checklist in its review:

```markdown
## Review: integration-function acceptance gate

Review [the canonical gate](https://github.com/gauravdhiman/a1-voice-agent-platform/blob/main/docs/04_development_guides/testing.md#integration-function-acceptance-gate)
and the implementation evidence before approval.

- Does the gate apply, and is the changed boundary identified?
- Is the requested use case mapped to each tool's purpose, inputs, outputs,
  side effects, and configuration? Reject contract-compatible semantic mismatch.
- Does the trace use the intended entrypoint/runtime and a realistic fixture?
- Are selection, realistic arguments, provider/stateful-fake behavior,
  read-back/result handling, side effects, and idempotent duplicate/retry
  behavior evidenced?
- Are the no-tool and dependency-unavailable paths evidenced or explicitly
  justified as not applicable?
- Are commands, environment/commit, fixture, redacted raw evidence, and verdict
  reproducible?
- Review verdict: APPROVE / REQUEST CHANGES / UNVERIFIED.
- If evidence fails, identify the missing evidence or defect and next action;
  do not approve by implication.
```

## Public agent and demo-page coverage

The homepage has separate contracts in `frontend/src/app/__tests__/landing-page.test.tsx`
and `frontend/src/components/home/particle-field.test.tsx`. They cover public entry
points, theme persistence and unavailable storage, navigation, and animation
cleanup/reduced motion. `e2e/tests/test_homepage_experience.py` verifies desktop and
mobile navigation, theme persistence, the demo-request route, and overflow.
Visually review the scroll formations in both themes; see the
[homepage experience](../02_features/homepage-experience.md).

The public-agent surface must be covered across the same boundaries used in
production:

| Layer                | Required coverage                                                                                                           |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Shared model/service | Defaults, slug validation, published filtering, uniqueness, and enable/disable transitions                                  |
| Backend routes       | Public organization access/list/token endpoints, demo metadata/token endpoints, platform-admin-only writes, and safe errors |
| Frontend services    | Public metadata, access-token, call-token, and error contracts                                                              |
| Browser E2E          | Open/protected organization pages, public demo page, visualizer defaults/selection, and dashboard controls                  |

The durable browser scenarios are in
[`e2e/tests/test_public_agent_pages.py`](../../e2e/tests/test_public_agent_pages.py)
and use boundary mocks while the runner builds the real application stack and
applies migrations.

Prefer red-green-refactor: prove the new test fails for the intended reason,
implement the smallest fix, then refactor while tests remain green. Use
meaningful branch coverage; new/changed logic should be directly covered. If a
branch cannot be tested, record the reason and follow-up.

## Commands

From the repository root:

```bash
pytest -q
pytest backend/tests/path/to/test_file.py -q
pytest -m 'not slow' -q

pytest backend/tests/evals -q
python scripts/run-agent-evals.py
python scripts/run-agent-evals.py --json-out /tmp/agent-evals.json
```

For frontend tests and checks:

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run test:run -- src/path/to/test.test.tsx
npm run test:coverage
```

The frontend test runner is Vitest 4, not Jest. Vitest requires Node 20+ and
should run on the host when the development container has incompatible
dependencies. Report pre-existing typecheck failures separately; do not hide
new source errors behind a blanket ignore.

## Isolated browser E2E

Run the full disposable lifecycle:

```bash
./scripts/run-e2e.sh
./scripts/run-e2e.sh --video-on
./scripts/run-e2e.sh -- -k 'billing_flow or phone_number_management_smoke or platform_plan_catalog_smoke' -x -vv
```

Arguments after `--` are passed to pytest, which supports selecting focused
scenarios without changing the disposable stack lifecycle.

The runner builds docker-compose.e2e.yml, applies the test schema and
migrations, runs Python Playwright tests against ports 3001/8001, stores the
HTML report under e2e/reports, and tears down only its named transient stack.
Its database is disposable PostgreSQL and its Supabase URL uses the reserved
`.invalid` domain because the browser suite mocks Supabase auth at the network
boundary. The runner waits for backend liveness; dependency-aware `/health`
would fail because this stack intentionally has no Supabase REST service. Do
not copy its down -v cleanup to persistent local Supabase or worktree stacks.

Use the `agent-browser`/browser automation skill for focused UI smoke checks.
Extend existing
durable E2E coverage instead of writing a throwaway Playwright script for each
task. Smoke-created rows, roles, files, screenshots, videos, downloads, and
temporary scripts must be removed before handoff.

Browser fixtures must mirror current API contracts, including dashboard
analytics arrays, tool definitions, and skill file summaries. Open edit controls
before asserting editable fields, and assert actual rendered content instead of
allowing loading, denied, or fallback states to pass.

Run the separate real-auth role suite against the isolated worktree URL printed
by its launcher; these five tests deliberately skip in the mocked E2E stack:

```bash
E2E_REAL_AUTH=1 E2E_BASE_URL=http://localhost:WORKTREE_PORT PYTHONPATH=e2e/tests \
  pytest e2e/tests/test_role_dashboard.py -q
```

For credit-catalog changes, cover the approved amounts/prices, reconciliation
failures, and atomic RPC validation and rollback. Component and billing-flow
tests must verify all four cards, call-minute rates, savings, unavailable
top-up states, and checkout failure recovery. A mocked browser checkout does
not prove Stripe settlement: separately verify a test-mode payment and signed
webhook handling, including duplicate-event delivery and unchanged historical
credit balances. Report changed-module coverage explicitly; a focused suite's
percentage is not repository-wide coverage.

The real PostgreSQL regression suite is
`backend/tests/integration/test_credit_product_catalog_database.py`. Set
`CREDIT_CATALOG_TEST_DATABASE_URL` privately to the selected worktree's isolated
loopback database URL, then run from the worktree root:

```bash
pytest backend/tests/integration/test_credit_product_catalog_database.py -q
```

The suite rejects remote hosts and skips when the variable is unset. A loopback
host alone does not prove isolation: confirm the database belongs to the
selected worktree before running. Each test rolls back catalog fixture rows,
RPC replacement, and role changes without changing Alembic revision state.
It exercises invalid payloads, upsert failure rollback, role denial, repeated
sync, and the downgrade contract against PostgreSQL. Report skipped SQL tests
as unverified. Credit-card component coverage must also include changed,
missing, inactive, invalid, and zero-cost voice pricing; a default-rate-only
test does not establish accurate minute estimates.

## Agent evaluation

The deterministic suite in evals/ is the PR regression layer. It uses fake or
stateful test providers and does not require real OAuth, calendar writes, or
paid realtime calls. See agent-evaluations.md for scenario and trace formats.

Model-backed and live-provider checks belong in staging/nightly/manual lanes.
Record the model/provider, prompt and tool-schema hashes, git SHA, latency,
tool sequence, arguments, results, and failure classification so regressions
can be compared without treating an external outage as an application bug.

## Release validation

Before production promotion, follow the mandatory browser and PSTN gate in
docs/05_operations/deployment/runbook.md. Health endpoints alone are
insufficient: inspect backend and voice-ws logs, verify call audio and call
finalization, and block on authentication, entitlement, concurrency, or
WebSocket failures.

## Observability regression gates

The [operator guide](../05_operations/observability.md#validation-commands) lists
the signal privacy/concurrency suite, 90% feature coverage gate, pinned Pipecat
observer tests, Prometheus alert firing/recovery tests and real OTLP smoke check.
Run backend and voice suites separately because both own a `src` package.
The `Observability contracts` workflow enforces separate 90% statement and branch floors
and alert-rule cases on pull requests and main. Other affected suites still need
local validation; this gate does not claim 90% coverage of the entire platform.
