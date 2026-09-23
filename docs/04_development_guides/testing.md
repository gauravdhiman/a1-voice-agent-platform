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
```

The runner builds docker-compose.e2e.yml, applies the test schema and
migrations, runs Python Playwright tests against ports 3001/8001, stores the
HTML report under e2e/reports, and tears down only its named transient stack.
Do not copy its down -v cleanup to persistent local Supabase or worktree
stacks.

Use the `agent-browser`/browser automation skill for focused UI smoke checks.
Extend existing
durable E2E coverage instead of writing a throwaway Playwright script for each
task. Smoke-created rows, roles, files, screenshots, videos, downloads, and
temporary scripts must be removed before handoff.

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
