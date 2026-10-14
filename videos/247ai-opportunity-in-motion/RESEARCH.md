# 24x7 AI — launch film research

## Product truth and business value

The audience is an owner or operator of a local service business. The immediate value is converting an incoming conversation into a useful next step when the team is occupied or closed. The film leads with that outcome; configuration follows as evidence of control.

| Capability verified | Business value | Film treatment | Evidence in selected worktree |
| --- | --- | --- | --- |
| Natural voice on a business number and website | Customers can ask instead of navigating menus | Two channels converge into one voice signal | frontend/src/app/page.tsx; voice-ws /ws and /twilio runtime; public site |
| Business instructions, services, hours, policies | Relevant answers and consistent handling | Hours/services/workflows become a coherent signal | docs/02_features/voice_agents/skills.md; platform tour |
| Calendar availability and appointment create/update/cancel | A conversation can become a booking | Question → availability → confirmed slot | shared/voice_agents/tools/implementations/google_calendar_appointment.py |
| Leads, orders/requests, human callback details | Owner receives actionable context | Capture → connect → next step | google_sheets_lead_capture.py; callback_request.py; configured skills |
| Calendar, email, records, configurable remote tools | Actions enter existing workflows | Three connected outcome nodes, generic categories | shared tool registry; resend_email.py; Google Sheets implementations |
| Test/approve, recordings, transcripts, call logs | Owner can shape and review the experience | Instructions → test → review | docs/02_features/platform-tour.md; frontend call surfaces |
| Business-specific workflows | Fits different service businesses | Services, appointments and requests, without a feature inventory | Current 15-skill library and public demos |

Source precedence: executable configuration and registry > current public product site > current documentation sections. Later legacy sections mentioning LiveKit, direct payment collection or live transfer were excluded. No pricing, uptime guarantee, unlimited calls, fabricated ROI, customer logos, testimonials or compliance claims.

The public site was captured fresh at https://www.247ai.live/. Capture returned HTTP 200, 12 screenshots, local Geist fonts and SVG assets. It reported a degraded extraction phase and omitted capped assets; this film uses only verified files. All diagrammatic call/booking surfaces are explicitly illustrative, not claimed recordings of a live customer transaction.

## Reference study

These are observations from selected representative moments, not a frame-by-frame reconstruction or an audio transcription. No reference footage, music or brand assets are reused.

| Reference | Observed character | Why it works | Principle adopted |
| --- | --- | --- | --- |
| [Cap](https://www.youtube.com/watch?v=dupJQXtZU0Q) | Sky blue/cloud environment, white recorder controls, large feature text, floating tilted browser crop | A consistent world makes the UI feel tangible; one task remains readable | One persistent visual world; macro views of the meaningful action |
| [Base44](https://www.youtube.com/watch?v=FXLmWojBELE) | Cream editorial typography switches to charcoal/lime, close code/dashboard crops, oversized verbs, icon grids | Contrast creates chapters; words and product detail share the rhythm | Large verb-led type; decisive dark/light cuts |
| [Teamble](https://www.youtube.com/watch?v=xNUx-rMGvvw) | Ink field, restrained purple glow, angled white product panels, light feedback-card stage | Depth makes a static product legible; value headers organize a complex story | Motivated perspective, clear value-before-detail hierarchy |
| [Lovable 2.0](https://www.youtube.com/watch?v=xDwR1_vrIg8) | Cream brand forms, giant changing number, traveling tubular color line, tilted product canvas, colored edge light | Scale shifts and the continuous line give an abstract product physical momentum | One traveling signal; restrained spectacular scale changes |
| [Zelios collection](https://zelios.agency/brand-launch-videos) | Article and embedded examples emphasize familiar friction, restraint, identity, chaos-to-clarity | Strong launches connect product mechanisms to a recognizable human problem | Start with a customer's call, finish with the owner's attention |
| [What Ships](https://whatships.com/) | Curated launch gallery; sampled Paper Mono production overview with typography variations and tightly arranged music/scene timeline | Motion and sound are planned together rather than decorated afterward | Phrase-level timing and a composed sonic ending |

## Concepts considered

1. **Opportunity in motion** — a call signal transforms into actions. Selected: distinctive to voice, causal, coherent across nine beats.
2. The night shift — a clock moves from closed shop to morning callback. Strong emotion, narrower after-hours framing.
3. A day without interruptions — owner's work with voice as a parallel track. More live action than the requested motion-led direction.
4. A customer speaks the whole film — conversational words turn into service objects. Unusual, but too much synthetic demo dialogue.
5. The call is a travelling camera — one continuous geometric tunnel through business workflows. Unusual and cinematic, but clarity could suffer.

## Original direction

**Opportunity in motion.** One circular call pulse becomes voice, travels between phone and web, organizes business knowledge, draws a calendar confirmation, routes a captured request, and becomes the official phone mark. Cobalt, cool paper and midnight come from the brand; a small mint success accent supports completed actions. The film alternates expansive type, dimensional object staging, and precise diagrams. Sparse narration leaves room for the original electronic score.

## Assets and rights

Official phone marks from frontend/public/brand-mark.svg and brand-mark-on-dark.svg. Geist / Geist Mono captured from the official public site ([official SIL Open Font License source](https://github.com/vercel/geist-font)). Original instrumental generated through Lyria 3.5; synthetic English narration through MiniMax speech-2.8-hd. No likeness cloning. Generated audio metadata and cost recorded in assets/audio/provenance.json. Third-party service logos are not used.

## Scope

Fresh project only. Earlier launch-film projects were not opened. No application code, repository configuration, commits, branches, deployment or production data were changed.

\n