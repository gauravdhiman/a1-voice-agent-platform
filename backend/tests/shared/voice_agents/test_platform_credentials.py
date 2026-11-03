"""Tests for encrypted platform voice-provider credential storage."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from shared.common.security import decrypt_data, encrypt_data
from shared.voice_agents.platform_credentials import (
    PlatformVoiceCredentialError,
    PlatformVoiceProvider,
    PlatformVoiceProviderCredentialService,
    PlatformVoiceProviderCredentialUpdate,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000041")


def _config(table):
    """Build a configured service-role Supabase client mock."""
    client = MagicMock()
    client.table.return_value = table
    config = MagicMock(is_configured=MagicMock(return_value=True))
    config.service_client = client
    return config


@pytest.mark.asyncio
async def test_status_returns_flags_without_secret_values(monkeypatch):
    """Status includes stored/env flags and never returns key material."""
    table = MagicMock()
    table.select.return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "provider": "google",
                "updated_at": "2026-10-31T10:00:00+00:00",
            }
        ]
    )
    monkeypatch.setenv("OPENAI_API_KEY", "openai-environment-key")

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        result = await PlatformVoiceProviderCredentialService().get_status()

    assert result.providers["google"].configured is True
    assert result.providers["google"].environment_fallback_configured is False
    assert result.providers["openai"].configured is False
    assert result.providers["openai"].environment_fallback_configured is True
    assert "api_key" not in result.model_dump_json()
    assert "openai-environment-key" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_set_credential_encrypts_key_before_upsert():
    """Stored database values contain only authenticated ciphertext."""
    table = MagicMock()
    table.upsert.return_value = table
    table.execute.return_value = MagicMock(data=[])
    provider = PlatformVoiceProvider.GOOGLE

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        result = await PlatformVoiceProviderCredentialService().set_provider_credential(
            provider,
            "  sensitive-google-key  ",
            USER_ID,
        )

    payload = table.upsert.call_args.args[0]
    assert payload["provider"] == provider.value
    assert payload["credential_encrypted"] != "sensitive-google-key"
    assert decrypt_data(payload["credential_encrypted"]) == {
        "api_key": "sensitive-google-key"
    }
    assert payload["updated_by"] == str(USER_ID)
    assert result.configured is True


@pytest.mark.asyncio
async def test_get_provider_credentials_decrypts_for_runtime_only():
    """The server-side runtime receives the decrypted provider map."""
    table = MagicMock()
    table.select.return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "provider": "openai",
                "credential_encrypted": encrypt_data({"api_key": "stored-openai"}),
            }
        ]
    )

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        result = (
            await PlatformVoiceProviderCredentialService().get_provider_credentials()
        )

    assert result == {"openai": "stored-openai"}


@pytest.mark.asyncio
async def test_get_provider_credentials_scopes_reads_to_required_providers():
    """An unrelated unreadable provider key cannot break another provider."""
    table = MagicMock()
    table.select.return_value = table
    table.in_.return_value = table
    table.execute.return_value = MagicMock(
        data=[
            {
                "provider": "google",
                "credential_encrypted": encrypt_data({"api_key": "stored-google"}),
            },
            {"provider": "openai", "credential_encrypted": "unrelated-broken-cipher"},
        ]
    )

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        result = (
            await PlatformVoiceProviderCredentialService().get_provider_credentials(
                {"google"}
            )
        )

    table.in_.assert_called_once_with("provider", ["google"])
    assert result == {"google": "stored-google"}


@pytest.mark.asyncio
async def test_unreadable_ciphertext_fails_closed():
    """Unreadable stored secrets do not become an env-fallback opportunity."""
    table = MagicMock()
    table.select.return_value = table
    table.execute.return_value = MagicMock(
        data=[{"provider": "google", "credential_encrypted": "broken-ciphertext"}]
    )

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        with pytest.raises(PlatformVoiceCredentialError):
            await PlatformVoiceProviderCredentialService().get_provider_credentials()


@pytest.mark.asyncio
async def test_database_read_errors_are_sanitized():
    """Database diagnostics never leak their raw details to callers."""
    table = MagicMock()
    table.select.return_value = table
    table.execute.side_effect = RuntimeError("private database diagnostic")

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        with pytest.raises(PlatformVoiceCredentialError) as exc_info:
            await PlatformVoiceProviderCredentialService().get_provider_credentials()

    assert "private database diagnostic" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_database_write_errors_are_sanitized():
    """Failed key writes return safe diagnostics without submitted values."""
    table = MagicMock()
    table.upsert.return_value = table
    table.execute.side_effect = RuntimeError("private database diagnostic")

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        with pytest.raises(PlatformVoiceCredentialError) as exc_info:
            await PlatformVoiceProviderCredentialService().set_provider_credential(
                PlatformVoiceProvider.GOOGLE,
                "submitted-secret",
                USER_ID,
            )

    assert "private database diagnostic" not in str(exc_info.value)
    assert "submitted-secret" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_removes_only_the_requested_provider():
    """Removing one provider is an independently scoped database mutation."""
    table = MagicMock()
    table.delete.return_value = table
    table.eq.return_value = table
    table.execute.return_value = MagicMock(data=[])

    with patch(
        "shared.voice_agents.platform_credentials.supabase_config", _config(table)
    ):
        await PlatformVoiceProviderCredentialService().delete_provider_credential(
            PlatformVoiceProvider.FISH
        )

    table.eq.assert_called_once_with("provider", "fish")


def test_credential_update_rejects_blank_keys():
    """Whitespace-only values cannot be stored as configured credentials."""
    with pytest.raises(ValidationError):
        PlatformVoiceProviderCredentialUpdate(api_key="   ")


def test_credential_update_repr_hides_the_secret():
    """Request models do not reveal valid keys through accidental logging."""
    payload = PlatformVoiceProviderCredentialUpdate(api_key="sensitive-key")

    assert "sensitive-key" not in repr(payload)
    assert payload.api_key.get_secret_value() == "sensitive-key"
