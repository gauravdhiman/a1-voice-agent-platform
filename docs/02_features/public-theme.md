# Public theme

All public marketing pages (homepage, industry pages, live demos,
request-demo, and auth) share one atmosphere theme: night ink blue by
default, day paper blue on toggle. The visitor's choice persists across
every public page. Dashboard styling is unaffected.

## How it works

- `frontend/src/components/public-theme/public-theme-context.tsx` holds the
  choice in `PublicThemeProvider` / `usePublicTheme`. The storage key is
  `247ai-home-theme` (shared with the original homepage-only key, so
  returning visitors keep their choice). Blocked storage falls back to
  memory-only switching; choices sync across open tabs.
- `public-theme-root.tsx` scopes the tokens and adds the `dark` class in
  night mode. That class switches every Tailwind `dark:` style and shadcn
  token inside, so the toggle drives functional widgets (forms, call
  cards, alerts) as well as the token-based chrome.
- `public-theme.module.css` holds the token values (mirroring the homepage
  atmosphere) plus the shared header, footer, eyebrow, panel, button, and
  split-layout primitives.
- `public-header.tsx` / `public-footer.tsx` are the common chrome. Header
  anchors point at homepage sections (`/#features`, `/#demos`,
  `/#industries`, `/#integrations`, `/#pricing`) so they work from every
  public page.

## Page coverage

- `/` renders the particle journey inside the same provider (see
  [homepage experience](homepage-experience.md)); its look is unchanged.
- `/dental` and `/hvac` render the shared `IndustryPage` template on the
  public theme. Copy, JSON-LD, and CTA targets are unchanged.
- `/demo/[slug]` keeps all call logic; only the header, hero, and card
  chrome moved to the theme. The amber public-demo notice is untouched.
- `/request-demo`, `/auth/signin`, and `/auth/signup` keep their forms and
  copy; the split brand panels use theme tokens instead of fixed dark
  gradients and stock photos.
- Minor auth flows (reset-password, verify-email, session,
  create-organization) are wrapped in the theme root so their widgets
  follow the toggle. OAuth popup callbacks are intentionally untouched.

## Validation

From `frontend/`:

```bash
npm run test:run -- src/components/public-theme src/components/home src/components/seo src/app/__tests__ src/app/demo
npx tsc --noEmit
npx eslint src/components/public-theme src/app/demo src/app/request-demo src/app/auth
```

Contracts live in `src/components/public-theme/public-theme.test.tsx`
(theme default, persistence, storage failure, header/footer links) plus
the existing page suites. Also visually inspect every converted page in
both themes on desktop and mobile.
