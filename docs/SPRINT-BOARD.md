# 📋 Sprint Board

**Last Updated:** 2026-06-19
**Product Direction:** Voice-only — platform focuses exclusively on phone-call
AI agents. Chat / multi-channel agents (F3, F14) are **deprioritized** and not on
the active roadmap.

> This board supersedes the earlier Sprint 1 board. It has been reconciled with
> the actual shipped work (see commit history and `docs/FEATURE_REPORT.md`).

---

## 🟢 Done

| ID | Feature | Completed | Notes |
|----|---------|-----------|-------|
| F2 | Phone Number Management | 2026-03-15 | Twilio search/purchase/assign/release, credit pricing, full CRUD. Tests green. |
| F1 | Skills System — Phase 1 (Markdown Instructions) | 2026-04-01 | Markdown-based agent system prompts (#18). |
| F1 | Skills System — Phase 2a (Progressive Disclosure) | 2026-04-02 | Skills with progressive disclosure (#19). |
| F1 | Skills System — Phase 2b (CRUD / Import / Files / Assignment) | 2026-05-03 | Skill CRUD, GitHub import, file management, agent assignment. |
| F1 | Skills System — Phase 2c (Platform Skills Fork/Refresh) | 2026-05-06 | Platform skills users fork + refresh; hidden-skills badge. |
| F1 | Skills System — Elaborate `appointment-booking` | 2026-05-06 | First "exceptional capability" with rich reference files. |
| F1 | Platform Skills Management (Admin UI) | 2026-06-20 | Platform-admin-only UI at `/platform/skills` to create/edit/hide-restore/manage files for platform skills. Backend RBAC already enforced; added `include_inactive` admin list + frontend UI + service methods + tests. |
| — | Landing Page Redesign | 2026-03-29 | Early-adopter CTA, 4-tier pricing, branding (CogniNets). |
| — | SMB 5-step Onboarding Wizard | 2026-03-29 | Template selection, validation, activation gating. |
| — | Security Hardening | 2026-03-29 | Rate limiting, JWT signature verification, security headers, ES256 for local Supabase. |
| — | Render.com Production Deployment | 2026-03-29 | `render.yaml`, `ENV_VARS.md`, `DEPLOY.md`. |
| — | Observability (OpenTelemetry) | 2026-03-29 | Traces, metrics, logs across backend + worker. |
| — | Billing & Notifications | 2026-03-29 | Stripe subscriptions/credits, Resend email notifications. |
| — | RBAC & Multi-tenancy | 2026-03-29 | Orgs, roles, permissions, invitations, OAuth (Google). |
| — | Dynamic Tool System | 2026-01–2026-03 | Gmail, Google Calendar, Google Sheets, Cal.com; encrypted OAuth token storage + auto-refresh. |
| — | Embed / Call Button | 2026-02 | Embeddable call widget with API key config. |

---

## 🟡 In Progress

| ID | Work Item | Status |
|----|-----------|--------|
| F1 | Built-in skill library expansion | Next — add `insurance-verification` and `dispatch-coordination` (PRD-named composable capabilities). `call-transfer`, `faq-responder`, `after-hours`, `lead-qualification`, `payment-collection` already seeded. |
| — | Worker single-instance scaling TODO | Under review — `TokenRefreshService` race condition risk at multi-instance. Scope decision pending (light distributed lock vs Celery+Redis). |

---

## 🔴 Backlog (Voice-Focused, Ordered)

Prioritized for the voice-only product direction. Chat/multi-channel items moved to
"Deprioritized."

| ID | Feature | Effort | Priority | Rationale |
|----|---------|--------|----------|-----------|
| F7 | Call Recording & Transcription | Medium | P2 | High value for voice agents; builds on existing call_logs + LiveKit. |
| F8 | CRM Integration | Medium | P2 | Tool-system extension; reuses existing tool architecture. |
| F4 | Call Analytics Dashboard | Low | P3 | Leverages call_logs + OTEL metrics already collected. |
| F13 | Campaign Management (Outbound calling) | High | P3 | Natural voice-agent extension; requires scheduling + compliance. |
| F5 | Voice Templates (Industry) | Low | P3 | Preset system prompts per industry; complements skills. |
| F6 | SMS/Text Fallback | Medium | P3 | Voice-adjacent; Twilio already integrated. |
| F9 | Multi-language Support | Medium | P3 | TTS/STT language switching for voice calls. |
| F10 | Call Scoring / QA | Medium | P4 | Post-call quality analysis. |
| F11 | Custom Voice / TTS | High | P4 | Branding/voice selection. |
| F12 | IVR Menu System | Medium | P4 | Menu-driven call routing. |

---

## ⚪ Deprioritized (Not on Active Roadmap)

The platform is intentionally voice-only for now. These remain documented for
future reconsideration but are not being worked on.

| ID | Feature | Reason |
|----|---------|--------|
| F3 | Chat Agents with Long-term Memory | Out of voice-only scope; would require new channel surface + memory backend (Letta/Agno). |
| F14 | Multi-channel (WhatsApp, Discord) | Out of voice-only scope. |

---

## 📝 Next Sprint Goals

- [ ] Expand built-in skill library (`insurance-verification`, `dispatch-coordination`).
- [ ] Decide worker scaling approach (distributed lock vs Celery+Redis) and implement.
- [ ] Prune merged/stale git branches (pending explicit approval per-branch).
- [ ] Reconcile remaining planning docs (`PRIORITY-LIST.md`, `SUMMARY.md`) with voice-only direction.

---

## 🔗 Links

- **PRD Documents:** `/docs/PRD-*.md`
- **Feature Report:** `/docs/FEATURE_REPORT.md`
- **Priority List:** `/docs/PRIORITY-LIST.md`
- **Database Schema:** `/docs/DATABASE_SCHEMA.md`
- **Skill definitions (seeded):** `backend/src/voice_agents/skill_seeds.py`
