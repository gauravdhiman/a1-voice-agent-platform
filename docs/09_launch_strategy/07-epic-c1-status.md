# Epic C1 Status — Pilot Billing Path (no money moves) (`codex/pricing-package`)

**Base:** `origin/codex/controlled-saas-launch` @ `d8b47c0` → target same.
**Scope discipline:** runbook + plan-card copy + publish spec ONLY.
Deliberately no `plan_versions` rows, Stripe products, migrations, or
engine changes (real money requires founder approval — see `06`).

## What shipped

- `05-pilot-billing-runbook.md`: test→live product/link setup, per-pilot
  duplicate-link + `metadata.organization_id` procedure, stay-on-call
  verification, failure table (delayed webhook, double charge, downgrade,
  custom invoice), never-do list.
- `06-plan-publish-spec.md`: exact Starter/Growth/Scale v1 rows, margin
  math (honest: misses the 70% floor at $0.10 COGS — publish review must
  raise prices, trim bundles, or prove pipeline COGS), publish checklist.
- Plan selector shows minutes-equivalence
  ("400 call minutes included (≈114 calls)") via exported
  `CREDITS_PER_VOICE_MINUTE` / `AVG_CALL_MINUTES`; engine untouched.

## Verification

| Layer | Result |
|---|---|
| `step-plan-selection.test.tsx` (4 existing + 1 new) | 5/5 pass |
| tsc / ESLint on touched files | clean (file's older jest-dom hits pre-existing) |

## Deferred to founder approval (Epic C2)

Catalog publish via Plan Catalog admin (`new_signups_only`), Stripe
live products, staging checkout→webhook→grant gate. The spec's margin
table is the decision input — do not publish without recomputing from
measured pilot COGS.
