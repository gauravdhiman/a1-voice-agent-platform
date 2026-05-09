# PRD: Skills System for Voice Agents

**Feature:** Agent Skills Integration  
**Status:** Draft  
**Priority:** P0 (Highest)  
**Target:** VoiceAI Platform v2.0  
**Created:** 2026-02-28

---

## 1. Problem Statement

### Current State
- Voice agents have fixed capabilities defined in system prompts
- No easy way to add new capabilities (appointment booking, insurance checks, call transfers)
- Each customer writes custom prompts from scratch for common functions
- Capabilities built once cannot be reused across agents or organizations

### Pain Points
1. **Capability Gaps:** Agents can't perform common business functions (book appointments, verify insurance, transfer calls) without custom prompt engineering
2. **Reusability:** Every organization re-invents "appointment booking" in their own prompts
3. **Maintenance:** Updating how agents handle bookings requires editing every agent's system prompt
4. **Composition:** No way to combine capabilities — an agent either has a dental prompt OR an HVAC prompt, not both

---

## 2. Solution Overview

Implement the **Agent Skills** format (agentskills.io) to enable:
- **Knowledge Packs:** Domain-specific knowledge (legal, real estate, dental, HVAC, etc.)
- **Workflows:** Multi-step repeatable processes
- **Tools:** Custom tool definitions and configurations
- ~~**Marketplace:** Share and discover skills from community~~ *(Deprioritized — see Section 8)*

### What are Agent Skills?
A skill is a folder containing:
```
skill-name/
├── SKILL.md              # Required: instructions & metadata
├── scripts/              # Optional: executable code
├── references/           # Optional: documentation
└── assets/               # Optional: templates, data
```

---

## 3. User Stories

| User | Story | Acceptance Criteria | Status |
|------|-------|-------------------|--------|
| Admin | I want to import skills from GitHub | Can paste a GitHub skills repo URL and import | ✅ Done |
| Admin | I want to create custom skills | Can define name, description, and upload files inline | ✅ Done |
| Admin | I want to enable skills for my agent | Can toggle skills on/off in agent config | ✅ Done |
| Admin | I want to preview skill content | Can expand file tree and view file contents | ✅ Done |
| Admin | I want to delete skills safely | Warned if skill is used by agents; can confirm delete | ✅ Done |
| Admin | I want pre-built skills for my industry | Can enable built-in skills with rich domain knowledge | 🎯 Phase 2c |
| Agent | I want to use skill knowledge in calls | Skill instructions injected into system prompt during calls | ✅ Done |

---

## 4. Technical Specification

### 4.1 Skill Format

**SKILL.md Structure:**
```yaml
---
name: dental-appointment
description: Schedule dental appointments, handle insurance verification, tooth numbering. Use when user mentions dentist, teeth, dental, appointments.
license: MIT
metadata:
  author: voiceai
  version: 1.0.0
  industry: healthcare
---
# Instructions for dental appointment scheduling
...
```

### 4.2 Database Schema

```sql
-- Skills table
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    version VARCHAR(20) NOT NULL,
    license VARCHAR(100),
    metadata JSONB,
    category VARCHAR(50),
    is_public BOOLEAN DEFAULT false,
    organization_id UUID REFERENCES organizations(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Skill versions
CREATE TABLE skill_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    content JSONB NOT NULL,  -- Full skill content as JSON
    changelog TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent skills (many-to-many)
CREATE TABLE agent_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES voice_agents(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    config JSONB,  -- Skill-specific configuration
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(agent_id, skill_id)
);

-- Skill marketplace categories
CREATE TABLE skill_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(50)
);
```

### 4.3 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VoiceAI Platform                       │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js)                                         │
│  - Skill Marketplace UI                                      │
│  - Agent Configuration                                       │
├─────────────────────────────────────────────────────────────┤
│  Backend (FastAPI)                                           │
│  - Skill CRUD APIs                                           │
│  - Marketplace APIs                                           │
│  - Skill Versioning                                           │
├─────────────────────────────────────────────────────────────┤
│  Worker (LiveKit Agents)                                     │
│  - Skill Loader                                              │
│  - Dynamic System Prompt Generation                          │
│  - Skill Context Injection                                   │
├─────────────────────────────────────────────────────────────┤
│  Database (Supabase)                                          │
│  - Skills, Versions, Agent Skills                            │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 API Endpoints

```python
# Skills CRUD
POST   /api/v1/skills                    # Create skill
GET    /api/v1/skills                     # List skills
GET    /api/v1/skills/{id}                # Get skill details
PUT    /api/v1/skills/{id}                # Update skill
DELETE /api/v1/skills/{id}                # Delete skill

# Skill Versions
POST   /api/v1/skills/{id}/versions      # Create new version
GET    /api/v1/skills/{id}/versions       # List versions
GET    /api/v1/skills/{id}/versions/{v}  # Get specific version

# Marketplace
GET    /api/v1/marketplace/skills        # Browse public skills
GET    /api/v1/marketplace/categories    # Browse categories
POST   /api/v1/marketplace/publish       # Publish to marketplace

# Agent Skills
GET    /api/v1/agents/{id}/skills        # List agent skills
POST   /api/v1/agents/{id}/skills        # Add skill to agent
DELETE /api/v1/agents/{id}/skills/{sid}  # Remove skill
```

### 4.5 Worker Integration

```python
# Skill Loader in Worker
class SkillLoader:
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def load_agent_skills(self, agent_id: str) -> list[Skill]:
        """Load all enabled skills for an agent"""
        # Fetch skills from DB
        # Parse SKILL.md
        # Return as Skill objects
    
    async def get_relevant_skills(self, context: dict) -> list[Skill]:
        """Selectively load skills based on conversation context"""
        # Use skill descriptions to match context
        # Return relevant skills

# Dynamic Prompt Generation
class PromptBuilder:
    def __init__(self, skill_loader: SkillLoader):
        self.skill_loader = skill_loader
    
    async def build_system_prompt(self, agent_id: str, context: dict) -> str:
        base_prompt = await self.get_base_prompt(agent_id)
        skills = await self.skill_loader.get_relevant_skills(context)
        skill_instructions = "\n\n".join(s.instructions for s in skills)
        
        return f"""
{base_prompt}

# Additional Capabilities
{skill_instructions}

# Context
Industry: {context.get('industry')}
Business: {context.get('business_name')}
"""
```

---

## 5. UI/UX Specification

### 5.1 Skill Marketplace

**Layout:**
- Hero: "Discover Skills for Your Voice Agents"
- Search bar with filters (category, industry, price)
- Category cards (Healthcare, Legal, Real Estate, Retail, etc.)
- Skill cards grid (name, description, rating, installs)
- Featured skills carousel

**Skill Card:**
```
┌─────────────────────────────┐
│ 🏥 Dental Assistant         │
│ Schedule appointments,      │
│ verify insurance...         │
│                             │
│ by VoiceAI Team    ⭐⭐⭐⭐⭐  │
│ Healthcare • Free           │
└─────────────────────────────┘
```

### 5.2 Agent Configuration

**Skill Selection Panel:**
- Toggle to enable/disable skills
- Skill preview on hover
- Version selector
- Configuration per skill

### 5.3 Skill Editor

**Create/Edit Skill:**
- Name input (validated)
- Description input (with AI suggestions)
- Category selector
- SKILL.md editor with preview
- Scripts uploader
- References manager

---

## 6. Pre-built Skills (Phase 2c)

### Strategy: Capabilities, Not Industries

Skills represent **agent capabilities** — composable functions an agent can perform. They are not industry-specific roles.

**Why capabilities?**
- **Composable:** An agent can have `appointment-booking` + `call-transfer` + `insurance-verification` all active at once
- **Reusable:** `appointment-booking` works for dental, HVAC, legal, salons — same capability, different context
- **Focused:** Each skill does ONE thing exceptionally well, with clear boundaries
- **Maintainable:** Update `appointment-booking` once, all agents using it improve

**What a capability skill contains:**
- **Instructions:** How to perform the capability (decision trees, response templates, guardrails)
- **Reference files:** Domain data the capability needs (pricing, forms, FAQs, service menus)
- **Tool integration:** What external actions it can take (calendar API, CRM lookup, form submission)

**Example composition:**

| Business Type | Active Capabilities |
|-------------|---------------------|
| Dental Practice | `appointment-booking` + `insurance-verification` + `new-patient-intake` |
| Restaurant | `reservation-booking` + `menu-inquiry` + `order-status` |
| HVAC Service | `appointment-booking` + `dispatch-coordination` + `warranty-check` |
| Law Firm | `appointment-booking` + `intake-qualification` + `conflict-check` |

Notice `appointment-booking` appears everywhere — it's a universal capability with business-specific reference files.

---

### First Skill: `appointment-booking`

**Why this capability first:**
1. **Universal need** — Every business that takes calls needs to schedule something
2. **Clear boundaries** — Inputs (date, time, service), outputs (confirmed booking), edge cases (reschedule, cancel, conflict)
3. **Tool integration** — Naturally connects to calendar APIs, demonstrating real value
4. **Reference-driven** — Different businesses configure it with their own service menus and hours
5. **E2E testable** — We can simulate a complete booking flow and assert outcomes

**What `appointment-booking` includes:**
- **SKILL.md:** How to gather booking requirements, handle conflicts, confirm details, send reminders, reschedule, cancel
- **references/service-menu.md:** Services offered, durations, prices (business-configurable)
- **references/hours.md:** Business hours, blackout dates, holiday closures (business-configurable)
- **references/faqs.md:** Common questions (cancellation policy, deposit required, what to bring)
- **references/forms.md:** Pre-appointment forms the agent can help complete

**Validation criteria:**
- E2E test: 10 realistic caller scenarios (book, reschedule, cancel, conflict, after-hours inquiry)
- Agent produces correct calendar event details every time
- Agent handles edge cases gracefully (double-booking, invalid times, no-show policy)

---

### Subsequent Capabilities (batches)

**Batch 1 — Core Communication:**
- `call-handling` — Greetings, hold etiquette, call wrap-up, tone/voice guidelines
- `call-transfer` — Routing rules (department, urgency, availability), warm vs cold transfer
- `voicemail-management` — Taking detailed messages, urgency triage, callback scheduling

**Batch 2 — Business Operations:**
- `insurance-verification` — Eligibility checks, coverage questions, pre-auth status, copay/deductible lookup
- `new-patient-intake` — Information gathering, form completion, consent, medical history
- `payment-processing` — Collecting payments over phone, billing questions, payment plan setup
- `dispatch-coordination` — Technician assignment, ETA communication, parts availability, job status

**Batch 3 — Qualification & Sales:**
- `lead-qualification` — BANT-style questions, urgency assessment, fit scoring
- `intake-qualification` — Legal matter screening, practice-area routing, conflict check
- `menu-inquiry` — Item descriptions, dietary restrictions, daily specials, allergy handling
- `order-status` — Lookup, modification, cancellation, refund policy

**Batch 4 — Follow-up:**
- `appointment-reminders` — Confirmation calls, no-show prevention, rescheduling outreach
- `feedback-collection` — Post-visit surveys, review requests, complaint handling
- `recall-campaigns` — Routine maintenance reminders, annual checkups, seasonal campaigns

### Per-Capability Standard
Every skill must include:

1. **`SKILL.md`** (200+ lines) structured as:
   - **Capability overview** — What this skill enables, when to use it
   - **Decision trees** — Caller says X → agent does Y (flowchart in comments)
   - **Response templates** — Greetings, confirmations, escalations, hold messages
   - **Guardrails** — What the agent MUST NOT do (e.g., "never confirm a booking without verifying phone number")
   - **Tool calls** — When and how to invoke external tools (calendar, CRM, forms)
   - **Error handling** — What to say when tools fail or data is missing

2. **`references/faqs.md`** — Caller questions and approved answers

3. **`references/glossary.md`** — Domain terminology the agent must understand and use correctly

4. **Business-configurable references** (skill files with `file_kind: "reference"`):
   - `service-menu.md` — What services are offered, durations, prices
   - `hours.md` — Operating hours, holidays, special schedules
   - `staff-directory.md` — Who handles what, extensions, availability
   - `policies.md` — Cancellation, refund, deposit, no-show, rescheduling rules

5. **Validation:** E2E test simulating 5-10 realistic caller scenarios per skill, asserting correct behavior

---

## 7. Security & Compliance

- **Organization Isolation:** Skills scoped to organizations
- **Sandboxed Execution:** Scripts run in isolated environment
- **Content Filtering:** Validate skill content before publishing
- **Audit Logging:** Track skill usage and modifications

---

## 8. Phased Implementation

### Phase 1: Foundation ✅ COMPLETE
- Database schema (`organization_skills`, `organization_skill_files`, `agent_skills`)
- CRUD APIs (create, update, delete, list)
- File management (upload, read, update, delete)
- Skill import from GitHub URL
- URL-based bookmarking (skill tabs, file selection)
- Skill loader in worker (`load_skill_reference` function)
- Agent skill assignment with toggle switches

### Phase 2a: Progressive Disclosure ✅ COMPLETE
- Skills visible on organization page (not in main nav)
- Built-in vs custom skill badges
- Expandable file tree with content preview
- Import drawer with GitHub URL input

### Phase 2b: CRUD & Agent Integration ✅ COMPLETE
- Create/edit custom skills inline
- Delete with agent-usage warning
- Real-time file count updates
- Agent skills tab with toggles
- E2E test coverage for all flows

### Phase 2c: Pre-Built Skill Content — NEXT 🎯
**Status:** Ready to start | **Effort:** Medium | **Impact:** High

Build exceptional, content-rich pre-built skills. We will perfect **one skill first** to establish reusable patterns, then replicate for others.

**Target industries/use cases:**
- Healthcare (dental, medical scheduling, insurance verification)
- Food service (restaurant reservations, order handling)
- Real estate (inquiries, showings, follow-ups)
- Legal (consultations, intake, scheduling)
- Home services (HVAC, electrician, plumber — scheduling, estimates, dispatch)

**Per-skill deliverables:**
1. Rich `SKILL.md` with deep domain instructions, decision trees, and response templates
2. Reference files (FAQs, pricing sheets, service menus, insurance forms)
3. Validation: E2E call simulation confirming the skill produces correct agent behavior
4. Documentation: What it does, when to use it, configuration options

**Approach:**
- Pick **one skill** (recommendation: *Dental Assistant* or *Restaurant Reservations*)
- Build it to "exceptional" standard — not just functional, but genuinely useful
- Learn patterns: what makes a skill effective? What files does it need? How should instructions be structured?
- Apply learnings to subsequent skills in batches

### Phase 3: Phone Number Management (F2)
**Status:** PRD ready | **Effort:** Large | **Impact:** High

Move to Feature F2 per `PRIORITY-LIST.md`. Buying, managing, and assigning phone numbers directly from the platform.

### Phase 4: Chat Agents with Memory (F3)
**Status:** PRD draft | **Effort:** XL | **Impact:** High

Move to Feature F3 per `PRIORITY-LIST.md`. Long-running chat agents with persistent memory.

### Phase 5: Marketplace — DEPRIORITIZED 🚫
**Rationale:** A marketplace requires a community of users creating and sharing skills. With zero users today, marketplace infrastructure delivers no value. Re-evaluate when:
- 50+ organizations actively using skills
- 10+ custom skills created by users organically
- Clear demand signal (users asking to share/publish skills)

**If revisited later:**
- Public skill browsing with categories
- Search and filters
- Rating/review system
- Publishing workflow (private → public)
- Skill versioning

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Skills system foundation | 100% | All Phase 1-2b features deployed with tests | ✅ |
| First pre-built skill quality | Exceptional | E2E call simulations pass 90%+ of scenarios | 🎯 Phase 2c |
| Pre-built skill library | 5+ skills | At least one per target industry | 🎯 Phase 2c |
| Time to configure agent | -50% | User enables pre-built skill vs writing custom prompt | Future |
| Customer satisfaction | +20% | NPS or CSAT survey post-call | Future |

---

## 10. Dependencies

- Supabase (existing)
- LiveKit Workers (existing)
- File storage for skill packages (S3/Supabase Storage)
- Redis (optional, for caching)

---

## 11. Open Questions

1. **Pricing Model:** Free vs premium skills in marketplace?
2. **Skill Review:** Manual or automated review before publishing?
3. **Script Execution:** What languages to support? How to sandbox?
4. **Skill Discovery:** How does agent know which skills to activate?
