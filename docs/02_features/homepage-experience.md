# Homepage experience

The `/` homepage tells the story of an always-on front desk through three
distinct use cases: resolving routine questions on the call, booking
appointments that grow revenue, and capturing after-hours leads with instant
alerts. Messaging addresses business owners. Example conversations and booking
outcomes are labeled as illustrations; the page does not invent customer
testimonials or live activity. The proof strip uses explicitly sourced,
directional research benchmarks and labels them as not being a promise of
customer results.

## Scope and entry points

- Only the homepage carries the particle journey. The day/night choice and
  the atmosphere tokens are shared with the other public pages (see
  [public theme](public-theme.md)). Other public routes keep their own
  layouts and the dashboard keeps its existing design.
- `frontend/src/app/page.tsx` renders `components/home/home-page.tsx`.
- Primary actions lead to `/request-demo`; sign-in leads to `/auth/signin`.
- Alex, Jordan, and Sofia retain their appointment, service-request, and
  restaurant-order demo routes. The homepage itself does not request microphone
  access or start calls.
- The proof strip leads with three simple signals: up to 85% of unanswered
  callers may not call back (CallRail), 42% of phone leads convert on the call
  (Invoca), and 56% of callers speak with a person (Invoca). Each source is
  linked in the page and the copy qualifies the numbers as directional.
- Industry tiles link to descriptive canonical guides: `/dental-appointment-booking`,
  `/hvac-service-call-answering`, `/restaurant-order-taking`,
  `/plumbing-service-requests`, `/auto-repair-service-booking`,
  `/veterinary-appointment-booking`, `/salon-appointment-booking`, and
  `/real-estate-lead-capture`. The former short paths remain permanent
  redirects for compatibility. The plumbing, auto-repair, veterinary, salon,
  and real-estate pages use a request-workflow CTA until a matching public demo
  is available. The general tile links to `/request-demo`.
- The journey copy names tool categories ("your business calendar", "your
  records"). The integrations section and relevant industry proof/demo copy
  may give examples such as Google Calendar, Microsoft Outlook, Google Sheets,
  or HubSpot, while making clear the connection is configurable around the
  visitor's existing stack.
- The integrations section explicitly welcomes custom business-tool
  connections. A quiet "beyond voice AI" panel after the main pricing CTA
  links to the broader custom-AI-solutions practice without competing with the
  voice-agent conversion path. The footer carries the same secondary
  attribution link.
- Pricing retains the existing concierge-pilot positioning and $79 starting
  monthly-plan copy. There is no new checkout or independently maintained plan table.

## Appearance and motion

The page starts in night mode (ink blue and pale blue). The day switch uses cool
paper blue, cobalt, and a small mint accent so the light experience feels clear,
active, and trustworthy. The CSS module scopes both palettes to the homepage.
`247ai-home-theme` remembers an explicit choice. Blocked local storage does not
prevent switching; the choice then lasts only for the current mount.

The decorative canvas transitions between a ringing counter service bell, a
voice wave, a booking calendar with frame and header guides, and a
three-ring captured-lead check as the visitor scrolls normally. Each
formation holds still for roughly 60% of its chapter (see `shapeProgress` in
`particle-field.tsx`) before easing into the next, so the bell, calendar,
and check can actually be read instead of blurring past. A live caption
under the field names the current formation. There is no scroll hijack
or timed requirement to read a chapter. Semantic headings, copy, navigation, and
calls to action render independently of canvas support.

Canvas work is bounded to 2,400 points on desktop and half that on narrow screens,
with a 1.5 device-pixel-ratio cap and approximately 30fps scheduling. Day-mode
dots render larger with boosted alpha, and dots grow up to 1.45x on very wide
viewports so formations stay solid past 1600px. Animation
stops when the journey leaves the viewport or the document is hidden. The effect
cleans up observers, listeners, and pending frames on unmount. Pointer movement
adds a small decorative offset without React state updates per frame.

The pause button stops ambient movement and reveal animations; scrolling can
still select a new static formation. OS reduced-motion preference disables
ambient movement and CSS transitions/reveals, including when changed mid-session.
Mobile navigation supports Escape and closes after selecting a destination.
The page includes a skip link, visible focus outlines, and labeled controls.

## Validation

From `frontend/`:

```bash
npm run test:run -- src/app/__tests__ src/components/home
npx tsc --noEmit
npx eslint src/components/home src/app/page.tsx
```

The browser contracts live in `e2e/tests/test_homepage_experience.py` and run with
the existing E2E suite. They cover theme persistence, pause control, demo-request
navigation, mobile navigation, reduced motion, and horizontal overflow. Also
visually inspect both themes and the scroll formations on desktop and mobile.

The shared PostCSS configuration uses the object plugin form supported by both
Next.js and Vitest/Vite so CSS modules run through the same Tailwind processor.
Production builds must use a clean build context, never the active dev output.
