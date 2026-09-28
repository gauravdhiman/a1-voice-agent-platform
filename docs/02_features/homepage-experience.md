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

- Only the homepage carries the aurora hero and concurrency story. The day/night choice,
  atmosphere tokens, and public header are shared with the other public pages
  (see [public theme](public-theme.md)). Other public routes keep their own
  layouts and the dashboard keeps its existing design.
- `frontend/src/app/page.tsx` renders `components/home/home-page.tsx`.
  The previous particle-journey experience is preserved unchanged as
  `components/home/home-page-legacy.tsx` and served at `/home-classic`
  (kept out of the sitemap) as a fallback while the new presentation rolls out.
- Primary actions lead to `/request-demo`; sign-in leads to `/auth/signin`.
- The appointment, service-request, and restaurant-order demos keep their
  dedicated routes. The homepage itself does not request microphone
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
- A guided-tour band sits between the live demos and the industries: one
  primary CTA plus deep links into each `/how-it-works` chapter, so
  post-demo curiosity has somewhere to go (see
  [platform tour](platform-tour.md)).
- Pricing retains the existing concierge-pilot positioning and $79 starting
  monthly-plan copy. There is no new checkout or independently maintained plan table.

## Appearance and motion

The page starts in night mode (ink blue and pale blue). The day switch uses cool
paper blue, cobalt, and a small mint accent so the light experience feels clear,
active, and trustworthy. The CSS module scopes both palettes to the homepage.
`247ai-home-theme` remembers an explicit choice. Blocked local storage does not
prevent switching; the choice then lasts only for the current mount.

The hero pairs the unchanged business story with a live concurrency
simulation: a shared 24x7 AI front-desk strip above three self-contained
caller → outcome lanes (Maria's question answered, Sam's urgent job
captured, Priya's table booked), each joined by a short CSS beam with a
traveling pulse. Lanes stack in the same story order on narrow screens, so
the diagram reads identically on mobile and desktop. Beams are transform-only
CSS (in the spirit of MagicUI's Animated Beam, but measuring-free); there is
no WebGL or physics engine. The transcript ticker below the lanes pauses on
hover/focus, via its own play/stop button, the page pause control, or
reduced motion.

The ambient background is a lightweight 2D canvas (`aurora-field.tsx`):
14 gradient orbs plus ~90 specks with mouse parallax, capped at ~30fps
with a 1.5 device-pixel-ratio ceiling. It pauses offscreen, in hidden
tabs, when the visitor pauses motion, and for reduced motion (one static
frame). Section reveals are a tiny IntersectionObserver wrapper with
transform/opacity CSS only.
The ambient canvas has no manual stop control: it pauses offscreen, in
hidden tabs, and renders one static frame for reduced motion. The transcript
ticker provides its own play/stop plus hover/focus hold, which freezes only
the message rotation — beam and wave motion continue while a visitor reads. OS reduced-motion preference disables
ambient movement and CSS transitions/reveals, including when changed mid-session.
The shared public mobile navigation opens as a right-side drawer, supports
Escape, and closes after selecting a destination or clicking outside it.
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
visually inspect both themes and the concurrency simulation on mobile (390px),
tablet (768px), laptop (1280px), desktop (1440px), and widescreen (1920px).

The shared PostCSS configuration uses the object plugin form supported by both
Next.js and Vitest/Vite so CSS modules run through the same Tailwind processor.
Production builds must use a clean build context, never the active dev output.
