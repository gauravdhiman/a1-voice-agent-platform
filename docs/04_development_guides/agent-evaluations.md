# Agent Evaluation System

## Purpose

The platform needs a repeatable way to determine whether a change improves or
regresses the complete agent experience. Manual voice calls remain useful for
final product validation, but they are too slow, expensive, and provider
dependent to be the primary regression strategy.

The evaluation system therefore separates four questions:

1. Does the underlying tool implement its contract correctly?
2. Does the tool runtime expose valid schemas, invoke the right function, and
   return failures safely?
3. Does the model choose the right tool and arguments for a conversation?
4. Does the live voice provider remain responsive under real transport and
   model conditions?

No single test can answer all four questions. A green deterministic suite is a
strong signal for the first two, but it is not evidence that Gemini Live, STT,
TTS, network latency, or a particular prompt will always behave correctly.

## Current implementation

The repository now contains a reusable evaluation core in `evals/`:

- `evals/core.py` runs ordered, isolated tool workflows and supports captured
  values such as `${booking.appointment.id}`.
- `evals/trace.py` evaluates model/tool traces for tool ordering, timezone-aware
  datetime arguments, supplied tool-schema types/required fields, missing tool
  results, fabricated success claims, and actionable error payloads.
- `evals/calendar.py` is the first adapter. It runs the real shared Google
  Calendar appointment service against a stateful fake Google HTTP API, so it
  never needs OAuth credentials or writes to a real calendar.
- `evals/resend.py` exercises the native Resend route catalog and send contract
  against a fake provider, including privacy, configuration, partial delivery,
  timeout, validation, and retry behavior.
- `scripts/run-agent-evals.py` produces a human summary and an optional JSON
  artifact suitable for CI and trend comparison.

The core is intentionally not Calendar-specific. A future tool suite should
provide an adapter implementing `invoke(tool_name, arguments)` and scenarios
using the same `EvalScenario`/`EvalStep` contract. The adapter must count
provider-side writes so confirmation and conflict cases can assert that no
mutation occurred.

## Running evaluations

Run the deterministic suite from the repository root:

```bash
python scripts/run-agent-evals.py
```

Run one deterministic tool suite while developing:

```bash
python scripts/run-agent-evals.py --suite calendar
python scripts/run-agent-evals.py --suite resend
```

Write a machine-readable report:

```bash
python scripts/run-agent-evals.py --json-out /tmp/agent-evals.json
```

Run the unit tests for the runner and deterministic adapters:

```bash
pytest backend/tests/evals -q
```

Evaluate a captured model trace without calling a model:

```bash
python scripts/run-agent-evals.py --trace path/to/trace.json
```

The trace format is an object containing `scenario_id` and ordered `events`.
Events use `type` values `user`, `assistant`, `tool_call`, and `tool_result`.
Scenarios may additionally specify `expected_tool_sequence` and
`forbidden_tools`. A trace may include the actual `tool_schemas` map used for
the run; when present, required fields and primitive argument types are checked
against it. A provider/model integration should emit this format after each run
so the same checks can be used in CI, offline replay, and incident analysis.

## What the Calendar suite covers

The initial suite includes 16 critical workflows:

- availability windows and duration-aware free starts;
- explicit rejection of naive datetimes;
- actionable timezone correction details;
- confirmation gates for create and cancel;
- last-second conflict rechecks;
- create followed by update using the returned appointment id;
- idempotent retry of a create request without duplicate events;
- lookup by time window and caller detail;
- email/detail updates without incorrectly calling availability;
- confirmation gating for existing-appointment updates;
- extending an appointment without conflicting with its own old interval;
- moving onto another event;
- past-time and invalid-duration validation;
- provider outage mapping; and
- successful cancellation.

The Resend suite adds seven workflows:

- route discovery without recipient addresses;
- configured-route fan-out;
- raw-recipient rejection;
- explicit missing-provider configuration;
- partial delivery reporting;
- invalid subject rejection; and
- timeout classification as retryable.

The scenarios intentionally assert outcomes and side effects rather than exact
natural-language wording. This keeps the fast suite stable while still proving
that the model-facing contract is safe.

## Error contract

Every tool error that can be recovered from should expose:

- a stable top-level `code` and concise `message` for compatibility;
- an `error` object with the same code/message;
- `next_action`, describing whether the model should correct arguments, ask for
  a detail, reauthorize, choose another time, or retry later;
- `retryable`, distinguishing a safe provider retry from a request that must be
  corrected first; and
- `field`, `expected_format`, and `hint` when a particular argument is wrong.

For example, a naive `start_time` is not just rejected. The result identifies
`start_time`, says that an ISO 8601 datetime with a numeric UTC offset is
required, and gives an offset-bearing example. The trace evaluator treats a
bare provider error as a contract failure because a model cannot reliably
recover from it.

## Evaluation layers and CI policy

The recommended lanes are:

### Pull request gate

- schema and tool contract tests;
- deterministic tool workflow evaluations;
- trace-contract tests; and
- no real OAuth, calendar writes, or paid realtime model calls.

This lane should be fast, deterministic, and required for merge.

### Main/staging validation

- the same deterministic suite against the merged artifact;
- pinned-model text/tool-selection evaluations using scenario prompts and fake
  tools;
- replay of a small redacted corpus of known production failures; and
- staging smoke tests for authentication, recording, and one end-to-end call.

Model-backed tests should record the model name/version, prompt hash, tool-schema
hash, scenario id, git SHA, latency, tool sequence, arguments, results, and
failure reason. The model is not the sole oracle: deterministic side-effect and
contract assertions remain authoritative, while a judge is limited to language
quality and intent criteria.

### Nightly/manual live lane

- Gemini Live or other realtime provider calls;
- STT/LLM/TTS calls;
- latency, silence, interruption, reconnect, and recording checks; and
- provider quota/availability diagnostics.

These tests are valuable but should be quarantined from the PR gate because an
external model outage must not look like an application regression. They should
still fail loudly, retain artifacts, and be compared against historical
baselines.

## Regression policy

Each report must be attributable to a code revision and configuration snapshot.
At minimum, retain:

- git SHA;
- scenario id and suite version;
- prompt and tool-schema hashes for model-backed runs;
- model/provider identifier;
- deterministic result and side-effect assertions; and
- latency and error classification where available.

A change should not be accepted merely because its new scenario passes. The
full suite must pass, no critical scenario may regress, and any non-critical
score drop must be visible in the report for review. New production incidents
should be added as replayable redacted traces or deterministic scenarios before
the corresponding fix is considered complete.

## Known limits

The deterministic suite cannot prove that a live model will select
`update_appointment` rather than `check_availability`, or that Gemini Live will
not stall after a tool result. Those require model-backed trace generation and
live transport tests. The reusable trace evaluator is the boundary for adding
those lanes without changing the core scenario assertions.
