# Use Case Templates Management (Admin)

**Audience:** Platform administrators.

## Purpose

Use case templates are reusable, industry-oriented starting points for an agent's
persona, tone, mission, greeting, and instructions. Platform admins manage them
from `/platform/templates`.

Active templates are available to authenticated users through the existing
`GET /api/v1/voice-templates/` endpoint. The agent create wizard and agent
editor already consume this active list and call
`buildMarkdownFromTemplate`, so a newly created or edited active template is
immediately available in both **Create agent** and **Insert template** flows.

## Admin workflow

- Create a template with a name, industry, and optional Markdown-capable text
  fields. The editor guidance explains how fields become the generated
  Markdown.
- Edit any template field or switch a template between active and inactive.
- Inspect the generated Markdown as rendered content or raw source before
  saving.
- Delete a template only after typing the exact phrase `Delete` in the shared
  destructive-action dialog.

Inactive templates remain visible to platform admins for maintenance but are
excluded from onboarding and agent editing. Deleting a template removes the
catalog row; it does not rewrite instructions already inserted into agents.

## API

All routes below require the `platform_admin` role. The frontend check is a UX
guard; the backend is authoritative.

| Action | Endpoint |
| --- | --- |
| List active + inactive | `GET /api/v1/platform/voice-templates/` |
| Get one | `GET /api/v1/platform/voice-templates/{template_id}` |
| Create | `POST /api/v1/platform/voice-templates/` |
| Update | `PUT /api/v1/platform/voice-templates/{template_id}` |
| Delete | `DELETE /api/v1/platform/voice-templates/{template_id}` |

The public list and get endpoints continue to filter on `is_active=true` so
the existing agent insertion behavior stays unchanged.

## Markdown behavior

The stored fields are composed into the canonical agent instruction Markdown:

- `mission` becomes `# Mission`.
- Business context comes from the organization's details at runtime, using
  variables such as `{{org.name}}`; it is not authored in this template.
- `greeting` becomes `# Default Greeting`.
- `custom_instructions` becomes `# Instructions` and supports Markdown lists,
  headings, code blocks, and other content supported by the shared
  `MarkdownRenderer`.

The same generated document is shown in the admin editor, the template preview
sheet, and the agent setup surfaces. When inserted into an agent, the generated
document becomes the agent's **Additional Instructions**. Persona and tone are
also inserted into the agent's structured settings and managed identity
section. Placeholder replacement remains deferred to the existing runtime-aware
helper so saved catalog content stays reusable across organizations.

## Tests

- Backend route tests cover platform-admin authorization and CRUD outcomes in
  `backend/tests/voice_templates/test_admin_routes.py`.
- Backend service tests cover active filtering and CRUD response/error handling
  in `backend/tests/voice_templates/test_service.py`.
- Frontend service tests cover admin endpoint contracts in
  `frontend/src/services/__tests__/voice-template-service.test.ts`.
- Frontend component tests cover list visibility, Markdown preview, create, and
  exact-phrase deletion confirmation in
  `frontend/src/components/voice-templates/__tests__/platform-voice-templates-manager.test.tsx`.
