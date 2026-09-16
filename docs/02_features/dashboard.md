# Workspace dashboard

The home dashboard is an operational snapshot of the organization selected in
the workspace switcher. Every role, including platform admins, sees that
organization's calls, agents, callback queue, and (when permitted) billing data.
The page never replaces the selected workspace with cross-organization totals.

## What the dashboard shows

| Position | Widget | Why it is useful |
| --- | --- | --- |
| Top | Call performance filters and four metrics | A single Today, Yesterday, 7-day, 15-day, or 30-day period and optional call status filter update the call widgets together. Metrics show total calls, completed calls, unsuccessful outcomes, and average completed-call duration. |
| First chart row | Daily call volume and peak call hours | Shows changes in call demand and the busiest hour in the organization's timezone. The volume chart follows the pointer with a date/count crosshair and also supports arrow-key and touch inspection. |
| Second insight row | Call outcomes and agent activity | Shows the selected window's status mix, active/configured agent counts, and the five busiest agents with call count, completed-call average, and latest call status/time. |
| Activity row | Recent calls and follow-up requests | Gives a short, privacy-conscious call-log preview plus the newest callback requests, with urgent requests first. Detailed records open in Call History or Callbacks. |
| Admin-only | Account capacity and platform pulse | Users with billing permission see current voice credits and subscription status. Platform admins also see a compact all-organization call pulse and a separate platform overview page. |

Regular users and organization admins get the same selected-workspace operating
picture. Permission-specific actions stay with the relevant roles: agent creation
and callback management are admin actions, and the billing request is made only
for a user allowed to manage billing. Platform admins retain the selected
workspace view, with a separate cross-organization pulse above it and a
platform-only overview page for broader call trends. If no organization is
selected, workspace widgets wait for a selection; a platform admin can still
see the platform pulse and open platform administration.

## Metric definitions and filters

- **Reporting period:** Today runs from local midnight to the current time;
  Yesterday covers the previous local calendar day. Both follow the selected
  organization's timezone. Last 7, 15, and 30 days are rolling 24-hour windows
  ending at the current time. Platform reports use UTC for calendar days.
  Rolling chart buckets use local calendar dates and may include partial days
  at either end.
- **Call status:** the dropdown contains statuses observed in the last 30 days.
  Selecting one filters the KPI counts, daily/hourly charts, outcome mix,
  per-agent call activity, and recent-call preview. Agent capacity, callbacks,
  credits, and subscription status do not depend on call filters.
- **Calls:** call-log records in the selected period and optional status. All
  sources are included, including browser tests and demos; the dashboard says so
  beside the metrics.
- **Completed:** records whose status is `completed`. The completion percentage
  is shown only when no single status filter is selected.
- **Unsuccessful:** records marked failed, busy, missed/unanswered, or canceled.
  Other and in-progress statuses remain available in the outcome mix.
- **Average connected:** mean recorded duration for completed calls in the
  selected period and status. Calls without a duration are excluded; no matching
  recorded duration is shown as unavailable rather than as zero.
- **Peak call hours:** calls grouped by hour in the organization's timezone. The
  report uses the organization timezone, with UTC as fallback.
- **Agent activity:** the five agents with the most calls matching the active
  call filters. Each row includes its matching call count, mean duration for
  completed calls with recorded durations, and most recent matching call.
  Unassigned calls are grouped separately.
- **Agent capacity:** configured and active agent counts for the selected
  organization. The API returns these counts only; it does not fetch prompts,
  settings, credentials, or other private agent configuration.
- **Recent calls:** up to six latest records matching the active call filters.
  The preview omits caller phone numbers and links to the full call history.
- **Follow-up requests:** latest new callback requests, urgent first. This is a
  short queue preview, not a total backlog count.
- **Platform pulse:** platform-admin-only, last-30-day call count and number of
  organizations with call activity. It is not an active-customer or paying
  organization count.
- **Platform overview:** a separate platform-admin page for cross-organization
  Today, Yesterday, 7-, 15-, or 30-day call volume, status mix, UTC demand
  patterns, and organizations with calls matching the selected period and
  status. It does not replace the selected-workspace dashboard.
- **Chart interaction:** Every workspace and platform dashboard chart uses the
  shared `InteractiveChart` surface. Its crosshair and date/category readout
  update on pointer movement; arrow keys, Home/End, and touch selection are
  supported. New dashboard charts should use this surface and supply their
  scale mapping for point, equal-width bar, or weighted-segment data.
- **Account capacity:** current credit balance and subscription status from the
  selected organization's billing summary. It is shown only when the user's
  resolved permissions allow billing management.

Call analytics, agent capacity, callbacks, and billing each keep independent
loading, empty, and retryable error states. A failed API response is never
rendered as a zero metric. Organization-specific query keys prevent a previous
workspace's data from remaining visible after an organization switch.

## Data and access boundaries

- `GET /api/v1/calls/organization/{org_id}/analytics` returns organization
  analytics and requires the caller to belong to or administer that
  organization. Specify either `period=today|yesterday` or
  `period_days=7|15|30`; `status` is optional; the IANA `timezone_name` is
  validated before aggregation.
- `GET /api/v1/calls/organization/{org_id}` supplies the paginated recent-call
  preview with the same half-open date window (`date_from` inclusive,
  `date_to_exclusive` exclusive) and status filters. Existing callers may use
  inclusive `date_to`; the two end-date parameters cannot be combined.
- `GET /api/v1/agents/organization/{org_id}/summary` requires `agent:read` for
  the organization and returns only `total_agents` and `active_agents`.
- `GET /api/v1/calls/platform/analytics` is platform-admin-only. It accepts the
  same calendar-day or 7/15/30-day period and optional status filter and
  aggregates in UTC. The
  home page uses it for the compact platform pulse; `/platform/dashboard` uses
  it for the detailed cross-organization overview. Neither replaces the
  selected-workspace report.
- Analytics reads request only aggregation fields, page deterministically, run
  synchronous database I/O in worker threads, and fail at the 100,000-row
  reporting cap rather than returning partial totals. Reports are live reads,
  not transactional snapshots; concurrent call updates may appear between
  pages. Removed agent names can be unavailable.

## Validation

Backend behavior and permission coverage: `backend/tests/call_logs/test_dashboard_analytics.py`
and `backend/tests/voice_agents/test_dashboard_agent_summary.py`. Frontend
role, filter, empty, error, and organization-switch behavior:
`frontend/src/app/(dashboard)/dashboard/__tests__/page.test.tsx`. Platform-page
role and filter behavior: `frontend/src/app/(dashboard)/platform/dashboard/__tests__/page.test.tsx`.
Browser coverage: `e2e/tests/test_role_dashboard.py`. Run browser coverage against an
isolated worktree stack with
`E2E_REAL_AUTH=1 E2E_BASE_URL=http://localhost:<worktree-port> .venv/bin/pytest e2e/tests/test_role_dashboard.py --browser-channel chrome -q`.
