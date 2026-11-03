"""Encrypted platform voice-provider credentials and admin-safe status models."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, field_validator

from shared.common.security import decrypt_data, encrypt_data
from shared.config import supabase_config

logger = logging.getLogger(__name__)


class PlatformVoiceProvider(str, Enum):
    """Voice providers with platform-managed API credentials."""

    GOOGLE = "google"
    DEEPGRAM = "deepgram"
    OPENAI = "openai"
    CARTESIA = "cartesia"
    CEREBRAS = "cerebras"
    OPENROUTER = "openrouter"
    FISH = "fish"


PLATFORM_VOICE_PROVIDER_ENV: dict[str, str] = {
    PlatformVoiceProvider.GOOGLE.value: "GEMINI_API_KEY",
    PlatformVoiceProvider.DEEPGRAM.value: "DEEPGRAM_API_KEY",
    PlatformVoiceProvider.OPENAI.value: "OPENAI_API_KEY",
    PlatformVoiceProvider.CARTESIA.value: "CARTESIA_API_KEY",
    PlatformVoiceProvider.CEREBRAS.value: "CEREBRAS_API_KEY",
    PlatformVoiceProvider.OPENROUTER.value: "OPENROUTER_API_KEY",
    PlatformVoiceProvider.FISH.value: "FISH_API_KEY",
}


class PlatformVoiceCredentialError(RuntimeError):
    """Raised when platform voice credentials cannot be read or changed safely."""


class PlatformVoiceProviderCredentialStatus(BaseModel):
    """Secret-free status for one platform voice provider."""

    configured: bool = Field(
        description="Whether an encrypted platform-managed key is stored."
    )
    environment_fallback_configured: bool = Field(
        description="Whether the provider environment fallback is configured."
    )
    updated_at: Optional[datetime] = None


class PlatformVoiceProviderCredentialsResponse(BaseModel):
    """Secret-free status for every supported platform voice provider."""

    providers: dict[str, PlatformVoiceProviderCredentialStatus]


class PlatformVoiceProviderCredentialUpdate(BaseModel):
    """Write-only input for creating or rotating one provider key."""

    api_key: SecretStr = Field(
        ...,
        repr=False,
        description="Write-only provider API key; maximum 4096 characters.",
        json_schema_extra={"writeOnly": True, "maxLength": 4096},
    )

    @field_validator("api_key")
    @classmethod
    def _require_non_blank_key(cls, value: SecretStr) -> SecretStr:
        cleaned = value.get_secret_value().strip()
        if not cleaned:
            raise ValueError("API key must not be blank")
        return SecretStr(cleaned)


class PlatformVoiceProviderCredentialService:
    """Store platform voice keys encrypted and expose only configured flags."""

    TABLE = "platform_voice_provider_credentials"

    @property
    def supabase(self):
        """Return the service-role client required by the credentials table."""
        if not supabase_config.is_configured() or not supabase_config.service_client:
            raise PlatformVoiceCredentialError("Supabase is not configured")
        return supabase_config.service_client

    async def get_status(self) -> PlatformVoiceProviderCredentialsResponse:
        """List configured keys and env-fallback availability without secrets."""
        try:
            response = await asyncio.to_thread(
                lambda: self.supabase.table(self.TABLE)
                .select("provider,updated_at")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 - database errors may contain payloads
            logger.error(
                "Could not read platform voice credential status (error_type=%s)",
                type(exc).__name__,
            )
            raise PlatformVoiceCredentialError(
                "Platform voice credentials are unavailable"
            ) from None

        stored = {
            str(row["provider"]): row.get("updated_at")
            for row in (response.data or [])
            if row.get("provider") in PLATFORM_VOICE_PROVIDER_ENV
        }
        return PlatformVoiceProviderCredentialsResponse(
            providers={
                provider: PlatformVoiceProviderCredentialStatus(
                    configured=provider in stored,
                    environment_fallback_configured=bool(
                        os.getenv(env_name, "").strip()
                    ),
                    updated_at=stored.get(provider),
                )
                for provider, env_name in PLATFORM_VOICE_PROVIDER_ENV.items()
            }
        )

    async def get_provider_credentials(
        self, providers: Optional[set[str]] = None
    ) -> dict[str, str]:
        """Decrypt only the requested platform keys for server-side use.

        Args:
            providers: Provider names required by a preset or catalog. When
                omitted, all supported providers are read for compatibility.

        Returns:
            Decrypted credentials keyed by provider. Unrequested keys are never
            returned, even if a database client returns extra rows.
        """
        selected_providers = (
            None
            if providers is None
            else set(providers).intersection(PLATFORM_VOICE_PROVIDER_ENV)
        )
        if selected_providers == set():
            return {}

        def fetch_credentials():
            query = self.supabase.table(self.TABLE).select(
                "provider,credential_encrypted"
            )
            if selected_providers is not None:
                query = query.in_("provider", sorted(selected_providers))
            return query.execute()

        try:
            response = await asyncio.to_thread(fetch_credentials)
        except Exception as exc:  # noqa: BLE001 - never log query payloads
            logger.error(
                "Could not read platform voice credentials (error_type=%s)",
                type(exc).__name__,
            )
            raise PlatformVoiceCredentialError(
                "Platform voice credentials are unavailable"
            ) from None

        credentials: dict[str, str] = {}
        for row in response.data or []:
            provider = str(row.get("provider", ""))
            if selected_providers is not None and provider not in selected_providers:
                continue
            encrypted = row.get("credential_encrypted")
            if provider not in PLATFORM_VOICE_PROVIDER_ENV or not encrypted:
                logger.error(
                    "Invalid platform voice credential row provider=%s", provider
                )
                raise PlatformVoiceCredentialError(
                    "Platform voice credentials could not be decrypted"
                )
            try:
                payload = decrypt_data(encrypted)
            except Exception as exc:  # pragma: no cover - decrypt_data is defensive
                logger.error(
                    "Could not decrypt platform voice credential provider=%s "
                    "(error_type=%s)",
                    provider,
                    type(exc).__name__,
                )
                raise PlatformVoiceCredentialError(
                    "Platform voice credentials could not be decrypted"
                ) from None
            api_key = payload.get("api_key") if isinstance(payload, dict) else None
            if not isinstance(api_key, str) or not api_key.strip():
                logger.error(
                    "Unreadable platform voice credential provider=%s", provider
                )
                raise PlatformVoiceCredentialError(
                    "Platform voice credentials could not be decrypted"
                )
            credentials[provider] = api_key.strip()
        return credentials

    async def set_provider_credential(
        self,
        provider: PlatformVoiceProvider,
        api_key: str,
        updated_by: UUID,
    ) -> PlatformVoiceProviderCredentialStatus:
        """Encrypt and upsert one provider key without changing other providers."""
        cleaned = api_key.strip()
        if not cleaned:
            raise ValueError("API key must not be blank")
        try:
            credential_encrypted = encrypt_data({"api_key": cleaned})
            await asyncio.to_thread(
                lambda: self.supabase.table(self.TABLE)
                .upsert(
                    {
                        "provider": provider.value,
                        "credential_encrypted": credential_encrypted,
                        "updated_by": str(updated_by),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    on_conflict="provider",
                )
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 - provider key is never logged
            logger.error(
                "Could not save platform voice credential provider=%s "
                "(error_type=%s)",
                provider.value,
                type(exc).__name__,
            )
            raise PlatformVoiceCredentialError(
                "Platform voice credential could not be saved"
            ) from None
        return PlatformVoiceProviderCredentialStatus(
            configured=True,
            environment_fallback_configured=bool(
                os.getenv(PLATFORM_VOICE_PROVIDER_ENV[provider.value], "").strip()
            ),
            updated_at=datetime.now(timezone.utc),
        )

    async def delete_provider_credential(self, provider: PlatformVoiceProvider) -> None:
        """Remove one stored key so runtime can use its environment fallback."""
        try:
            await asyncio.to_thread(
                lambda: self.supabase.table(self.TABLE)
                .delete()
                .eq("provider", provider.value)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 - provider key is never logged
            logger.error(
                "Could not remove platform voice credential provider=%s "
                "(error_type=%s)",
                provider.value,
                type(exc).__name__,
            )
            raise PlatformVoiceCredentialError(
                "Platform voice credential could not be removed"
            ) from None


platform_voice_provider_credential_service = PlatformVoiceProviderCredentialService()


__all__ = [
    "PLATFORM_VOICE_PROVIDER_ENV",
    "PlatformVoiceCredentialError",
    "PlatformVoiceProvider",
    "PlatformVoiceProviderCredentialService",
    "PlatformVoiceProviderCredentialStatus",
    "PlatformVoiceProviderCredentialUpdate",
    "PlatformVoiceProviderCredentialsResponse",
    "platform_voice_provider_credential_service",
]
