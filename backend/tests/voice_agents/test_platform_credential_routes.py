"""Authorization and safe-response tests for platform voice credentials."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from shared.voice_agents.platform_credentials import (
    PlatformVoiceProvider,
    PlatformVoiceProviderCredentialsResponse,
    PlatformVoiceProviderCredentialStatus,
    PlatformVoiceProviderCredentialUpdate,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000042")


def _profile(is_admin: bool) -> Mock:
    """Build a mock profile with one platform role decision."""
    profile = Mock()
    profile.has_role = Mock(return_value=is_admin)
    return profile


@pytest.mark.asyncio
async def test_get_credentials_requires_platform_admin():
    from src.voice_agents.platform_credential_routes import (
        get_platform_voice_provider_credentials,
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_platform_voice_provider_credentials(
            user_data=(USER_ID, _profile(is_admin=False))
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_credentials_returns_only_provider_status():
    from src.voice_agents.platform_credential_routes import (
        get_platform_voice_provider_credentials,
    )

    response = PlatformVoiceProviderCredentialsResponse(
        providers={
            "google": PlatformVoiceProviderCredentialStatus(
                configured=True,
                environment_fallback_configured=False,
            )
        }
    )
    with patch(
        "src.voice_agents.platform_credential_routes.platform_voice_"
        "provider_credential_service"
    ) as credential_service:
        credential_service.get_status = AsyncMock(return_value=response)
        result = await get_platform_voice_provider_credentials(
            user_data=(USER_ID, _profile(is_admin=True))
        )

    assert result.providers["google"].configured is True
    assert "api_key" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_set_credentials_requires_platform_admin():
    from src.voice_agents.platform_credential_routes import (
        set_platform_voice_provider_credential,
    )

    with pytest.raises(HTTPException) as exc_info:
        await set_platform_voice_provider_credential(
            provider=PlatformVoiceProvider.GOOGLE,
            payload=PlatformVoiceProviderCredentialUpdate(api_key="secret"),
            user_data=(USER_ID, _profile(is_admin=False)),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_set_credentials_forwards_write_only_value_to_service():
    from src.voice_agents.platform_credential_routes import (
        set_platform_voice_provider_credential,
    )

    status = PlatformVoiceProviderCredentialStatus(
        configured=True,
        environment_fallback_configured=True,
    )
    with patch(
        "src.voice_agents.platform_credential_routes.platform_voice_"
        "provider_credential_service"
    ) as credential_service:
        credential_service.set_provider_credential = AsyncMock(return_value=status)
        result = await set_platform_voice_provider_credential(
            provider=PlatformVoiceProvider.OPENAI,
            payload=PlatformVoiceProviderCredentialUpdate(api_key="secret"),
            user_data=(USER_ID, _profile(is_admin=True)),
        )

    credential_service.set_provider_credential.assert_awaited_once_with(
        PlatformVoiceProvider.OPENAI,
        "secret",
        USER_ID,
    )
    assert result.configured is True
    assert "secret" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_set_credentials_rejects_overlong_value_without_echoing_it():
    """Length errors return a safe message and never include submitted key text."""
    from src.voice_agents.platform_credential_routes import (
        MAX_PLATFORM_VOICE_API_KEY_LENGTH,
        set_platform_voice_provider_credential,
    )

    secret = "x" * (MAX_PLATFORM_VOICE_API_KEY_LENGTH + 1)
    with patch(
        "src.voice_agents.platform_credential_routes.platform_voice_"
        "provider_credential_service"
    ) as credential_service:
        with pytest.raises(HTTPException) as exc_info:
            await set_platform_voice_provider_credential(
                provider=PlatformVoiceProvider.GOOGLE,
                payload=PlatformVoiceProviderCredentialUpdate(api_key=secret),
                user_data=(USER_ID, _profile(is_admin=True)),
            )

    credential_service.set_provider_credential.assert_not_called()
    assert exc_info.value.status_code == 422
    assert secret not in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_credentials_requires_platform_admin():
    from src.voice_agents.platform_credential_routes import (
        delete_platform_voice_provider_credential,
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_platform_voice_provider_credential(
            provider=PlatformVoiceProvider.FISH,
            user_data=(USER_ID, _profile(is_admin=False)),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_credentials_removes_only_requested_provider():
    from src.voice_agents.platform_credential_routes import (
        delete_platform_voice_provider_credential,
    )

    with patch(
        "src.voice_agents.platform_credential_routes.platform_voice_"
        "provider_credential_service"
    ) as credential_service:
        credential_service.delete_provider_credential = AsyncMock()
        result = await delete_platform_voice_provider_credential(
            provider=PlatformVoiceProvider.FISH,
            user_data=(USER_ID, _profile(is_admin=True)),
        )

    credential_service.delete_provider_credential.assert_awaited_once_with(
        PlatformVoiceProvider.FISH
    )
    assert result.status_code == 204


def test_platform_credential_routes_use_generic_api_credentials_path():
    from src.voice_agents.platform_credential_routes import (
        platform_voice_credential_router,
    )

    paths = {route.path for route in platform_voice_credential_router.routes}
    assert "/api/v1/platform/api-credentials/" in paths
    assert "/api/v1/platform/api-credentials/{provider}" in paths
