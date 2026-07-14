"""
Authentication middleware for extracting user information from JWT tokens.
"""

import base64
import json
import logging
import time
from typing import Optional
from uuid import UUID

import httpx
import jwt
from fastapi import Header, HTTPException, status
from src.auth.models import UserProfile
from src.auth.service import auth_service
from src.rbac.user_roles.service import user_role_service

from shared.config import settings, supabase_config

logger = logging.getLogger(__name__)

# Module-level JWKS cache to avoid fetching on every request
_jwks_cache: dict = {"keys": {}, "fetched_at": 0.0}
_JWKS_CACHE_TTL = 300  # 5 minutes


def _get_jwks_key(kid: str) -> Optional[dict]:
    """Return the JWKS key dict for a given kid, refreshing cache as needed."""
    global _jwks_cache
    now = time.monotonic()
    if now - _jwks_cache["fetched_at"] > _JWKS_CACHE_TTL or kid not in _jwks_cache["keys"]:
        supabase_url = settings.supabase_url or ""
        # Inside Docker the URL uses host.docker.internal; try both host variants
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        fallback_url = jwks_url.replace("host.docker.internal", "127.0.0.1")
        for url in [jwks_url, fallback_url]:
            try:
                resp = httpx.get(url, timeout=5)
                resp.raise_for_status()
                keys_list = resp.json().get("keys", [])
                _jwks_cache["keys"] = {k["kid"]: k for k in keys_list}
                _jwks_cache["fetched_at"] = now
                break
            except Exception as exc:
                logger.debug("_get_jwks_key: failed to fetch JWKS from %s: %s", url, exc)
    return _jwks_cache["keys"].get(kid)


def _peek_jwt_header(token: str) -> dict:
    """Decode the JWT header without signature verification."""
    try:
        header_b64 = token.split(".")[0]
        # Add padding
        header_b64 += "=" * (4 - len(header_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(header_b64))
    except Exception:
        return {}


def _decode_jwt_verified(token: str) -> dict:
    """
    Decode and verify a JWT token signature.

    Supports both HS256 (cloud Supabase, uses JWT_SECRET_KEY) and
    ES256 (local Supabase CLI v2.75+, uses JWKS endpoint).
    Raises HTTPException 500 (misconfiguration) or 401 (bad token).
    """
    header = _peek_jwt_header(token)
    alg = header.get("alg", "HS256")

    try:
        if alg == "ES256":
            kid = header.get("kid", "")
            jwk = _get_jwks_key(kid)
            if jwk is None:
                logger.error("_decode_jwt_verified: ES256 key kid=%s not found in JWKS", kid)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token signing key not found",
                )
            public_key = jwt.algorithms.ECAlgorithm.from_jwk(jwk)
            return jwt.decode(
                token,
                key=public_key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # HS256 path (cloud Supabase)
            if not settings.jwt_secret_key:
                logger.error(
                    "_decode_jwt_verified: JWT_SECRET_KEY is not set — authentication service unavailable"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication service unavailable",
                )
            return jwt.decode(
                token,
                key=settings.jwt_secret_key,
                algorithms=["HS256"],
                audience="authenticated",
            )
    except HTTPException:
        raise
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
