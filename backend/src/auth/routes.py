"""
Authentication API routes.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from opentelemetry import trace
from pydantic import BaseModel, Field
from src.auth.middleware import get_authenticated_user
from src.security.rate_limiter import limiter
from src.auth.models import (
    AuthResponse,
    ErrorResponse,
    SignInRequest,
    SignUpRequest,
    UserProfile,
)
from src.auth.service import auth_service
from src.organization.service import organization_service
from src.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Create auth router
auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class ProcessInvitationRequest(BaseModel):
    """Request model for processing an invitation."""

    token: str = Field(..., description="Invitation token")
    user_id: UUID = Field(..., description="User ID to add to organization")


@auth_router.post(
    "/signup",
    response_model=AuthResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        409: {"model": ErrorResponse, "description": "User already exists"},
        429: {"description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("5/minute")
@tracer.start_as_current_span("auth.routes.sign_up")
async def sign_up(request: Request, body: SignUpRequest) -> AuthResponse:
    """
    Register a new user account.

    - **email**: Valid email address
    - **password**: Strong password (8+ chars, uppercase, lowercase, number, special char)
    - **password_confirm**: Must match password
    - **first_name**: User's first name
    - **last_name**: User's last name
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("user.email", body.email)

    auth_response, error = await auth_service.sign_up(body)

    if error:
        detail = error.detail if isinstance(error.detail, str) else str(error.detail)
        if error.status_code == status.HTTP_409_CONFLICT or "already registered" in detail.lower():
            current_span.set_attribute("error.type", "user_already_exists")
        elif error.status_code >= 500:
            current_span.set_attribute("error.type", "internal_error")
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, detail))
        raise error

    current_span.set_attribute("user.id", str(auth_response.user.id))
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return auth_response


@auth_router.post(
    "/signin",
    response_model=AuthResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid credentials"},
        429: {"description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("10/minute")
@tracer.start_as_current_span("auth.routes.sign_in")
async def sign_in(request: Request, body: SignInRequest) -> AuthResponse:
    """
    Authenticate user with email and password.

    - **email**: Registered email address
    - **password**: User password
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("user.email", body.email)

    auth_response, error = await auth_service.sign_in(body)

    if error:
        detail = error.detail if isinstance(error.detail, str) else str(error.detail)
        if error.status_code >= 500:
            current_span.set_attribute("error.type", "internal_error")
        else:
            current_span.set_attribute("error.type", "invalid_credentials")
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, detail))
        raise error

    current_span.set_attribute("user.id", str(auth_response.user.id))
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return auth_response


@auth_router.post(
    "/signout",
    responses={
        200: {"description": "Successfully signed out"},
        400: {"model": ErrorResponse, "description": "Sign out failed"},
    },
)
@tracer.start_as_current_span("auth.routes.sign_out")
async def sign_out(authorization: str = Header(None)) -> JSONResponse:
    """
    Sign out user and invalidate session.

    Requires Authorization header with Bearer token.
    """
    current_span = trace.get_current_span()
    if not authorization or not authorization.startswith("Bearer "):
        current_span.set_status(
            trace.Status(
                trace.StatusCode.ERROR, "Missing or invalid authorization header"
            )
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": "Missing or invalid authorization header",
            },
        )

    access_token = authorization.replace("Bearer ", "")
    current_span.set_attribute("token.provided", True)

    success, error = await auth_service.sign_out(access_token)

    if error:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, error.message))
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=error.model_dump()
        )

    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"message": "Successfully signed out"}
    )


@auth_router.post(
    "/refresh",
    response_model=AuthResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid refresh token"},
        429: {"description": "Too many requests"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("30/minute")
@tracer.start_as_current_span("auth.routes.refresh_token")
async def refresh_token(request: Request, body: dict[str, str]) -> AuthResponse:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    current_span = trace.get_current_span()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        current_span.set_status(
            trace.Status(trace.StatusCode.ERROR, "Refresh token is required")
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "missing_token", "message": "Refresh token is required"},
        )

    current_span.set_attribute("token.provided", True)

    auth_response, error = await auth_service.refresh_token(refresh_token)

    if error:
        detail = error.detail if isinstance(error.detail, str) else str(error.detail)
        if error.status_code >= 500:
            current_span.set_attribute("error.type", "internal_error")
        else:
            current_span.set_attribute("error.type", "invalid_token")
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, detail))
        raise error

    current_span.set_attribute("user.id", str(auth_response.user.id))
    current_span.set_status(trace.Status(trace.StatusCode.OK))
    return auth_response


@auth_router.get(
    "/me",
    response_model=UserProfile,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired token"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@tracer.start_as_current_span("auth.routes.get_current_user")
async def get_current_user(
    org_id: Optional[UUID] = Query(
        None,
        description=(
            "Organization the embedded permissions object should be scoped to. "
            "If omitted, the resolver returns an empty permissions object."
        ),
    ),
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> UserProfile:
    """
    Get current user profile, with resolved permissions for the current org.

    The `permissions` and `current_organization_id` fields are computed
    server-side on every call from the user's roles and the requested
    `org_id`. The contract is documented in
    `docs/tw-drafts/navigation-redesign.md` Section 5.

    Requires Authorization header with Bearer token.
    """
    from src.auth.permissions_service import resolve_permissions

    current_span = trace.get_current_span()
    user_id, user_profile = user_auth

    current_span.set_attribute("user.id", str(user_id))
    if org_id is not None:
        current_span.set_attribute("org.id", str(org_id))

    # Resolve the permissions object for the requested org context.
    resolved = resolve_permissions(user_profile, current_organization_id=org_id)
    user_profile.permissions = resolved.permissions
    user_profile.current_organization_id = resolved.current_organization_id

    current_span.set_attribute(
        "permissions.count", sum(len(v) for v in resolved.permissions.values())
    )
    current_span.set_status(trace.Status(trace.StatusCode.OK))

    return user_profile


@auth_router.post(
    "/process-invitation",
    responses={
        200: {"description": "Invitation processed successfully"},
        400: {
            "model": ErrorResponse,
            "description": "Invalid invitation token or user",
        },
        403: {
            "model": ErrorResponse,
            "description": "user_id does not match the authenticated caller",
        },
        404: {"model": ErrorResponse, "description": "Invitation not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@tracer.start_as_current_span("auth.routes.process_invitation")
async def process_invitation(
    request: ProcessInvitationRequest,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> JSONResponse:
    """
    Process an invitation to add a user to an organization.

    This endpoint is called after user signup when they have an invitation token.
    It links the user to the organization specified in the invitation.

    - **token**: Invitation token from email
    - **user_id**: User ID to add to organization. Must match the
      authenticated caller — the invitation can only be processed by
      the user whose account the invitation was issued for. Substituting
      another user's UUID returns 403.
    """
    current_user_id, user_profile = user_data

    # CRIT: the body's user_id MUST match the authenticated caller.
    # Without this check, an attacker who intercepts an invitation
    # token could substitute any other user's UUID and have the
    # new member be linked to the wrong account.
    if request.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id does not match the authenticated caller",
        )

    current_span = trace.get_current_span()
    current_span.set_attribute("invitation.token", request.token[:8] + "...")
    current_span.set_attribute("user.id", str(request.user_id))

    try:
        # Process the invitation using the organization service
        invitation, error = await organization_service.process_invitation(
            request.token, request.user_id
        )

        if error:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, error))
            status_code = status.HTTP_400_BAD_REQUEST
            if "not found" in error.lower():
                status_code = status.HTTP_404_NOT_FOUND
            return JSONResponse(
                status_code=status_code,
                content={"error": "invitation_error", "message": error},
            )

        current_span.set_attribute("organization.id", str(invitation.organization_id))
        current_span.set_status(trace.Status(trace.StatusCode.OK))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Successfully added to organization",
                "organization_id": str(invitation.organization_id),
                "invitation_id": str(invitation.id),
            },
        )

    except Exception as e:
        current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        logging.error(f"Error processing invitation: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_error",
                "message": "Failed to process invitation",
            },
        )
