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
- Each chapter is a full section with copy on one side and the preview on
  the other, alternating sides down the page, plus a sticky chapter-jump
  nav. Every step renders its own scene (no reused generic card): cursors
  click Save/Test/Approve, live calls connect with waveforms and
  transcripts, bookings travel a beam into the calendar, skills attach and
  apply, recordings play. Steps auto-advance only while their section is
  on screen, with play/pause, replay, clickable step dots, and hover/focus
  hold. Each step has its own dwell time (scene timeline plus a beat of
  hold), so transitions never cut a scene off mid-story. Reduced motion
  shows a static first step with manual dots.
- Motion is transform/opacity plus one interval per visible section; there
  is no canvas on this page.
- The page is in the sitemap (`monthly`, `0.9`). It is linked from the
  shared header nav and from a guided-tour band on the homepage (with deep
  links into each chapter).

## Validation

From `frontend/`:

```bash
npm run test:run -- src/app/__tests__/how-it-works.test.tsx src/components/tour
npx tsc --noEmit
npx eslint src/components/tour src/app/how-it-works
```

Browser contracts live in `e2e/tests/test_how_it_works.py`: tab
switching, replay control, demo-request navigation, mobile layout, and
horizontal overflow. Also visually inspect all five chapters in both
themes on desktop and mobile.
