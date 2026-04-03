# Skills System

## Overview

Skills are reusable knowledge and procedure packages (written in markdown) that can be assigned to voice agents. They enable agents to handle specific scenarios (booking appointments, transferring calls, answering FAQs) without embedding all procedures directly into the agent's instructions.

## Progressive Disclosure

Skills use **progressive disclosure** — a two-step loading process that keeps the agent's initial system prompt small and focused:

1. **At call start**: Only skill metadata (name + description) is included in the system prompt as an "Available Skills" section.
2. **During conversation**: When the agent needs a specific procedure, it calls the `load_skill` tool with the skill slug. The full skill content is loaded into context on-demand.

This design is critical for voice agents where:
- Latency matters (smaller initial prompt = faster first response)
- Most calls only use 1-2 skills out of many assigned
- Token usage is minimized (unused skills aren't loaded)

## Skill Architecture

```
Organization Skill Library          Agent Skill Assignment
┌─────────────────────────┐        ┌──────────────────────┐
│ Built-in Skills         │        │ Receptionist Agent   │
│  📋 appointment-booking │───────>│  ✓ appointment-booking│
│  📋 call-transfer       │───────>│  ✓ call-transfer     │
│  📋 faq-responder       │───────>│  ✓ faq-responder     │
│  📋 after-hours         │        │                      │
│  📋 lead-qualification  │        └──────────────────────┘
│  📋 payment-collection  │
│                         │
│ Custom Skills           │
│  📋 insurance-verify    │
│  📋 company-policies    │
└─────────────────────────┘
```

## Database Tables

### organization_skills

Organization-level skill library. Each skill has a unique slug within the org.

Key fields:
- `slug` — URL-safe identifier (kebab-case, e.g., `appointment-booking`)
- `name`, `description` — Used as metadata in the system prompt
- `content` — Full skill markdown (loaded by `load_skill` tool)
- `category` — `built_in` (read-only) or `custom` (editable)
- `content_hash` — SHA-256 of content for efficient change detection
- `version`, `author` — Versioning and attribution
- `source_url`, `source_ref` — For imported skills (Phase 2b)

### organization_skill_files

Reference files for skills (Phase 2b). Stores additional files like `references/policies.md` that skills can reference.

### agent_skills

Junction table linking agents to skills. Each assignment has an `is_active` flag.

## Built-in Skills

Six built-in skills are seeded when an organization completes onboarding:

| Skill | Slug | Purpose |
|-------|------|---------|
| Appointment Booking | `appointment-booking` | Schedule, reschedule, cancel appointments |
| Call Transfer | `call-transfer` | Escalate to human with context handoff |
| FAQ Responder | `faq-responder` | Answer common questions from knowledge base |
| After Hours | `after-hours` | Handle calls outside business hours |
| Lead Qualification | `lead-qualification` | Qualify inbound sales leads (BANT framework) |
| Payment Collection | `payment-collection` | Process payments, explain invoices |

Built-in skills are:
- **Read-only** — Org admins cannot edit content (can only enable/disable)
- **Auto-synced** — Platform admins can update content across all orgs via `POST /api/v1/skills/sync-all`
- **Content-hashed** — Sync uses SHA-256 comparison to skip unchanged skills

## API Endpoints

### Organization-level

```
GET    /api/v1/organizations/{org_id}/skills         — List org skills
POST   /api/v1/organizations/{org_id}/skills         — Create custom skill (admin only)
PUT    /api/v1/organizations/{org_id}/skills/{id}     — Update skill (admin only)
DELETE /api/v1/organizations/{org_id}/skills/{id}     — Delete custom skill (admin only)
POST   /api/v1/organizations/{org_id}/skills/seed    — Seed built-in skills (idempotent)
```

### Agent-level

```
GET    /api/v1/agents/{agent_id}/skills              — List agent's assigned skills
POST   /api/v1/agents/{agent_id}/skills              — Assign skill (admin only)
DELETE /api/v1/agents/{agent_id}/skills/{skill_id}    — Unassign skill (admin only)
```

### Tool-facing

```
GET    /api/v1/skills/{org_id}/{slug}                — Get full skill content by slug
POST   /api/v1/skills/sync-all                       — Sync built-in skills across all orgs (platform admin)
```

## Permissions

| Action | Platform Admin | Org Admin | Regular User |
|--------|---------------|-----------|-------------|
| View skills | ✓ | ✓ | ✓ |
| Create custom skill | ✓ | ✓ | ✗ |
| Edit custom skill | ✓ | ✓ | ✗ |
| Delete custom skill | ✓ | ✓ | ✗ |
| Edit built-in skill | ✗ | ✗ | ✗ |
| Delete built-in skill | ✗ | ✗ | ✗ |
| Enable/disable built-in | ✓ | ✓ | ✗ |
| Assign skill to agent | ✓ | ✓ | ✗ |
| Sync all orgs | ✓ | ✗ | ✗ |

## Worker Integration

The worker registers a `load_skill` function tool when an agent has assigned skills:

```python
# Fetch skill summaries for prompt metadata
skill_summaries = await skill_service.get_agent_skill_summaries(agent_id)

# Register load_skill tool
load_skill_fn = create_load_skill_function(org_id, skill_service)
livekit_tools.append(function_tool(load_skill_fn, ...))

# Build prompt with skill metadata
instructions = PromptBuilder.build(
    org=org, agent=agent,
    agent_skills=skill_summaries,
)
```

## Frontend UI

### Organization Page — Skills Tab

Split-view layout:
- **Left panel**: Filterable skill list with category badges
- **Right panel**: Selected skill content rendered as markdown
- Create custom skills via side drawer
- Edit custom skills inline (built-in skills are read-only)

### Agent Detail Page — Skills Tab

Toggle-based assignment:
- Each org skill shown as a card with toggle switch
- Click row to view skill content in side drawer
- "Manage Skills" link (admin only) to organization settings
