# Platform tour (/how-it-works)

The guided tour explains the 24x7 AI platform to non-technical business
owners in five chapters: create an agent in plain words, answer on the
website and business number, connect existing business tools, teach skills
in natural language, and review calls with recordings and logs. Messaging
stays owner-first (easy setup, test-and-approve before anything goes live).

## Presentation

- `frontend/src/app/how-it-works/page.tsx` renders
  `components/tour/platform-tour-page.tsx` on the shared public theme.
- Each chapter pairs plain-language steps with a stylized preview of the
  real product screen (agent setup form, channel cards, tool rows, skill
  library, call-log table) using one fictional business, and every preview
  frame is tagged "Illustrative preview". Nothing invents customer stories
  or live activity.
- Every chapter keeps all three highlights visible as rows with an expanded
  explanation beside its matching preview. The sticky chapter nav jumps to
  sections; it does not switch which highlight is shown. Each chapter sits in
  its own softly tinted panel with a numbered label and header divider, while
  numbered highlight rows stay grouped inside. Each highlight has
  its own scene (no reused generic card): cursors click Save/Test/Approve,
  live calls connect with waveforms and transcripts, bookings travel a beam
  into the calendar, skills attach and apply, and recordings play. The phone
  number types one character at a time, then the cursor clicks Save; the final
  digit remains fully visible. In the website preview, the browser frame stays
  visible while the Talk to us button appears after the snippet is saved. Copy
  explains that the 24x7 AI assistant answers without phone menus or hold music,
  follows the business owner's instructions, and captures callback requests.
- Scene motion is illustrative. Each preview starts when it enters the
  viewport, replays after its timeline and a three-second pause, and pauses
  outside the viewport. The page remains readable without animation, and
  reduced-motion preferences disable motion across the tour. No canvas is
  used.
- The page is in the sitemap (`monthly`, `0.9`). It is linked from the
  shared header nav and from a guided-tour band on the homepage (with deep
  links into each chapter).
- The hero scroll cue points to the five chapters and leaves room for the
  sticky public header when navigating to the section.

## Validation

From `frontend/`:

```bash
npm run test:run -- src/app/__tests__/how-it-works.test.tsx src/components/tour
npx tsc --noEmit
npx eslint src/components/tour src/app/how-it-works
```

Browser contracts live in `e2e/tests/test_how_it_works.py`: all highlights
remain visible, a visible preview replays, chapter links navigate,
demo-request navigation works, and the mobile layout has no horizontal
overflow. Visually inspect all five chapters in both themes on desktop and
mobile.
