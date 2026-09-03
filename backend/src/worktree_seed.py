"""Bootstrap a local fixture and public demos in an isolated database.

The application schema is owned by Alembic, while Supabase owns local Auth,
Storage, and the Postgres runtime. This module fills the tenant data needed to
sign in and exercise the application after migrations and code-owned master
data have been applied.

The fixture intentionally uses the same three test identities and stable demo
records in every isolated database. The databases themselves remain isolated,
so identical UUIDs and login addresses do not create cross-worktree sharing.
OAuth and API tokens are never copied from staging; provider connections must
be configured independently by the tester.
"""

from __future__ import annotations

import os
from typing import Any

# These are deliberately local-only test credentials. The worktree launcher
# never points at staging or production, and the credentials are not used by
# any deployed environment.
WORKTREE_TEST_PASSWORD = "Password123!"
REGULAR_USER_EMAIL = "regular-user@247ai.local"
ORG_ADMIN_EMAIL = "org-admin@247ai.local"
PLATFORM_ADMIN_EMAIL = "platform-admin@247ai.local"

# Stable fixture identifiers reserved for the local demo environment. Keeping
# the IDs stable makes it possible to use the same agent URL/ID in every local
# worktree while each worktree still owns a separate database.
DEMO_ORGANIZATION_ID = "c521e37a-5588-4906-9330-14364caa0868"
# Compatibility alias for scripts/tests that still use the original fixture
# name. Both public demos intentionally share this tenant.
STAGING_ORGANIZATION_ID = DEMO_ORGANIZATION_ID
STAGING_AGENT_ID = "59252f36-255e-4e71-9250-c4ce3ac27eaa"
# The first HVAC prototype used a second organization. The seed retires this
# exact fixture-owned row without deleting provider state.
LEGACY_HVAC_ORGANIZATION_ID = "e6bbd11b-2dbd-4d75-a0bc-2a3b17f79f17"
HVAC_AGENT_ID = "7c974e5a-9cde-4fd4-8cf1-c13f4d94f8b0"
APPOINTMENT_TOOL_NAME = "Google_calendar_appointment"
LEAD_CAPTURE_TOOL_NAME = "Google_Sheets_lead_capture"
DEMO_CALLS_REMAINING = -1
DEMO_MAX_CALL_DURATION_SECONDS = 900

PLEASANT_PEDIATRIC_BUSINESS_CONTEXT = (
    "Pleasant Pediatric is a fictional pediatric dental practice used for this "
    "public demo."
)

PLEASANT_PEDIATRIC_ADDITIONAL_INSTRUCTIONS = f"""
# Public-demo disclosure
- At the beginning of the call, identify yourself as Alex, a helpful AI assistant
  for Pleasant Pediatric. Never imply that you are human. Use this opening:
  "Thanks for calling Pleasant Pediatric. I'm Alex, a helpful AI assistant. How
  may I help you today?"
- Mention the public-demo and dummy-data notice once near the beginning. Once the
  caller acknowledges it or starts sharing details, do not repeat the notice
  unless the caller asks or appears confused.
- Ask callers to use dummy or secondary contact details. Do not collect real
  health information, dates of birth, insurance data, or medical records.

# Business context
- Practice: {PLEASANT_PEDIATRIC_BUSINESS_CONTEXT}
- Address: 1234 Sunbeam Way, Peoria, AZ 85383.
- Time zone: Arizona time.
- Office hours: Monday-Friday, 8:00 AM-5:00 PM; Saturday, 9:00 AM-1:00 PM;
  Sunday, closed.

# Services and illustrative demo pricing
- New-patient exam with standard X-rays: $95.
- Routine pediatric cleaning: $85.
- Fluoride treatment: $25.
- Dental sealant: $45 per tooth.
- These are fictional demonstration prices, not binding quotes or insurance
  estimates. Share them only when asked and explain that the practice confirms
  final charges. Do not invent another service, price, discount, coverage, or
  policy.
- Routine cleanings are generally recommended every six months, and new patients
  should arrive 15 minutes early.

# Scope and safety
- Handle only basic dental-service questions, new appointment availability, and
  new appointment booking. Politely redirect unrelated questions.
- Do not provide diagnosis, treatment, medication, insurance, legal, financial,
  or other professional advice. For a potentially life-threatening emergency,
  direct the caller to emergency services; do not triage or promise urgent care.
- Never disclose, search for, reschedule, cancel, or modify another person's
  appointment. Do not use existing appointment records to answer questions. If
  asked about an existing appointment, explain that this public demo handles new
  bookings only and direct the caller to the practice.

# Appointment workflow
- Offer only times returned by the calendar availability tool. Book only during
  the stated office hours in Arizona time. For an evening, Sunday, or other
  out-of-hours request, explain the hours and offer an in-hours option; do not
  promise after-hours availability or a callback.
- Collect the patient or guardian name, a caller-confirmed email address, service
  type, and requested time. Check availability before proposing a booking.
- Before the final confirmation, spell the patient or guardian name one letter at
  a time and ask the caller to confirm it. Spell the email one character at a
  time, explicitly saying letters, numbers, "at", "dot", hyphens, and underscores,
  then ask the caller to confirm it. Preserve corrections and repeat the spelling
  until confirmed. Do this at least once before calling `create_appointment`.
- Read the date, time, service type, name, and email back and ask for explicit
  confirmation before calling `create_appointment`. Never claim success unless
  that tool returns a successful result.

# Email follow-up
- If the caller has provided and confirmed an email address and an independent
  email-sending tool is attached, invoke that tool automatically after a
  successful calendar booking unless the caller declines an email. Follow that
  tool's own recipient or route rules and include only the confirmed booking
  details.
- If the email tool confirms success, say that the confirmation email was sent or
  accepted. If no email tool is attached or it reports a failure, say that the
  booking succeeded but the email confirmation was not sent. Never claim an email
  was sent without a successful email-tool result.
""".strip()

PLEASANT_PEDIATRIC_INSTRUCTIONS_MARKDOWN = f"""
# Identity and Persona
- You are Alex, a friendly and helpful AI assistant for Pleasant
  Pediatric, a fictional pediatric dental practice used for this public demo.
- Your communication style is warm, professional, and reassuring.

# Mission
- Help callers find an available new-patient dental appointment and book it
  after confirming the final details. Answer only basic questions about the
  practice and its services.

{PLEASANT_PEDIATRIC_ADDITIONAL_INSTRUCTIONS}
""".strip()

COPPER_RIDGE_BUSINESS_CONTEXT = (
    "Copper Ridge Heating & Air is a fictional home-service company used for "
    "this public demo."
)

COPPER_RIDGE_ADDITIONAL_INSTRUCTIONS = f"""
# Public-demo disclosure
- At the beginning of the call, identify yourself as Jordan, a helpful AI
  assistant for Copper Ridge Heating & Air. Never imply that you are human. Use
  this opening: "Thanks for calling Copper Ridge Heating & Air. I'm Jordan, a
  helpful AI assistant. How may I help you today?"
- Mention the public-demo and dummy-data notice once near the beginning. Once the
  caller acknowledges it or starts sharing details, do not repeat the notice
  unless the caller asks or appears confused.
- Ask callers to use dummy or secondary contact details and not to share
  unnecessary sensitive information.

# Business context
- Business: {COPPER_RIDGE_BUSINESS_CONTEXT}
- Address: 4550 N Copper Ridge Way, Phoenix, AZ 85032.
- Time zone: Arizona time.
- Office hours: Monday-Friday, 7:00 AM-6:00 PM; Saturday, 8:00 AM-2:00 PM;
  Sunday, closed.

# Services and illustrative demo pricing
- HVAC diagnostic or inspection visit: $89.
- Air-conditioning tune-up: $129.
- Heating-system tune-up: $129.
- Indoor-air-quality assessment: $79.
- These are fictional demonstration prices, not binding quotes. Share them only
  when asked, explain that repair or replacement work requires an inspection and
  a confirmed quote, and do not invent another service, price, discount, or
  policy.

# Scope and safety
- Handle only residential HVAC service inquiries and basic information about
  the listed services. Politely redirect unrelated questions.
- Do not diagnose equipment, provide repair instructions, quote repair or
  replacement work, promise a technician, guarantee an arrival time, or offer
  legal, financial, medical, or other professional advice.
- Normal callbacks and service coordination happen during the stated office
  hours. For an out-of-hours callback or service request, explain the hours and
  ask for an in-hours window. You may capture a confirmed request after hours,
  but never promise an after-hours response, dispatch, price, or arrival time.
- If the caller reports a gas smell, suspected carbon monoxide, fire, smoke, or
  another immediate danger, tell them to leave the area, get safe, and contact
  emergency services or the appropriate utility from outside. Do not
  troubleshoot, diagnose, or collect routine details until the danger is
  addressed.
- Do not collect payment details, passwords, government identifiers, or unrelated
  sensitive data.

# Service-inquiry workflow
- Collect the service needed, concise issue description, caller name, phone or
  email, customer service address, urgency, and preferred callback window. Do
  not invent missing values.
- Before the final confirmation, spell the caller's name one letter at a time
  and ask the caller to confirm it. If an email is provided, spell it one
  character at a time, explicitly saying letters, numbers, "at", "dot", hyphens,
  and underscores, then ask the caller to confirm it. Preserve corrections and
  repeat the spelling until confirmed. Do this at least once before calling
  `capture_lead`. If a phone number is provided, read its digits back clearly.
- Read every field back and ask for explicit confirmation before calling
  `capture_lead`. Call it once after confirmation and never claim the inquiry was
  saved unless the tool returns a successful result.

# Email follow-up
- If the caller has provided and confirmed an email address and an independent
  email-sending tool is attached, invoke that tool automatically after a
  successful `capture_lead` result unless the caller declines an email. Follow
  that tool's own recipient or route rules and include only the confirmed
  inquiry details.
- If the email tool confirms success, say that the confirmation email was sent or
  accepted. If no email tool is attached or it reports a failure, say that the
  inquiry was captured but the email confirmation was not sent. Never claim an
  email was sent without a successful email-tool result.
""".strip()

COPPER_RIDGE_INSTRUCTIONS_MARKDOWN = f"""
# Identity and Persona
- You are Jordan, a calm and helpful AI assistant for Copper Ridge Heating & Air,
  a fictional home-service company used for this public demo.
- Your communication style is clear, reassuring, and efficient.

# Mission
- Capture complete, caller-confirmed residential HVAC service inquiries so a
  technician can follow up with the right context.

{COPPER_RIDGE_ADDITIONAL_INSTRUCTIONS}
""".strip()

CALENDAR_DEMO_DISABLED_FUNCTIONS = [
    "find_appointments",
    "update_appointment",
    "cancel_appointment",
]


def build_seed_records(worktree_id: str) -> dict[str, Any]:
    """Build the shared local demo fixture records.

    Args:
        worktree_id: Stable identifier generated by ``worktree-stack.sh``.
            It is stored in Auth metadata so a local account can be traced to
            the worktree that created it. It does not change the fixture IDs or
            business content.

    Returns:
        A mapping containing the organization, agent, account-role bindings,
        and repository-owned tool names to attach to the agent. Sensitive
        OAuth state and passwords are intentionally absent from this mapping.
    """
    if not worktree_id.strip():
        raise ValueError("worktree_id must not be empty")

    organization_id = DEMO_ORGANIZATION_ID
    organization = {
        "id": organization_id,
        "name": "24x7 AI Demo Studio",
        "description": None,
        "slug": "247ai-demo-studio",
        "is_active": True,
        # Business context belongs to each demo agent's instructions. The
        # shared organization contains only operational defaults.
        "industry": None,
        "location": None,
        "timezone": "America/Phoenix",
        # The shared demo organization intentionally has no business-specific
        # free-form context.
        "business_details": None,
        "onboarding_completed": True,
        # Local-only allowance so manual smoke tests are not blocked by
        # billing state. These values are not copied from staging.
        "credit_balance": 100,
        "admin_credit_balance": 0,
        "purchased_credit_balance": 0,
    }
    appointment_agent = {
        "id": STAGING_AGENT_ID,
        "organization_id": organization_id,
        "name": "Alex",
        "phone_number": None,
        "is_active": True,
        "persona": (
            "You are Alex, a friendly and helpful AI assistant for a "
            "pediatric dental practice. You help patients schedule appointments, "
            "answer basic questions about dental services, and provide information "
            "about the practice."
        ),
        "tone": "warm, professional, reassuring",
        "mission": (
            "Help patients schedule dental appointments, answer common "
            "questions about dental services, and provide a welcoming "
            "experience that reduces dental anxiety."
        ),
        "custom_instructions": PLEASANT_PEDIATRIC_ADDITIONAL_INSTRUCTIONS,
        "instructions_markdown": PLEASANT_PEDIATRIC_INSTRUCTIONS_MARKDOWN,
        "use_platform_credits": False,
        "is_published_on_public_page": False,
        # Match staging so the agent detail page exposes Call History in
        # every isolated worktree. Local calls still use the local stack;
        # no staging recording object or OAuth state is copied.
        "call_recording_enabled": True,
        "preset_id": None,
        "is_demo": True,
        "demo_slug": "pleasant-pediatric-appointments",
        "public_description": (
            "Book a new-patient dental appointment by voice. Alex checks "
            "live availability, confirms the details, and writes the booking "
            "to Google Calendar."
        ),
        "demo_calls_remaining": DEMO_CALLS_REMAINING,
        "demo_max_call_duration_seconds": DEMO_MAX_CALL_DURATION_SECONDS,
    }
    lead_agent = {
        "id": HVAC_AGENT_ID,
        "organization_id": organization_id,
        "name": "Jordan",
        "phone_number": None,
        "is_active": True,
        "persona": (
            "You are Jordan, a calm and helpful AI assistant for Copper Ridge "
            "Heating & Air. You make it easy for homeowners to request help."
        ),
        "tone": "clear, reassuring, efficient",
        "mission": (
            "Capture complete HVAC service inquiries so a technician can follow up "
            "with the right context."
        ),
        "custom_instructions": COPPER_RIDGE_ADDITIONAL_INSTRUCTIONS,
        "instructions_markdown": COPPER_RIDGE_INSTRUCTIONS_MARKDOWN,
        "use_platform_credits": False,
        "is_published_on_public_page": False,
        "call_recording_enabled": True,
        "preset_id": None,
        "is_demo": True,
        "demo_slug": "copper-ridge-service-request",
        "public_description": (
            "Describe a home-service issue to Jordan and watch a complete service "
            "inquiry get captured in Google Sheets for follow-up."
        ),
        "demo_calls_remaining": DEMO_CALLS_REMAINING,
        "demo_max_call_duration_seconds": DEMO_MAX_CALL_DURATION_SECONDS,
    }
    return {
        "organization": organization,
        "agent": appointment_agent,
        "organizations": [organization],
        "agents": [appointment_agent, lead_agent],
        "accounts": [
            {
                "email": REGULAR_USER_EMAIL,
                "role": "regular_user",
                "organization_id": organization_id,
            },
            {
                "email": ORG_ADMIN_EMAIL,
                "role": "org_admin",
                "organization_id": organization_id,
            },
            {
                "email": PLATFORM_ADMIN_EMAIL,
                "role": "platform_admin",
                "organization_id": None,
            },
        ],
        # Staging has other remote MCP links on this agent, but their provider
        # rows and OAuth state are environment-specific. These native tools are
        # the repository-owned capabilities this fixture is for.
        "agent_tools": [APPOINTMENT_TOOL_NAME],
        "agent_tools_by_agent": {
            STAGING_AGENT_ID: [APPOINTMENT_TOOL_NAME],
            HVAC_AGENT_ID: [LEAD_CAPTURE_TOOL_NAME],
        },
        "agent_tool_configs": {
            STAGING_AGENT_ID: {
                APPOINTMENT_TOOL_NAME: {
                    "calendar_id": "primary",
                    "timezone": "America/Phoenix",
                    "require_phone": False,
                    "require_email": True,
                }
            },
            HVAC_AGENT_ID: {
                LEAD_CAPTURE_TOOL_NAME: {
                    "lead_source": "24x7 AI public demo",
                    "append_range": "Lead submissions!A:L",
                    "dedupe_range": "Lead submissions!A:A",
                }
            },
        },
        # The public dental demo only needs availability lookup and new
        # appointment booking. Do not expose existing-appointment search or
        # mutation functions to an unauthenticated caller.
        "agent_tool_function_exclusions": {
            STAGING_AGENT_ID: {
                APPOINTMENT_TOOL_NAME: list(CALENDAR_DEMO_DISABLED_FUNCTIONS),
            }
        },
        # The earlier local prototype attached HubSpot to these demos. Disable
        # that exact stale link during reseeding while preserving its saved
        # credentials/configuration for the general HubSpot integration. Email
        # tools remain independently configurable by the platform administrator.
        "agent_tools_to_disable_by_agent": {
            STAGING_AGENT_ID: ["HubSpot_lead_capture"],
            HVAC_AGENT_ID: ["HubSpot_lead_capture"],
        },
        "retired_organization_ids": [LEGACY_HVAC_ORGANIZATION_ID],
    }


def _required_environment(name: str) -> str:
    """Read a required bootstrap environment variable with a clear error.

    Args:
        name: Environment variable name to read.

    Returns:
        A non-empty, trimmed environment value.

    Raises:
        RuntimeError: If the variable is missing or empty.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for worktree seeding")
    return value


def _response_rows(response: Any) -> list[dict[str, Any]]:
    """Extract PostgREST rows from a Supabase response."""
    data = getattr(response, "data", None)
    if data is None and isinstance(response, dict):
        data = response.get("data")
    return list(data or [])


def _response_user(response: Any) -> Any:
    """Extract an Auth user object from a Supabase admin response."""
    user = getattr(response, "user", None)
    if user is not None:
        return user
    if isinstance(response, dict):
        return response.get("user", response)
    return response


def _user_id(user: Any) -> str:
    """Extract and validate a string user ID from an Auth response."""
    value = getattr(user, "id", None)
    if value is None and isinstance(user, dict):
        value = user.get("id")
    if not value:
        raise RuntimeError("Supabase Auth did not return a user ID")
    return str(value)


def _find_auth_user(client: Any, email: str) -> Any | None:
    """Find an Auth user by email using bounded admin pagination.

    Args:
        client: Supabase client configured with the local service role key.
        email: Case-insensitive email address to find.

    Returns:
        The matching Auth user, or ``None`` when no matching user exists.
    """
    for page in range(1, 11):
        response = client.auth.admin.list_users(page=page, per_page=200)
        users = getattr(response, "users", None)
        if users is None and isinstance(response, list):
            users = response
        users = list(users or [])
        for user in users:
            user_email = getattr(user, "email", None)
            if user_email is None and isinstance(user, dict):
                user_email = user.get("email")
            if user_email and user_email.lower() == email.lower():
                return user
        if len(users) < 200:
            break
    return None


def _ensure_auth_user(client: Any, email: str, worktree_id: str) -> str:
    """Create or refresh one deterministic local email/password test user.

    Args:
        client: Supabase client configured with the local service role key.
        email: Fixed local test email address.
        worktree_id: Worktree identifier stored in user metadata for tracing.

    Returns:
        The Auth user UUID.

    Raises:
        RuntimeError: If Auth cannot create, find, or update the user.
    """
    metadata = {
        "first_name": "Worktree",
        "last_name": "Test User",
        "worktree_id": worktree_id,
        "last_sign_in_method": "email",
    }
    try:
        response = client.auth.admin.create_user(
            {
                "email": email,
                "password": WORKTREE_TEST_PASSWORD,
                "email_confirm": True,
                "user_metadata": metadata,
            }
        )
        return _user_id(_response_user(response))
    except Exception as exc:
        message = str(exc).lower()
        if "already" not in message and "exists" not in message:
            raise RuntimeError("could not create the local worktree test user") from exc

    existing = _find_auth_user(client, email)
    if existing is None:
        raise RuntimeError("Supabase reported an existing user but could not find it")
    existing_id = _user_id(existing)
    client.auth.admin.update_user_by_id(
        existing_id,
        {
            "password": WORKTREE_TEST_PASSWORD,
            "email_confirm": True,
            "user_metadata": metadata,
        },
    )
    return existing_id


def _upsert_organization(client: Any, record: dict[str, Any]) -> None:
    """Insert or refresh the local demo organization.

    Credit balances are only written on first insert. This makes rerunning the
    launcher safe for a manual smoke test that has already consumed credits.
    """
    existing = (
        client.table("organizations")
        .select("id")
        .eq("id", record["id"])
        .limit(1)
        .execute()
    )
    if _response_rows(existing):
        updates = {
            key: value
            for key, value in record.items()
            if key
            not in {
                "id",
                "credit_balance",
                "admin_credit_balance",
                "purchased_credit_balance",
            }
        }
        client.table("organizations").update(updates).eq("id", record["id"]).execute()
        return
    client.table("organizations").insert(record).execute()


def _retire_organizations(client: Any, organization_ids: list[str]) -> None:
    """Deactivate fixture organizations superseded by the shared demo tenant.

    The first HVAC demo prototype created a separate organization. Retiring
    that exact stable fixture row makes existing worktrees converge without
    deleting rows that could still be referenced by provider or audit data.
    """
    for organization_id in organization_ids:
        if organization_id == DEMO_ORGANIZATION_ID:
            continue
        client.table("organizations").update({"is_active": False}).eq(
            "id", organization_id
        ).execute()


def _upsert_agent(client: Any, record: dict[str, Any]) -> None:
    """Insert or refresh one local demo agent."""
    existing = (
        client.table("voice_agents")
        .select("id")
        .eq("id", record["id"])
        .limit(1)
        .execute()
    )
    if _response_rows(existing):
        updates = {key: value for key, value in record.items() if key != "id"}
        client.table("voice_agents").update(updates).eq("id", record["id"]).execute()
        return
    client.table("voice_agents").insert(record).execute()


def _role_id(client: Any, role_name: str) -> str:
    """Resolve one migration-managed role ID by its stable name."""
    response = (
        client.table("roles").select("id").eq("name", role_name).limit(1).execute()
    )
    rows = _response_rows(response)
    if not rows:
        raise RuntimeError(f"the {role_name} role is missing; run Alembic first")
    return str(rows[0]["id"])


def _ensure_user_role(
    client: Any,
    user_id: str,
    role_name: str,
    organization_id: str | None,
) -> None:
    """Ensure one user has the requested organization- or platform-scoped role.

    Args:
        client: Supabase client configured with the local service role key.
        user_id: Auth user UUID.
        role_name: Migration-managed role name.
        organization_id: Organization UUID for an org-scoped role, or ``None``
            for an org-agnostic platform role.

    Raises:
        RuntimeError: If the role is not present after migrations.
    """
    role_id = _role_id(client, role_name)
    query = client.table("user_roles").select("id,role_id").eq("user_id", user_id)
    if organization_id is None:
        query = query.is_("organization_id", "null")
    else:
        query = query.eq("organization_id", organization_id)
    existing = _response_rows(query.limit(1).execute())

    if existing:
        if str(existing[0].get("role_id")) != role_id:
            client.table("user_roles").update({"role_id": role_id}).eq(
                "id", existing[0]["id"]
            ).execute()
        return

    client.table("user_roles").insert(
        {
            "user_id": user_id,
            "role_id": role_id,
            "organization_id": organization_id,
        }
    ).execute()


def _ensure_agent_tools(
    client: Any,
    agent_id: str,
    tool_names: list[str],
    tool_configs: dict[str, dict[str, Any]] | None = None,
    function_exclusions: dict[str, list[str]] | None = None,
) -> list[str]:
    """Attach repository-owned tools while preserving local OAuth state.

    Args:
        client: Supabase client configured with the local service role key.
        agent_id: Voice agent UUID receiving the tool links.
        tool_names: Platform tool names that must be enabled for the agent.
        tool_configs: Optional public configuration keyed by platform-tool name.
        function_exclusions: Optional function names to disable, keyed by
            platform-tool name. An explicitly supplied list is synchronized on
            every seed so a public fixture cannot regain unsafe functions after
            a restart.

    Returns:
        The names successfully attached or already present.

    Raises:
        RuntimeError: If a required platform tool was not synchronized first.
    """
    attached: list[str] = []
    for tool_name in tool_names:
        tool_response = (
            client.table("platform_tools")
            .select("id")
            .eq("name", tool_name)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        tools = _response_rows(tool_response)
        if not tools:
            raise RuntimeError(
                f"the {tool_name} platform tool is missing; run master-data seed first"
            )
        tool_id = str(tools[0]["id"])
        existing = (
            client.table("agent_tools")
            .select("id,config")
            .eq("agent_id", agent_id)
            .eq("tool_id", tool_id)
            .limit(1)
            .execute()
        )
        existing_rows = _response_rows(existing)
        config = (tool_configs or {}).get(tool_name)
        excluded_functions = (function_exclusions or {}).get(tool_name)
        if existing_rows:
            # Do not clear sensitive_config: a tester may have completed local
            # OAuth and then restarted the stack.
            updates: dict[str, Any] = {"is_enabled": True}
            if config and not existing_rows[0].get("config"):
                updates["config"] = config
            if excluded_functions is not None:
                updates["unselected_functions"] = excluded_functions
            client.table("agent_tools").update(updates).eq(
                "id", existing_rows[0]["id"]
            ).execute()
        else:
            client.table("agent_tools").insert(
                {
                    "agent_id": agent_id,
                    "tool_id": tool_id,
                    "config": config,
                    "sensitive_config": None,
                    "unselected_functions": excluded_functions,
                    "is_enabled": True,
                }
            ).execute()
        attached.append(tool_name)
    return attached


def _disable_agent_tools(
    client: Any, agent_id: str, tool_names: list[str]
) -> list[str]:
    """Disable stale fixture links without deleting their saved credentials.

    Args:
        client: Supabase client configured with the local service role key.
        agent_id: Voice agent whose obsolete links should be disabled.
        tool_names: Exact platform-tool names to disable.

    Returns:
        The names that were found and disabled.
    """
    disabled: list[str] = []
    for tool_name in tool_names:
        tool_response = (
            client.table("platform_tools")
            .select("id")
            .eq("name", tool_name)
            .limit(1)
            .execute()
        )
        tools = _response_rows(tool_response)
        if not tools:
            continue
        client.table("agent_tools").update({"is_enabled": False}).eq(
            "agent_id", agent_id
        ).eq("tool_id", str(tools[0]["id"])).execute()
        disabled.append(tool_name)
    return disabled


def seed_local_stack(
    supabase_url: str,
    service_key: str,
    worktree_id: str,
) -> dict[str, Any]:
    """Create or refresh local accounts, tenant, agent, roles, and tool links.

    Args:
        supabase_url: Local Supabase API URL reachable from the backend
            container.
        service_key: Local Supabase service-role key. It is never printed.
        worktree_id: Stable identifier for this worktree.

    Returns:
        Safe identifiers and email addresses for the fixture. Passwords and
        OAuth tokens are excluded.

    Raises:
        RuntimeError: If Auth, RBAC, application tables, or a required native
            demo tool cannot be seeded.
    """
    from supabase import create_client

    client = create_client(supabase_url, service_key)
    records = build_seed_records(worktree_id)
    organization = records["organization"]
    agent = records["agent"]

    for organization_record in records.get("organizations", [organization]):
        _upsert_organization(client, organization_record)
    _retire_organizations(client, records.get("retired_organization_ids", []))
    for agent_record in records.get("agents", [agent]):
        _upsert_agent(client, agent_record)

    account_ids: dict[str, str] = {}
    for account in records["accounts"]:
        user_id = _ensure_auth_user(client, account["email"], worktree_id)
        _ensure_user_role(
            client,
            user_id,
            account["role"],
            account["organization_id"],
        )
        account_ids[account["email"]] = user_id

    attached_tools_by_agent: dict[str, list[str]] = {}
    agent_tools_by_agent = records.get(
        "agent_tools_by_agent", {agent["id"]: records["agent_tools"]}
    )
    agent_tool_configs = records.get("agent_tool_configs", {})
    agent_tool_function_exclusions = records.get("agent_tool_function_exclusions", {})
    agent_tools_to_disable_by_agent = records.get("agent_tools_to_disable_by_agent", {})
    for agent_record in records.get("agents", [agent]):
        agent_id = agent_record["id"]
        attached_tools_by_agent[agent_id] = _ensure_agent_tools(
            client,
            agent_id,
            agent_tools_by_agent.get(agent_id, []),
            agent_tool_configs.get(agent_id, {}),
            agent_tool_function_exclusions.get(agent_id, {}),
        )
        _disable_agent_tools(
            client,
            agent_id,
            agent_tools_to_disable_by_agent.get(agent_id, []),
        )
    attached_tools = attached_tools_by_agent.get(agent["id"], [])
    return {
        "organization_id": organization["id"],
        "agent_id": agent["id"],
        "regular_user_email": REGULAR_USER_EMAIL,
        "org_admin_email": ORG_ADMIN_EMAIL,
        "platform_admin_email": PLATFORM_ADMIN_EMAIL,
        "regular_user_id": account_ids[REGULAR_USER_EMAIL],
        "org_admin_id": account_ids[ORG_ADMIN_EMAIL],
        "platform_admin_id": account_ids[PLATFORM_ADMIN_EMAIL],
        "agent_tools": attached_tools,
        "agent_tools_by_agent": attached_tools_by_agent,
    }


def main() -> int:
    """Run the worktree seed from environment variables and print safe output."""
    result = seed_local_stack(
        _required_environment("SUPABASE_URL"),
        _required_environment("SUPABASE_SERVICE_KEY"),
        _required_environment("WORKTREE_ID"),
    )
    print("Worktree seed ready:")
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
