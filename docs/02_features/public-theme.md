# Public theme

All public marketing pages (homepage, industry pages, live demos,
request-demo, and auth) share the homepage atmosphere: night ink blue by
default, day paper blue on toggle. The choice is the single site-wide
theme, so a toggle anywhere is honored everywhere, including the
dashboard. Dashboard styling is otherwise unaffected.

## How it works

- `frontend/src/contexts/theme-context.tsx` is the single source of truth
  (`"light"` / `"dark"` / `"system"`, persisted under the `"theme"` key,
  applied as a class on `<html>`). It migrates the legacy public-pages key
  (`"247ai-home-theme"`: night becomes dark, day becomes light) on a
  returning visitor's first load, and picks up choices made in other tabs.
  The apply effect never overwrites a stored choice with the default on
  mount (see the `applyRan` guard).
- `frontend/src/components/public-theme/public-theme-context.tsx` is a thin
  adapter: `"dark"` shows night, `"light"` shows day. With no explicit
  choice yet, public pages keep their historical night default while the
  dashboard follows the OS; the moment anyone toggles (public switch,
  dashboard header toggle, or settings page), both surfaces move together.
  Before hydration the night default is shown so server render and first
  paint match without a flash.
- `public-theme-root.tsx` scopes the tokens and adds the `dark` class in
  night mode. That class switches every Tailwind `dark:` style and shadcn
  token inside, so the toggle drives functional widgets (forms, call
  cards, alerts) as well as the token-based chrome.
- `public-theme.module.css` holds the token values (mirroring the homepage
  atmosphere) plus the shared header, footer, eyebrow, panel, button, and
  split-layout primitives. The filled primary CTA has an outlined secondary
  sibling for paired hero actions. Industry pages also use a quiet secondary AI
  solutions callout near the bottom. Root-scoped color rules (`.root .primary`,
  `.root a.secondaryOutline`,
  `.root .signIn`) keep button and link colors winning over the generic
  `.root a` reset.
- `theme-switch.tsx` is the single switch visual for the whole site (sun,
  sliding knob, moon, `role="switch"`), used by the shared public header and
  the dashboard header alike. The knob position comes
  from the button's own `data-dark` state. Colors come from explicit
  `--switch-*` mappings per surface (atmosphere tokens on public pages,
  shadcn foreground tokens in `globals.css` for the dashboard), because
  similarly-named tokens mean different things per surface and a shared
  fallback chain once washed the dashboard control out. `ThemeSwitch` is
  presentational (each surface wires what it shows); `SiteThemeSwitch`
  wires it to the resolved site-wide theme for the dashboard header. The
  dashboard settings page keeps its explicit light/dark/system selector,
  since a binary switch cannot express "follow system."
- `public-header.tsx` / `public-footer.tsx` are the common chrome for the
  homepage, landing pages, demos, request-demo, and auth routes. Header
  anchors point at homepage sections (`/#features`, `/#demos`,
  `/#industries`, `/#integrations`, `/#pricing`) with one route link to
  `/how-it-works`, so they work from every public page. At the
  mobile breakpoint the same header exposes a keyboard-dismissible right-side
  drawer approximately 80% of the viewport wide; selecting a destination or
  clicking the scrim closes it, and the drawer intentionally keeps the
  homepage's compact navigation without duplicating the conversation CTA.
- Demo call cards use a compact short-desktop layout so the call action stays
  reachable on 1280×720 screens while the full spacing remains available on
  taller displays.

## Page coverage

- `/` renders the aurora hero with the live concurrency story on the shared theme (see
  [homepage experience](homepage-experience.md); the previous particle journey
  is preserved at `/home-classic`) and uses the same shared
  header component as every other public route.
- The descriptive industry routes render the shared `IndustryPage` template on
  the public theme. Their heroes fill the first viewport like the homepage
  hero, pair the filled primary CTA with the outlined secondary, and stack
  both full-width on mobile. Each page includes a fifth outcome card for existing
  business-tool integrations and a secondary AI-solutions callout below the
  main conversion path. The shared footer includes the same subtle attribution
  link.
- `/demo/[slug]` keeps all call logic; only the header, hero, and card
  chrome moved to the theme, plus example opener lines per agent so
  first-time callers know what to say. The amber public-demo notice is
  untouched.
- `/demo/[slug]/outcome` leads with the proven results (always expanded,
  plain language: what was saved, where it went, what the tool confirmed),
  then the business value, star rating, and the interest form. Jargon
  ("handoff", "workflow", "provider mutation") stays out of headings.
  Layout order is deliberate: confirmation banner with a "See what was
  saved" anchor, then the rating strip merged into the conversion panel
  (both in the main view), then the value strip, then the full captured
  details at `#call-results`. Star ratings dual-write: one PII-free row
  per session in the platform (`demo_feedback`, summarized on the admin
  Interests page) plus the PostHog funnel event; the interest form writes
  platform leads visible in the same admin surface.
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
npx eslint src/components/public-theme src/contexts src/app/demo src/app/request-demo src/app/auth
```

Contracts live in `src/components/public-theme/public-theme.test.tsx`
(single key, night default, persisted restore, legacy migration,
public-toggle/dashboard-control sync, storage failure, header/footer
links) plus the existing page suites. Also visually verify the toggle
syncs between a public page and the dashboard in both directions, with a
reload in between.
