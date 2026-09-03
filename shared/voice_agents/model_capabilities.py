"""Provider-backed capability checks for voice-engine configurations.

Preset validation is intentionally provider-specific behind a small common
contract. The voice runtime currently disables reasoning for OpenRouter LLM
stages so pipeline latency stays predictable. OpenRouter exposes model
metadata through its catalog endpoint, which lets platform admins catch a
model that makes reasoning mandatory before publishing a preset.

Unknown providers are skipped until they have a resolver. This keeps adding a
provider an additive change instead of making the generic preset service know
every provider's catalog API.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Protocol

import httpx

from shared.voice_agents.key_resolver import normalize_stage_provider
from shared.voice_agents.speech_config import PipelineSpeechConfig, SpeechConfig

logger = logging.getLogger(__name__)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_DEFAULT_MODEL = "openai/gpt-4.1"
OPENROUTER_CATALOG_TIMEOUT_SECONDS = 10.0
DEFAULT_MODEL_CAPABILITY_CACHE_TTL_SECONDS = 600.0


class ReasoningSupport(str):
    """How a model's API treats reasoning configuration."""

    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ModelCapabilities:
    """Capabilities returned by a provider's model catalog."""

    provider: str
    model: str
    model_exists: bool
    reasoning_support: str = ReasoningSupport.UNKNOWN
    supports_tools: Optional[bool] = None


@dataclass(frozen=True)
class ModelCapabilityLookup:
    """Result of looking up one model without leaking provider diagnostics."""

    capabilities: Optional[ModelCapabilities] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ModelCapabilityCheck:
    """Safe validation result suitable for an admin-facing API error."""

    valid: bool
    checked: bool
    code: Optional[str] = None
    message: Optional[str] = None
    capabilities: Optional[ModelCapabilities] = None

    @classmethod
    def skipped(cls) -> "ModelCapabilityCheck":
        """Return a valid result for a provider without a resolver yet."""
        return cls(valid=True, checked=False)

    @classmethod
    def success(cls, capabilities: ModelCapabilities) -> "ModelCapabilityCheck":
        """Return a successful, catalog-backed check."""
        return cls(valid=True, checked=True, capabilities=capabilities)

    @classmethod
    def failure(cls, code: str, message: str) -> "ModelCapabilityCheck":
        """Return a failed check with a stable code and safe explanation."""
        return cls(valid=False, checked=True, code=code, message=message)


class ModelCapabilityResolver(Protocol):
    """Provider adapter contract used by :class:`ModelCapabilityService`."""

    async def lookup(self, model: str) -> ModelCapabilityLookup:
        """Resolve model capabilities from the provider catalog."""


ClientFactory = Callable[[], httpx.AsyncClient]


class OpenRouterModelCatalog:
    """Resolve OpenRouter model metadata with a short in-process cache."""

    def __init__(
        self,
        *,
        client_factory: Optional[ClientFactory] = None,
        cache_ttl_seconds: float = DEFAULT_MODEL_CAPABILITY_CACHE_TTL_SECONDS,
    ) -> None:
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=OPENROUTER_CATALOG_TIMEOUT_SECONDS)
        )
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, ModelCapabilityLookup]] = {}

    async def lookup(self, model: str) -> ModelCapabilityLookup:
        """Look up one OpenRouter model and cache successful catalog reads.

        The API key is read only on the server. It is never included in a
        returned object, an exception message, or a persisted validation error.
        """
        now = time.monotonic()
        cached = self._cache.get(model)
        if cached and cached[0] > now:
            return cached[1]

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return ModelCapabilityLookup(
                error_code="provider_credentials_missing",
                error_message=(
                    "OpenRouter model validation requires the platform "
                    "OPENROUTER_API_KEY."
                ),
            )

        try:
            async with self._client_factory() as client:
                response = await client.get(
                    OPENROUTER_MODELS_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code in (401, 403):
                    return ModelCapabilityLookup(
                        error_code="provider_authentication_error",
                        error_message=(
                            "The platform OpenRouter credentials were rejected. "
                            "Verify OPENROUTER_API_KEY."
                        ),
                    )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError:
            logger.warning("OpenRouter model catalog returned an HTTP error")
            return ModelCapabilityLookup(
                error_code="provider_catalog_unavailable",
                error_message=(
                    "The OpenRouter model catalog could not be reached. "
                    "Try again before publishing the preset."
                ),
            )
        except (httpx.HTTPError, ValueError):
            logger.warning("OpenRouter model catalog lookup failed", exc_info=True)
            return ModelCapabilityLookup(
                error_code="provider_catalog_unavailable",
                error_message=(
                    "The OpenRouter model catalog could not be verified. "
                    "Try again before publishing the preset."
                ),
            )

        records = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(records, list):
            logger.warning("OpenRouter model catalog response had an invalid shape")
            return ModelCapabilityLookup(
                error_code="provider_catalog_unavailable",
                error_message=(
                    "The OpenRouter model catalog returned an invalid response. "
                    "Try again before publishing the preset."
                ),
            )

        record = next(
            (
                item
                for item in records
                if isinstance(item, dict) and str(item.get("id", "")) == model
            ),
            None,
        )
        if record is None:
            result = ModelCapabilityLookup(
                error_code="model_not_found",
                error_message=(
                    f"OpenRouter model '{model}' was not found in the model "
                    "catalog. Choose an available model."
                ),
            )
            self._cache[model] = (now + self._cache_ttl_seconds, result)
            return result

        capabilities = ModelCapabilities(
            provider="openrouter",
            model=model,
            model_exists=True,
            reasoning_support=_reasoning_support(record),
            supports_tools=_supports_tools(record),
        )
        result = ModelCapabilityLookup(capabilities=capabilities)
        self._cache[model] = (now + self._cache_ttl_seconds, result)
        return result

    def clear_cache(self) -> None:
        """Clear cached catalog responses, primarily for tests and operations."""
        self._cache.clear()


def _reasoning_support(record: Mapping[str, object]) -> str:
    """Translate OpenRouter reasoning metadata to the common support values."""
    reasoning = record.get("reasoning")
    if reasoning is True:
        return ReasoningSupport.OPTIONAL
    if reasoning is False:
        return ReasoningSupport.NONE
    if isinstance(reasoning, Mapping):
        if reasoning.get("mandatory") is True:
            return ReasoningSupport.REQUIRED
        if reasoning.get("mandatory") == "true":
            return ReasoningSupport.REQUIRED
        if reasoning.get("supported_efforts") or "default_enabled" in reasoning:
            return ReasoningSupport.OPTIONAL

    supported_parameters = record.get("supported_parameters")
    if isinstance(supported_parameters, list) and any(
        str(value) in {"reasoning", "reasoning.effort", "include_reasoning"}
        for value in supported_parameters
    ):
        return ReasoningSupport.OPTIONAL
    return ReasoningSupport.NONE


def _supports_tools(record: Mapping[str, object]) -> Optional[bool]:
    """Extract tool support when the catalog explicitly advertises it."""
    supported_parameters = record.get("supported_parameters")
    if not isinstance(supported_parameters, list):
        return None
    parameters = {str(value) for value in supported_parameters}
    if "tools" in parameters or "tool_choice" in parameters:
        return True
    return None


class ModelCapabilityService:
    """Provider-neutral model capability validation for live voice configs."""

    def __init__(
        self,
        resolvers: Optional[Mapping[str, ModelCapabilityResolver]] = None,
    ) -> None:
        self._resolvers = dict(resolvers or {"openrouter": OpenRouterModelCatalog()})

    async def validate_speech_config(
        self, config: SpeechConfig
    ) -> ModelCapabilityCheck:
        """Validate the LLM model capabilities needed by a speech config.

        Realtime configs and pipeline providers without a resolver are allowed
        through. OpenRouter is currently the first provider with a catalog
        adapter because its reasoning metadata directly affects the runtime
        configuration used by voice-ws.
        """
        if not isinstance(config, PipelineSpeechConfig):
            return ModelCapabilityCheck.skipped()

        provider = normalize_stage_provider(config.llm.provider, stage="llm")
        resolver = self._resolvers.get(provider)
        if resolver is None:
            return ModelCapabilityCheck.skipped()

        model = config.llm.model or OPENROUTER_DEFAULT_MODEL
        lookup = await resolver.lookup(model)
        if lookup.error_code:
            return ModelCapabilityCheck.failure(
                lookup.error_code,
                lookup.error_message or "The selected model could not be validated.",
            )
        if lookup.capabilities is None or not lookup.capabilities.model_exists:
            return ModelCapabilityCheck.failure(
                "model_not_found",
                f"The selected {provider} model '{model}' was not found.",
            )
        if lookup.capabilities.reasoning_support == ReasoningSupport.REQUIRED:
            return ModelCapabilityCheck.failure(
                "model_reasoning_required",
                (
                    f"OpenRouter model '{model}' requires reasoning, but voice "
                    "pipelines disable reasoning for predictable latency. "
                    "Choose a model that allows reasoning to be disabled."
                ),
            )
        return ModelCapabilityCheck.success(lookup.capabilities)


model_capability_service = ModelCapabilityService()


__all__ = [
    "DEFAULT_MODEL_CAPABILITY_CACHE_TTL_SECONDS",
    "ModelCapabilities",
    "ModelCapabilityCheck",
    "ModelCapabilityLookup",
    "ModelCapabilityResolver",
    "ModelCapabilityService",
    "OPENROUTER_DEFAULT_MODEL",
    "OPENROUTER_MODELS_URL",
    "OpenRouterModelCatalog",
    "ReasoningSupport",
    "model_capability_service",
]
