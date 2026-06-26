"""Platform skill seed templates (Phase 2c re-design).

Library shape: 15 industry-specific skills, 5 per industry, covering the
five capability slots every voice agent needs:

    booking    faq    intake    recall    escalation

Each skill is a separate platform template so org admins see one
"dental-appointment-booking" next to "restaurant-reservation-booking"
and pick the one that matches their business. There is no master skill
that gets forked and customized per industry; Option B (industry-specific
variants) won over Option A (master + per-industry reference injection)
because fork-time surgery is confusing and hard to reason about.

All skill content is decoupled from specific external tools. Skills
describe user-visible actions (e.g. "check the calendar for openings")
and reference ``load_skill_reference`` so the agent loads reference files
on-demand. The agent + its tool wiring decide how to do it.

The 8 legacy generic skills (appointment-booking, insurance-verification,
dispatch-coordination, call-transfer, faq-responder, after-hours,
lead-qualification, payment-collection) were removed in this pass. Their
content was either stubs or dental-flavored; the new industry-specific
library replaces them outright.
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════════════════════════
# DENTAL — 5 skills
# ═══════════════════════════════════════════════════════════════════════════════

DENTAL_APPOINTMENT_BOOKING = """# Dental Appointment Booking

## When to activate

Activate when the caller wants to **schedule, reschedule, or cancel** a dental
visit. Trigger phrases include: "schedule", "make an appointment", "book a
cleaning", "I need to come in", "cancel my appointment", "reschedule", "move
my appointment", "change my time", "what openings do you have".

Do **not** activate if the caller only wants to ask a general question
(use `dental-faq`) or is in acute pain (use `dental-escalation` to get them
help fast, then come back here if the call resolves).

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller asks about a visit] --> B{New or existing patient?}
    B -->|New| C[new-patient-intake]
    B -->|Existing| D{Action?}
    D -->|Book| E[Collect: visit type, preferred day/window, provider preference]
    D -->|Reschedule| F[Pull up existing appointment; offer 2 alternatives]
    D -->|Cancel| G[Confirm reason; offer to rebook within 90 days]
    E --> H{Check openings}
    F --> H
    H -->|Found| I[Confirm slot; collect best callback number; close]
    H -->|None in window| J[Offer next best window or waitlist]
    C --> D
    G --> I
```

## Procedure

1. **Identify** the action: book / reschedule / cancel / "not sure".
2. **New patient?** If yes, activate `dental-new-patient-intake` first; come
   back here once intake is complete.
3. **Collect the visit type** in the caller's words; do not interrogate for
   procedure codes — the practice matches codes during scheduling.
4. **Offer a window**, not a single time. People planning a visit want
   flexibility ("any time next Tuesday afternoon?").
5. **Confirm the slot** with: date, day-of-week, time, provider name.
6. **Verify the callback number** by reading it back.
7. **Close** with a one-sentence summary and what happens next
   (confirmation by text/email, arrival instructions).

## Reschedule and cancel

- **Reschedule**: pull up the existing appointment, offer two alternatives
  inside the original window, do not lecture about cancellation policy.
- **Cancel**: ask the reason only if it informs a same-day waitlist offer.
  Be brief; do not push to rebook unless the caller invites it.

## Reference files

- `references/services-and-duration.md` — visit types and typical durations
  so you can suggest sensible slots.

Load on demand via ``load_skill_reference`` when the caller asks "what kinds
of visits" or you need duration to find an opening.

## Guardrails

- **Do not** quote specific procedure codes or prices — those come from the
  practice, not the skill.
- **Do not** confirm a slot without a verified callback number.
- **Do not** mention tools by name. Describe the action: "check the schedule
  for openings", "send a confirmation", "add to the waitlist".
- **Do not** promise same-day appointments unless the caller says they're
  flexible and you have confirmed availability for today.
- **Never** discuss clinical advice, diagnoses, or symptoms. If the caller
  describes pain, switch to `dental-escalation`.

## Handoff

- New patient without demographics on file → `dental-new-patient-intake`
- Insurance / coverage question that surfaced → `dental-faq`
- Acute pain, swelling, trauma → `dental-escalation` immediately
- Caller wants a callback confirmation → confirm with the practice's
  preferred channel (text or email) without naming a vendor
"""


DENTAL_FAQ = """# Dental FAQ

## When to activate

Activate when the caller asks a **general question about the practice** that
doesn't require scheduling, billing, or clinical judgment. Trigger phrases:
"do you accept", "what are your hours", "where are you located", "do you
take walk-ins", "is there parking", "what's your cancellation policy",
"do you see kids", "are you in-network with".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller asks a general question] --> B{Topic}
    B -->|Hours / location / parking| C[Answer from references]
    B -->|Insurance / payment| D[Confirm and offer follow-up]
    B -->|Services / who is on staff| E[Answer from references]
    B -->|Policy / cancellation / no-show| F[Answer from references]
    C --> G[Offer more help]
    D --> G
    E --> G
    F --> G
```

## Procedure

1. **Listen** for the topic. Most callers state it within their first sentence.
2. **Answer directly** — do not stack clarifying questions on a simple info
   request. If the caller said "what time do you close", say the closing
   time.
3. **Cite specifics**: actual hours including weekends, full address with
   landmark, exact policy quote — not vague handwaves.
4. **Offer one more thing** at the end: "Is there anything else I can help
   with?" Most callers will say no thanks; some will pivot to booking.

## Reference files

- `references/practice-info.md` — hours, address, parking, contact info
- `references/services-and-staff.md` — services offered, providers, age ranges

Load on demand. If you cannot find the answer in references, say so plainly
and offer to have someone call back with the specifics — do not invent.

## Guardrails

- **Do not** answer questions about symptoms, pain, or treatment — those are
  clinical. Switch to `dental-escalation`.
- **Do not** quote prices you have not been given. If asked, say pricing
  varies and offer to have the office follow up.
- **Do not** mention tools by name. Just answer.
- **Do not** give legal or billing advice; offer a callback.

## Handoff

- Caller wants to schedule → `dental-appointment-booking`
- Insurance coverage question → `dental-faq` (covered above) or handoff to
  billing via `dental-escalation`
- Symptom or acute concern → `dental-escalation`
"""


DENTAL_NEW_PATIENT_INTAKE = """# Dental New Patient Intake

## When to activate

Activate when the caller identifies as a **new patient** (no record on
file) and needs to provide demographics, medical history, or insurance
information before booking. Trigger phrases: "I'm a new patient",
"first time", "I haven't been there before", "I need to fill out forms",
"can I give you my insurance".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller is new] --> B{Age group?}
    B -->|Adult| C[Collect: full name, DOB, phone, email]
    B -->|Child| D[Collect child + guardian info]
    C --> E{Insurance?}
    D --> E
    E -->|Yes| F[Collect: carrier, member ID, group; note policyholder]
    E -->|No / unsure| G[Note self-pay; offer payment-plan info]
    F --> H[Medical history: meds, allergies, conditions]
    G --> H
    H --> I[Confirm visit type and preferred window]
    I --> J[Hand off to dental-appointment-booking]
```

## Procedure

1. **Reassure** the caller that intake takes about five minutes and that
   they can pause or ask questions.
2. **Demographics first**: full legal name, date of birth, best callback
   number, email. Spell back the name and number.
3. **Insurance** if applicable: carrier name, member ID, group number.
   Ask whether they are the policyholder; if not, get policyholder's name
   and relationship.
4. **Medical history**: current medications, known allergies, relevant
   conditions (heart, diabetes, pregnancy, blood thinners). One question
   at a time; do not rapid-fire.
5. **Confirm visit type** and rough window; hand off to
   `dental-appointment-booking` with the new patient now on file.

## Reference files

- `references/intake-questions.md` — the structured question list so you
  don't forget anything.

Load on demand at the start of the call to keep the questions consistent.

## Guardrails

- **Do not** ask for SSN or full payment card numbers over the phone. SSN
  is collected on the patient form, not by phone. Card numbers go through
  the secure payment channel, never read aloud.
- **Do not** offer medical advice even when discussing medical history.
  Collect, do not interpret.
- **Do not** mention tools by name.
- **Do not** put a caller on hold for more than 60 seconds during intake;
  offer a callback instead.

## Handoff

- Demographics collected → `dental-appointment-booking` for scheduling
- Insurance complexity (coordination of benefits, secondary) → practice
  callback; collect what you can and route
- Medical urgency surfaces during intake → `dental-escalation`
"""


DENTAL_RECALL_AND_REMINDER = """# Dental Recall & Reminder

## When to activate

Activate when the practice is calling (or the agent is taking a call
about) a **recall, reminder, or routine follow-up** — typically hygiene
recalls, treatment-plan follow-ups, or post-procedure check-ins. Trigger
phrases: "this is a reminder", "you're due for", "we're calling about
your cleaning", "follow-up from your last visit".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Outreach or inbound about a recall] --> B{Reason}
    B -->|Hygiene / cleaning recall| C[Confirm: last visit, recall window]
    B -->|Treatment plan follow-up| D[Confirm: pending treatment, urgency]
    B -->|Post-procedure check-in| E[Ask how recovery is going]
    C --> F{Ready to book?}
    D --> F
    E --> G{Any concerns?}
    G -->|Yes| H[dental-escalation]
    G -->|No| I[Close warmly]
    F -->|Yes| J[dental-appointment-booking]
    F -->|No| K[Note preference; close]
```

## Procedure

1. **Identify** the recall reason before pitching a date. Recalls for
   treatment plans carry different urgency than six-month cleanings.
2. **Confirm the last visit** if you have it; do not invent dates.
3. **Offer two windows**, not a single time. People planning a visit want
   flexibility.
4. **Respect the answer**. If the caller says "not now", mark it and
   close warmly; do not push.
5. **For post-procedure check-ins**, ask one open question
   ("how's the recovery going?") and listen for warning signs that
   need escalation.

## Reference files

- `references/recall-windows.md` — typical hygiene intervals (6 mo),
  perio intervals (3-4 mo), and how to phrase "you're due".

Load on demand only if the caller asks about frequency or the practice's
recall policy.

## Guardrails

- **Do not** create urgency that isn't there. A six-month cleaning
  recall is not "overdue" — it's "due".
- **Do not** mention tools by name.
- **Do not** ask about payment during a recall; that's a separate call.
- **Do not** keep pushing after the caller has declined twice in a row.

## Handoff

- Caller wants to book → `dental-appointment-booking`
- Recovery concern surfaces during post-procedure check → `dental-escalation`
- Insurance question during recall → `dental-faq`
"""


DENTAL_ESCALATION = """# Dental Escalation

## When to activate

Activate when the caller has an **urgent or sensitive situation** that needs
a human quickly: acute pain, swelling, infection, trauma, allergic
reaction during a visit, billing dispute that can't be resolved, or an
explicit request for a manager. Trigger phrases: "I'm in pain", "my face
is swollen", "I can't breathe", "I want to speak to", "this is
unacceptable", "I want my money back".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Urgent / sensitive call] --> B{Life-threatening?}
    B -->|Yes: breathing / chest / severe bleeding| C[Direct to 911 immediately; stay on line]
    B -->|No| D{Urgency}
    D -->|Acute dental: pain, swelling, trauma, infection| E[Same-day triage; collect symptoms + best callback]
    D -->|Billing dispute| F[Acknowledge; collect details; route to billing]
    D -->|Wants a human / manager| G[Collect: name, callback, summary; route]
    E --> H{Resolved by phone?}
    F --> I[Confirm callback window]
    G --> I
    H -->|Yes| J[Close with action items]
    H -->|No| K[Hand off to dental-appointment-booking if slot available]
```

## Procedure

1. **Triage first, route second.** Acute symptoms first; complaints about
   billing wait for the appropriate channel.
2. **Acknowledge** the caller's situation without minimizing. Don't say
   "I understand how you feel" — say "that's serious, let me get you
   help".
3. **Collect**: name, callback number, brief description of the situation
   (one or two sentences), when it started.
4. **For acute dental concerns**: offer the earliest same-day slot if
   the practice has one; otherwise route to on-call triage.
5. **For billing disputes**: do not argue. Acknowledge, collect, route.
6. **For requests for a human**: do not delay. Collect the handoff
   summary and route.

## Reference files

None. This skill is about routing, not lookup. If you find yourself
needing reference data, you have likely misclassified the call.

## Guardrails

- **Never** give clinical advice. Even "rinse with warm salt water" is
  clinical — the practice's on-call line handles that.
- **Do not** quote prices for unscheduled emergency treatment.
- **Do not** argue with a caller who wants a manager. Acknowledge, route.
- **Do not** mention tools by name.

## Handoff

- Slot available for same-day acute visit → `dental-appointment-booking`
- Insurance / coverage question on an urgent call → `dental-faq`
- New patient in acute pain → `dental-new-patient-intake` after slot is
  secured
"""


# ═══════════════════════════════════════════════════════════════════════════════
# RESTAURANT — 5 skills
# ═══════════════════════════════════════════════════════════════════════════════

RESTAURANT_RESERVATION_BOOKING = """# Restaurant Reservation Booking

## When to activate

Activate when the caller wants to **book, change, or cancel a
reservation**. Trigger phrases: "I'd like a table", "reservation for",
"book a table", "can I get a table for", "change my reservation",
"cancel my reservation", "what time do you have".

Do **not** activate for takeout / pickup orders (use
`restaurant-special-request` to capture details and have the kitchen
call back) or large private events (those usually require a manager —
hand off via `restaurant-escalation`).

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller wants a table] --> B{Party size}
    B -->|1-6 standard| C[Offer 2 windows in requested date]
    B -->|7+ or private event| D[restaurant-escalation to manager]
    B -->|Unsure| E[Ask party size first; do not interrogate]
    C --> F{Time of day}
    F -->|Standard dinner / lunch| G[Confirm: name, time, party size, contact]
    F -->|Off-hours / unusual| H[Confirm with manager availability]
    G --> I{Special requests?}
    I -->|Allergies / accessibility| J[Note in reservation; do not require confirmation]
    I -->|None| K[Confirm reservation; send confirmation]
    H --> K
    D --> K
    J --> K
```

## Procedure

1. **Date and party size first.** Don't ask "what's the occasion" — it's
   filler that wastes a minute on every call.
2. **Offer two windows**, not a single time. People planning dinner
   usually have a flexible window.
3. **Confirm**: date, day-of-week, time, party size, name, callback
   number.
4. **Ask about allergies or accessibility needs.** This is the one
   question worth asking — not "what's the special occasion".
5. **Close** with confirmation timing: "We'll send a confirmation by
   text/email shortly."

## Reschedule and cancel

- **Reschedule**: pull up the existing reservation, offer two
  alternatives. Be brief; people reschedule because life happened.
- **Cancel**: ask "for tonight or another date" only if it informs
  whether to offer a waitlist. Most cancellations end the call.

## Reference files

- `references/hours-and-seating.md` — operating hours, last-seating time,
  table count by section (so you know what's actually available).

Load on demand when the caller asks about hours or you need to assess
availability for an unusual request.

## Guardrails

- **Do not** promise a specific table or section ("by the window") unless
  you can verify it.
- **Do not** quote menu prices unless the reference file has them.
- **Do not** ask about the occasion or special events the restaurant
  doesn't track.
- **Do not** mention tools by name.

## Handoff

- 7+ party or private event → `restaurant-escalation`
- Allergy raises a question you can't answer → `restaurant-escalation`
- Caller wants takeout / catering → `restaurant-special-request`
"""


RESTAURANT_MENU_AND_INFO = """# Restaurant Menu & Info

## When to activate

Activate when the caller asks **general questions about the restaurant**:
menu, hours, location, dietary options, specials, dress code, parking,
reservations policy. Trigger phrases: "what's on the menu", "do you
have", "are you open", "where are you", "do you take walk-ins", "is it
kid-friendly".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller asks about the restaurant] --> B{Topic}
    B -->|Menu item / ingredients| C[Answer from references; offer more]
    B -->|Dietary: vegan / GF / allergy| D[Confirm and offer follow-up if unsure]
    B -->|Hours / location / parking| E[Answer directly]
    B -->|Reservations policy| F[Answer; offer to book via reservation skill]
    C --> G[Anything else?]
    D --> G
    E --> G
    F --> G
```

## Procedure

1. **Listen** for the topic; most callers state it upfront.
2. **Answer concretely**: actual hours (incl. brunch / happy hour),
   full address with landmark, specific ingredient or dish, exact policy.
3. **For dietary questions**, be conservative. If the reference doesn't
   confirm the dish is gluten-free, say "we can check with the kitchen
   when you arrive" rather than guessing.
4. **For menu items**, name the dish and a one-sentence description.
   Don't recite the whole menu.
5. **Offer one more thing** at the end. Most callers will say no.

## Reference files

- `references/menu-highlights.md` — signature dishes, daily specials, dietary tags
- `references/practice-info.md` — hours, address, parking, dress code

Load on demand. Keep both files under 10 KB; menu content changes often
and the practice will fork + edit.

## Guardrails

- **Never** invent menu items. If the caller asks about a dish you
  don't see, say "let me have someone get back to you" rather than
  describe something the kitchen doesn't make.
- **Do not** quote prices you have not been given.
- **Do not** make medical or allergy guarantees. "Gluten-free" requires
  kitchen verification for severe allergies.
- **Do not** mention tools by name.

## Handoff

- Caller wants to book → `restaurant-reservation-booking`
- Takeout / catering request → `restaurant-special-request`
- Complaint → `restaurant-escalation`
"""


RESTAURANT_SPECIAL_REQUEST = """# Restaurant Special Request (Takeout, Catering, Custom)

## When to activate

Activate when the caller has a **non-reservation request**: takeout /
pickup order, catering inquiry, custom celebration (anniversary cake,
private dining arrangement), gift card purchase. Trigger phrases: "I'd
like to order takeout", "do you do catering", "can I get a cake",
"private room", "gift card", "large order".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Non-reservation request] --> B{Type}
    B -->|Takeout / pickup| C[Capture: items, pickup time, contact]
    B -->|Catering| D[Capture: date, headcount, dietary; route to manager]
    B -->|Custom celebration| E[Capture: date, party size, vision; route]
    B -->|Gift card| F[Capture: amount, recipient, delivery; route]
    C --> G{Order details clear?}
    D --> H[restaurant-escalation to manager]
    E --> H
    F --> H
    G -->|Yes| I[Confirm pickup time and contact]
    G -->|No| J[Have manager call back within 30 min]
```

## Procedure

1. **Classify** the request type. Takeout is the only one you can
   typically fulfill directly. Catering, custom celebrations, and gift
   cards need a manager.
2. **Takeout**: capture items (read back), pickup time (offer 2 windows),
   name, callback number, any allergies. Confirm and close.
3. **Catering and celebrations**: capture the basics (date, headcount,
   any dietary constraints), then route. Do not promise pricing or
   availability — the manager will follow up.
4. **Gift cards**: capture amount, recipient name, delivery preference;
   route.
5. **Close** with the callback window the manager will use ("someone
   will reach out within X").

## Reference files

None for takeout details — the menu lives in `restaurant-menu-and-info`
references. For catering packages, the practice will have its own
document once they fork the skill.

## Guardrails

- **Do not** promise catering pricing or availability.
- **Do not** promise a specific cake / decoration without manager
  confirmation.
- **Do not** process payment over the phone for any of these requests
  unless the practice has explicitly enabled it for this caller.
- **Do not** mention tools by name.

## Handoff

- Manager-needed request → `restaurant-escalation`
- Menu question during takeout → `restaurant-menu-and-info`
- Reservation needed too → `restaurant-reservation-booking`
"""


RESTAURANT_RESERVATION_FOLLOWUP = """# Restaurant Reservation Follow-up

## When to activate

Activate when the restaurant is calling (or the agent is taking a call
about) a **post-visit follow-up**: thank-you for a recent visit,
celebration acknowledgment, lost-and-found inquiry, repeat-visit
outreach. Trigger phrases: "this is about your recent visit",
"following up from your dinner", "did you enjoy your meal", "did you
leave something behind".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Follow-up about a visit] --> B{Purpose}
    B -->|Thank-you / feedback| C[Capture feedback; close warmly]
    B -->|Lost and found| D[Capture item description + best callback]
    B -->|Repeat-visit offer| E[Offer to book again]
    C --> F[Anything else?]
    D --> G[restaurant-escalation]
    E --> H{Ready to book?}
    H -->|Yes| I[restaurant-reservation-booking]
    H -->|No| J[Note preference; close]
```

## Procedure

1. **Identify** the follow-up reason before pitching. Lost-and-found and
   feedback have different urgency than a marketing repeat-visit offer.
2. **For feedback**: ask one open question and listen. Do not defend
   the restaurant; do not promise a free meal or comp; route complaints.
3. **For lost and found**: capture item description (color, brand, where
   they sat if they remember) and best callback. Do not promise the item
   will be found.
4. **For repeat-visit offers**: ask if the caller would like to book
   again. If yes, hand off. If no, thank them and close.

## Reference files

None. This skill is conversational, not data-driven. For lost-and-found
details the manager has a separate log; the agent routes, doesn't search.

## Guardrails

- **Do not** promise a comp or refund for a complaint. Acknowledge, route.
- **Do not** confirm an item will be found. Capture details and route.
- **Do not** mention tools by name.

## Handoff

- Repeat booking → `restaurant-reservation-booking`
- Complaint / dissatisfaction → `restaurant-escalation`
- Lost and found → `restaurant-escalation`
"""


RESTAURANT_ESCALATION = """# Restaurant Escalation

## When to activate

Activate when the caller has a **complaint, sensitive situation, or
request that needs a manager**: bad experience, billing dispute,
allergy incident, large private event, lost-and-found, repeated
complaint, explicit request for a manager. Trigger phrases: "this was
terrible", "I want a refund", "I had an allergic reaction", "I want to
speak to", "I left something", "I need to book for 12 people".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Complaint / sensitive / manager-needed] --> B{Severity}
    B -->|Allergy / safety incident| C[Acknowledge seriously; collect: what, when, who served]
    B -->|Service complaint| D[Capture experience; do not argue; route]
    B -->|Billing dispute| E[Acknowledge; collect details; route to GM]
    B -->|Wants a manager| F[Collect name, callback, summary; route]
    C --> G{Medical attention needed?}
    G -->|Yes| H[Direct to 911 or nearest ER; stay engaged]
    G -->|No| I[Confirm callback within 24h]
    D --> I
    E --> I
    F --> I
```

## Procedure

1. **Triage by severity first.** Allergy / safety incidents are not
   handled like lost-and-found.
2. **Acknowledge without minimizing**. Do not say "I understand how you
   feel". Say "that's serious, let me get you to the right person".
3. **Collect**: name, callback number, brief description of the
   situation (one or two sentences), when it happened, who was involved
   (if known).
4. **For allergy / safety incidents**: ask if anyone needs medical
   attention right now. If yes, direct to 911 or the nearest ER and
   stay engaged until help is on the way.
5. **Confirm the callback window**: a manager will reach out within the
   timeframe the practice has set (typically within 24 hours for
   non-emergencies).

## Reference files

None. Routing only.

## Guardrails

- **Never** offer a refund, comp, or gift card without manager approval.
- **Do not** argue with a caller about what happened. Acknowledge, route.
- **Do not** diagnose allergic reactions or suggest treatments. Direct
  to medical care if needed.
- **Do not** mention tools by name.

## Handoff

- Routine complaint / lost and found / private event → manager callback
  (already initiated by the agent)
- Caller also wants to book → `restaurant-reservation-booking` after
  the manager has been notified
"""


# ═══════════════════════════════════════════════════════════════════════════════
# HVAC — 5 skills
# ═══════════════════════════════════════════════════════════════════════════════

HVAC_SERVICE_APPOINTMENT = """# HVAC Service Appointment

## When to activate

Activate when the caller wants to **schedule a service call** for HVAC
equipment: heating, cooling, ventilation, thermostat, water heater (if
the practice services it). Trigger phrases: "no heat", "no air", "AC is
out", "furnace won't start", "thermostat isn't working", "I need
someone to come out", "schedule a service call".

For emergency situations (gas smell, carbon monoxide, sparking
equipment), activate `hvac-escalation` first; service scheduling comes
after the safety call.

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller wants service] --> B{Emergency?}
    B -->|Yes: gas / CO / sparks / smoke| C[hvac-escalation immediately]
    B -->|No| D{Urgency}
    D -->|No heat in cold / no AC in heat| E[Same-day if available; else next-day]
    D -->|Routine| F[Standard 2-3 day window]
    E --> G[Collect: equipment type, age, symptoms, address]
    F --> G
    G --> H{Found slot?}
    H -->|Yes| I[Confirm: day, window, contact, access notes]
    H -->|No| J[Offer waitlist or earlier slot at premium time]
```

## Procedure

1. **Triage safety first.** Gas, CO, sparks, smoke → escalate before
   scheduling.
2. **Identify equipment type and age** if the caller knows it
   (helps technician prep). Don't interrogate; ask once.
3. **Describe symptoms in the caller's words.** Don't diagnose. "The
   furnace isn't kicking on" is enough; the technician figures out why.
4. **Determine urgency**: no-heat-in-cold and no-AC-in-heat are
   same-day priorities; everything else is a routine window.
5. **Offer a window**, not a single time. Service windows are 2-4 hours
   by nature.
6. **Collect access notes**: gate code, pets, where the equipment is
   located if non-obvious.
7. **Confirm**: day, window, contact, address, symptoms, access notes.

## Reference files

- `references/equipment-types.md` — common HVAC equipment categories so
  you can use the caller's language without naming specific brands.

Load on demand when the caller mentions equipment you're not sure how
to categorize.

## Guardrails

- **Never** diagnose over the phone. "Sounds like a capacitor" is a
  diagnosis; let the technician on-site decide.
- **Do not** quote repair prices without a technician assessment.
- **Do not** promise a specific technician or specific arrival time
  within the window.
- **Do not** mention tools by name.

## Handoff

- Emergency (gas / CO / sparks / smoke) → `hvac-escalation` first
- Maintenance-plan inquiry → `hvac-maintenance-recall`
- Warranty question → `hvac-service-info` (FAQ)
"""


HVAC_SERVICE_INFO = """# HVAC Service Info

## When to activate

Activate when the caller asks **general questions** about HVAC service:
pricing model, warranty coverage, maintenance plans, what to do
before the technician arrives, what equipment you service. Trigger
phrases: "do you service", "what's your service call fee", "is this
covered under warranty", "do you have a maintenance plan", "should I
do anything before they come".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller asks a service question] --> B{Topic}
    B -->|Pricing / fees| C[Answer from references; offer callback for quote]
    B -->|Warranty / coverage| D[Answer from references; note: depends on equipment age]
    B -->|Maintenance plan| E[Describe; offer to enroll or callback]
    B -->|Pre-visit prep| F[Answer from references]
    C --> G[Anything else?]
    D --> G
    E --> H{Enroll now?}
    H -->|Yes| I[Capture name, contact, equipment]
    H -->|No| G
    F --> G
```

## Procedure

1. **Listen** for the topic. Most callers state it in the first sentence.
2. **Answer concretely**: actual service-call fee range, what's
   included, what isn't, what the maintenance plan covers.
3. **For warranty questions**: most warranties depend on the equipment
   age and the manufacturer's terms. Say so plainly; do not promise
   coverage.
4. **For maintenance plans**: describe the cadence (typically 2x/year
   for HVAC), what's included (filter swap, basic inspection), what
   the discount on service calls is. Offer to enroll or have someone
   follow up.
5. **For pre-visit prep**: simple stuff. Clear access to the unit, have
   the make/model if known, secure pets.

## Reference files

- `references/pricing-and-plans.md` — service-call fee, maintenance plan tiers, what's covered
- `references/warranty-handling.md` — common warranty scenarios and how
  to phrase them

Load on demand. Both files should be small enough that you can read
them quickly mid-call.

## Guardrails

- **Do not** quote a specific repair price over the phone.
- **Do not** promise warranty coverage without verifying the equipment
  and registration.
- **Do not** offer discounts that aren't in the references.
- **Do not** mention tools by name.

## Handoff

- Caller wants to book service → `hvac-service-appointment`
- Emergency / safety issue surfaces → `hvac-escalation`
- Maintenance enrollment → callback or in-line form capture
"""


HVAC_DIAGNOSIS_AND_TRIAGE = """# HVAC Diagnosis & Triage

## When to activate

Activate when the caller describes an **HVAC problem** and wants help
figuring out what's wrong before scheduling. Trigger phrases: "why
isn't my", "what could cause", "is this normal", "how do I check",
"should I be worried", "my unit is making a sound".

For safety situations (gas smell, CO, sparks, smoke), activate
`hvac-escalation` immediately. This skill is for non-emergency
diagnostic conversation.

## Mermaid decision tree

```mermaid
flowchart TD
    A[Caller describes a problem] --> B{Safety first}
    B -->|Gas / CO / sparks / smoke| C[hvac-escalation immediately]
    B -->|No| D{Symptom}
    D -->|No heat / no cool| E[Ask age + last service; recommend service call]
    D -->|Strange sound| F[Ask when it started; recommend service if persists]
    D -->|Thermostat issue| G[Ask basic checks: power, batteries, settings]
    D -->|Airflow weak| H[Ask filter age; recommend filter swap if old]
    E --> I[Offer service slot]
    F --> I
    G --> J{Resolved?}
    H --> K{Resolved?}
    J -->|Yes| L[Close]
    J -->|No| I
    K -->|Yes| L
    K -->|No| I
```

## Procedure

1. **Safety triage first**, regardless of the caller's framing. Gas,
   CO, sparks, smoke always escalate.
2. **Listen to the symptom** in the caller's words. Don't jump to a
   diagnosis based on one phrase.
3. **Ask the minimum context**: equipment age, when the symptom started,
   any recent changes (filter swap, power outage, weather event).
4. **For thermostat issues**: walk through basic checks (power to
   thermostat, batteries if applicable, mode setting, setpoint vs
   actual temperature). Many "no heat" calls are a thermostat set to
   "cool" by mistake.
5. **For airflow**: ask when the filter was last changed. A clogged
   filter is the most common cause.
6. **For everything else**: recommend service. The technician on-site
   diagnoses; the phone agent does not.
7. **If the symptom resolves** during the call (e.g., they check the
   thermostat setting), confirm and close. **If it doesn't**, offer a
   service slot.

## Reference files

- `references/common-symptoms.md` — short checklist of "check this first"
  for common symptoms, so the agent walks through sensible basic checks.

Load on demand. Keep this file small (under 8 KB) so the agent can read
it in one shot mid-call.

## Guardrails

- **Never** diagnose a specific component failure over the phone.
- **Do not** quote a repair price without a technician assessment.
- **Do not** tell the caller to attempt any repair that involves opening
  the unit, working with electrical panels, or anything gas-related.
- **Do not** mention tools by name.

## Handoff

- Service slot needed → `hvac-service-appointment`
- Safety issue → `hvac-escalation`
- General info / plans → `hvac-service-info`
"""


HVAC_MAINTENANCE_RECALL = """# HVAC Maintenance Recall

## When to activate

Activate when the practice is calling (or the agent is taking a call
about) **scheduled maintenance**: semi-annual checkups, filter-swap
reminders, post-service follow-ups, seasonal tune-up campaigns. Trigger
phrases: "this is your maintenance reminder", "you're due for a
tune-up", "time for your spring / fall checkup", "filter replacement
reminder".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Recall / maintenance outreach] --> B{Reason}
    B -->|Semi-annual checkup| C[Confirm: last service, plan, preferred week]
    B -->|Filter swap| D[Offer mail-order filter or tech visit]
    B -->|Post-service follow-up| E[Ask: any concerns since the visit?]
    B -->|Seasonal tune-up campaign| F[Confirm; offer two windows]
    C --> G{Book now?}
    D --> G
    E --> H{Any concerns?}
    H -->|Yes| I[hvac-service-appointment or hvac-escalation]
    H -->|No| J[Close warmly]
    F --> G
    G -->|Yes| K[hvac-service-appointment]
    G -->|No| L[Note preference; close]
```

## Procedure

1. **Identify the recall reason** before pitching a date. Seasonal
   campaigns and filter reminders carry different urgency.
2. **For semi-annual checkups**: confirm last service date (don't
   invent), offer two windows inside the recommended window for the
   season.
3. **For filter swaps**: offer to mail a filter or schedule a tech
   visit, depending on the practice's model. Don't push either way.
4. **For post-service follow-ups**: ask one open question
   ("anything we should know about since the visit?") and listen for
   warning signs that need a service call or escalation.
5. **Respect declines**. If the caller says "not now" twice, close
   warmly and stop.

## Reference files

- `references/seasonal-cadence.md` — when to recommend spring vs fall
  tune-ups, typical filter lifespans.

Load on demand when the caller asks about cadence or frequency.

## Guardrails

- **Do not** create urgency that isn't there. A semi-annual checkup is
  recommended, not overdue.
- **Do not** push upsells during a recall. Keep it to the recall at hand.
- **Do not** mention tools by name.

## Handoff

- Caller wants to book → `hvac-service-appointment`
- Concern surfaces during follow-up → `hvac-service-appointment` or
  `hvac-escalation` depending on severity
- General question about plans / coverage → `hvac-service-info`
"""


HVAC_ESCALATION = """# HVAC Escalation

## When to activate

Activate when the caller has an **emergency, urgent safety situation,
or complaint needing a manager**: gas smell, carbon monoxide alarm,
sparking equipment, smoke, water leak near electrical, billing dispute
that can't be resolved, repeated no-show, explicit request for a
manager. Trigger phrases: "I smell gas", "CO alarm going off",
"something is sparking", "there's smoke", "water everywhere",
"this is the third time", "I want to speak to", "I want my money
back".

## Mermaid decision tree

```mermaid
flowchart TD
    A[Emergency / safety / complaint] --> B{Life / property threat?}
    B -->|Yes: gas / CO / fire / major leak| C[Direct to 911 + utility; stay engaged]
    B -->|No| D{Urgency}
    D -->|No heat in cold + vulnerable resident| E[Emergency same-day; collect: address, contact, equipment]
    D -->|Billing dispute| F[Acknowledge; collect details; route to GM]
    D -->|Service complaint| G[Acknowledge; collect details; route]
    D -->|Wants a manager| H[Collect: name, callback, summary; route]
    E --> I{Service available today?}
    I -->|Yes| J[hvac-service-appointment with priority flag]
    I -->|No| K[Emergency dispatch partner; confirm ETA]
    F --> L[Confirm callback within 24h]
    G --> L
    H --> L
```

## Procedure

1. **Triage safety first.** Gas, CO, sparks, fire, major leak → direct
   to 911 and the utility immediately. Stay on the line until the
   caller is safe.
2. **For no-heat-in-cold with a vulnerable resident** (elderly,
   infant, medical condition that requires heat): treat as emergency
   even though it's not life-threatening for the equipment. Get an
   address and contact immediately.
3. **Collect**: name, callback number, address, brief description of
   the situation (one or two sentences), when it started.
4. **Confirm the callback window**: emergency partner ETA for
   no-heat / no-cool cases; 24 hours for routine complaints.
5. **For complaints**: do not argue. Acknowledge, collect, route.

## Reference files

- `references/emergency-contacts.md` — utility emergency numbers, fire
  department, emergency dispatch partner. Keep this small and current.

Load on demand only when you need an emergency contact.

## Guardrails

- **For gas / CO / fire / sparking**: always direct to 911 / utility
  first. Do not diagnose, do not "check the breaker" — leave the
  building first.
- **Never** quote a repair price over the phone for an emergency.
- **Do not** argue with a caller who wants a manager. Acknowledge, route.
- **Do not** mention tools by name.

## Handoff

- Service slot needed (emergency same-day) → `hvac-service-appointment`
- Routine complaint routed to GM → already initiated by agent
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM SKILL TEMPLATES (Seeded into platform_skills table)
# ═══════════════════════════════════════════════════════════════════════════════

PLATFORM_SKILL_TEMPLATES = [
    # ── Dental ──────────────────────────────────────────────────────────────
    {
        "slug": "dental-appointment-booking",
        "name": "Dental Appointment Booking",
        "description": "Schedule, reschedule, or cancel dental visits for an existing patient. Use when the caller says schedule, book, reschedule, move my appointment, or cancel my appointment.",
        "content": DENTAL_APPOINTMENT_BOOKING,
        "default_files": [
            {
                "file_path": "references/services-and-duration.md",
                "file_kind": "reference",
                "content": """# Services & Duration

Default visit types for a general dental practice. Practices will fork this
file and edit durations to match their own scheduling.

## Hygiene / preventive

| Visit type | Typical duration |
|---|---|
| Adult cleaning (prophylaxis) | 60 min |
| Child cleaning | 45 min |
| Periodic exam (with cleaning) | 60 min |
| Periodic exam only | 30 min |
| Fluoride treatment | 15 min |

## Restorative

| Visit type | Typical duration |
|---|---|
| Single-surface filling | 60 min |
| Multi-surface filling | 90 min |
| Crown prep | 90 min |
| Crown delivery | 45 min |

## Specialty

| Visit type | Typical duration |
|---|---|
| Initial endodontic consult | 45 min |
| Initial perio consult | 60 min |
| Extraction (simple) | 45 min |
| Extraction (surgical) | 75 min |
""",
            },
        ],
    },
    {
        "slug": "dental-faq",
        "name": "Dental FAQ",
        "description": "Answer general questions about the dental practice: hours, location, parking, services, providers, insurance networks, policies. Use when the caller asks do you, are you, what time, where, or how much without scheduling intent.",
        "content": DENTAL_FAQ,
        "default_files": [
            {
                "file_path": "references/practice-info.md",
                "file_kind": "reference",
                "content": """# Practice Info

The practice will fork this file and replace placeholders with their own
info. Keep answers concrete: actual hours, full address, real policy
quotes.

## Hours

| Day | Hours |
|---|---|
| Mon | 8:00 AM – 5:00 PM |
| Tue | 8:00 AM – 5:00 PM |
| Wed | 8:00 AM – 5:00 PM |
| Thu | 8:00 AM – 5:00 PM |
| Fri | 8:00 AM – 3:00 PM |
| Sat | Closed |
| Sun | Closed |

## Address & parking

123 Main Street, Suite 200
[City, State ZIP]

Free parking in the surface lot behind the building. Street parking also
available.

## Contact

- Phone: (555) 123-4567
- Email: hello@example-dental.com
- Emergency after hours: (555) 987-6543
""",
            },
            {
                "file_path": "references/services-and-staff.md",
                "file_kind": "reference",
                "content": """# Services & Staff

## Services we offer

- General dentistry (cleanings, fillings, crowns)
- Cosmetic dentistry (whitening, veneers)
- Pediatric dentistry (ages 3+)
- Endodontics (root canals)
- Periodontics (gum treatment)
- Oral surgery (extractions)

## Providers

| Provider | Role | Sees |
|---|---|---|
| Dr. A | General dentist | Adults + children 8+ |
| Dr. B | General dentist | Adults + children 3+ |
| Hygienist 1 | Dental hygienist | All ages |
| Hygienist 2 | Dental hygienist | Adults + children 8+ |

## Patient age ranges

- We see patients age 3 and up
- Pediatric specialty referrals available for under 3
""",
            },
        ],
    },
    {
        "slug": "dental-new-patient-intake",
        "name": "Dental New Patient Intake",
        "description": "Capture demographics, insurance, and medical history for a new dental patient before booking. Use when the caller says I'm a new patient, first time, I haven't been there, or can I give you my insurance.",
        "content": DENTAL_NEW_PATIENT_INTAKE,
        "default_files": [
            {
                "file_path": "references/intake-questions.md",
                "file_kind": "reference",
                "content": """# Intake Questions

Ask in this order. Read back the name and number before moving on.

## Demographics

1. Full legal name (first, middle, last)?
2. Date of birth?
3. Best callback number?
4. Email?

## Insurance (if any)

5. Do you have dental insurance?
6. Carrier name (the company on the card)?
7. Member ID?
8. Group number?
9. Are you the policyholder? If no: policyholder name and relationship?

## Medical history

10. Are you currently taking any medications?
11. Do you have any allergies (medications, latex, foods)?
12. Do you have any medical conditions we should know about?
    - Heart conditions
    - Diabetes
    - Pregnancy
    - Blood thinners
    - Artificial joints
    - Other

## Visit

13. Reason for today's call (cleaning, specific concern, both)?
14. Any time-of-day preferences for the first visit?

Notes for the agent:
- Skip medical-history questions if the practice handles intake via a
  separate form. Adjust to match the practice's actual workflow.
- Do not ask for SSN over the phone.
""",
            },
        ],
    },
    {
        "slug": "dental-recall-and-reminder",
        "name": "Dental Recall & Reminder",
        "description": "Handle routine hygiene recalls, treatment-plan follow-ups, and post-procedure check-ins. Use when the caller says this is a reminder, you're due for, following up, or time for a checkup.",
        "content": DENTAL_RECALL_AND_REMINDER,
        "default_files": [
            {
                "file_path": "references/recall-windows.md",
                "file_kind": "reference",
                "content": """# Recall Windows

## Hygiene recalls

| Type | Interval |
|---|---|
| Routine prophylaxis (low-risk adult) | 6 months |
| Perio maintenance (post-treatment) | 3-4 months |
| High caries risk | 3-4 months |
| Pediatric (high-risk) | 6 months |

## Treatment-plan follow-ups

| Treatment | Follow-up |
|---|---|
| Filling | None required, next routine recall |
| Crown | 2-week delivery appointment |
| Root canal | Crown within 30 days; routine recall 6 months |
| Extraction (simple) | 1-week check call |
| Extraction (surgical) | 1-week check call |

## Phrasing

- "You're due for" — use for recalls that match the typical interval
- "It's been about six months since" — for routine recalls
- "We'd like to see you back" — for treatment-plan follow-ups
- Avoid "overdue" — it sounds accusatory and is rarely accurate.
""",
            },
        ],
    },
    {
        "slug": "dental-escalation",
        "name": "Dental Escalation",
        "description": "Route urgent, sensitive, or complaint calls to a human fast: acute pain, swelling, trauma, billing disputes, requests for a manager. Use when the caller says I'm in pain, my face is swollen, I want to speak to, this is unacceptable, or I want my money back.",
        "content": DENTAL_ESCALATION,
        "default_files": [],
    },

    # ── Restaurant ──────────────────────────────────────────────────────────
    {
        "slug": "restaurant-reservation-booking",
        "name": "Restaurant Reservation Booking",
        "description": "Book, reschedule, or cancel a restaurant reservation for parties of 1-6. Use when the caller says table for, reservation for, book a table, change my reservation, or cancel my reservation.",
        "content": RESTAURANT_RESERVATION_BOOKING,
        "default_files": [
            {
                "file_path": "references/hours-and-seating.md",
                "file_kind": "reference",
                "content": """# Hours & Seating

The restaurant will fork this file and edit to match its own layout.
Keep numbers current; they're used to assess availability for unusual
requests.

## Hours

| Service | Days | Hours |
|---|---|---|
| Lunch | Tue-Sun | 11:30 AM – 2:30 PM |
| Dinner | Tue-Sun | 5:00 PM – 10:00 PM |
| Brunch | Sat-Sun | 10:00 AM – 2:00 PM |
| Closed | Monday | — |

## Last seating

- Lunch: 2:00 PM
- Dinner: 9:30 PM
- Brunch: 1:30 PM

## Seating capacity

| Section | Tables | Total seats |
|---|---|---|
| Main dining | 18 | 56 |
| Bar | 8 | 16 |
| Patio | 6 | 24 |
| Private room | 1 | 12 |

Notes:
- The bar and patio share a waitlist; main dining and private room are
  separate.
- "Private room" is the only section that books in 12+ parties; route
  smaller private requests to manager via escalation skill.
""",
            },
        ],
    },
    {
        "slug": "restaurant-menu-and-info",
        "name": "Restaurant Menu & Info",
        "description": "Answer questions about the menu, hours, location, dietary options, specials, and reservations policy. Use when the caller asks what's on the menu, do you have, are you open, where are you, do you take walk-ins, or is it kid-friendly.",
        "content": RESTAURANT_MENU_AND_INFO,
        "default_files": [
            {
                "file_path": "references/menu-highlights.md",
                "file_kind": "reference",
                "content": """# Menu Highlights

The restaurant will fork this file and update as the menu changes. Keep
it short; the agent reads this in one shot when the caller asks about
the menu.

## Signature dishes

| Dish | Description |
|---|---|
| Pan-seared branzino | Whole fish, lemon-capper brown butter, seasonal vegetables |
| Wild mushroom risotto | Arborio rice, porcini, parmesan, white truffle oil |
| 14-oz dry-aged ribeye | 45-day dry age, bone marrow butter, twice-baked potato |
| House-made pappardelle | Slow-braised short rib ragù, grana padano |

## Dietary tags

The kitchen can accommodate:

- Vegetarian (most pasta and sides are adaptable)
- Vegan (limited options, ask the chef with 24h notice)
- Gluten-free (most proteins and sides; pasta requires 24h notice)
- Nut allergies (no peanuts in the kitchen; tree nuts present)

For severe allergies, recommend the caller notify the server at seating.

## Daily specials

- Tue: half-price bottles of wine under $80
- Wed: pasta night, 20% off all pasta dishes
- Thu: oyster night, $1.50 each
- Sun brunch: free bottomless mimosas with entrée
""",
            },
        ],
    },
    {
        "slug": "restaurant-special-request",
        "name": "Restaurant Special Request",
        "description": "Handle non-reservation requests: takeout / pickup orders, catering inquiries, custom celebrations, gift card purchases. Use when the caller says takeout, catering, gift card, private room for 7+, or a celebration.",
        "content": RESTAURANT_SPECIAL_REQUEST,
        "default_files": [],
    },
    {
        "slug": "restaurant-reservation-followup",
        "name": "Restaurant Reservation Follow-up",
        "description": "Handle post-visit follow-ups: thank-you, lost-and-found, repeat-visit outreach. Use when the caller says this is about your recent visit, following up, did you enjoy, or I left something behind.",
        "content": RESTAURANT_RESERVATION_FOLLOWUP,
        "default_files": [],
    },
    {
        "slug": "restaurant-escalation",
        "name": "Restaurant Escalation",
        "description": "Route complaints, allergy incidents, billing disputes, private events, lost-and-found, and requests for a manager. Use when the caller says this was terrible, I want a refund, I had an allergic reaction, I want to speak to, or I need to book for 12 people.",
        "content": RESTAURANT_ESCALATION,
        "default_files": [],
    },

    # ── HVAC ────────────────────────────────────────────────────────────────
    {
        "slug": "hvac-service-appointment",
        "name": "HVAC Service Appointment",
        "description": "Schedule an HVAC service call for heating, cooling, ventilation, thermostat, or water heater issues. Use when the caller says no heat, no air, AC is out, furnace won't start, thermostat isn't working, or schedule a service call.",
        "content": HVAC_SERVICE_APPOINTMENT,
        "default_files": [
            {
                "file_path": "references/equipment-types.md",
                "file_kind": "reference",
                "content": """# Equipment Types

Common HVAC equipment categories. The agent uses the caller's words, not
brand names — don't push the caller to identify their specific brand or
model.

## Heating

- Furnace (gas, electric, oil)
- Boiler
- Heat pump
- Ductless mini-split
- Radiant floor / baseboard

## Cooling

- Central air conditioner
- Heat pump (cooling mode)
- Ductless mini-split
- Window unit (limited service)
- Evaporative cooler (dry climates)

## Ventilation

- Whole-house fan
- ERV / HRV (energy / heat recovery ventilator)
- Ductwork
- Air handler

## Controls

- Thermostat (programmable, smart, manual)
- Zoning system
- Smart-home integration

## Water heating (if the practice services it)

- Tank water heater (gas, electric)
- Tankless water heater
- Heat pump water heater

When the caller is unsure, take their description at face value: the
technician on-site will identify the equipment.
""",
            },
        ],
    },
    {
        "slug": "hvac-service-info",
        "name": "HVAC Service Info",
        "description": "Answer general questions about HVAC service: pricing model, warranty coverage, maintenance plans, pre-visit prep, equipment serviced. Use when the caller asks do you service, what's your service call fee, is this covered under warranty, or do you have a maintenance plan.",
        "content": HVAC_SERVICE_INFO,
        "default_files": [
            {
                "file_path": "references/pricing-and-plans.md",
                "file_kind": "reference",
                "content": """# Pricing & Plans

## Service call

- Standard service call fee: $89 (waived with repair)
- After-hours / weekend: $149 (waived with repair over $300)
- Diagnostic-only visits are billed at the service-call fee

## Maintenance plan

| Tier | Visits / year | Cost / year | Includes |
|---|---|---|---|
| Basic | 2 (spring + fall) | $179 | Filter swap, visual inspection, priority scheduling |
| Plus | 2 | $289 | Basic + coil cleaning, condensate flush, thermostat calibration |
| Premium | 2 | $449 | Plus + 10% off any repair, waived diagnostic |

## What's not covered by maintenance

- Repairs (parts and labor)
- Equipment replacement
- After-hours emergency calls

## Warranty handling

Most manufacturer warranties require:

- Equipment registered within 60 days of install
- Annual maintenance documented
- Use of authorized service provider for warranty repairs

We do not promise warranty coverage without verifying the equipment and
its registration. Offer to have someone follow up if the caller isn't
sure.
""",
            },
        ],
    },
    {
        "slug": "hvac-diagnosis-and-triage",
        "name": "HVAC Diagnosis & Triage",
        "description": "Walk the caller through basic HVAC troubleshooting and decide whether a service call is needed. Use when the caller says why isn't my, what could cause, is this normal, how do I check, or my unit is making a sound.",
        "content": HVAC_DIAGNOSIS_AND_TRIAGE,
        "default_files": [
            {
                "file_path": "references/common-symptoms.md",
                "file_kind": "reference",
                "content": """# Common Symptoms

Quick basic-checklist the agent walks through before recommending a
service call. If the symptom resolves during the call, no appointment
needed. If it doesn't, escalate to service appointment.

## No heat

1. Thermostat set to "heat" mode (not "cool" or "off")?
2. Setpoint above current room temperature?
3. Furnace power switch on (usually a light switch near the furnace)?
4. Air filter clean? (clogged filter is the #1 cause)
5. Pilot light on (for older gas furnaces)?
6. Recent power outage? (some systems need a manual restart)

If all six check out and still no heat → service call.

## No cooling

1. Thermostat set to "cool" mode?
2. Setpoint below current room temperature?
3. Outdoor unit running? (you should hear the compressor)
4. Air filter clean?
5. Condensate drain clear? (some systems shut down if the drain backs up)
6. Recent power outage?

If all six check out and still no cool → service call.

## Thermostat not responding

1. Batteries fresh?
2. Display lit?
3. Circuit breaker for the HVAC system on?
4. Recently changed the batteries or settings?

If still unresponsive → service call.

## Weak airflow

1. Filter age? (most filters are 1-3 months)
2. Vents open in the affected rooms?
3. Recent ductwork changes?

Most often filter-related. If a fresh filter doesn't fix it → service call.

## Strange sounds

- Clicking on startup: usually normal (system cycling)
- Hissing: refrigerant leak possibility; service call
- Banging / clanking: blower or compressor issue; service call
- High-pitched squeal: belt or bearing; service call

For any persistent or unusual sound → service call.
""",
            },
        ],
    },
    {
        "slug": "hvac-maintenance-recall",
        "name": "HVAC Maintenance Recall",
        "description": "Handle scheduled maintenance: semi-annual checkups, filter-swap reminders, post-service follow-ups, seasonal tune-up campaigns. Use when the caller says this is your maintenance reminder, you're due for a tune-up, time for your spring or fall checkup.",
        "content": HVAC_MAINTENANCE_RECALL,
        "default_files": [
            {
                "file_path": "references/seasonal-cadence.md",
                "file_kind": "reference",
                "content": """# Seasonal Cadence

## Spring (Mar-May)

- Cooling system checkup: filter, coils, condensate, refrigerant level
- Recommended timing: March-April, before first heat wave
- Suggest when temperatures climb above 70°F consistently

## Fall (Sep-Nov)

- Heating system checkup: filter, burners, heat exchanger, ignition
- Recommended timing: September-October, before first cold snap
- Suggest when temperatures drop below 50°F consistently

## Filter reminders

- 1-inch filters: every 1-3 months
- 4-inch media filters: every 6-12 months
- High-MERV / electrostatic: vary; follow manufacturer

## Post-service follow-up timing

- 1 week after any repair (especially refrigerant or electrical)
- 1 month after system replacement (verify performance)
""",
            },
        ],
    },
    {
        "slug": "hvac-escalation",
        "name": "HVAC Escalation",
        "description": "Route HVAC emergencies and complaints: gas smell, CO alarm, sparking, smoke, water near electrical, billing disputes, requests for a manager. Use when the caller says I smell gas, CO alarm, sparking, smoke, water everywhere, this is the third time, or I want to speak to.",
        "content": HVAC_ESCALATION,
        "default_files": [
            {
                "file_path": "references/emergency-contacts.md",
                "file_kind": "reference",
                "content": """# Emergency Contacts

Only load this when the agent needs an emergency number to share with
the caller. Keep the list current; numbers change.

## Life / property threats

- Gas leak: leave the building, then call 911 and the local utility
  gas-emergency line (typically 1-800-GAS-LEAK)
- Carbon monoxide: leave the building, then 911 and utility
- Fire: 911
- Major water leak near electrical: 911 (electrocution risk) and
  water utility

## After-hours service partners

- 24h emergency dispatch: see practice's internal list
- For vulnerable residents (elderly, infant, medical condition
  requiring climate control): prioritize same-day response

## When in doubt

Direct the caller to 911 first. Do not attempt remote diagnosis for
life-safety situations.
""",
            },
        ],
    },
]
