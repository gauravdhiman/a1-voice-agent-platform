# Platform Skills Library

**Last updated:** 2026-06-24
**Status:** Phase 2c re-design — 15 industry-specific skills, no legacy stubs

The platform ships a focused library of **15 built-in skills** — five per
industry (dental, restaurant, HVAC), one per capability slot. There are
no "generic" skills in the library anymore; the old eight
(`appointment-booking`, `call-transfer`, `faq-responder`, etc.) were
either stubs or had dental-flavored reference data that didn't
generalize.

## Why industry-specific?

Each business type has different workflows, vocabulary, urgency models,
and reference data. Splitting skills by industry instead of trying to
ship one "universal" skill per capability gives each skill room to be
genuinely excellent at the caller's actual situation rather than
adequate at every situation.

The org admin picks the skills that match their business. If they need
to customize one, they fork it like any other platform skill and the
fork becomes their working copy.

## Library shape

| Industry | Booking | Knowledge | Intake / Special | Follow-up | Escalation |
|---|---|---|---|---|---|
| **Dental** | `dental-appointment-booking` | `dental-faq` | `dental-new-patient-intake` | `dental-recall-and-reminder` | `dental-escalation` |
| **Restaurant** | `restaurant-reservation-booking` | `restaurant-menu-and-info` | `restaurant-special-request` | `restaurant-reservation-followup` | `restaurant-escalation` |
| **HVAC** | `hvac-service-appointment` | `hvac-service-info` | `hvac-diagnosis-and-triage` | `hvac-maintenance-recall` | `hvac-escalation` |

Every industry has exactly one of each capability slot. Restaurant and
HVAC don't have medical-style patient intake; their "intake" slot is
**special-request** (restaurant: takeout/catering) and **diagnosis-and-triage**
(HVAC: troubleshooting before scheduling).

## Skill content standards

Every skill in this library follows the same structural rules:

1. **SKILL.md** opens with *When to activate* (concrete caller trigger
   phrases), then a mermaid decision diagram, then a procedure,
   reference file list, guardrails, and handoff language.
2. **Decision diagrams use mermaid**, not walls of prose. They render
   inline in the platform-skill editor and the org's skill editor.
3. **No tool names in skill content.** Skills describe the user-visible
   action ("check the schedule", "send a confirmation"); the agent
   picks the tool. This keeps skills durable as the platform's toolset
   evolves.
4. **Reference files are small** (under ~12 KB each) and only loaded
   on demand. The agent references them by filename in the SKILL.md so
   it knows what's available to pull.
5. **Guardrails are explicit.** Every skill has a `## Guardrails`
   section listing what the agent must not do (no diagnosis, no price
   quoting without a source, no promising specific technicians, etc.).
6. **Handoff language is explicit.** Every skill lists which other
   skills it's expected to hand off to and the conditions under which
   it does so.

## When to add new skills

The library is deliberately small. Add a new skill only when:

* There's a call workflow that's not covered by any existing skill in
  the industry, AND
* The workflow is general enough that most businesses in that industry
  will want it (don't add niche skills for one org), AND
* The skill can be written without naming specific external tools
  (otherwise it's an integration, not a skill).

If a workflow is unique to a single org, the org should build a custom
skill in their own library instead.

## When to fork vs. edit

**Fork** a platform skill when:

* The practice has different hours, menu, services, or pricing than the
  defaults in the platform version
* The practice wants to add workflows the platform version doesn't
  cover
* The practice wants to change the trigger phrases or guardrails to
  match their house style

**Don't fork** when:

* You just want to enable / disable the skill — that's the toggle on
  the org-skill assignment, no fork needed
* You want to assign it to a different agent — that's the agent-skill
  assignment, no fork needed

## What was removed (vs. previous library)

The library used to contain 8 generic skills:

| Old slug | Why removed |
|---|---|
| `appointment-booking` | Dental-flavored reference data, ~360 lines of dental-specific decision tree |
| `insurance-verification` | Dental-flavored; only relevant to medical practices |
| `dispatch-coordination` | HVAC-flavored; only relevant to field-service businesses |
| `call-transfer` | Stub (~90 lines); no concrete transfer mechanism to integrate with |
| `faq-responder` | Stub; replaced by per-industry info skills |
| `after-hours` | Stub; covered by per-industry escalation skills |
| `lead-qualification` | Stub; out of scope for the three target industries |
| `payment-collection` | Stub; deferred — would need a payment-tool integration |

If you previously forked any of these, your forks remain. We only
removed the seed entries from the platform library.

## Roadmap

Future library additions are tracked in `docs/SPRINT-BOARD.md`. Likely
next additions:

* `legal-intake` (law-firm industry)
* `property-showing-booking` (real-estate industry)
* `recall-campaigns` (when we have email/SMS tools wired up)

Each will follow the same structural rules.
