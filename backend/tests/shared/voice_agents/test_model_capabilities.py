"""Tests for provider-backed voice model capability validation."""

import httpx
import pytest

from shared.voice_agents.model_capabilities import (
    ModelCapabilityService,
    OpenRouterModelCatalog,
    ReasoningSupport,
)
from shared.voice_agents.speech_config import parse_speech_config


def _pipeline_config(*, provider: str = "openrouter", model: str | None = None):
    return parse_speech_config(
        {
            "engine_mode": "pipeline",
            "stt": {"provider": "deepgram"},
            "llm": {"provider": provider, "model": model},
            "tts": {"provider": "cartesia"},
        }
    )


@pytest.mark.asyncio
async def test_openrouter_catalog_detects_mandatory_reasoning(monkeypatch):
    """OpenRouter metadata marks a model requiring reasoning as required."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "z-ai/glm-5.3-flash",
                        "reasoning": {"mandatory": True},
                    }
                ]
            },
            request=request,
        )

    catalog = OpenRouterModelCatalog(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    result = await catalog.lookup("z-ai/glm-5.3-flash")

    assert result.error_code is None
    assert result.capabilities is not None
    assert result.capabilities.reasoning_support == ReasoningSupport.REQUIRED
    assert requests[0].headers["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_openrouter_catalog_detects_non_reasoning_model(monkeypatch):
    """A model without reasoning metadata is compatible with disabled reasoning."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"id": "openai/gpt-4.1", "supported_parameters": []}]},
            request=request,
        )

    catalog = OpenRouterModelCatalog(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    result = await catalog.lookup("openai/gpt-4.1")

    assert result.capabilities is not None
    assert result.capabilities.reasoning_support == ReasoningSupport.NONE


@pytest.mark.asyncio
async def test_openrouter_catalog_caches_catalog_response(monkeypatch):
    """Repeated checks for one model do not make repeated catalog requests."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={"data": [{"id": "openai/gpt-4.1"}]},
            request=request,
        )

    catalog = OpenRouterModelCatalog(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    await catalog.lookup("openai/gpt-4.1")
    await catalog.lookup("openai/gpt-4.1")

    assert request_count == 1


@pytest.mark.asyncio
async def test_openrouter_catalog_reports_missing_credentials(monkeypatch):
    """Capability checks fail safely when the platform catalog key is absent."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    catalog = OpenRouterModelCatalog()

    result = await catalog.lookup("openai/gpt-4.1")

    assert result.capabilities is None
    assert result.error_code == "provider_credentials_missing"


@pytest.mark.asyncio
async def test_openrouter_catalog_reports_model_not_found(monkeypatch):
    """An unknown model cannot pass a live configuration check."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"id": "openai/gpt-4.1"}]},
            request=request,
        )

    catalog = OpenRouterModelCatalog(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    result = await catalog.lookup("does-not-exist/model")

    assert result.capabilities is None
    assert result.error_code == "model_not_found"


@pytest.mark.asyncio
async def test_openrouter_catalog_reports_provider_outage(monkeypatch):
    """Provider outages return a safe retryable validation error."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    catalog = OpenRouterModelCatalog(
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    result = await catalog.lookup("openai/gpt-4.1")

    assert result.capabilities is None
    assert result.error_code == "provider_catalog_unavailable"


@pytest.mark.asyncio
async def test_model_capability_service_rejects_mandatory_reasoning():
    """The provider-neutral service turns the catalog fact into an admin error."""

    class Resolver:
        async def lookup(self, model: str):
            from shared.voice_agents.model_capabilities import (
                ModelCapabilities,
                ModelCapabilityLookup,
            )

            return ModelCapabilityLookup(
                capabilities=ModelCapabilities(
                    provider="openrouter",
                    model=model,
                    model_exists=True,
                    reasoning_support=ReasoningSupport.REQUIRED,
                )
            )

    service = ModelCapabilityService({"openrouter": Resolver()})
    result = await service.validate_speech_config(
        _pipeline_config(model="z-ai/glm-5.3-flash")
    )

    assert result.valid is False
    assert result.code == "model_reasoning_required"
    assert "disable" in result.message.lower()


@pytest.mark.asyncio
async def test_model_capability_service_skips_unimplemented_provider():
    """Adding OpenRouter checks does not block providers without an adapter."""
    service = ModelCapabilityService({})

    result = await service.validate_speech_config(
        _pipeline_config(provider="cerebras", model="llama-3.3-70b")
    )

    assert result.valid is True
    assert result.checked is False
