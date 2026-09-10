# Epic D Status — Soft Escalation + Owner Value (`codex/owner-value`)

**Base:** `origin/codex/controlled-saas-launch` @ `8a06c16` → target same.
**Scope:** soft escalation end-to-end (tool → runtime hook → API →
dashboard) + deterministic eval coverage. No PSTN transfer, no SMS
transport, no outcome summaries (tracked in `03-deferred-and-followups.md`).

## Design (explicit orchestration boundary, per repo invariants)

- `Callback_request` tool owns ONE side effect: owner email via its own
  attachment config, using the shared Resend provider library directly.
  It never invokes another registered tool.
- Persistence is deterministic and model-free: the voice runtime adapter
  calls `record_callback_tool_outcome` next to the demo-outcome hook;
  production accepted results insert `callback_escalations` rows.
  Demos are skipped (shared neutral org; receipts cover demos).
- Dashboard (`/callbacks`) + org-scoped API drive new → acknowledged →
  resolved; cross-tenant writes blocked by id+org matching.

## What shipped

- Migration `20260904000001` (`callback_escalations`, RLS service-role).
- `shared/voice_agents/callback_service.py` + runtime hook in
  `voice-ws/src/tools/assembly.py` (success + exception paths).
- `CallbackRequestTool` (E.164 validation, spell-back contract, urgent
  gating, idempotent sends, stable error shape).
- `backend/src/escalations/` (org-member list, org-admin create/patch).
- `evals/callback.py` (7 scenarios) + CLI `--suite callback` + pytest gate.
- Frontend `callback-service.ts`, `useEscalations`, `/callbacks` page.
- Docs: `DATABASE_SCHEMA.md` (table + history 81 + ER), backend README,
  deferred tracker.

## Verification

| Layer | Result |
|---|---|
| Backend new (routes 7 + service 5 + tool 6 + eval gate 1) | 19 pass; +19 with resend/demo/lead neighbors (35/35 incl. eval CLI 7/7 PASS) |
| Frontend new (service 4 + page 3) | 7/7 pass |
| tsc / ESLint / flake8 / black on touched files | clean (remaining repo hits proven pre-existing) |
| Migration | single head, SQL rendered + verified |
| E2E full stack | 69 pass, 1 fail — same pre-existing skills `.prose` failure (proven on clean baseline); new callbacks test green after making the list mock stateful across the mutation refetch |

## Known limitations

- Owner notify is email-only; SMS transport is Phase 2.
- `record_callback_tool_outcome` cannot be live-call verified on the host
  (Pipecat tests need the runtime container); covered by unit contract +
  staging PSTN gate before any pilot SLA.
