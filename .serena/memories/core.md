# Core

AI voice agent platform (voice-only). Multi-tenant SaaS — orgs, RBAC, billing, phone numbers, skills.

## Project structure
- `backend/` — FastAPI app (Python 3.11), entry: `main.py`, routes in `src/<module>/routes.py`, services in `src/<module>/services.py`
- `frontend/` — Next.js 15 + React 19 + Tailwind CSS v4, App Router, pages in `src/app/(dashboard)/`
- `shared/` — Code shared between backend + worker (config, models, services)
- `worker/` — LiveKit voice AI agent worker
- `supabase/` — Local Supabase config (runs on `http://127.0.0.1:54321`)
- `e2e/` — Playwright E2E tests (isolated Docker stack on ports 3001/8001)

## Key modules (backend)
- `auth/` — Google OAuth, JWT, Supabase Auth
- `rbac/` — Roles, permissions, invitations
- `billing/` — Stripe subscriptions/credits
- `voice_agents/` — Agent CRUD, skills, tools, embed/call button
- `phone_numbers/` — Twilio search/purchase/assign
- `call_logs/` — Call logging + transcription
- `notifications/` — Resend email notifications
- `security/` — Rate limiting, headers, encryption
- `services/` — Background services (token refresh)

## Key memories
- Tech stack details: `mem:tech_stack`
- Dev/test/lint commands: `mem:suggested_commands`
- Code conventions: `mem:conventions`
- Task completion checklist: `mem:task_completion`
