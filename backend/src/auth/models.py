"""
Pydantic models for authentication requests and responses.
"""

import re
from typing import Annotated, Optional
from uuid import UUID

from pydantic import AfterValidator, BaseModel, EmailStr, Field, field_validator
from src.rbac.roles.models import UserRoleWithPermissions


def validate_auth_email(value: str) -> str:
    """Validate email format for auth endpoints.

    Uses a permissive check so local/dev addresses (e.g. ``test@dev.local``)
    accepted by Supabase are not rejected by strict DNS-oriented validators.
    """
    normalized = value.strip()
    if "@" not in normalized:
        raise ValueError("Invalid email address")
    local, _, domain = normalized.partition("@")
    if not local or not domain:
        raise ValueError("Invalid email address")
    return normalized


AuthEmail = Annotated[str, AfterValidator(validate_auth_email)]


class SignUpRequest(BaseModel):
    """User registration request model."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., min_length=8, max_length=128, description="User password"
    )
    password_confirm: str = Field(..., description="Password confirmation")
    first_name: str = Field(
        ..., min_length=1, max_length=50, description="User first name"
    )
    last_name: str = Field(
        ..., min_length=1, max_length=50, description="User last name"
    )
    invitation_token: Optional[str] = Field(
        None, description="Invitation token for organization membership"
    )
    captcha_token: Optional[str] = Field(
        None,
        max_length=2048,
        description="Cloudflare Turnstile token (required when enforced)",
    )
    terms_accepted: bool = Field(
        default=False,
        description=(
            "Whether the user accepted the Terms & Conditions and Privacy Policy. "
            "Signup is rejected when false."
        ),
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError(
                'Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)'
            )

        return v

    def model_post_init(self, __context) -> None:
        """Validate that passwords match."""
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")


class SignInRequest(BaseModel):
    """User login request model."""

    email: AuthEmail = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class LinkedInAuthorizationResponse(BaseModel):
    """Direct LinkedIn authorization URL and signed state."""

    authorization_url: str = Field(
        ..., description="LinkedIn authorization URL opened by the browser"
    )
    state: str = Field(..., description="Signed state used for callback validation")


class LinkedInCodeExchangeRequest(BaseModel):
    """One-time LinkedIn authorization code returned to the app callback."""

    code: str = Field(
        ..., min_length=1, max_length=2048, description="LinkedIn authorization code"
    )
    state: str = Field(
        ..., min_length=1, max_length=4096, description="Signed OAuth state"
    )


class SessionHandoffRequest(BaseModel):
    """Signed one-time token issued after backend OAuth completes."""

    handoff: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="Short-lived signed OAuth session handoff token",
    )


class SessionHandoffResponse(BaseModel):
    """Supabase session tokens returned from a one-time OAuth handoff exchange."""

    access_token: str = Field(..., description="Supabase access token")
    refresh_token: str = Field(..., description="Supabase refresh token")
    expires_in: int = Field(..., description="Token expiration in seconds")
    token_type: str = Field(default="bearer", description="Token type")


class AuthResponse(BaseModel):
    """Authentication response model."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    user: "UserProfile" = Field(..., description="User profile information")
    joined_organization_id: Optional[UUID] = Field(
        None,
        description="Organization joined via invitation during this auth flow",
    )
    joined_organization_name: Optional[str] = Field(
        None,
        description="Display name of the organization joined via invitation",
    )


class SignUpResponse(BaseModel):
    """Signup response when session may be withheld pending email verification."""

    user: "UserProfile" = Field(..., description="Newly registered user profile")
    email_verification_required: bool = Field(
        ...,
        description=(
            "True when Supabase did not issue a session (confirm-email enabled). "
            "The client must not sign the user in until email is verified."
        ),
    )
    access_token: Optional[str] = Field(
        None, description="JWT access token when immediate sign-in is allowed"
    )
    refresh_token: Optional[str] = Field(
        None, description="Refresh token when immediate sign-in is allowed"
    )
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(
        None, description="Token expiration in seconds when a session was issued"
    )
    joined_organization_id: Optional[UUID] = Field(
        None,
        description="Organization joined via invitation during signup",
    )
    joined_organization_name: Optional[str] = Field(
        None,
        description="Display name of the organization joined via invitation",
    )


class UserProfile(BaseModel):
    """User profile information."""

    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    email_confirmed_at: Optional[str] = Field(
        None, description="Email confirmation timestamp"
    )
    created_at: str = Field(..., description="Account creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    has_organizations: Optional[bool] = Field(
        None, description="Whether the user has organizations"
    )
    roles: list[UserRoleWithPermissions] = Field(
        default=[], description="User's roles with organization context"
    )
    current_organization_id: Optional[UUID] = Field(
        None,
        description=(
            "Organization the embedded permissions object is scoped to. "
            "Computed server-side on every /me response."
        ),
    )
    permissions: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Resource -> actions map resolved server-side for the current "
            "org context. Wildcard is encoded as {'*': ['*']}. See "
            "docs/tw-drafts/navigation-redesign.md for the contract."
        ),
    )

    def has_role(self, role_name: str, organization_id: Optional[str] = None) -> bool:
        """Check if user has a specific role."""
        for user_role in self.roles:
            if user_role.role.name == role_name:
                # If organization_id is specified, check if role is for that organization
                if organization_id:
                    # Check if this role is assigned to the user for the specific organization
                    if str(user_role.organization_id) == organization_id:
                        return True
                else:
                    # For platform-wide roles (organization_id is None)
                    if (
                        role_name == "platform_admin"
                        and user_role.organization_id is None
                    ):
                        return True
        return False

    def has_permission(
        self, permission_name: str, organization_id: Optional[str] = None
    ) -> bool:
        """Check if user has a specific permission."""
        for user_role in self.roles:
            for permission in user_role.role.permissions:
                if permission.name == permission_name:
                    # If organization_id is specified, check if role is for that organization
                    if organization_id:
                        if str(user_role.organization_id) == organization_id:
                            return True
                    else:
                        # For platform-wide permissions
                        if (
                            user_role.role.name == "platform_admin"
                            and user_role.organization_id is None
                        ):
                            return True
        return False


class EmailAvailabilityResponse(BaseModel):
    """Public signup helper indicating whether an email is already registered."""

    exists: bool = Field(
        ..., description="True when an auth user already uses this email"
    )
    sign_in_methods: list[str] = Field(
        default_factory=list,
        description="Linked sign-in methods when exists=true (email, google, linkedin)",
    )
    message: Optional[str] = Field(
        None,
        description="Human-readable guidance for the signup form",
    )


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")


# Update forward references
AuthResponse.model_rebuild()
SignUpResponse.model_rebuild()
