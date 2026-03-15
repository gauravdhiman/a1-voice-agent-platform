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
- No easy way to extend agent knowledge for specific domains
- Each customer needs custom prompts for their business context
- No reusability or marketplace for agent capabilities

### Pain Points
1. **Knowledge Gaps:** Agents don't have domain-specific knowledge (legal, medical, technical)
2. **Reusability:** Can't share agent configurations across organizations
3. **Maintenance:** Hard to update agent behavior without code changes
4. **Extensibility:** No marketplace to discover new capabilities

---

## 2. Solution Overview

Implement the **Agent Skills** format (agentskills.io) to enable:
- **Knowledge Packs:** Domain-specific knowledge (legal, real estate, dental, etc.)
- **Workflows:** Multi-step repeatable processes
- **Tools:** Custom tool definitions and configurations
- **Marketplace:** Share and discover skills from community

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

| User | Story | Acceptance Criteria |
|------|-------|-------------------|
| Admin | I want to upload a skill package | Can upload .zip or connect from marketplace |
| Admin | I want to enable skills for my agent | Can select skills in agent config |
| Admin | I want to create custom skills | Can define SKILL.md with business knowledge |
| Developer | I want to publish skills to marketplace | Can publish and version skills |
| Agent | I want to load relevant skills on demand | Agent activates skills based on conversation |

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

## 6. Pre-built Skills (MVP)

### Healthcare
- Dental Assistant
- Medical Scheduling
- Insurance Verification

### Business
- Appointment Scheduler
- Lead Qualifier
- Customer Support

### Industry
- Restaurant Reservations
- Real Estate Inquiries
- Legal Consultations

---

## 7. Security & Compliance

- **Organization Isolation:** Skills scoped to organizations
- **Sandboxed Execution:** Scripts run in isolated environment
- **Content Filtering:** Validate skill content before publishing
- **Audit Logging:** Track skill usage and modifications

---

## 8. Phased Implementation

### Phase 1: Foundation (2 weeks)
- Database schema
- Basic CRUD APIs
- Skill loader in worker
- Simple skill selection UI

### Phase 2: Marketplace (2 weeks)
- Public skill browsing
- Category navigation
- Search and filters
- Rating system

### Phase 3: Advanced (2 weeks)
- Skill versioning
- Custom scripts execution
- Analytics dashboard
- Publishing workflow

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Skills created (first month) | 20+ |
| Skills activated (first month) | 100+ |
| Time to configure agent | -50% |
| Customer satisfaction | +20% |

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
