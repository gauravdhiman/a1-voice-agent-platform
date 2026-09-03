# Conditional Call Forwarding — Concierge Guide (Epic A leftover, closed here)

**Purpose:** Stage 1 of the trust ladder — the owner's primary number stays
public; their carrier forwards to our Twilio number only on busy, no-answer,
or after-hours. The owner executes (we have no access to their carrier);
we own the guide, the screen-share, and the test-call proof.

> Carrier codes change. Always confirm on the carrier's current support
> page during the setup call — never read codes from memory as fact.

## What to ask for (works on any carrier)

"Conditional call forwarding of my business number to +1-XXX-XXX-XXXX on
busy and no-answer (and after-hours schedule, if supported)." If the rep
offers only unconditional forwarding, take it as a fallback and note the
daytime tradeoff to the owner.

## Mobile (owner does this live on the setup call, ~2 minutes)

- **iPhone:** Settings → Phone → Call Forwarding. Note: iOS exposes
  unconditional forwarding only — for conditional rules, use carrier codes
  below or the carrier app.
- **Android:** Phone app → Settings → Supplementary/Call forwarding →
  separate toggles for busy / unanswered / unreachable.
- **Carrier codes** (dial from the business line; verify current):
  T-Mobile documents `**61*number#` (no answer), `**62*` (unreachable),
  `**67*` (busy); Verizon documents `*71` + number (busy/no-answer) and
  `*72`/`*73` (unconditional on/off); AT&T publishes equivalents in its
  wireless support pages. Confirm, don't assume.

## Landline / VoIP / PBX

- **VoIP dashboards** (RingCentral, Grasshopper, Dialpad, etc.): Call
  Handling / Business Hours rules → overflow to external number. Ask the
  owner to share screen; it takes five minutes and you verify the rule
  list together.
- **Landline/PBX:** varies by provider and admin access. If the owner
  cannot self-serve, fallback to Stage 1b (after-hours schedule only, if
  supported) or Stage 2 (AI number straight onto Google profile/website).

## Test-call proof (every setup, no exceptions)

1. From your own phone, call the owner's primary number; let it ring out.
2. Confirm the AI answers, handles the test booking, and the call appears
   in the org call log with the credit deduction.
3. Show the owner the log row + recording, then hand over the pilot link.
4. Record which forwarding mode was used (conditional-busy / no-answer /
   schedule / unconditional-fallback) in the pilot row for later analysis.
