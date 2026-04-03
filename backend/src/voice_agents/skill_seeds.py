"""
Built-in skill content for seeding new organizations.

Each skill contains comprehensive markdown with procedures, edge cases,
and example dialogue. These are loaded progressively — only the name and
description appear in the system prompt; full content loads via load_skill tool.
"""

BUILT_IN_SKILLS = [
    {
        "slug": "appointment-booking",
        "name": "Appointment Booking",
        "description": "Handle scheduling, rescheduling, and cancellation of appointments.",
        "content": """# Appointment Booking

## When to Use
- Caller explicitly asks to book, change, or cancel an appointment
- Conversation naturally leads to scheduling
- Caller asks about availability

## Booking Procedure
1. **Greet and confirm intent**: "I'd be happy to help you schedule an appointment."
2. **Ask for preferred date and time**: Offer 2-3 options if possible.
3. **Check availability** using the calendar tool (if connected).
4. **Collect required information**:
   - Full name
   - Contact phone number
   - Reason for visit / service type
   - For new patients/customers: date of birth, insurance info (if applicable)
5. **Confirm all details**: Read back date, time, service type, and name.
6. **Provide pre-visit instructions**: "Please arrive 15 minutes early" or similar.
7. **Offer to send confirmation**: Via text or email if available.

## Rescheduling Procedure
1. Ask for the caller's name to locate the existing appointment.
2. Confirm the current appointment details.
3. Ask for the new preferred date and time.
4. Check availability and confirm the change.
5. Note: Mention any rescheduling policies (e.g., 24-hour notice).

## Cancellation Procedure
1. Ask for the caller's name and appointment date.
2. Confirm the appointment they want to cancel.
3. Ask for the reason (optional, for records).
4. Mention any cancellation policies or fees if applicable.
5. Offer to reschedule instead: "Would you like to reschedule for another time?"
6. Confirm the cancellation.

## Edge Cases
- **No availability on preferred date**: Offer the 3 nearest available slots.
- **Caller unsure of service needed**: Ask clarifying questions about their needs.
- **Walk-in inquiry**: Explain walk-in policy if applicable, or recommend booking.
- **Multiple appointments**: Handle one at a time, confirm each before moving to the next.
- **Emergency/urgent**: Assess urgency and escalate if needed rather than scheduling normally.
""",
    },
    {
        "slug": "call-transfer",
        "name": "Call Transfer",
        "description": "Escalate calls to a human agent with proper context handoff.",
        "content": """# Call Transfer

## When to Use
- Caller explicitly asks to speak with a person
- Issue is beyond your capabilities or authorization
- Caller is upset and needs human empathy
- Request requires access to systems you don't have
- Legal, medical, or financial advice is needed

## Transfer Procedure
1. **Acknowledge the need**: "I understand you'd like to speak with someone directly. Let me connect you."
2. **Collect a brief summary** of the issue (so the human agent has context).
3. **Set expectations**: "I'll transfer you now. There may be a brief hold."
4. **Warm transfer** (preferred): Stay on the line and introduce the caller to the agent.
5. If warm transfer unavailable: "I'll transfer you to [department]. I've noted your issue so they'll have context."

## When NOT to Transfer
- Caller asks a question you can answer — try to help first.
- Simple requests (hours, location, general info) — handle these directly.
- Caller is just frustrated but the issue is within your capabilities.

## Handling "I Want a Real Person"
1. Don't take it personally or argue.
2. Acknowledge: "I completely understand. Let me connect you right away."
3. Provide the summary to the human agent.
4. If no human is available: "I'm sorry, no one is available right now. Can I take your number and have someone call you back within [timeframe]?"

## After Hours Transfer
- If transferring outside business hours: "Our team is currently unavailable. I can take a message and have someone call you back first thing tomorrow."
- Collect: name, phone number, brief description of the issue, best time to call back.
""",
    },
    {
        "slug": "faq-responder",
        "name": "FAQ Responder",
        "description": "Answer frequently asked questions from the organization's knowledge base.",
        "content": """# FAQ Responder

## When to Use
- Caller asks a common question about the business
- Questions about hours, location, services, pricing, policies
- General inquiries that don't require scheduling or transactions

## Procedure
1. **Listen to the question** carefully and identify the topic.
2. **Answer directly** — don't ask unnecessary follow-up questions for simple info.
3. **Use business context** from your instructions (hours, location, services).
4. **Be specific**: Give actual hours, addresses, and prices when available.
5. **Offer more help**: "Is there anything else I can help you with?"

## Common Question Categories
- **Business hours**: State exact hours, including weekends and holidays.
- **Location and directions**: Provide full address and any helpful landmarks.
- **Services offered**: List services clearly, mention specialties.
- **Pricing**: Share prices if available; if not, offer to have someone follow up.
- **Insurance/payment**: Explain accepted methods, insurance networks.
- **Wait times**: Be honest about current wait times if known.
- **Parking**: Mention parking availability and any validation.

## When You Don't Know the Answer
1. Don't guess or make up information.
2. Say: "That's a great question. I want to make sure I give you accurate information."
3. Offer alternatives:
   - "Let me have someone call you back with that information."
   - "You can find that on our website at [URL]."
   - "I can transfer you to someone who can help with that specific question."

## Tone
- Be confident and helpful, not robotic.
- Keep answers concise — callers on the phone want quick answers.
- If listing multiple items, keep it to 3-4 at a time to avoid overwhelming the caller.
""",
    },
    {
        "slug": "after-hours",
        "name": "After Hours",
        "description": "Handle calls received outside business hours with voicemail and callback scheduling.",
        "content": """# After Hours

## When to Use
- Call received outside of business hours
- Weekends or holidays when the office is closed
- Staff unavailable but phone system is active

## Procedure
1. **Greet warmly**: "Thank you for calling {{org.name}}. We're currently closed."
2. **State business hours**: "Our regular hours are [hours]. We'll reopen [next opening]."
3. **Offer to take a message**:
   - Collect: caller's name, phone number, reason for calling
   - Ask: "Is there a best time for us to call you back?"
4. **For urgent matters**:
   - If the business has an emergency line: "For emergencies, please call [number]."
   - If medical/dental: "If this is a medical emergency, please call 911 or go to your nearest emergency room."
5. **Confirm the message**: "I have your name as [name] and number as [number]. Someone will call you back [timeframe]."
6. **Close warmly**: "Thank you for calling. We look forward to helping you during our regular hours."

## What NOT to Do
- Don't try to schedule appointments for dates you can't verify availability.
- Don't provide medical, legal, or financial advice.
- Don't promise specific callback times unless instructed to.
- Don't share personal phone numbers of staff members.

## Emergency Protocols
- **Medical emergency**: Direct to 911 immediately.
- **Urgent but not emergency**: Take message, mark as urgent.
- **Billing emergency** (e.g., disputed charge): Take message, reassure the caller.
""",
    },
    {
        "slug": "lead-qualification",
        "name": "Lead Qualification",
        "description": "Qualify inbound sales leads using structured questioning.",
        "content": """# Lead Qualification

## When to Use
- Caller inquires about services or products
- Potential new customer exploring options
- Someone responding to marketing or advertising

## Qualification Framework (BANT)
Gather these four pieces of information naturally — don't interrogate:

### 1. Budget
- "Are you looking for a specific price range?"
- "Have you gotten quotes from other providers?"
- Don't push if they're uncomfortable discussing budget.

### 2. Authority
- "Are you the one making the decision on this, or is there someone else involved?"
- "Should I include anyone else when we follow up?"

### 3. Need
- "What brought you to us today?"
- "Can you tell me more about what you're looking for?"
- "What's most important to you in a [service/product]?"

### 4. Timeline
- "When are you hoping to get started?"
- "Is there a deadline or event driving this?"

## Procedure
1. **Warm greeting**: Be enthusiastic but not pushy.
2. **Ask open-ended questions**: Let them talk, listen for buying signals.
3. **Take notes**: Record all key information for follow-up.
4. **Provide value**: Answer their questions honestly, share relevant info.
5. **Next step**: Schedule a consultation, demo, or follow-up call.
6. **Collect contact info**: Name, phone, email, best time to reach them.

## Do's and Don'ts
- **Do**: Be genuinely helpful, not salesy.
- **Do**: Acknowledge their needs before pitching.
- **Don't**: Pressure or create false urgency.
- **Don't**: Badmouth competitors.
- **Don't**: Make promises you can't keep about pricing or availability.
""",
    },
    {
        "slug": "payment-collection",
        "name": "Payment Collection",
        "description": "Process payments, explain invoices, and handle billing inquiries.",
        "content": """# Payment Collection

## When to Use
- Caller asks about a bill or invoice
- Caller wants to make a payment
- Billing disputes or questions about charges
- Payment plan inquiries

## Payment Procedure
1. **Verify identity**: Ask for name and account/invoice number.
2. **Pull up account details** using available tools.
3. **Explain charges clearly**: Break down the invoice line by line if asked.
4. **Process payment** if tools are available:
   - Confirm the amount
   - Collect payment method details
   - Process and confirm the transaction
   - Provide a confirmation number
5. **If unable to process**: "I can note your intent to pay. Our billing team will follow up with payment options."

## Billing Inquiry Procedure
1. Listen to the specific concern.
2. Explain the charge in plain language (avoid jargon).
3. If there's a legitimate error: "I see the issue. Let me get this corrected for you."
4. If the charge is correct but unexpected: Explain what it's for calmly.
5. If you can't resolve: Escalate to the billing department.

## Payment Plans
- If the caller can't pay in full: "We do offer payment plan options."
- Explain available plans (if you have that information).
- If unsure of plan details: "Let me connect you with our billing team to discuss payment arrangements."

## Sensitive Handling
- **Never read full credit card numbers back** to the caller.
- Be empathetic with callers struggling to pay.
- Don't make judgments about a caller's financial situation.
- Follow PCI compliance: Don't store card details.
- For disputed charges: Acknowledge the concern, investigate, and follow up.
""",
    },
]
