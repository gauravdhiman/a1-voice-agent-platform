"""Platform-admin routes for write-only platform API credentials."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

from shared.voice_agents.platform_credentials import (
    PlatformVoiceCredentialError,
    PlatformVoiceProvider,
    PlatformVoiceProviderCredentialsResponse,
    PlatformVoiceProviderCredentialStatus,
    PlatformVoiceProviderCredentialUpdate,
    platform_voice_provider_credential_service,
)

platform_voice_credential_router = APIRouter(
    prefix="/api/v1/platform/api-credentials",
    tags=["Platform API credentials"],
)
MAX_PLATFORM_VOICE_API_KEY_LENGTH = 4096


def _require_platform_admin(user_profile: UserProfile) -> None:
    """Reject all users without the platform-admin role."""
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Platform admin access required",
    )


@platform_voice_credential_router.get(
    "/", response_model=PlatformVoiceProviderCredentialsResponse
)
async def get_platform_voice_provider_credentials(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformVoiceProviderCredentialsResponse:
    """Return stored-key and environment-fallback status without key values."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    try:
        return await platform_voice_provider_credential_service.get_status()
    except PlatformVoiceCredentialError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform API credentials are temporarily unavailable",
        ) from None


@platform_voice_credential_router.put(
    "/{provider}", response_model=PlatformVoiceProviderCredentialStatus
)
async def set_platform_voice_provider_credential(
    provider: PlatformVoiceProvider,
    payload: PlatformVoiceProviderCredentialUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PlatformVoiceProviderCredentialStatus:
    """Create or rotate one encrypted platform voice-provider key."""
    user_id, user_profile = user_data
    _require_platform_admin(user_profile)
    api_key = payload.api_key.get_secret_value()
    if len(api_key) > MAX_PLATFORM_VOICE_API_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key must be 4096 characters or fewer",
        )
    try:
        return await platform_voice_provider_credential_service.set_provider_credential(
            provider,
            api_key,
            user_id,
        )
    except PlatformVoiceCredentialError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform API credential could not be saved",
        ) from None


@platform_voice_credential_router.delete(
    "/{provider}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_platform_voice_provider_credential(
    provider: PlatformVoiceProvider,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Response:
    """Remove one stored key; runtime may then use its environment fallback."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    try:
        await platform_voice_provider_credential_service.delete_provider_credential(
            provider
        )
    except PlatformVoiceCredentialError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Platform API credential could not be removed",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
