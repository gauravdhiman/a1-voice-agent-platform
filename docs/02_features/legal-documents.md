# Legal Documents (Terms & Conditions and Privacy Policy)

## Overview

The platform maintains the **Terms & Conditions** and **Privacy Policy** as
versioned, platform-admin-managed documents. Public pages always render the
latest published version; platform admins edit drafts and publish new versions
from `/platform/legal`; new signups must acknowledge both documents before an
account is created; and publishing can notify every previously signed-up user
by email.

Product name in the documents is **24x7 AI**; public pages are
`https://247ai.live/terms` and `https://247ai.live/privacy`.

> **Counsel review required:** the current seed content in
> `backend/src/legal/content.py` is not approved for publication. Updated review
> copies that correct unsupported claims and match the current product are in
> [`docs/legal-review/terms-of-service-review-draft.md`](../legal-review/terms-of-service-review-draft.md)
> and [`docs/legal-review/privacy-policy-review-draft.md`](../legal-review/privacy-policy-review-draft.md).
> Those copies are not the live policy and must not be published until counsel
> and the operator resolve their marked company, contact, billing, and provider
> facts. After approval, update the versioned legal-document seed and publish
> through the documented platform-admin workflow.

## Document model

| Concept    | Implementation                                                                                                                                |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Documents  | `document_key` ∈ `terms` (Terms & Conditions) / `privacy` (Privacy Policy)                                                                    |
| Versions   | `legal_document_versions` rows: one `draft` and one `is_current` per key, enforced by partial unique indexes                                  |
| Publish    | Demotes the predecessor to `deprecated`, promotes the draft to `published` + `is_current`, writes a `legal_document_publish_events` audit row |
| Acceptance | `legal_document_acceptances` rows keyed `(user_id, document_key, version_number)`; source ∈ `signup`, `oauth`, `reaccept`                     |
| Notify     | Optional `legal_update_notification_outbox` rows (one per previously signed-up user) drained by the notification scheduler                    |

Full columns, constraints, and indexes: [`docs/DATABASE_SCHEMA.md`](../DATABASE_SCHEMA.md#legal-document-tables).
Migration: `20261012000001_add_legal_document_versioning.py`.

## Public pages

- `GET /api/v1/legal/{terms|privacy}` returns the current published version as
  Markdown (`LegalDocumentPublic`); 404 when no version has been published yet.
- `/terms` and `/privacy` render that Markdown with loading, empty (404), and
  error states. Both are linked from the public footer and included in the
  sitemap.

## Acceptance capture

**Email/password signup** — the signup form shows a required acknowledgement
checkbox linking `/terms` and `/privacy` in new tabs. The submit button stays
disabled until it is checked, and the backend independently rejects signup with
`400 "You must accept the Terms & Conditions and Privacy Policy to sign up."`
(`SignUpRequest.terms_accepted`), before Turnstile validation. A successful
signup records an acceptance row per currently published document
(`source="signup"`); a capture failure is logged and never fails a completed
signup.

**OAuth (Google, LinkedIn, backend-managed redirect flows)** — the authorize
endpoints accept `terms_accepted`, carry it in the HMAC-signed OAuth state, and
the identity returned by `exchange_code` preserves it. When a **new** account
would be created without the acknowledgement, `complete_oauth_sign_in` rejects
with `403 "You must accept the Terms & Conditions and Privacy Policy to create
an account."` **before** the Supabase user is created, so no orphan user is left
behind. Existing users are never blocked from signing in. The frontend disables
both OAuth buttons until the checkbox is checked and threads
`terms_accepted=true` into the authorize URL.

**Google Identity Services (GIS) ID-token popup** — known gap. This legacy
surface (`GoogleSignInButton`, production-dormant: it is not mounted by any
production page) exchanges the Google ID token directly with Supabase, so there
is no backend route where acceptance can be enforced server-side. The frontend
handler (`signInWithGoogleIdToken`) fail-closes with a client-side guard and
requires `termsAccepted` on the credential payload. If this surface is ever
re-enabled, it MUST gain server-side enforcement (see
`docs/02_features/authentication_rbac/google-identity-services.md`).

`legal_document_acceptances.source = 'reaccept'` is reserved for a future
user-facing re-acknowledgement flow after material document changes.

## Platform-admin management (`/platform/legal`)

Gated by `assert_platform_role(..., "platform_admin")` on every backend route —
the UI hides the nav entry for other roles and the backend still denies them.

- Tabs per document (Terms / Privacy) with the full version history table
  (version number, status, current marker, summary of changes, publish dates).
- **View** (every row): opens a right drawer showing that version's rendered
  Markdown, status, and publish date — including deprecated versions.
- **Edit new draft** / **Continue draft**: a draft editor for the summary of
  changes and the Markdown body. Creating a draft copies the current published
  content as the starting point; only one draft per document can exist (409).
- **Preview** (draft editor): opens a right drawer rendering the unsaved
  editor Markdown exactly as the public page renders it.
- **Publish** (per draft row or from the editor) opens a dialog with the
  "Notify all signed-up users by email" checkbox **checked by default**.
- **Delete draft** removes an unpublished draft; the confirmation dialog
  closes itself after a successful delete.

Publish result reports `notified_count` (recipients queued) in the success
toast.

## User notification dispatch

When publish runs with notify enabled:

1. A `dispatch_id` is generated and one `legal_update_notification_outbox` row
   is enqueued per user who signed up **before** `published_at` (enumerated via
   the Supabase admin API; users without an email are skipped). Rows capture
   the recipient address, name, and `summary_of_changes` as of publish time.
2. The existing `NotificationRetryScheduler` drains the outbox on its regular
   pass (`legal.documents_updated` event, template in
   `backend/src/notifications/templates.py`), sending through
   `notification_service.send_notification` with idempotency key
   `legal:{document_key}:{version_number}:{user_id}`.
3. Failed sends stay pending with bounded exponential retry
   (`attempt_count` capped); at-least-once delivery, duplicates suppressed by
   the notification idempotency key.

The notification email links to the public document page and includes the
document title, version number, and the summary of changes.

## Master-data seeding

The `legal_documents` master-data domain seeds the **initial published v1**
for both documents (`python -m src.master_data.cli preview|apply`, see
[Master-data seeding runbook](../05_operations/master_data_seeding_runbook.md)). Seeding is strictly additive:
a document key with any existing version row is never overwritten. Fresh
environments therefore show both public pages immediately after
`./scripts/worktree-stack.sh up` (which runs the seeder).

## Tests

- `backend/tests/legal/` — service, admin/public routes, migration contract.
- `backend/tests/auth/` — signup acceptance gating, OAuth state round-trip and
  new-user enforcement.
- Frontend — signup consent gating, publish dialog defaults, public document
  page states, admin page gating (Vitest; see `frontend/src/components/legal/`).
