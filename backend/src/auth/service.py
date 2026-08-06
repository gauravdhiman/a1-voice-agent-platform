"""
Authentication service for handling user registration, login, and session management.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status

# The `gotrue` package was renamed to `supabase_auth` in supabase-py >= 2.20.
# The error classes are identical; only the import path moved. Keep the
# explicit fallback so older supabase installs (gotrue) still work.
try:  # pragma: no cover - import shim exercised at runtime, not per-test
    from supabase_auth.errors import AuthApiError
except ImportError:  # pragma: no cover
    from gotrue.errors import AuthApiError
from opentelemetry import metrics, trace
from src.organization.provisioning import ensure_default_organization_for_user
from src.rbac.user_roles.service import user_role_service
from src.shared.utils import extract_first_last_name

from shared.config import supabase_config

from .models import AuthResponse, SignInRequest, SignUpRequest, UserProfile

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Get meter for this module
meter = metrics.get_meter(__name__)

# Create metrics
auth_attempts_counter = meter.create_counter(
    "auth.attempts", description="Number of authentication attempts"
)

auth_success_counter = meter.create_counter(
    "auth.success", description="Number of successful authentications"
)

auth_failure_counter = meter.create_counter(
    "auth.failures", description="Number of failed authentications"
)


class AuthService:
    """Service for handling authentication operations."""

    def __init__(self):
        self.supabase_config = supabase_config

    @property
    def supabase(self):
        """Get Supabase client, raise error if not configured."""
        if not self.supabase_config.is_configured():
            raise ValueError(
                "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY."
            )
        return self.supabase_config.client

    @tracer.start_as_current_span("auth.sign_up")
    async def sign_up(
        self, request: SignUpRequest
    ) -> tuple[Optional[AuthResponse], Optional[HTTPException]]:
        """
        Register a new user account.

        Args:
            request: SignUpRequest with user registration details

        Returns:
            tuple of (AuthResponse or None, HTTPException or None)
        """
        # Record metrics
        auth_attempts_counter.add(1, {"operation": "signup", "source": "backend"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("user.email", request.email)
        if request.invitation_token:
            current_span.set_attribute(
                "invitation.token", request.invitation_token[:8] + "..."
            )
        logging.info(f"Attempting to sign up user: {request.email}")

        try:
            # Sign up with Supabase Auth
            response = self.supabase.auth.sign_up(
                {
                    "email": request.email,
                    "password": request.password,
                    "options": {
                        "data": {
                            "first_name": request.first_name,
                            "last_name": request.last_name,
                        }
                    },
                }
            )

            if not response or not response.user:
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Sign up failed")
                )
                logging.error("Sign up failed - no user returned from Supabase")
                auth_failure_counter.add(
                    1, {"operation": "signup", "error": "no_user_returned"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user account",
                )

            user = response.user
            session = response.session

            # Log the successful sign up
            logging.info(f"User signed up successfully: {user.id}")
            current_span.set_attribute("user.id", str(user.id))
            auth_success_counter.add(1, {"operation": "signup"})

            # Get user profile from metadata
            user_metadata = user.user_metadata or {}

            # Extract first_name and last_name using utility function
            first_name, last_name = extract_first_last_name(user_metadata)

            profile = UserProfile(
                id=user.id,
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                is_verified=user.email_confirmed_at is not None,
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else "",
            )

            # Create auth response
            auth_response = AuthResponse(
                user=profile,
                access_token=session.access_token if session else None,
                refresh_token=session.refresh_token if session else None,
                token_type="bearer",
                expires_in=3600,  # Default 1 hour
            )

            # Provision the default organization for first-time users.
            try:
                org_id, org_error = await ensure_default_organization_for_user(
                    UUID(str(user.id)),
                    user.email,
                )
                if org_error:
                    logging.warning(
                        "Could not provision default organization: %s", org_error
                    )
                elif org_id:
                    logging.info(
                        "Provisioned default organization %s for user %s",
                        org_id,
                        user.id,
                    )
                    current_span.set_attribute("role.assigned", True)
                    current_span.set_attribute("organization.id", str(org_id))
            except Exception as e:
                logging.error(f"Error provisioning default organization: {e}")
                current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))

            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return auth_response, None

        except AuthApiError as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.warning(f"Sign up auth error: {e}")
            auth_failure_counter.add(1, {"operation": "signup", "error": "auth_error"})
            error_msg = str(e).lower()
            if "already registered" in error_msg or "user already" in error_msg:
                return None, HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User already registered",
                )
            if "rate limit" in error_msg or "email rate" in error_msg:
                return None, HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many signup attempts. Please try again later.",
                )
            return None, HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.error(f"Sign up error: {e}")
            auth_failure_counter.add(1, {"operation": "signup", "error": "exception"})
            return None, HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during sign up",
            )

    @tracer.start_as_current_span("auth.sign_in")
    async def sign_in(
        self, request: SignInRequest
    ) -> tuple[Optional[AuthResponse], Optional[HTTPException]]:
        """
        Authenticate user with email and password.

        Args:
            request: SignInRequest with user credentials

        Returns:
            tuple of (AuthResponse or None, HTTPException or None)
        """
        # Record metrics
        auth_attempts_counter.add(1, {"operation": "signin", "source": "backend"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("user.email", request.email)
        logging.info(f"Attempting to sign in user: {request.email}")

        try:
            # Sign in with Supabase Auth
            response = self.supabase.auth.sign_in_with_password(
                {"email": request.email, "password": request.password}
            )

            if not response or not response.user:
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Invalid credentials")
                )
                logging.warning(f"Sign in failed for user: {request.email}")
                auth_failure_counter.add(
                    1, {"operation": "signin", "error": "invalid_credentials"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email or password",
                )

            user = response.user
            session = response.session

            # Log the successful sign in
            logging.info(f"User signed in successfully: {user.id}")
            current_span.set_attribute("user.id", str(user.id))
            auth_success_counter.add(1, {"operation": "signin"})

            # Get user profile from metadata
            user_metadata = user.user_metadata or {}

            # Extract first_name and last_name using utility function
            first_name, last_name = extract_first_last_name(user_metadata)

            profile = UserProfile(
                id=user.id,
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                is_verified=user.email_confirmed_at is not None,
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else "",
            )

            # Create auth response
            auth_response = AuthResponse(
                user=profile,
                access_token=session.access_token if session else None,
                refresh_token=session.refresh_token if session else None,
                token_type="bearer",
                expires_in=3600,  # Default 1 hour
            )

            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return auth_response, None

        except AuthApiError as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.warning(f"Sign in auth error: {e}")
            auth_failure_counter.add(1, {"operation": "signin", "error": "auth_error"})
            return None, HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credentials. Please try again with the correct credentials.",
            )
        except Exception as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.error(f"Sign in error: {e}")
            auth_failure_counter.add(1, {"operation": "signin", "error": "exception"})
            return None, HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during sign in",
            )

    @tracer.start_as_current_span("auth.sign_out")
    async def sign_out(self, access_token: str) -> tuple[bool, Optional[HTTPException]]:
        """
        Sign out user and invalidate session.

        Args:
            access_token: User's access token

        Returns:
            tuple of (success boolean, HTTPException or None)
        """
        # Record metrics
        auth_attempts_counter.add(1, {"operation": "signout", "source": "backend"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("token.provided", bool(access_token))
        logging.info("Attempting to sign out user")

        try:
            # Sign out by invalidating the token
            # Note: We're not using set_session to avoid refresh_token requirement
            # Instead, we'll invalidate the token directly
            self.supabase.auth.sign_out(access_token)

            logging.info("User signed out successfully")
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            auth_success_counter.add(1, {"operation": "signout"})
            return True, None

        except Exception as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.error(f"Sign out error: {e}")
            auth_failure_counter.add(1, {"operation": "signout", "error": "exception"})
            return False, HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to sign out"
            )

    @tracer.start_as_current_span("auth.refresh_token")
    async def refresh_token(
        self, refresh_token: str
    ) -> tuple[Optional[AuthResponse], Optional[HTTPException]]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            tuple of (AuthResponse or None, HTTPException or None)
        """
        # Record metrics
        auth_attempts_counter.add(
            1, {"operation": "refresh_token", "source": "backend"}
        )

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("token.provided", bool(refresh_token))
        logging.info("Attempting to refresh token")

        try:
            # Refresh session with Supabase Auth
            response = self.supabase.auth.refresh_session(refresh_token)

            if not response or not response.user:
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Invalid refresh token")
                )
                logging.warning("Token refresh failed")
                auth_failure_counter.add(
                    1, {"operation": "refresh_token", "error": "invalid_token"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid refresh token",
                )

            user = response.user
            session = response.session

            # Log the successful token refresh
            logging.info(f"Token refreshed successfully for user: {user.id}")
            current_span.set_attribute("user.id", str(user.id))
            auth_success_counter.add(1, {"operation": "refresh_token"})

            # Get user profile from metadata
            user_metadata = user.user_metadata or {}

            # Extract first_name and last_name using utility function
            first_name, last_name = extract_first_last_name(user_metadata)

            profile = UserProfile(
                id=user.id,
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                is_verified=user.email_confirmed_at is not None,
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else "",
            )

            # Create auth response
            auth_response = AuthResponse(
                user=profile,
                access_token=session.access_token if session else None,
                refresh_token=session.refresh_token if session else None,
                token_type="bearer",
                expires_in=3600,  # Default 1 hour
            )

            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return auth_response, None

        except Exception as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.error(f"Token refresh error: {e}")
            auth_failure_counter.add(
                1, {"operation": "refresh_token", "error": "exception"}
            )
            return None, HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during token refresh",
            )

    @tracer.start_as_current_span("auth.get_user")
    async def get_user(
        self, access_token: str
    ) -> tuple[Optional[UserProfile], Optional[HTTPException]]:
        """
        Get current user profile with roles and permissions.

        Args:
            access_token: User's access token

        Returns:
            tuple of (UserProfile or None, HTTPException or None)
        """
        # Record metrics
        auth_attempts_counter.add(1, {"operation": "get_user", "source": "backend"})

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("token.provided", bool(access_token))
        logging.info("Attempting to get user profile")

        try:
            # Validate token directly without setting session to avoid refresh_token requirement
            # We'll decode the JWT and validate with Supabase API directly
            user_response = self.supabase.auth.get_user(access_token)

            if not user_response or not user_response.user:
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Invalid token")
                )
                logging.warning(
                    "Failed to get user - invalid token or no user response"
                )
                auth_failure_counter.add(
                    1, {"operation": "get_user", "error": "invalid_token"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )

            user = user_response.user

            if not user:
                current_span.set_status(
                    trace.Status(trace.StatusCode.ERROR, "Invalid token")
                )
                logging.warning("Failed to get user - invalid token")
                auth_failure_counter.add(
                    1, {"operation": "get_user", "error": "invalid_token"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                )

            # Log the successful user retrieval
            logging.info(f"Retrieved user profile: {user.id}")
            current_span.set_attribute("user.id", str(user.id))
            auth_success_counter.add(1, {"operation": "get_user"})

            # Get user roles with permissions and organization context
            roles_with_permissions, roles_error = (
                await user_role_service.get_all_user_roles_with_permissions(
                    UUID(user.id)
                )
            )
            if roles_error:
                logging.warning(
                    f"Failed to get roles for user {user.id}: {roles_error}"
                )
                # Continue without roles - don't fail the entire request
                roles_with_permissions = []

            # Get user profile from metadata
            user_metadata = user.user_metadata or {}

            # Extract first_name and last_name using utility function
            first_name, last_name = extract_first_last_name(user_metadata)

            profile = UserProfile(
                id=user.id,
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                email_confirmed_at=(
                    user.email_confirmed_at.isoformat()
                    if user.email_confirmed_at
                    else None
                ),
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else "",
                roles=roles_with_permissions,
            )

            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return profile, None

        except Exception as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.error(f"Get user error: {e}")
            auth_failure_counter.add(1, {"operation": "get_user", "error": "exception"})
            return None, HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while fetching user profile",
            )

    @tracer.start_as_current_span("auth.get_user_by_email")
    async def get_user_by_email(
        self, email: str
    ) -> tuple[Optional[UserProfile], Optional[str]]:
        """
        Get user by email address.

        Args:
            email: User's email address

        Returns:
            tuple of (UserProfile or None, error message or None)
        """
        # Record metrics
        auth_attempts_counter.add(
            1, {"operation": "get_user_by_email", "source": "backend"}
        )

        # Set attribute on current span
        current_span = trace.get_current_span()
        current_span.set_attribute("user.email", email)
        logging.info(f"Attempting to get user by email: {email}")

        try:
            # Use Supabase Admin API to list users and find by email
            # Note: In production with high volume, you'd want to cache this or use a different approach
            response = self.supabase.auth.admin.list_users()

            # Handle different response formats
            users_list = []
            if hasattr(response, "users"):
                # Response has .users attribute
                users_list = response.users
            elif isinstance(response, list):
                # Response is directly a list
                users_list = response
            else:
                logging.warning(
                    f"Unexpected response format from list_users: {type(response)}"
                )
                current_span.set_status(trace.Status(trace.StatusCode.OK))
                return None, None

            if not users_list:
                logging.info(f"No users found in system")
                current_span.set_status(trace.Status(trace.StatusCode.OK))
                return None, None

            # Find user by email
            user = None
            for u in users_list:
                if u.email and u.email.lower() == email.lower():
                    user = u
                    break

            if not user:
                logging.info(f"No user found with email: {email}")
                current_span.set_status(trace.Status(trace.StatusCode.OK))
                return None, None  # User not found is not an error

            # Get user roles with permissions and organization context
            roles_with_permissions, roles_error = (
                await user_role_service.get_all_user_roles_with_permissions(
                    UUID(user.id)
                )
            )
            if roles_error:
                logging.warning(
                    f"Failed to get roles for user {user.id}: {roles_error}"
                )
                # Continue without roles - don't fail the entire request
                roles_with_permissions = []

            # Extract first_name and last_name from metadata
            user_metadata = user.user_metadata or {}
            first_name, last_name = extract_first_last_name(user_metadata)

            profile = UserProfile(
                id=user.id,
                email=user.email,
                first_name=first_name,
                last_name=last_name,
                email_confirmed_at=(
                    user.email_confirmed_at.isoformat()
                    if user.email_confirmed_at
                    else None
                ),
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else "",
                roles=roles_with_permissions,
            )

            logging.info(f"Found user by email: {email}")
            current_span.set_attribute("user.id", str(user.id))
            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return profile, None

        except Exception as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.error(f"Get user by email error: {e}")
            return None, str(e)


# Global auth service instance
auth_service = AuthService()
