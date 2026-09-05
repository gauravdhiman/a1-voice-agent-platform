"""
Authentication service for handling user registration, login, and session management.
"""

import logging
from typing import Any, Optional
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
from src.organization.service import organization_service
from src.rbac.user_roles.service import user_role_service
from src.shared.utils import extract_first_last_name

from shared.config import create_isolated_supabase_client, supabase_config

from .models import (
    AuthResponse,
    EmailAvailabilityResponse,
    SignInRequest,
    SignUpRequest,
    SignUpResponse,
    UserProfile,
)
from .sign_in_methods import (
    GENERIC_EXISTING_ACCOUNT_MESSAGE,
    SignInGuidance,
    SignInMethod,
    resolve_sign_in_guidance,
)

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
    ) -> tuple[Optional[SignUpResponse], Optional[HTTPException]]:
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
            from src.notifications.email_verification_service import (
                email_verification_service,
            )
            from src.notifications.platform_settings_service import (
                platform_notification_settings_service,
            )
            from src.notifications.signup_notifier import signup_notifier

            email_verification_required = (
                await platform_notification_settings_service.is_email_verification_required()
            )

            auth_client = create_isolated_supabase_client()
            try:
                create_response = auth_client.auth.admin.create_user(
                    {
                        "email": request.email,
                        "password": request.password,
                        "email_confirm": not email_verification_required,
                        "user_metadata": {
                            "first_name": request.first_name,
                            "last_name": request.last_name,
                            "last_sign_in_method": "email",
                        },
                    }
                )
            except AuthApiError as create_error:
                message = str(create_error).lower()
                if "already" in message or "exists" in message:
                    raise
                logging.error("Admin create_user failed: %s", create_error)
                auth_failure_counter.add(
                    1, {"operation": "signup", "error": "create_user_failed"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user account",
                )

            user = (
                create_response.user
                if hasattr(create_response, "user")
                else create_response
            )
            if not user:
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

            session = None
            access_token = None
            refresh_token = None
            expires_in = None

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
                email=user.email or request.email,
                first_name=first_name or request.first_name,
                last_name=last_name or request.last_name,
                email_confirmed_at=_format_auth_timestamp(user.email_confirmed_at),
                created_at=_format_auth_timestamp(user.created_at),
                updated_at=_format_auth_timestamp(user.updated_at),
            )

            current_span.set_attribute(
                "auth.email_verification_required", email_verification_required
            )

            user_name = f"{request.first_name} {request.last_name}".strip()
            if email_verification_required:
                sent, send_error = (
                    await email_verification_service.create_and_send_verification(
                        UUID(str(user.id)),
                        user.email or request.email,
                        user_name or request.first_name or "User",
                    )
                )
                if not sent:
                    logging.warning(
                        "Verification email failed for %s: %s", user.id, send_error
                    )
            else:
                sign_in_response = auth_client.auth.sign_in_with_password(
                    {"email": request.email, "password": request.password}
                )
                session = sign_in_response.session if sign_in_response else None
                if session:
                    access_token = session.access_token
                    refresh_token = session.refresh_token
                    expires_in = session.expires_in
                elif sign_in_response and sign_in_response.user:
                    profile = UserProfile(
                        id=sign_in_response.user.id,
                        email=sign_in_response.user.email or request.email,
                        first_name=first_name or request.first_name,
                        last_name=last_name or request.last_name,
                        email_confirmed_at=_format_auth_timestamp(
                            sign_in_response.user.email_confirmed_at
                        ),
                        created_at=_format_auth_timestamp(
                            sign_in_response.user.created_at
                        ),
                        updated_at=_format_auth_timestamp(
                            sign_in_response.user.updated_at
                        ),
                    )

            joined_organization_id = None
            joined_organization_name = None
            if request.invitation_token:
                invitation, invite_error = (
                    await organization_service.process_invitation(
                        request.invitation_token,
                        UUID(str(user.id)),
                        user.email or request.email,
                    )
                )
                if invite_error:
                    logging.error(
                        "Invitation processing failed during signup for %s: %s",
                        user.id,
                        invite_error,
                    )
                    current_span.set_status(
                        trace.Status(trace.StatusCode.ERROR, "invitation_error")
                    )
                    return None, HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "invitation_error",
                            "message": invite_error,
                        },
                    )
                elif invitation:
                    joined_organization_id = invitation.organization_id
                    joined_organization_name = invitation.organization_name

            if not joined_organization_id:
                org_name = (
                    f"{request.first_name}'s Organization"
                    if request.first_name
                    else None
                )
                try:
                    org_id, org_error = await ensure_default_organization_for_user(
                        UUID(str(user.id)),
                        user.email or request.email,
                        organization_name=org_name,
                    )
                    if org_error:
                        logging.warning(
                            "Could not provision organization: %s", org_error
                        )
                    elif org_id:
                        logging.info(
                            "Provisioned organization %s for user %s",
                            org_id,
                            user.id,
                        )
                        current_span.set_attribute("role.assigned", True)
                        current_span.set_attribute("organization.id", str(org_id))
                except Exception as e:
                    logging.error("Error provisioning organization", exc_info=True)
                    current_span.set_status(
                        trace.Status(trace.StatusCode.ERROR, str(e))
                    )

            signup_method = "invitation" if request.invitation_token else "email"
            await signup_notifier.notify_new_user(
                email=user.email or request.email,
                user_id=UUID(str(user.id)),
                method=signup_method,
                first_name=request.first_name,
                last_name=request.last_name,
                organization_name=joined_organization_name,
                is_new_user=True,
            )

            sign_up_response = SignUpResponse(
                user=profile,
                email_verification_required=email_verification_required,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=expires_in,
                joined_organization_id=joined_organization_id,
                joined_organization_name=joined_organization_name,
            )

            current_span.set_status(trace.Status(trace.StatusCode.OK))
            return sign_up_response, None

        except AuthApiError as e:
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logging.warning(f"Sign up auth error: {e}")
            auth_failure_counter.add(1, {"operation": "signup", "error": "auth_error"})
            error_msg = str(e).lower()
            if "already registered" in error_msg or "user already" in error_msg:
                guidance_user = await self._find_auth_user_by_email(request.email)
                guidance = (
                    resolve_sign_in_guidance(guidance_user)
                    if guidance_user is not None
                    else SignInGuidance([], GENERIC_EXISTING_ACCOUNT_MESSAGE)
                )
                return None, HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": guidance.message,
                        "sign_in_methods": guidance.sign_in_methods,
                    },
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
            auth_client = create_isolated_supabase_client()
            response = auth_client.auth.sign_in_with_password(
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

            from src.notifications.platform_settings_service import (
                platform_notification_settings_service,
            )

            verification_required = (
                await platform_notification_settings_service.is_email_verification_required()
            )

            if verification_required and not user.email_confirmed_at:
                auth_failure_counter.add(
                    1, {"operation": "signin", "error": "email_not_confirmed"}
                )
                return None, HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": (
                            "Please verify your email address before signing in."
                        ),
                        "code": "email_not_confirmed",
                    },
                )

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

            await self._record_last_sign_in_method(str(user.id), "email")

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

    @tracer.start_as_current_span("auth.check_email_availability")
    async def check_email_availability(
        self, email: str
    ) -> tuple[EmailAvailabilityResponse, Optional[HTTPException]]:
        """Check whether an email is available for new registration."""
        current_span = trace.get_current_span()
        current_span.set_attribute("user.email", email)

        try:
            user = await self._find_auth_user_by_email(email)
            if user is None:
                return EmailAvailabilityResponse(exists=False), None

            guidance = resolve_sign_in_guidance(user)
            return (
                EmailAvailabilityResponse(
                    exists=True,
                    sign_in_methods=guidance.sign_in_methods,
                    message=guidance.message,
                ),
                None,
            )
        except Exception as exc:
            logging.error("Email availability check failed: %s", exc, exc_info=True)
            return EmailAvailabilityResponse(exists=False), HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to verify email availability",
            )

    async def _get_sign_in_methods_for_email(self, email: str) -> list[SignInMethod]:
        """Return sign-in methods for an existing auth user when deterministic."""
        user = await self._find_auth_user_by_email(email)
        if user is None:
            return []
        return resolve_sign_in_guidance(user).sign_in_methods

    def _hydrate_auth_user(self, user: Any) -> Any:
        """Load the full auth user record including metadata and identities."""
        user_id = getattr(user, "id", None)
        if not user_id:
            return user

        response = self.supabase.auth.admin.get_user_by_id(str(user_id))
        if hasattr(response, "user") and response.user is not None:
            return response.user
        if isinstance(response, dict):
            return response.get("user", user)
        return user

    async def _find_auth_user_by_email(self, email: str) -> Optional[Any]:
        """Locate a Supabase auth user record by email using the admin API."""
        normalized_email = email.strip().lower()
        if not normalized_email:
            return None

        page = 1
        max_pages = 10
        while page <= max_pages:
            response = self.supabase.auth.admin.list_users(page=page, per_page=200)
            users_list: list[Any] = []
            if hasattr(response, "users"):
                users_list = response.users or []
            elif isinstance(response, list):
                users_list = response

            for user in users_list:
                user_email = getattr(user, "email", None)
                if user_email and user_email.lower() == normalized_email:
                    return self._hydrate_auth_user(user)

            if len(users_list) < 200:
                break
            page += 1

        return None

    async def _record_last_sign_in_method(
        self, user_id: str, method: SignInMethod
    ) -> None:
        """Persist the last successful sign-in method for signup guidance."""
        try:
            response = self.supabase.auth.admin.get_user_by_id(user_id)
            user = response.user if hasattr(response, "user") else response
            metadata = dict(getattr(user, "user_metadata", None) or {})
            metadata["last_sign_in_method"] = method
            self.supabase.auth.admin.update_user_by_id(
                user_id,
                {"user_metadata": metadata},
            )
        except Exception as exc:
            logging.warning(
                "Failed to record last sign-in method for user %s: %s",
                user_id,
                exc,
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
            user = await self._find_auth_user_by_email(email)
            if not user:
                logging.info("No user found with email: %s", email)
                current_span.set_status(trace.Status(trace.StatusCode.OK))
                return None, None

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


def _format_auth_timestamp(value: object) -> str:
    """Format Supabase auth timestamp fields for API responses."""
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[union-attr]
    return str(value)


# Global auth service instance
auth_service = AuthService()
