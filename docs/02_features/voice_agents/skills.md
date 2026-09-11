# Skills System

> **Runtime note:** Skills are loaded and executed by the Pipecat `voice-ws`
> runtime. Any legacy LiveKit wrapper snippets below are historical context;
> the current registration boundary is documented in [`voice-ws` README](../../../voice-ws/README.md)
> and the [system architecture](../../01_architecture/system_architecture.md).

> **Library index:** see [`skills_library.md`](./skills_library.md) for the
> current 15-skill library, industry coverage, content standards, and the
> rationale for industry-specific (rather than universal) skills.

## Overview

Skills are **composable agent capabilities** — markdown instructions that
extend what a voice agent can do. The platform ships a focused library
of built-in skills that org admins can enable per-agent; orgs can also
fork any platform skill to customize it for their own workflows.

The current library is industry-specific: each business type (dental,
restaurant, HVAC) gets its own set of skills tuned to that industry's
workflows. The skill catalog and rationale live in
[`skills_library.md`](./skills_library.md).

## Progressive Disclosure

Skills use **progressive disclosure** — a three-level loading process that keeps the agent's initial system prompt small and focused:

1. **At call start**: Only skill metadata (name + description) is included in the system prompt as an "Available Skills" section.
2. **During conversation**: When the agent needs a specific procedure, it calls the `load_skill` tool with the skill slug. The full SKILL.md content is loaded into context on-demand.
3. **Deeper references**: If a loaded skill references a sub-file (e.g., "see *references/policies.md*"), the agent calls `load_skill_reference` with the skill slug and file path to load that file's content.

Loaded skill and reference content is lower-priority procedural guidance. It
cannot expand the agent's configured scope or override platform guardrails,
tool schemas, authorization requirements, or caller safety rules.

This design is critical for voice agents where:
- Latency matters (smaller initial prompt = faster first response)
- Most calls only use 1-2 skills out of many assigned
- Token usage is minimized (unused skills aren't loaded)
- Reference files (scripts, documentation, data) are never loaded unless explicitly needed

## Skill Architecture

```
Industry-Specific Library         Agent Composition (Example: Dental)
┌─────────────────────────────┐  ┌──────────────────────────────┐
│ Built-in Skills (15)          │  │ Dental Receptionist Agent      │
│                               │  │                              │
│  Dental (5)                  │  │  ✓ dental-appointment-booking │
│   • dental-appointment-booking│──┤  ✓ dental-faq                  │
│   • dental-faq               │  │  ✓ dental-new-patient-intake   │
│   • dental-new-patient-intake │  │  ✓ dental-recall-and-reminder  │
│   • dental-recall-and-reminder│  │  ✓ dental-escalation           │
│   • dental-escalation        │  │                              │
│                               │  │ HVAC Service Agent           │
│  Restaurant (5)              │  │                              │
│   • restaurant-reservation-...│  │  ✓ hvac-service-appointment    │
│   • restaurant-menu-and-info  │  │  ✓ hvac-service-info           │
│   • restaurant-special-request│  │  ✓ hvac-diagnosis-and-triage   │
│   • restaurant-reservation-...│  │  ✓ hvac-maintenance-recall     │
│   • restaurant-escalation     │  │  ✓ hvac-escalation             │
│                               │  │                              │
│  HVAC (5)                    │  └──────────────────────────────┘
│   • hvac-service-appointment  │
│   • hvac-service-info         │  Org Skill Library (per org)
│   • hvac-diagnosis-and-triage │  ┌──────────────────────────────┐
│   • hvac-maintenance-recall   │  │ Forks of platform skills      │
│   • hvac-escalation           │  │ Custom org-specific skills    │
│                               │  │ Reference files (per skill)  │
└─────────────────────────────┘  └──────────────────────────────┘
```

**Key principle:** Platform skills are industry-specific. Org admins
pick the ones that match their business; they fork to customize.
Reference files are loaded on-demand via `load_skill_reference`.

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

Reference files for skills. Stores additional files like `references/policies.md` that skills can reference. Files are loaded on-demand via the `load_skill_reference` tool for progressive disclosure.

Key fields:
- `file_path` — Relative path within the skill (e.g., "references/booking-policies.md")
- `content` — Full file content
- `file_kind` — Classification: `reference`, `script`, `asset`, or `other`
- `content_hash` — SHA-256 of content for change detection

### agent_skills

Junction table linking agents to skills. Each assignment has an `is_active` flag.

## Built-in Skills (Capabilities)

Six built-in capabilities are seeded when an organization completes onboarding. These are universal functions that work across all industries when configured with business-specific reference files.

| Capability | Slug | What It Does |
|-----------|------|-------------|
| **Appointment Booking** | `appointment-booking` | Schedule, reschedule, cancel appointments |
| **Call Transfer** | `call-transfer` | Escalate to human with context handoff |
| **FAQ Responder** | `faq-responder` | Answer common questions from knowledge base |
| **After Hours** | `after-hours` | Handle calls outside business hours |
| **Lead Qualification** | `lead-qualification` | Qualify inbound sales leads (BANT framework) |
| **Payment Collection** | `payment-collection` | Process payments, explain invoices |

**Built-in capabilities are:**
- **Read-only content** — Org admins cannot edit SKILL.md (platform controls the capability logic)
- **Configurable via reference files** — Admins upload business-specific data (service menu, hours, policies) as skill files
- **Auto-synced** — Platform admins can update capability logic across all orgs via `POST /api/v1/skills/sync-all`
- **Composable** — An agent can have `appointment-booking` + `insurance-verification` + `call-transfer` all active

**How they work together:**
```
Caller: "I need to book a cleaning and I have Delta Dental"
Agent (with appointment-booking + insurance-verification):
  1. Uses appointment-booking SKILL.md to gather: service type, date, time
  2. Uses insurance-verification SKILL.md to check: Delta Dental coverage, copay
  3. Uses appointment-booking reference files to confirm: cleaning takes 45 min, $120
  4. Books appointment with all context
```

## API Endpoints

### Organization-level

```
GET    /api/v1/organizations/{org_id}/skills         — List org skills
POST   /api/v1/organizations/{org_id}/skills         — Create custom skill (admin only)
PUT    /api/v1/organizations/{org_id}/skills/{id}     — Update skill (admin only)
DELETE /api/v1/organizations/{org_id}/skills/{id}     — Delete custom skill (admin only)
POST   /api/v1/organizations/{org_id}/skills/seed    — Seed built-in skills (idempotent)
POST   /api/v1/organizations/{org_id}/skills/import  — Import skill from GitHub/skills.sh URL (admin only)
GET    /api/v1/organizations/{org_id}/skills/{id}/agents — List agents using a skill
```

### Skill files

```
GET    /api/v1/organizations/{org_id}/skills/{id}/files          — List skill files (summaries)
POST   /api/v1/organizations/{org_id}/skills/{id}/files          — Create file (admin only)
PUT    /api/v1/organizations/{org_id}/skills/{id}/files/{fid}    — Update file (admin only)
DELETE /api/v1/organizations/{org_id}/skills/{id}/files/{fid}    — Delete file (admin only)
```

### Agent-level

```
GET    /api/v1/agents/{agent_id}/skills              — List agent's assigned skills
POST   /api/v1/agents/{agent_id}/skills              — Assign skill (admin only)
DELETE /api/v1/agents/{agent_id}/skills/{skill_id}    — Unassign skill (admin only)
```

### Tool-facing

```
GET    /api/v1/skills/{org_id}/{slug}                         — Get full skill content (load_skill tool)
GET    /api/v1/skills/{org_id}/{slug}/files/{file_path}       — Get reference file content (load_skill_reference tool)
POST   /api/v1/skills/sync-all                               — Sync built-in skills across all orgs (platform admin)
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
| Create/edit/delete skill files | ✓ | ✓ | ✗ |
| Import skills from URL | ✓ | ✓ | ✗ |
| Sync all orgs | ✓ | ✗ | ✗ |

## voice-ws Integration

voice-ws registers `load_skill` and `load_skill_reference` function tools when an agent has assigned skills:

```python
# Fetch skill summaries for prompt metadata
skill_summaries = await skill_service.get_agent_skill_summaries(agent_id)

# Register load_skill tool (Level 2: load SKILL.md)
load_skill_fn = create_load_skill_function(org_id, skill_service)
livekit_tools.append(function_tool(load_skill_fn, ...))

# Register load_skill_reference tool (Level 3: load sub-files)
load_skill_ref_fn = create_load_skill_reference_function(org_id, skill_service)
livekit_tools.append(function_tool(load_skill_ref_fn, ...))

# Build prompt with skill metadata
instructions = PromptBuilder.build(
    org=org, agent=agent,
    agent_skills=skill_summaries,
)
```

## Frontend UI

### Organization Page — Skills Tab

Split-view layout:
- **Left panel**: Filterable skill list with expandable accordions showing file trees
- **Right panel**: Selected skill or file content rendered as markdown/code/JSON
- Create custom skills via side drawer
- Edit custom skills inline (built-in skills are read-only)
- Import skills from GitHub/skills.sh URLs via input field
- Add/edit/delete reference files within custom skills
- Delete custom skill with agent-usage warning dialog
- URL state management (`?skill=...&file=...`) for bookmarkable navigation

### Agent Detail Page — Skills Tab

Toggle-based assignment:
- Each org skill shown as a card with toggle switch
- Click row to view skill content in side drawer with file tree
- Click individual files to view content (markdown, code, JSON rendering)
- "Manage Skills" link (admin only) to organization settings

## Skill Import

Skills can be imported from GitHub repositories or skills.sh URLs. The importer fetches the entire skill package (SKILL.md + all reference files) via the GitHub REST API — no git clone or shell commands.

**Supported URL formats:**
- GitHub tree: `https://github.com/owner/repo/tree/main/skills/my-skill`
- GitHub repo: `https://github.com/owner/repo` (imports all skills)
- skills.sh: `https://skills.sh/owner/repo/skill-name`
- Key shorthand: `owner/repo/skill-name`
- npx command: `npx skillsadd owner/repo`

**Import process:**
1. Parse URL → extract owner, repo, ref, path
2. Fetch repo tree recursively via GitHub API
3. Locate SKILL.md files within the specified path
4. Parse YAML frontmatter for name/description metadata
5. Fetch all companion files (references, scripts, assets)
6. Store skill + files in database with source_url/source_ref
