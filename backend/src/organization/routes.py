"""
Organization API routes for the multi-tenant SaaS platform.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from opentelemetry import trace
from src.auth.dependencies import (
    assert_has_permission,
    assert_has_role,
    assert_platform_role,
)
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.billing.service import billing_service
from src.billing.versioned_subscription_service import versioned_subscription_service
from src.organization.invitation_models import (
    Invitation,
    InvitationCreate,
    InvitationRole,
)
from src.organization.member_models import OrganizationMember
from src.organization.models import (
    Organization,
    OrganizationCreate,
    OrganizationUpdate,
    PlatformOrganizationCreate,
    WebsiteBusinessContextRequest,
    WebsiteBusinessContextResponse,
)
from src.organization.service import organization_service
from src.organization.website_context_service import (
    WebsiteContextGenerationError,
    WebsiteContextNoPages,
    WebsiteContextNotConfigured,
    WebsiteContextRateLimited,
    normalize_website_url,
    website_business_context_service,
)
from src.rbac.roles.service import role_service
from src.rbac.user_roles.models import UserRoleCreate
from src.rbac.user_roles.service import user_role_service
from src.security.rate_limiter import limiter

from shared.common.errors import ErrorCode

# Get tracer for this module
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

# Create organization router
organization_router = APIRouter(prefix="/api/v1/organizations", tags=["Organizations"])


@organization_router.post(
    "/", response_model=Organization, status_code=status.HTTP_201_CREATED
)
@tracer.start_as_current_span("organization.routes.create_organization")
async def create_organization(
    org_data: PlatformOrganizationCreate,
    user_data: tuple[UUID, "UserProfile"] = Depends(get_authenticated_user),
):
    """Create a new organization (requires platform_admin role)."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.name", org_data.name)

    # Check if user has platform_admin role
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform administrators can create organizations",
    )

    organization, error = await organization_service.create_organization(org_data)
    if error:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    selected_plan_version_id = getattr(org_data, "plan_version_id", None)
    try:
        if selected_plan_version_id:
            await versioned_subscription_service.assign_plan_for_platform_admin(
                organization.id, selected_plan_version_id
            )
        else:
            # Preserve the existing API behavior for older platform-admin
            # clients that do not send a plan yet.
            await versioned_subscription_service.activate_default_free_plan(
                organization.id
            )
    except Exception as plan_error:
        logger.error(
            "Failed to assign a plan for newly created organization %s: %s",
            organization.id,
            plan_error,
            exc_info=True,
        )
        deleted, delete_error = await organization_service.delete_organization(
            organization.id
        )
        if not deleted:
            logger.error(
                "Failed to clean up organization %s after plan activation failure: %s",
                organization.id,
                delete_error,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to provision the organization with its selected plan",
        ) from plan_error

    current_span.set_attribute("organization.id", str(organization.id))
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return organization


@organization_router.post(
    "/self", response_model=Organization, status_code=status.HTTP_201_CREATED
)
@tracer.start_as_current_span("organization.routes.create_self_organization")
async def create_self_organization(
    org_data: OrganizationCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a new organization for the current user and assign them as org_admin."""
    current_user_id, _ = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.name", org_data.name)

    try:
        # Create the organization
        organization, error = await organization_service.create_organization(org_data)
        if error:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

        # Get the org_admin role
        org_admin_role, role_error = await role_service.get_role_by_name("org_admin")
        if role_error or not org_admin_role:
            # If org_admin role doesn't exist, we should still return the organization
            # but log the issue
            current_span.add_event(
                "org_admin_role_not_found", {"error": str(role_error)}
            )
        else:
            # Assign org_admin role to user for their organization
            user_role_data = UserRoleCreate(
                user_id=current_user_id,
                role_id=org_admin_role.id,
                organization_id=organization.id,
            )

            user_role, role_assign_error = await user_role_service.assign_role_to_user(
                user_role_data
            )
            if role_assign_error or not user_role:
                # Log the error but don't fail the organization creation
                current_span.add_event(
                    "role_assignment_failed", {"error": str(role_assign_error)}
                )
            else:
                current_span.add_event(
                    "role_assigned",
                    {
                        "role_id": str(org_admin_role.id),
                        "organization_id": str(organization.id),
                    },
                )

        current_span.set_attribute("organization.id", str(organization.id))
        current_span.set_status(trace.Status(trace.StatusCode.OK))
        return organization

    except Exception as e:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}",
        )


@organization_router.get("/{org_id}/members", response_model=list[OrganizationMember])
@tracer.start_as_current_span("organization.routes.get_organization_members")
async def get_organization_members(
    org_id: UUID, user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user)
):
    """Get all members of an organization."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    # Check if user has permission to view organization members.
    # The 3-way OR is: platform_admin (org-agnostic) OR org_admin on
    # the target org OR `organization:read` permission on the target
    # org. The `_check_access` short-circuits on platform_admin, so
    # we can compose the two remaining checks in a try/except chain.
    try:
        assert_has_role(
            user_profile,
            "org_admin",
            org_id=org_id,
            error_message="Insufficient permissions to view organization members",
        )
    except HTTPException:
        assert_has_permission(
            user_profile,
            "organization",
            "read",
            org_id=org_id,
            error_message="Insufficient permissions to view organization members",
        )

    members, error = await user_role_service.get_users_by_organization(org_id)
    if error:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )

    current_span.set_attribute("members.count", len(members))
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return members


@organization_router.post(
    "/{org_id}/invite", response_model=Invitation, status_code=status.HTTP_201_CREATED
)
@tracer.start_as_current_span("organization.routes.invite_member")
async def invite_member(
    org_id: UUID,
    request: Request,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Invite a new member to an organization."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    # Check if user has permission to invite members. The 3-way OR
    # is: platform_admin (org-agnostic) OR org_admin on the target
    # org OR `member:create` permission on the target org. The
    # `_check_access` short-circuit on platform_admin keeps the
    # call-site shape identical to a single permission check.
    try:
        assert_has_role(
            user_profile,
            "org_admin",
            org_id=org_id,
            error_message="Insufficient permissions to invite members",
        )
    except HTTPException:
        try:
            assert_has_permission(
                user_profile,
                "member",
                "create",
                org_id=org_id,
                error_message="Insufficient permissions to invite members",
            )
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": ErrorCode.INSUFFICIENT_PERMISSIONS.value,
                    "message": "Insufficient permissions to invite members",
                },
            )

    # Parse request body manually to preserve the existing route contract while
    # accepting an explicit organization-scoped invitation role.
    body = await request.json()
    email = body.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Email is required",
            },
        )

    try:
        invitation_role = InvitationRole(
            body.get("role", InvitationRole.REGULAR_USER.value)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": ErrorCode.VALIDATION_ERROR.value,
                "message": "Role must be regular_user or org_admin",
            },
        ) from exc

    if invitation_role == InvitationRole.ORG_ADMIN and not (
        user_profile.has_role("platform_admin")
        or user_profile.has_role("org_admin", str(org_id))
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": ErrorCode.INSUFFICIENT_PERMISSIONS.value,
                "message": "Only organization administrators can invite organization administrators",
            },
        )

    # Create InvitationCreate with the current user as invited_by
    invite_data = InvitationCreate(
        email=email,
        organization_id=org_id,
        invited_by=current_user_id,
        role=invitation_role,
    )

    # Import here to avoid circular imports
    from src.organization.service import organization_service as org_service

    invitation, error = await org_service.create_invitation(invite_data)
    if error:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))

        # Handle specific error codes with appropriate HTTP status codes
        if error == ErrorCode.USER_ALREADY_MEMBER.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error_code": ErrorCode.USER_ALREADY_MEMBER.value,
                    "message": "User is already a member of this organization",
                },
            )
        else:
            # Generic error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": ErrorCode.VALIDATION_ERROR.value,
                    "message": error,
                },
            )

    current_span.set_attribute("invitation.id", str(invitation.id))
    current_span.set_attribute("invitation.email", email)
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return invitation


@organization_router.get("/{org_id}", response_model=Organization)
@tracer.start_as_current_span("organization.routes.get_organization")
async def get_organization(
    org_id: UUID, user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user)
):
    """Get an organization by ID."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    # Check if user has permission to view organizations. The 3-way
    # OR is: platform_admin (org-agnostic) OR org_admin on the target
    # org OR `organization:read` permission on the target org.
    try:
        assert_has_role(
            user_profile,
            "org_admin",
            org_id=org_id,
            error_message="Insufficient permissions to view organizations",
        )
    except HTTPException:
        assert_has_permission(
            user_profile,
            "organization",
            "read",
            org_id=org_id,
            error_message="Insufficient permissions to view organizations",
        )

    organization, error = await organization_service.get_organization_by_id(org_id)
    if error:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)

    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return organization


@organization_router.get("/", response_model=list[Organization])
@tracer.start_as_current_span("organization.routes.get_all_organizations")
async def get_all_organizations(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user)
):
    """Get all organizations the user has access to."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))

    if user_profile.has_role("platform_admin"):
        # Platform admin can see all organizations
        organizations, error = await organization_service.get_all_organizations()
        if error:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
            )
        current_span.set_attribute("organizations.count", len(organizations))
        current_span.set_status(trace.Status(trace.StatusCode.OK))
        return organizations
    else:
        # Regular users and org admins can only see organizations they belong to
        organizations, error = await user_role_service.get_organizations_for_user(
            current_user_id
        )
        if error:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
            )
        current_span.set_attribute("organizations.count", len(organizations))
        current_span.set_status(trace.Status(trace.StatusCode.OK))
        return organizations


@organization_router.patch("/{org_id}", response_model=Organization)
@tracer.start_as_current_span("organization.routes.update_organization")
async def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update an organization (requires platform_admin or org_admin role)."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    # Check if user has platform_admin or org_admin role for this organization
    assert_has_role(
        user_profile,
        "org_admin",
        org_id=org_id,
        error_message="Only platform administrators or organization administrators can update organizations",
    )

    organization, error = await organization_service.update_organization(
        org_id, org_data
    )
    if error:
        if "not found" in error.lower():
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return organization


@organization_router.post(
    "/{org_id}/business-context-from-website",
    response_model=WebsiteBusinessContextResponse,
)
@limiter.limit("3/hour")
@tracer.start_as_current_span("organization.routes.generate_website_business_context")
async def generate_website_business_context(
    org_id: UUID,
    request: Request,
    body: WebsiteBusinessContextRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Generate an unsaved business-context draft from a public website.

    Only organization administrators may initiate the provider calls. The
    endpoint returns a draft and never modifies the organization record.
    """
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    assert_has_role(
        user_profile,
        "org_admin",
        org_id=org_id,
        error_message=(
            "Only platform administrators or organization administrators can "
            "generate business context"
        ),
    )

    try:
        website = normalize_website_url(body.website)
        result = await website_business_context_service.generate(website)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except WebsiteContextNotConfigured as exc:
        logger.warning("Website context generation is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Website context generation is not available right now.",
        ) from exc
    except WebsiteContextRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Website analysis is temporarily busy. Please try again shortly.",
        ) from exc
    except WebsiteContextNoPages as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="We could not find readable public pages on that website.",
        ) from exc
    except WebsiteContextGenerationError as exc:
        logger.warning("Website context generation failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="We could not prepare a draft from that website. Please try again.",
        ) from exc

    current_span.set_attribute(
        "website_context.pages_analyzed", result["pages_analyzed"]
    )
    current_span.set_attribute(
        "website_context.page_limit_reached", result["page_limit_reached"]
    )
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return result


@organization_router.post("/{org_id}/complete-onboarding", response_model=Organization)
@tracer.start_as_current_span("organization.routes.complete_onboarding")
async def complete_onboarding(
    org_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Mark onboarding as completed for an organization (org_admin only, one-way, idempotent)."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    assert_has_role(
        user_profile,
        "org_admin",
        org_id=org_id,
        error_message="Only organization administrators can complete onboarding",
    )

    subscription = await billing_service.get_organization_subscription(org_id)
    if not subscription or subscription.status not in {"active", "trial"}:
        current_span.set_status(
            trace.Status(trace.StatusCode.ERROR, "Active subscription required")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active or trial subscription is required before completing onboarding",
        )

    organization, error = await organization_service.complete_onboarding(org_id)
    if error:
        if "not found" in error.lower():
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    # Note: do not seed org skills here. Platform skills are seeded at app
    # startup (`seed_platform_skills`); orgs fork what they need. The previous
    # `seed_built_in_skills` call did not exist and the except block referenced
    # an undefined `logger`, which turned complete-onboarding into HTTP 500.

    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return organization


@organization_router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
@tracer.start_as_current_span("organization.routes.delete_organization")
async def delete_organization(
    org_id: UUID, user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user)
):
    """Delete an organization (requires platform_admin role)."""
    current_user_id, user_profile = user_data
    current_span = trace.get_current_span()
    current_span.set_attribute("user.id", str(current_user_id))
    current_span.set_attribute("organization.id", str(org_id))

    # Check if user has platform_admin role
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Only platform administrators can delete organizations",
    )

    success, error = await organization_service.delete_organization(org_id)
    if error:
        if "not found" in error.lower():
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        else:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
            )

    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return None
