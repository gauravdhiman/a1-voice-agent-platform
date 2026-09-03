# Plan Publish Spec — Starter / Growth / Scale v1 (Epic C2 input)

> ⛔ **REQUIRES FOUNDER APPROVAL — DO NOT APPLY.** No `plan_versions`
> rows, Stripe Products/Prices, or migrations in this change. This spec is
> the exact review packet for the publish decision after pilot COGS are
> measured. Publishing path: Plan Catalog admin (reviewed) with migration
> mode `new_signups_only`; never ad-hoc seeds.

## Design constraints (locked)

- Metering engine untouched: `ceil(min) × 10 credits/min`, settle order
  plan → bonus → purchased.
- Minutes in marketing, credits inside: bundles convert at 10 cr/min.
- Margin floor ≥70% at 60–70% bundle utilization; COGS assumption
  $0.10/min (revisit with measured pilot data before publishing).
- Phone rentals at system rate on top (local incl. per tier, extras +$5).

## Proposed catalog (monthly, USD)

| Tier | Price | Credits | ≈Minutes | ≈Calls¹ | Agents | Seats | Numbers² | Concurrent |
|---|---|---|---|---|---|---|---|---|
| Trial (free, keep current) | $0 | 100 recurring | 10 | ~3 | 1 | 1 | 0³ | 1 |
| Starter | $79 ($63 annual) | 4,000 | 400 | ~115 | 1 | 3 | 1 local | 1 |
| Growth | $179 ($143 annual) | 12,000 | 1,200 | ~340 | 3 | 5 | 2 local | 2 |
| Scale | $399 ($319 annual) | 32,000 | 3,200 | ~915 | 5 | 10 | 3 local | 3 |

¹ At 3.5 min avg call. ² Extra local +$5/mo, toll-free +$8/mo (manual until
metered). ³ Trial uses a shared demo path, not a rented number.

Feature flags: `credit_topup_enabled=true` all paid tiers;
`embed_widget=true` all; `custom_branding` Growth+; `premium_tools`
Scale only (define list at publish review).

## Margin check (to redo with measured COGS before approval)

| Tier | Revenue | 70% use → COGS@0.10 | Margin |
|---|---|---|---|
| Starter | $79 | 280 min → $28 | 65% ⚠️ (raise to $89 or trim to 350 min if COGS ≥ $0.10) |
| Growth | $179 | 840 min → $84 | 53% ⚠️ (same lever) |
| Scale | $399 | 2240 min → $224 | 44% ⚠️ |

Honest note: at $0.10 COGS these miss the 70% floor at 70% utilization —
the floor holds only if real COGS lands ≈$0.06 (pipeline stack) or
utilization runs ≈50%. **The publish review must pick two of: raise
prices, trim bundles, or prove pipeline COGS.** Overage at tier rate
(≥3x COGS) protects the tail either way.

## Publish checklist (founder + reviewer)

- [ ] Measured COGS/min from ≥10 pilots recorded (recompute table above)
- [ ] Stripe Products/Prices created (test → live), price ids recorded
- [ ] `plan_versions` drafted via Plan Catalog admin, `preview` reviewed
- [ ] Migration mode `new_signups_only`; grandfathering note for Trial
- [ ] Onboarding + billing pages show minutes-equivalence (Epic C1 done)
- [ ] `DATABASE_SCHEMA.md` + runbook updated with live price ids
- [ ] Staging checkout → webhook → grant verified end-to-end (Epic C gate)
