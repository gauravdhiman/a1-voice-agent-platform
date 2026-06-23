# VoiceAI Platform - Feature Priority List

**Last Updated:** 2026-06-23
**Version:** 2.2

> **Product Direction:** Voice-only. The platform focuses exclusively on phone-call AI agents. Chat agents (F3) and multi-channel (F14) are deprioritized — see `SPRINT-BOARD.md`.

---

## Vision
Build an **AI voice agent platform** (voice-only) that combines:
1. **Voice Agents** - Phone-call capable AI agents (current, core focus)
2. **Skills System** - Agentic capabilities extension (Agent Skills format)
3. **Phone Numbers** - Buy, manage, and use phone numbers seamlessly

> Chat Agents with long-term memory (formerly pillar #3) are **out of scope** for
> the current voice-only direction. The PRD (`PRD-chat-agents-memory.md`) is kept
> for future reference only.

---

## 📋 Feature Backlog (Scrum Style)

### 🟢 Done (Shipped)
| ID | Feature | Effort | Impact | Completed |
|----|---------|--------|--------|-----------|
| F1 | Skills System — Phases 1, 2a, 2b, 2c | M | High | 2026-05-06 |
| F1 | Built-in skill library (8 skills) | M | High | 2026-06-22 |
| F1 | Platform Skills Management (Admin UI) | M | High | 2026-06-22 |
| F1 | Shared `<SkillEditor>` + org skills tab migration | M | High | 2026-06-22 |
| F2 | Phone Number Management (Twilio + LiveKit) | L | High | 2026-03-15 |

### 🟡 In Progress / Next (priority order)
| # | Feature | Effort | Impact | Status |
|---|---------|--------|--------|--------|
| 1 | Worker single-instance scaling (`TokenRefreshService` race condition) | M | High | Decision pending — recommend Postgres advisory lock vs Celery+Redis |
| 2 | Platform skills soft-delete (`is_deleted`) + show-deleted filter + Restore | M | High | Next — finishes platform admin CRUD |
| 3 | Skill library continuation (`call-handling`, `voicemail-management`, `new-patient-intake`, `intake-qualification`, `menu-inquiry`, `order-status`, `appointment-reminders`, `feedback-collection`, `recall-campaigns`) | M | High | Next |

### ⚪ Deprioritized (Voice-Only Direction)
| ID | Feature | Effort | Impact | Status |
|----|---------|--------|--------|--------|
| F3 | Chat Agents with Memory | H | High | Deprioritized — out of voice-only scope |
| F4 | Call Analytics Dashboard | L | Medium | Backlog |

### 🔴 Future (Backlog)
| ID | Feature | Effort | Impact |
|----|---------|--------|--------|
| F5 | Voice Templates (Industry) | L | Medium |
| F6 | SMS/Text Fallback | M | Medium |
| F7 | Call Recording & Transcription | M | High |
| F8 | CRM Integration | M | High |
| F9 | Multi-language Support | M | High |
| F10 | Call Scoring/QA | M | Medium |
| F11 | Custom Voice/TTS | H | Medium |
| F12 | IVR Menu System | M | Medium |
| F13 | Campaign Management | H | High |
| F14 | Multi-channel (WhatsApp, Discord) | M | Medium |

---

## 📄 Feature Specifications

---

### F1: Skills System for Voice Agents
**Status:** Done (Phases 1–2c + admin UI + shared editor + 8 built-in skills) — skill library continuation is next | **Effort:** Medium | **Impact:** High

**What:**
- Enable extensibility through **composable agent capabilities**
- Capabilities are universal functions: `appointment-booking`, `call-transfer`, `insurance-verification`
- Each capability is configured with business-specific reference files (service menu, hours, policies)
- Agents compose capabilities like building blocks, not monolithic industry personas

**Why:**
- **Composable:** Mix `appointment-booking` + `insurance-verification` for a dental agent, or `appointment-booking` + `dispatch-coordination` for HVAC — same capability, different context
- **Reusable:** Build `appointment-booking` once, every business uses it
- **Maintainable:** Update one capability, all agents using it improve
- **Focused:** Each capability does ONE thing exceptionally well

**Skill Structure:**
```
appointment-booking/
├── SKILL.md              # Core capability instructions (decision trees, templates, guardrails)
├── references/
│   ├── faqs.md           # Common questions and approved answers
│   ├── glossary.md       # Domain terminology
│   └── (business-configurable files uploaded by user)
│       ├── service-menu.md    # Services, durations, prices
│       ├── hours.md           # Operating hours, holidays
│       ├── staff-directory.md # Extensions, departments
│       └── policies.md        # Cancellation, refund, no-show rules
```

**First Capability:** `appointment-booking` — universal need, clear boundaries, testable end-to-end

**Seeded built-in skills (8, done):** `appointment-booking`, `insurance-verification`,
`dispatch-coordination`, `call-transfer`, `faq-responder`, `after-hours`,
`lead-qualification`, `payment-collection` — in `backend/src/voice_agents/skill_seeds.py`.

**Subsequent Capabilities (pending, priority order):**
1. `call-handling`, `voicemail-management` — Core communication (call-transfer already seeded)
2. `new-patient-intake` — Business operations (insurance-verification, payment-collection already seeded)
3. `intake-qualification`, `menu-inquiry`, `order-status` — Qualification & sales (lead-qualification already seeded)
4. `appointment-reminders`, `feedback-collection`, `recall-campaigns` — Follow-up

**File:** `PRD-skills-system.md` (updated)

---

### F2: Phone Number Management (Twilio + LiveKit)
**Status:** Done (2026-03-15) | **Effort:** Medium | **Impact:** High

**What:**
- Buy phone numbers directly from the platform
- Support both Twilio and LiveKit number APIs
- Seamless onboarding - user picks country → sees numbers → subscribes
- Use numbers with voice agents
- Cancel/discard numbers when not needed

**Why:**
- Users find Twilio setup technically challenging
- Single pane of glass for number management
- No need to leave platform
- Unified experience regardless of underlying provider

**User Flow:**
1. User clicks "Buy Number" in dashboard
2. Selects country
3. Sees available numbers (from Twilio/LiveKit based on availability)
4. Picks number → enters payment
5. Number added to their account
6. Can assign to any voice agent
7. Can cancel/discard anytime

**Technical Notes:**
- Twilio API for buying numbers
- LiveKit SIP Trunking for LiveKit numbers
- Abstract provider details from user
- Handle number porting (future)

---

### F3: Chat Agents with Long-term Memory
**Status:** Deprioritized (voice-only direction) | **Effort:** High | **Impact:** High

**What:**
- Create chat-based AI agents (not just voice)
- Persistent memory across conversations
- Cloud-based agents like OpenClaw

**Why:**
- New product line for SMB/Enterprise
- Complements voice agents
- Can handle complex multi-turn conversations

**Approach:** Use Agno framework

**File:** `PRD-chat-agents-memory.md` (exists)

---

### F4: Call Analytics Dashboard
**Status:** Future | **Effort:** Low | **Impact:** Medium

**What:**
- View call statistics
- Agent performance metrics
- Usage patterns

---

## 📊 Estimation Guide

### By Effort
| Size | Days | Description |
|------|------|-------------|
| XS | 1-2 | Quick wins, UI changes |
| S | 3-5 | Small features, one service |
| M | 1-2 weeks | Medium complexity, 2 services |
| L | 2-4 weeks | Large features, multiple services |
| XL | 4+ weeks | Platform-level changes |

### By Impact
| Level | Description |
|-------|-------------|
| High | Revenue driver, key differentiator |
| Medium | Enhances user experience |
| Low | Nice to have |

---

## 🔄 Sprint Planning

### Sprint 1 (Complete)
- ✅ F2: Phone Number Management — shipped 2026-03-15 (PR #2).
- ✅ F1: Skills System — Phases 1, 2a, 2b, 2c shipped (2026-04-01 → 2026-05-06).
- ✅ Landing page, onboarding wizard, security hardening, Render.com deployment.

### Sprint 2 (Current)
- ✅ Built-in skill library expanded to 8 skills (added `insurance-verification`, `dispatch-coordination`).
- ✅ Platform Skills Management (admin UI) — `/platform/skills` with create/edit/hide-restore/files + import-from-URL.
- ✅ Shared `<SkillEditor>` extracted; org skills tab migrated to it (org + platform share one UI).
- 🎯 Worker single-instance scaling: resolve `TokenRefreshService` race-condition TODO (recommend Postgres advisory lock vs Celery+Redis).
- 🎯 Platform skills soft-delete (`is_deleted`) + show-deleted filter + Restore.

### Deprioritized
- 💬 F3: Chat Agents with Memory — out of voice-only scope. PRD retained for
  future reference only.

### Future (Backlog)
- Phase 5: Marketplace (re-evaluate when 50+ orgs using skills)

---

## 📦 Delivery Checklist

For each feature, ensure:
- [ ] PRD created and approved
- [ ] Technical design documented
- [ ] Database migrations (if needed)
- [ ] Backend API implemented
- [ ] Frontend UI implemented
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests (if applicable)
- [ ] Documentation updated
- [ ] PR submitted and merged

---

## 🗂️ File Structure

```
docs/
├── PRIORITY-LIST.md          # This file
├── PRD-skills-system.md      # Feature 1 spec
├── PRD-chat-agents-memory.md # Feature 3 spec
├── PRD-phone-numbers.md      # Feature 2 spec (NEW)
├── tw-drafts/               # Technical specs & notes
│   └── ...
```

---

## Next Steps
1. Pick the worker-scaling approach (recommend Postgres advisory lock) and implement + test.
2. Implement platform skills soft-delete (`is_deleted`) + show-deleted filter + Restore.
3. Continue the built-in skill library (`new-patient-intake`, `call-handling`, …).
4. (Optional) prune merged/stale git branches.

> Full status, ordering, and rationale live in `SPRINT-BOARD.md` (the source of
> truth). This file is the feature backlog/spec companion.

