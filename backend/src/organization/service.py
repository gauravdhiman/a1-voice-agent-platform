"""
Organization service for managing organizations in a multi-tenant SaaS platform.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from opentelemetry import metrics, trace
from src.notifications.models import SendNotificationRequest
from src.notifications.service import notification_service
from src.organization.invitation_models import (
    Invitation,
    InvitationCreate,
    InvitationStatus,
)
from src.organization.models import Organization, OrganizationCreate, OrganizationUpdate
from src.rbac.roles.service import role_service
from src.rbac.user_roles.models import UserRoleCreate
from src.rbac.user_roles.service import user_role_service

from shared.common.errors import ErrorCode
from shared.common.security import decrypt_data, encrypt_data
from shared.config import settings
from shared.organization.service import BaseOrganizationService
from shared.organization.timezone import normalize_timezone_input

logger = logging.getLogger(__name__)

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Get meter for this module
meter = metrics.get_meter(__name__)

# Create metrics
organization_operations_counter = meter.create_counter(
    "organization.operations", description="Number of organization operations"
)

organization_errors_counter = meter.create_counter(
    "organization.errors", description="Number of organization operation errors"
)


class OrganizationService(BaseOrganizationService):
    """Service for handling organization operations."""

    # ------------------------------------------------------------------
    # Provider-credentials blob helpers (Phase 3)
    # ------------------------------------------------------------------
    @staticmethod
    def _organization_from_dict(org_dict: dict) -> Organization:
        """Build an :class:`Organization` from a raw Supabase row.

        Resolves the Google API key from the encrypted ``provider_credentials``
        blob (the source of truth as of Phase 3), falling back to the legacy
        plaintext ``google_api_key`` column for rows that have not yet been
        migrated. The encrypted blob is also attached to the model so the worker
        path (which decrypts it itself) and any internal caller can read it.

        Also derives ``provider_credentials_status`` — a per-provider
        "configured?" boolean map (never the decrypted values) — so the
        org-settings UI can show Configured/Not-configured pills per provider
        without exposing secrets to the frontend.

        Args:
            org_dict: A raw row from the ``organizations`` table.

        Returns:
            An :class:`Organization` with ``google_api_key`` populated from the
            decrypted blob (so the existing org-settings UI form still works),
            ``provider_credentials`` carrying the opaque encrypted blob, and
            ``provider_credentials_status`` carrying the per-provider boolean
            map.
        """
        provider_credentials = org_dict.get("provider_credentials")
        google_api_key = org_dict.get("google_api_key")
        creds: dict = {}
        if provider_credentials:
            try:
                decrypted = decrypt_data(provider_credentials)
                if isinstance(decrypted, dict):
                    creds = decrypted
                    if creds.get("google"):
                        google_api_key = creds["google"]
            except Exception as e:
                logger.error(
                    "Failed to decrypt provider_credentials for org %s: %s",
                    org_dict.get("id"),
                    e,
                    exc_info=True,
                )
        # Per-provider "configured?" booleans. `google` is True when resolvable
        # from the blob OR the legacy plaintext column fallback; string providers
        # are True when present in the decrypted blob.
        provider_credentials_status = {
            "google": bool(google_api_key),
            "deepgram": bool(creds.get("deepgram")),
            "openai": bool(creds.get("openai")),
            "cartesia": bool(creds.get("cartesia")),
            "cerebras": bool(creds.get("cerebras")),
            "openrouter": bool(creds.get("openrouter")),
            "fish": bool(creds.get("fish")),
            "resend": bool(creds.get("resend")),
        }
        return Organization(
            id=org_dict["id"],
            name=org_dict["name"],
            description=org_dict["description"],
            slug=org_dict["slug"],
            website=org_dict.get("website"),
            is_active=org_dict["is_active"],
            industry=org_dict.get("industry"),
            location=org_dict.get("location"),
            timezone=org_dict.get("timezone"),
            business_details=org_dict.get("business_details"),
            google_api_key=google_api_key,
            provider_credentials=provider_credentials,
            provider_credentials_status=provider_credentials_status,
            onboarding_completed=org_dict.get("onboarding_completed", False),
            public_page_enabled=bool(org_dict.get("public_page_enabled", False)),
            public_page_passphrase_enabled=bool(
                org_dict.get("public_page_passphrase_enabled", False)
            ),
            created_at=org_dict["created_at"],
            updated_at=org_dict["updated_at"],
        )

    @staticmethod
    def _merge_provider_credentials(
        existing_blob: Optional[str], updates: dict
    ) -> Optional[str]:
        """Merge provider-credential updates into the encrypted blob.

        Decrypts the existing blob (if any), applies ``updates`` (where a
        ``None`` value clears that provider), drops cleared keys, and re-encrypts.
        Returns ``None`` when no providers remain (so the column can be set to
        NULL).

        Args:
            existing_blob: The current encrypted ``provider_credentials`` value
                (or ``None``).
            updates: A dict of provider -> value (string or nested dict) to
                merge; a ``None`` value clears that provider.

        Returns:
            The new encrypted blob, or ``None`` if no providers remain.
        """
        creds: dict = {}
        if existing_blob:
            try:
                decrypted = decrypt_data(existing_blob)
                if isinstance(decrypted, dict):
                    creds = dict(decrypted)
            except Exception as e:
                logger.error(
                    "Failed to decrypt existing provider_credentials for merge: %s",
                    e,
                    exc_info=True,
                )
        for provider, value in updates.items():
            if value is None:
                creds.pop(provider, None)
            else:
                creds[provider] = value
        if not creds:
            return None
        return encrypt_data(creds)

    @tracer.start_as_current_span("organization.create_organization")
    async def create_organization(
        self, org_data: OrganizationCreate
    ) -> tuple[Optional[Organization], Optional[str]]:
        """Create a new organization."""
        organization_operations_counter.add(1, {"operation": "create_organization"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("organization.name", org_data.name)
        try:
            response = (
                self.supabase.table("organizations")
                .insert(
                    {
                        "name": org_data.name,
                        "description": org_data.description,
                        "slug": org_data.slug,
                        "website": str(org_data.website) if org_data.website else None,
                        "is_active": org_data.is_active,
                        "industry": org_data.industry,
                        "location": org_data.location,
                        "business_details": org_data.business_details,
                    }
                )
                .execute()
            )

            if not response.data:
                logger.error(f"Failed to create organization: {org_data.name}")
                current_span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR, "Failed to create organization"
                    )
                )
                organization_errors_counter.add(
                    1, {"operation": "create_organization", "error": "no_data_returned"}
                )
                return None, "Failed to create organization"

            org_dict = response.data[0]
            organization = self._organization_from_dict(org_dict)
            current_span.set_attribute("organization.id", str(organization.id))
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return organization, None

        except Exception as e:
            logger.error(
                f"Exception while creating organization '{org_data.name}': {e}",
                exc_info=True,
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "create_organization", "error": "exception"}
            )
            return None, str(e)

    @tracer.start_as_current_span("organization.get_organization_by_id")
    async def get_organization_by_id(
        self, org_id: UUID
    ) -> tuple[Optional[Organization], Optional[str]]:
        """Get an organization by its ID."""
        organization_operations_counter.add(1, {"operation": "get_organization_by_id"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("organization.id", str(org_id))
        try:
            response = (
                self.supabase.table("organizations")
                .select("*")
                .eq("id", str(org_id))
                .execute()
            )

            if not response.data:
                logger.warning(f"Organization not found: {org_id}")
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Organization not found")
                )
                organization_errors_counter.add(
                    1, {"operation": "get_organization_by_id", "error": "not_found"}
                )
                return None, "Organization not found"

            org_dict = response.data[0]
            organization = self._organization_from_dict(org_dict)
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return organization, None

        except Exception as e:
            logger.error(
                f"Exception while getting organization {org_id}: {e}", exc_info=True
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "get_organization_by_id", "error": "exception"}
            )
            return None, str(e)

    @tracer.start_as_current_span("organization.get_organization_by_slug")
    async def get_organization_by_slug(
        self, slug: str
    ) -> tuple[Optional[Organization], Optional[str]]:
        """Get an organization by its slug."""
        organization_operations_counter.add(
            1, {"operation": "get_organization_by_slug"}
        )

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("organization.slug", slug)
        try:
            response = (
                self.supabase.table("organizations")
                .select("*")
                .eq("slug", slug)
                .execute()
            )

            if not response.data:
                logger.warning(f"Organization not found with slug: {slug}")
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Organization not found")
                )
                organization_errors_counter.add(
                    1, {"operation": "get_organization_by_slug", "error": "not_found"}
                )
                return None, "Organization not found"

            org_dict = response.data[0]
            organization = self._organization_from_dict(org_dict)
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return organization, None

        except Exception as e:
            logger.error(
                f"Exception while getting organization with slug '{slug}': {e}",
                exc_info=True,
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "get_organization_by_slug", "error": "exception"}
            )
            return None, str(e)

    @tracer.start_as_current_span("organization.get_all_organizations")
    async def get_all_organizations(self) -> tuple[list[Organization], Optional[str]]:
        """Get all organizations."""
        organization_operations_counter.add(1, {"operation": "get_all_organizations"})

        try:
            response = self.supabase.table("organizations").select("*").execute()

            organizations = []
            for org_dict in response.data:
                organizations.append(self._organization_from_dict(org_dict))

            return organizations, None

        except Exception as e:
            logger.error(
                f"Exception while getting all organizations: {e}", exc_info=True
            )
            organization_errors_counter.add(
                1, {"operation": "get_all_organizations", "error": "exception"}
            )
            return [], str(e)

    async def _is_organization_slug_taken(
        self, slug: str, exclude_org_id: UUID
    ) -> tuple[bool, str]:
        """Return whether ``slug`` is already used by another organization."""
        response = (
            self.supabase.table("organizations")
            .select("id")
            .eq("slug", slug)
            .neq("id", str(exclude_org_id))
            .limit(1)
            .execute()
        )
        if response.data:
            return True, f"Slug '{slug}' is already taken"
        return False, ""

    @tracer.start_as_current_span("organization.update_organization")
    async def update_organization(
        self, org_id: UUID, org_data: OrganizationUpdate
    ) -> tuple[Optional[Organization], Optional[str]]:
        """Update an organization."""
        organization_operations_counter.add(1, {"operation": "update_organization"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("organization.id", str(org_id))
        try:
            update_data = {}
            if org_data.name is not None:
                update_data["name"] = org_data.name
                current_span.set_attribute("organization.name.updated", True)
            if org_data.description is not None:
                update_data["description"] = org_data.description
            if org_data.slug is not None:
                from shared.organization.slug_utils import (
                    normalize_organization_slug,
                    validate_organization_slug,
                )

                normalized = normalize_organization_slug(org_data.slug)
                is_valid, validation_error = validate_organization_slug(normalized)
                if not is_valid:
                    return None, validation_error
                taken, taken_error = await self._is_organization_slug_taken(
                    normalized, org_id
                )
                if taken:
                    return None, taken_error
                update_data["slug"] = normalized
            if org_data.website is not None:
                update_data["website"] = org_data.website
            # is_active is intentionally excluded from frontend updates for safety
            # it should only be changed through administrative actions or specific backend logic
            if org_data.industry is not None:
                update_data["industry"] = org_data.industry
            if org_data.location is not None:
                update_data["location"] = org_data.location
            if org_data.timezone is not None:
                normalized_tz, tz_error = normalize_timezone_input(org_data.timezone)
                if tz_error:
                    return None, tz_error
                update_data["timezone"] = normalized_tz
            if org_data.business_details is not None:
                update_data["business_details"] = org_data.business_details

            # ── Provider credentials (Phase 3) ──────────────────────────────
            # All per-org provider keys now live in one Fernet-encrypted
            # ``provider_credentials`` JSON blob. The legacy plaintext
            # ``google_api_key`` column is no longer the source of truth: a
            # Google key supplied here is validated, then encrypted into
            # ``provider_credentials["google"]`` (merged with any existing
            # providers), and the plaintext column is cleared so the secret
            # exists only in encrypted form. ``provider_credentials_input``
            # carries the other providers (deepgram/openai/cartesia/cerebras/
            # openrouter/fish/resend) plus google when the credentials card
            # is used. An empty ``google_api_key`` clears the
            # google entry from the blob.
            cred_updates: dict = {}
            if (
                org_data.google_api_key is not None
                and org_data.google_api_key.strip() != ""
            ):
                is_valid, validation_error = await self.validate_google_api_key(
                    org_data.google_api_key
                )
                if not is_valid:
                    current_span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR,
                            f"Invalid Google API key: {validation_error}",
                        )
                    )
                    organization_errors_counter.add(
                        1,
                        {
                            "operation": "update_organization",
                            "error": "invalid_google_api_key",
                        },
                    )
                    return None, f"Invalid Google API key: {validation_error}"
                cred_updates["google"] = org_data.google_api_key
            elif org_data.google_api_key is not None:
                # Empty string means clear the Google key from the blob.
                logger.info("Clearing Google API key from provider_credentials")
                cred_updates["google"] = None

            if org_data.provider_credentials_input:
                # Merge per-provider inputs (e.g. {"openai": "...", "deepgram": "..."}).
                # A None / empty value clears that provider. Legacy provider keys
                # may remain in stored JSON from older rows.
                #
                # Google is now managed exclusively on the "API Credentials"
                # tab (the Organization Info tab's Google field was removed), so
                # a google key arrives here via ``provider_credentials_input``.
                # Validate it exactly like the legacy ``google_api_key`` field
                # so the credentials-tab path can't bypass the check. A None /
                # empty value clears the google entry (no validation needed).
                google_input = org_data.provider_credentials_input.get("google")
                if google_input is not None and google_input.strip() != "":
                    is_valid, validation_error = await self.validate_google_api_key(
                        google_input
                    )
                    if not is_valid:
                        current_span.set_status(
                            trace.Status(
                                trace.StatusCode.ERROR,
                                f"Invalid Google API key: {validation_error}",
                            )
                        )
                        organization_errors_counter.add(
                            1,
                            {
                                "operation": "update_organization",
                                "error": "invalid_google_api_key",
                            },
                        )
                        return None, f"Invalid Google API key: {validation_error}"
                cred_updates.update(org_data.provider_credentials_input)

            if cred_updates:
                # Fetch the existing blob to merge (preserves other providers).
                existing = (
                    self.supabase.table("organizations")
                    .select("provider_credentials")
                    .eq("id", str(org_id))
                    .limit(1)
                    .execute()
                )
                existing_blob = None
                if existing.data:
                    existing_blob = existing.data[0].get("provider_credentials")
                new_blob = self._merge_provider_credentials(existing_blob, cred_updates)
                update_data["provider_credentials"] = new_blob
                # The secret now lives only in the encrypted blob; clear the
                # legacy plaintext column (retained for rollback safety, dropped
                # in a follow-up migration once the encrypted path is verified).
                update_data["google_api_key"] = None

            if org_data.public_page_enabled is not None:
                update_data["public_page_enabled"] = org_data.public_page_enabled
            if org_data.public_page_passphrase_enabled is not None:
                update_data["public_page_passphrase_enabled"] = (
                    org_data.public_page_passphrase_enabled
                )
                if not org_data.public_page_passphrase_enabled:
                    update_data["public_page_passphrase_hash"] = None

            if org_data.public_page_passphrase is not None:
                from shared.organization.public_page_security import (
                    hash_public_page_passphrase,
                )

                if org_data.public_page_passphrase.strip() == "":
                    update_data["public_page_passphrase_hash"] = None
                else:
                    update_data["public_page_passphrase_hash"] = (
                        hash_public_page_passphrase(org_data.public_page_passphrase)
                    )
                    update_data["public_page_passphrase_enabled"] = True

            if not update_data:
                return await self.get_organization_by_id(org_id)

            response = (
                self.supabase.table("organizations")
                .update(update_data)
                .eq("id", str(org_id))
                .execute()
            )

            if not response.data:
                logger.error(f"Organization not found or update failed: {org_id}")
                current_span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        "Organization not found or update failed",
                    )
                )
                organization_errors_counter.add(
                    1,
                    {
                        "operation": "update_organization",
                        "error": "not_found_or_failed",
                    },
                )
                return None, "Organization not found or update failed"

            org_dict = response.data[0]
            organization = self._organization_from_dict(org_dict)
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return organization, None

        except Exception as e:
            logger.error(
                f"Exception while updating organization {org_id}: {e}", exc_info=True
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "update_organization", "error": "exception"}
            )
            return None, str(e)

    @tracer.start_as_current_span("organization.complete_onboarding")
    async def complete_onboarding(
        self, org_id: UUID
    ) -> tuple[Optional[Organization], Optional[str]]:
        """Mark organization onboarding as completed (idempotent, one-way)."""
        organization_operations_counter.add(1, {"operation": "complete_onboarding"})

        current_span = trace.get_current_span()
        current_span.set_attribute("organization.id", str(org_id))
        try:
            response = (
                self.supabase.table("organizations")
                .update({"onboarding_completed": True})
                .eq("id", str(org_id))
                .execute()
            )

            if not response.data:
                logger.error(
                    f"Organization not found for onboarding completion: {org_id}"
                )
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Organization not found")
                )
                organization_errors_counter.add(
                    1, {"operation": "complete_onboarding", "error": "not_found"}
                )
                return None, "Organization not found"

            org_dict = response.data[0]
            organization = self._organization_from_dict(org_dict)
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return organization, None

        except Exception as e:
            logger.error(
                f"Exception while completing onboarding for organization {org_id}: {e}",
                exc_info=True,
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "complete_onboarding", "error": "exception"}
            )
            return None, str(e)

    @tracer.start_as_current_span("organization.delete_organization")
    async def delete_organization(self, org_id: UUID) -> tuple[bool, Optional[str]]:
        """Delete an organization."""
        organization_operations_counter.add(1, {"operation": "delete_organization"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("organization.id", str(org_id))
        try:
            response = (
                self.supabase.table("organizations")
                .delete()
                .eq("id", str(org_id))
                .execute()
            )

            if not response.data:
                logger.warning(f"Organization not found for deletion: {org_id}")
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Organization not found")
                )
                organization_errors_counter.add(
                    1, {"operation": "delete_organization", "error": "not_found"}
                )
                return False, "Organization not found"

            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return True, None

        except Exception as e:
            logger.error(
                f"Exception while deleting organization {org_id}: {e}", exc_info=True
            )
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "delete_organization", "error": "exception"}
            )
            return False, str(e)

    @tracer.start_as_current_span("organization.create_invitation")
    async def create_invitation(
        self, invite_data: InvitationCreate
    ) -> tuple[Optional[Invitation], Optional[str]]:
        """Create a new invitation for an organization member."""
        organization_operations_counter.add(1, {"operation": "create_invitation"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("invitation.email", invite_data.email)
        current_span.set_attribute("organization.id", str(invite_data.organization_id))

        try:
            # Check if user already exists with this email
            from src.auth.service import auth_service

            existing_user, error = await auth_service.get_user_by_email(
                invite_data.email
            )

            # Handle error from get_user_by_email
            if error:
                logger.error(f"Failed to check if user exists: {error}")
                return None, "Failed to check user existence"

            if existing_user:
                # User exists - check if they're already a member of this organization
                current_span.add_event(
                    "user_exists", {"user_id": str(existing_user.id)}
                )
                logger.info(
                    f"User {invite_data.email} already exists - checking organization membership"
                )

                # Cancel any existing pending invitations for this email and organization
                logger.info(
                    f"Cancelling any existing pending invitations for {invite_data.email} in organization {invite_data.organization_id}"
                )
                cancel_response = (
                    self.supabase.table("invitations")
                    .update({"status": InvitationStatus.CANCELLED.value})
                    .eq("email", invite_data.email)
                    .eq("organization_id", str(invite_data.organization_id))
                    .eq("status", InvitationStatus.PENDING.value)
                    .execute()
                )

                if cancel_response.data:
                    logger.info(
                        f"Cancelled {len(cancel_response.data)} existing pending invitation(s) for {invite_data.email}"
                    )

                # Check if user is already a member of this organization
                user_roles, membership_error = await user_role_service.get_user_roles(
                    existing_user.id, invite_data.organization_id
                )

                if membership_error:
                    logger.error(f"Failed to check user membership: {membership_error}")
                    return None, "Failed to check user membership"

                if user_roles and len(user_roles) > 0:
                    # User is already a member - return error without sending any email
                    logger.info(
                        f"User {invite_data.email} is already a member of organization {invite_data.organization_id}"
                    )

                    current_span.set_attribute("user.id", str(existing_user.id))
                    current_span.set_attribute("invitation.status", "already_member")
                    current_span.set_status(trace.Status(trace.StatusCode.OK))

                    # Return error code instead of string message
                    return None, ErrorCode.USER_ALREADY_MEMBER.value

                # User is not a member - add them to the organization
                current_span.add_event(
                    "adding_existing_user", {"user_id": str(existing_user.id)}
                )
                logger.info(
                    f"User {invite_data.email} is not a member - adding to organization"
                )

                # Get the regular_user role
                member_role, role_error = await role_service.get_role_by_name(
                    "regular_user"
                )
                if role_error or not member_role:
                    logger.error(f"Could not find 'regular_user' role: {role_error}")
                    return None, "Role not found"

                # Add user to organization
                user_role_data = UserRoleCreate(
                    user_id=existing_user.id,
                    role_id=member_role.id,
                    organization_id=invite_data.organization_id,
                )

                user_role, role_assign_error = (
                    await user_role_service.assign_role_to_user(user_role_data)
                )
                if role_assign_error or not user_role:
                    logger.error(f"Failed to assign role to user: {role_assign_error}")
                    return None, "Failed to assign role to user"

                # Create a virtual invitation record for tracking
                token = secrets.token_urlsafe(32)
                expires_at = datetime.now(timezone.utc) + timedelta(days=7)
                invitation_dict = {
                    "id": secrets.token_urlsafe(16),  # Temporary ID
                    "email": invite_data.email,
                    "organization_id": str(invite_data.organization_id),
                    "invited_by": str(invite_data.invited_by),
                    "token": token,
                    "status": InvitationStatus.ACCEPTED.value,
                    "expires_at": expires_at.isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "accepted_at": datetime.now(timezone.utc).isoformat(),
                }

                invitation = Invitation(
                    id=invitation_dict["id"],
                    email=invitation_dict["email"],
                    organization_id=invitation_dict["organization_id"],
                    invited_by=invitation_dict["invited_by"],
                    token=invitation_dict["token"],
                    status=InvitationStatus.ACCEPTED,
                    expires_at=invitation_dict["expires_at"],
                    created_at=invitation_dict["created_at"],
                    accepted_at=invitation_dict["accepted_at"],
                )

                current_span.set_attribute("user.id", str(existing_user.id))
                current_span.set_attribute("invitation.type", "direct_addition")

                # Send notification email
                try:
                    # Get the organization name
                    org, org_error = await self.get_organization_by_id(
                        invite_data.organization_id
                    )
                    if org_error or not org:
                        logger.warning(
                            f"Could not fetch organization name: {org_error}"
                        )

                    # Create notification request
                    notification_request = SendNotificationRequest(
                        event_key="organization.invitation",
                        recipient_email=invite_data.email,
                        recipient_name=f"{existing_user.first_name} {existing_user.last_name}",
                        organization_id=invite_data.organization_id,
                        user_id=existing_user.id,
                        template_variables={
                            "recipient_name": f"{existing_user.first_name} {existing_user.last_name}",
                            "inviter_name": "An administrator",
                            "organization_name": (
                                org.name if org else "the organization"
                            ),
                            "role_name": "Member",
                            "invitation_url": f"{self._get_frontend_url()}/auth/signin",
                            "expiry_days": "7",
                            "app_name": settings.app_name,
                        },
                    )

                    # Send the notification
                    await notification_service.send_notification(notification_request)

                    logger.info(
                        f"Member added notification sent to {invite_data.email}"
                    )
                except Exception as email_error:
                    logger.error(
                        f"Failed to send notification email: {email_error}",
                        exc_info=True,
                    )
                    # Don't fail the operation if email sending fails
                    current_span.add_event(
                        "email_send_failed", {"error": str(email_error)}
                    )

                current_span.set_status(trace.Status(trace.StatusCode.OK))
                return invitation, None
            else:
                # User doesn't exist - create invitation token and send signup email
                current_span.add_event(
                    "user_not_exists", {"action": "create_invitation"}
                )
                logger.info(
                    f"User {invite_data.email} doesn't exist - creating invitation"
                )

                # Cancel any existing pending invitations for this email and organization
                logger.info(
                    f"Cancelling any existing pending invitations for {invite_data.email} in organization {invite_data.organization_id}"
                )
                cancel_response = (
                    self.supabase.table("invitations")
                    .update({"status": InvitationStatus.CANCELLED.value})
                    .eq("email", invite_data.email)
                    .eq("organization_id", str(invite_data.organization_id))
                    .eq("status", InvitationStatus.PENDING.value)
                    .execute()
                )

                if cancel_response.data:
                    logger.info(
                        f"Cancelled {len(cancel_response.data)} existing pending invitation(s) for {invite_data.email}"
                    )

                # Generate a unique invitation token
                token = secrets.token_urlsafe(32)
                expires_at = datetime.now(timezone.utc) + timedelta(
                    days=7
                )  # Invitation expires in 7 days

                # Insert the invitation into the database
                response = (
                    self.supabase.table("invitations")
                    .insert(
                        {
                            "email": invite_data.email,
                            "organization_id": str(invite_data.organization_id),
                            "invited_by": str(invite_data.invited_by),
                            "token": token,
                            "status": InvitationStatus.PENDING.value,
                            "expires_at": expires_at.isoformat(),
                        }
                    )
                    .execute()
                )

                if not response.data:
                    logger.error(f"Failed to create invitation for {invite_data.email}")
                    current_span.set_status(
                        trace.Status(
                            trace.StatusCode.ERROR, "Failed to create invitation"
                        )
                    )
                    organization_errors_counter.add(
                        1,
                        {"operation": "create_invitation", "error": "no_data_returned"},
                    )
                    return None, "Failed to create invitation"

                invitation_dict = response.data[0]
                invitation = Invitation(
                    id=invitation_dict["id"],
                    email=invitation_dict["email"],
                    organization_id=invitation_dict["organization_id"],
                    invited_by=invitation_dict["invited_by"],
                    token=invitation_dict["token"],
                    status=InvitationStatus(invitation_dict["status"]),
                    expires_at=invitation_dict["expires_at"],
                    created_at=invitation_dict["created_at"],
                    accepted_at=invitation_dict.get("accepted_at"),
                )

                current_span.set_attribute("invitation.id", str(invitation.id))
                current_span.set_attribute("invitation.type", "signup_invitation")

                # Send the invitation email
                try:
                    # Get the organization name
                    org, org_error = await self.get_organization_by_id(
                        invite_data.organization_id
                    )
                    if org_error or not org:
                        logger.warning(
                            f"Could not fetch organization name for invitation: {org_error}"
                        )

                    # Create notification request
                    notification_request = SendNotificationRequest(
                        event_key="organization.invitation",
                        recipient_email=invite_data.email,
                        organization_id=invite_data.organization_id,
                        template_variables={
                            "recipient_name": "there",  # Generic greeting since we don't know their name yet
                            "inviter_name": "An administrator",
                            "organization_name": (
                                org.name if org else "the organization"
                            ),
                            "role_name": "Member",
                            "invitation_url": f"{self._get_frontend_url()}/auth/signup?token={token}",
                            "expiry_days": "7",
                            "app_name": settings.app_name,
                        },
                    )

                    # Send the notification
                    await notification_service.send_notification(notification_request)

                    logger.info(f"Invitation email sent to {invite_data.email}")
                except Exception as email_error:
                    logger.error(
                        f"Failed to send invitation email: {email_error}", exc_info=True
                    )
                    # Don't fail the invitation creation if email sending fails
                    current_span.add_event(
                        "email_send_failed", {"error": str(email_error)}
                    )

                current_span.set_status(trace.Status(trace.StatusCode.OK))
                return invitation, None

        except Exception as e:
            logger.error(f"Exception while creating invitation: {e}", exc_info=True)
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            organization_errors_counter.add(
                1, {"operation": "create_invitation", "error": "exception"}
            )
            return None, str(e)

    @tracer.start_as_current_span("organization.validate_google_api_key")
    async def validate_google_api_key(self, api_key: str) -> tuple[bool, Optional[str]]:
        """Validate a Google API key by making a test request.

        Args:
            api_key: The Google API key to validate

        Returns:
            tuple of (is_valid, error_message)
        """
        import httpx

        organization_operations_counter.add(1, {"operation": "validate_google_api_key"})

        current_span = trace.get_current_span()
        current_span.set_attribute("api_key_present", bool(api_key))

        try:
            # Test the API key by calling Google's models endpoint
            # This is a lightweight call that validates the key
            url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    current_span.set_status(trace.Status(trace.StatusCode.OK))
                    logger.info("Google API key validated successfully")
                    return True, None
                elif response.status_code == 401:
                    error_msg = "Invalid API key - authentication failed"
                    current_span.set_status(
                        trace.Status(trace.StatusCode.ERROR, error_msg)
                    )
                    logger.warning(f"Google API key validation failed: {error_msg}")
                    return False, "Invalid API key"
                elif response.status_code == 403:
                    error_msg = "API key lacks required permissions"
                    current_span.set_status(
                        trace.Status(trace.StatusCode.ERROR, error_msg)
                    )
                    logger.warning(f"Google API key validation failed: {error_msg}")
                    return False, "API key lacks required permissions"
                else:
                    error_msg = f"API validation returned status {response.status_code}"
                    current_span.set_status(
                        trace.Status(trace.StatusCode.ERROR, error_msg)
                    )
                    logger.warning(
                        f"Google API key validation unexpected status: {response.status_code}"
                    )
                    return (
                        False,
                        f"Validation failed with status {response.status_code}",
                    )

        except httpx.TimeoutException:
            error_msg = "Validation request timed out"
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            logger.warning(f"Google API key validation timed out")
            return False, "Validation timed out - please try again"
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            logger.error(f"Google API key validation exception: {e}", exc_info=True)
            return False, "Unable to validate API key"

    def _get_frontend_url(self) -> str:
        """Get the frontend URL from environment variables."""
        from shared.config import settings

        return settings.app_base_url or "http://localhost:3000"

    @tracer.start_as_current_span("organization.process_invitation")
    async def process_invitation(
        self, token: str, user_id: UUID, expected_email: str
    ) -> tuple[Optional[Invitation], Optional[str]]:
        """Atomically claim an email-bound invitation for a user.

        The database function locks the invitation row, validates its pending
        state and expiry, inserts an idempotent membership, and marks the
        invitation accepted in one transaction. Repeating the request for the
        same user is safe; a different email or user cannot reuse the token.
        """
        organization_operations_counter.add(1, {"operation": "process_invitation"})

        current_span = trace.get_current_span()
        current_span.set_attribute("invitation.token", token[:8] + "...")
        current_span.set_attribute("user.id", str(user_id))

        try:
            response = self.supabase.rpc(
                "claim_invitation",
                {
                    "p_token": token,
                    "p_user_id": str(user_id),
                    "p_email": expected_email.strip().lower(),
                },
            ).execute()
            payload = getattr(response, "data", None)
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            if not isinstance(payload, dict) or not payload.get("success"):
                error_code = (
                    payload.get("error")
                    if isinstance(payload, dict)
                    else "invitation_claim_failed"
                )
                error_messages = {
                    "invalid_request": "Invalid invitation request",
                    "invitation_not_found": "Invitation not found",
                    "invitation_email_mismatch": (
                        "This invitation belongs to a different email address"
                    ),
                    "invitation_already_accepted": "Invitation already accepted",
                    "invitation_not_pending": "Invitation is no longer available",
                    "invitation_expired": "Invitation has expired",
                    "role_not_found": "Role not found",
                }
                message = error_messages.get(
                    str(error_code), "Unable to process invitation"
                )
                current_span.set_status(trace.Status(trace.StatusCode.ERROR, message))
                return None, message

            invitation_payload = payload.get("invitation")
            if not isinstance(invitation_payload, dict):
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Invitation payload missing")
                )
                return None, "Unable to process invitation"

            invitation = Invitation(**invitation_payload)
            current_span.set_attribute(
                "organization.id", str(invitation.organization_id)
            )
            current_span.set_attribute(
                "organization.name", invitation.organization_name or ""
            )
            current_span.set_status(trace.Status(trace.StatusCode.OK))

            logger.info(
                "User %s successfully joined organization %s via invitation",
                user_id,
                invitation.organization_id,
            )
            return invitation, None

        except Exception:
            logger.error("Exception while processing invitation", exc_info=True)
            current_span.set_status(
                trace.Status(trace.StatusCode.ERROR, "invitation_claim_failed")
            )
            organization_errors_counter.add(
                1, {"operation": "process_invitation", "error": "exception"}
            )
            return None, "Unable to process invitation"


# Global organization service instance
organization_service = OrganizationService()
