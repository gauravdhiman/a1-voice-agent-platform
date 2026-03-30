"""
Authentication middleware for extracting user information from JWT tokens.
"""

import logging
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Header, HTTPException, status
from src.auth.models import UserProfile
from src.auth.service import auth_service
from src.rbac.user_roles.service import user_role_service

from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)


def _decode_jwt_verified(token: str) -> dict:
    """
    Decode and verify a JWT token signature.

    Uses settings.jwt_secret_key for HS256 verification when configured.
    Raises HTTPException 500 (misconfiguration) or 401 (bad token).
    """
    if not settings.jwt_secret_key:
        logger.error(
            "_decode_jwt_verified: JWT_SECRET_KEY is not set — authentication service unavailable"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable",
        )
    try:
        return jwt.decode(
            token,
            key=settings.jwt_secret_key,
            algorithms=["HS256"],  # hardcoded — never runtime-configurable
            audience="authenticated",  # Supabase JWTs always have aud: "authenticated"
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience",
        )
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )


async def check_billing_permissions(
    organization_id: UUID, authorization: str = Header(None)
) -> tuple[UUID, UserProfile]:
    """
    Check billing permissions for a specific organization.
    This is used as a FastAPI dependency for billing operations.

    Args:
        organization_id: The organization ID to check permissions for
        authorization: The Authorization header value (Bearer token)

    Returns:
        tuple[UUID, UserProfile]: (user_id, user_profile)

    Raises:
        HTTPException: If authentication or authorization fails
    """
    # First, authenticate the user
    user_id, user_profile = await get_authenticated_user(authorization)

    try:
        # Check if user has platform admin role (bypasses organization checks)
        if user_profile.has_role("platform_admin"):
            # Platform admins have access to everything
            return user_id, user_profile

        # Also check if user is org_admin for this organization
        if user_profile.has_role("org_admin", str(organization_id)):
            return user_id, user_profile

        # Check if user has billing permissions for this organization
        if user_profile.has_permission("billing:subscribe", str(organization_id)):
            return user_id, user_profile

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for billing operations in this organization",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("check_billing_permissions: unexpected error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authorization error",
        )


async def get_current_user_id(authorization: str = Header(None)) -> UUID:
    """
    Extract the current user ID from the authorization header.

    Args:
        authorization: The Authorization header value (Bearer token)

    Returns:
        UUID: The current user's ID

    Raises:
        HTTPException: If the token is invalid or missing
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    # E2E test mock bypass — test environment only
    if settings.environment == "test" and token == "mock-jwt-token":
        return UUID("00000000-0000-0000-0000-000000000000")

    try:
        payload = _decode_jwt_verified(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: user ID not found",
            )

        return UUID(user_id)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_current_user_id: unexpected error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


async def get_authenticated_user(
    authorization: str = Header(None),
) -> tuple[UUID, UserProfile]:
    """
    Comprehensive authentication middleware that validates:
    1. JWT token authenticity
    2. User existence and active status
    3. Returns both user ID and profile

    This is the primary authentication method that should be used
    instead of get_current_user_id for security-critical operations.

    Args:
        authorization: The Authorization header value (Bearer token)

    Returns:
        tuple[UUID, UserProfile]: (user_id, user_profile)

    Raises:
        HTTPException: If authentication fails at any step
    """
    # Step 1: Extract and validate JWT token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    token = authorization.replace("Bearer ", "")

    # E2E test mock bypass — test environment only
    if settings.environment == "test" and token == "mock-jwt-token":
        test_uuid = UUID("00000000-0000-0000-0000-000000000000")
        mock_user = UserProfile(
            id=test_uuid,
            email="test@gmail.com",
            first_name="Test",
            last_name="User",
            created_at="2026-01-21T00:00:00Z",
            updated_at="2026-01-21T00:00:00Z",
            roles=[]
        )
        return test_uuid, mock_user

    try:
        # Step 1: Verify JWT signature before trusting any claims
        _decode_jwt_verified(token)

        # Step 2: Validate token against Supabase and get authoritative user profile
        user_profile, error = await auth_service.get_user(token)

        if error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Use the user ID from the Supabase-validated profile (authoritative source)
        return user_profile.id, user_profile

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID in token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_authenticated_user: unexpected error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


def verify_supabase_token(token: str) -> tuple[Optional[dict], Optional[str]]:
    """
    Verify a Supabase JWT token and return the payload.

    Args:
        token: The JWT token to verify

    Returns:
        tuple[Optional[dict], Optional[str]]: (payload, error_message)
    """
    try:
        if not supabase_config.is_configured():
            return None, "Supabase not configured"

        payload = _decode_jwt_verified(token)
        return payload, None

    except HTTPException as e:
        return None, e.detail
    except Exception as e:
        return None, str(e)


async def check_organization_access(
    organization_id: UUID, authorization: str = Header(None)
) -> tuple[UUID, UserProfile]:
    """
    Check if user has access to an organization (platform admin or org member).
    This is for organization data access without requiring billing permissions.

    Args:
        organization_id: The organization ID to check access for
        authorization: The Authorization header value (Bearer token)

    Returns:
        tuple[UUID, UserProfile]: (user_id, user_profile)

    Raises:
        HTTPException: If authentication or authorization fails
    """
    # First, authenticate the user
    user_id, user_profile = await get_authenticated_user(authorization)

    try:
        # Check if user has platform admin role (bypasses organization checks)
        if user_profile.has_role("platform_admin"):
            # Platform admins have access to everything
            return user_id, user_profile

        # Check if user is org_admin for this organization
        if user_profile.has_role("org_admin", str(organization_id)):
            return user_id, user_profile

        # Check if user has any role in this organization
        has_org_access = any(
            str(user_role.organization_id) == str(organization_id)
            for user_role in user_profile.roles
        )

        if not has_org_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have access to this organization",
            )

        return user_id, user_profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error("check_organization_access: unexpected error", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authorization error",
        )
