# VoiceAI Platform - Feature Priority List

**Last Updated:** 2026-03-01
**Version:** 2.0

---

## Vision
Build an AI voice agent platform that combines:
1. **Voice Agents** - Phone-call capable AI agents (current)
2. **Skills System** - Agentic capabilities extension (Agent Skills format)
3. **Chat Agents** - Long-running task agents with memory (Agno/Letta-based)
4. **Phone Numbers** - Buy, manage, and use phone numbers seamlessly

---

## 📋 Feature Backlog (Scrum Style)

### 🟢 Ready to Start (This Sprint)
| ID | Feature | Effort | Impact | Sprint |
|----|---------|--------|--------|--------|
| F1 | Skills System for Voice Agents | M | High | 1 |
| F2 | Phone Number Management (Twilio + LiveKit) | L | High | 1 |

### 🟡 In Discovery/Planning
| ID | Feature | Effort | Impact | Status |
|----|---------|--------|--------|--------|
| F3 | Chat Agents with Memory | H | High | PRD Draft |
| F4 | Call Analytics Dashboard | L | Medium | - |

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
**Status:** Ready | **Effort:** Medium | **Impact:** High

**What:**
- Enable extensibility through Agent Skills format
- Allow users to add custom capabilities to voice agents
- Support marketplace for sharing skills

**Why:**
- Extensibility beyond built-in tools
- Community marketplace potential
- Knowledge base management

**File:** `PRD-skills-system.md` (exists)

---

### F2: Phone Number Management (Twilio + LiveKit) ⚡ NEW
**Status:** Ready | **Effort:** Low | **Impact:** High

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
**Status:** PRD Draft | **Effort:** High | **Impact:** High

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

### Sprint 1 (Current)
- [ ] F1: Skills System - Research complete, ready to implement
- [ ] F2: Phone Numbers - PRD ready, can start

### Sprint 2+
- [ ] F3: Chat Agents with Memory
- [ ] F4: Call Analytics Dashboard

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

