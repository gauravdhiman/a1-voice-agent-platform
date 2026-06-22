# VoiceAI Platform - Feature Priority List

**Last Updated:** 2026-06-19
**Version:** 2.1

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
| F1 | Skills System for Voice Agents (Phases 1, 2a, 2b, 2c) | M | High | 2026-05-06 |
| F2 | Phone Number Management (Twilio + LiveKit) | L | High | 2026-03-15 |

### 🟡 In Progress / Next
| ID | Feature | Effort | Impact | Status |
|----|---------|--------|--------|--------|
| F1+ | Built-in skill library expansion (`insurance-verification`, `dispatch-coordination`) | M | High | Next |
| — | Worker single-instance scaling (TokenRefreshService) | M | High | Under review |

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
**Status:** Done (Phases 1–2c shipped) — built-in skill library expansion in progress | **Effort:** Medium | **Impact:** High

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

**Subsequent Capabilities (priority order):**
1. `call-handling`, `call-transfer` — Core communication
2. `insurance-verification`, `new-patient-intake` — Business operations
3. `lead-qualification`, `intake-qualification` — Qualification & sales
4. `appointment-reminders`, `feedback-collection` — Follow-up

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
- 🎯 Built-in skill library expansion: add `insurance-verification` and
  `dispatch-coordination` (PRD-named composable capabilities). Note:
  `call-transfer`, `faq-responder`, `after-hours`, `lead-qualification`, and
  `payment-collection` are already seeded in `skill_seeds.py`.
- 🎯 Worker single-instance scaling: resolve `TokenRefreshService` race-condition
  TODO (scope decision: distributed lock vs Celery+Redis).

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
1. ✅ Review updated priority list
2. ⏳ Create PRD for Phone Numbers (F2)
3. ⏳ Finalize PRD for Skills System (F1)
4. Start Sprint 1 implementation

