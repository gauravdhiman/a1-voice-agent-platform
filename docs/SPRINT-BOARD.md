# 📋 Sprint Board

**Last Updated:** 2026-06-23
**Current branch:** `phase-2b/skill-files-import` (merge `2094d32` brings in `develop/multi-agent-evolution`)
**Product direction:** Voice-only — the platform focuses exclusively on phone-call
AI agents. Chat / multi-channel agents (F3, F14) are **deprioritized** and not on
the active roadmap.

> Reconciled with the actual code/commits. Source of truth for what's done vs
> pending. See also `docs/PRIORITY-LIST.md` (feature backlog) and
> `docs/FEATURE_REPORT.md`.

---

## 🟢 Done

### Skills system (F1) — complete through admin management
| Item | Completed | Notes |
|------|-----------|-------|
| Phase 1 — Markdown agent instructions (#18) | 2026-04-01 | Markdown system prompts. |
| Phase 2a — Progressive disclosure (#19) | 2026-04-02 | Skills + on-demand reference loading. |
| Phase 2b — CRUD / Import / Files / Assignment | 2026-05-03 | Skill CRUD, GitHub import, file mgmt, agent assignment. |
| Phase 2c — Platform skills fork/refresh | 2026-05-06 | Orgs fork platform skills + refresh; hidden-skills badge. |
| Elaborate `appointment-booking` skill | 2026-05-06 | First "exceptional capability" w/ rich reference files. |
| Built-in skill library (8 skills) | 2026-06-22 | Added `insurance-verification` + `dispatch-coordination`. Full set: appointment-booking, insurance-verification, dispatch-coordination, call-transfer, faq-responder, after-hours, lead-qualification, payment-collection. (`backend/src/voice_agents/skill_seeds.py`) |
| Platform Skills Management (Admin UI) | 2026-06-22 | Platform-admin-only UI at `/platform/skills`: list/create/edit/hide-restore/files + import-from-URL. Backend RBAC on all routes; `include_inactive` admin list. |
| Shared `<SkillEditor>` + org skills tab migration | 2026-06-22 | Extracted shared master-detail editor (`frontend/src/components/skills/skill-editor.tsx`); org skills tab now renders it via `OrganizationSkillsTab`. Org + platform share one UI — no drift. |

### Platform foundations (shipped)
| Item | Completed | Notes |
|------|-----------|-------|
| Phone Number Management (F2) | 2026-03-15 | Twilio search/purchase/assign/release; credit pricing; full CRUD. |
| RBAC & Multi-tenancy | 2026-03-29 | Orgs, roles, permissions, invitations, Google OAuth. |
| Billing & Notifications | 2026-03-29 | Stripe subscriptions/credits; Resend email notifications. |
| Dynamic Tool System | 2026-01–2026-03 | Gmail, Google Calendar, Google Sheets, Cal.com; encrypted OAuth token storage + auto-refresh. |
| Embed / Call Button | 2026-02 | Embeddable call widget w/ API key config. |
| Observability (OpenTelemetry) | 2026-03-29 | Traces, metrics, logs across backend + worker. |
| Security Hardening | 2026-03-29 | Rate limiting, JWT signature verification, security headers, ES256 for local Supabase. |
| SMB 5-step Onboarding Wizard | 2026-03-29 | Template selection, validation, activation gating. |
| Landing Page Redesign | 2026-03-29 | Early-adopter CTA, 4-tier pricing, branding (CogniNets). |
| Render.com Production Deployment | 2026-03-29 | `render.yaml`, `ENV_VARS.md`, `DEPLOY.md`. |

### Tooling / housekeeping
- `.gitignore` hardened: `.agents/`, `.codex/skills/graphify/`, `.codex/hooks.json`, `graphify-out/`; `.graphifyignore` added for code-only graphify runs.

---

## 🟡 In Progress / Next (priority order)

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | **Worker single-instance scaling** (`TokenRefreshService`) | Decision pending | Background token-refresh loop races at multi-instance (double-refresh, lost updates). **Recommended:** Postgres advisory lock keyed by `agent_tool_id` (zero new infra). Alternative in the existing TODO: Celery + Redis (heavier). Currently single-instance → future risk, not a live bug. (`backend/src/services/token_refresh_service.py`) |
| 2 | **Platform skills soft-delete + show-deleted/restore** | Next | Add `is_deleted` to `platform_skills`; admin "show deleted" filter + Restore. Finishes the platform-admin CRUD story (create/edit/import ✅; delete/restore ❌). TODO at `frontend/src/app/(dashboard)/platform/skills/page.tsx`. |
| 3 | **Skill library continuation** | Next | Build remaining PRD capabilities: `call-handling`, `voicemail-management`, `new-patient-intake`, `intake-qualification`, `menu-inquiry`, `order-status`, `appointment-reminders`, `feedback-collection`, `recall-campaigns`. |

---

## 🔴 Backlog (Voice-focused, ordered)

| ID | Feature | Effort | Priority | Rationale |
|----|---------|--------|----------|-----------|
| F7 | Call Recording & Transcription | Medium | P2 | High value; builds on `call_logs` + LiveKit. |
| F8 | CRM Integration | Medium | P2 | Reuses the dynamic-tool architecture. |
| F4 | Call Analytics Dashboard | Low | P3 | Leverages `call_logs` + OTEL metrics already collected. |
| F13 | Campaign Management (Outbound) | High | P3 | Voice-agent extension; needs scheduling + compliance. |
| F5 | Voice Templates (Industry) | Low | P3 | Preset system prompts per industry; complements skills. |
| F6 | SMS/Text Fallback | Medium | P3 | Twilio already integrated. |
| F9 | Multi-language Support | Medium | P3 | TTS/STT language switching. |
| F10 | Call Scoring / QA | Medium | P4 | Post-call quality analysis. |
| F11 | Custom Voice / TTS | High | P4 | Branding / voice selection. |
| F12 | IVR Menu System | Medium | P4 | Menu-driven call routing. |

### Low-priority housekeeping
- Prune merged/stale git branches (~7 fully-merged + several squash-merged remotes safe to delete) — deferred; needs per-branch confirmation.
- Minor TODO: `backend/src/billing/routes.py:187` placeholder `billing@{slug}.example.com` email.

---

## ⚪ Deprioritized (not on active roadmap — voice-only)

| ID | Feature | Reason |
|----|---------|--------|
| F3 | Chat Agents with Long-term Memory | Out of voice-only scope; needs new channel surface + memory backend (Letta/Agno). PRD retained for reference. |
| F14 | Multi-channel (WhatsApp, Discord) | Out of voice-only scope. |
| — | Skills Marketplace | Re-evaluate when 50+ orgs use skills. |

---

## 📝 Next sprint (suggested)
- [ ] Worker scaling: pick approach (recommend Postgres advisory lock) → implement + test.
- [ ] Platform skills soft-delete (`is_deleted`) + show-deleted filter + Restore.
- [ ] Add 1–2 more built-in skills (e.g. `new-patient-intake`, `call-handling`).
- [ ] (Optional) prune stale branches.

---

## 🔗 Links
- **Feature backlog:** `docs/PRIORITY-LIST.md`
- **PRDs:** `docs/PRD-*.md`
- **Feature report:** `docs/FEATURE_REPORT.md`
- **DB schema:** `docs/DATABASE_SCHEMA.md`
- **Platform skills admin doc:** `docs/02_features/voice_agents/platform_skills_admin.md`
- **Skill definitions (seeded):** `backend/src/voice_agents/skill_seeds.py`
