"""API-boundary validation tests for code-owned native tool configuration."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from shared.voice_agents.tool_models import PlatformTool, ToolSource


def _resend_platform_tool() -> PlatformTool:
    """Build the minimum catalog row needed by the native config guard."""
    return PlatformTool(
        id=uuid4(),
        name="Resend_email",
        description="Test Resend tool",
        tool_source=ToolSource.LEGACY,
        is_active=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


class TestNativeToolConfigValidation:
    """Ensure invalid JSONB config is rejected before it reaches persistence."""

    def test_valid_resend_routes_are_accepted(self) -> None:
        """A normalized route map passes the API boundary validator."""
        from src.voice_agents.tool_routes import _validate_native_tool_config

        _validate_native_tool_config(
            _resend_platform_tool(),
            {
                "routes": [
                    {
                        "route_id": "customer_support",
                        "label": "Customer Support",
                        "recipients": ["support@example.com"],
                    }
                ]
            },
        )

    def test_invalid_resend_routes_return_safe_http_error(self) -> None:
        """Validation errors do not expose configured recipient addresses."""
        from src.voice_agents.tool_routes import _validate_native_tool_config

        with pytest.raises(HTTPException) as exc_info:
            _validate_native_tool_config(
                _resend_platform_tool(),
                {
                    "routes": [
                        {
                            "route_id": "support",
                            "label": "Support",
                            "recipients": ["not-an-email"],
                        }
                    ]
                },
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid configuration for tool 'Resend_email'."
        assert "not-an-email" not in str(exc_info.value.detail)

    def test_resend_legacy_api_key_is_removed_from_public_config(self) -> None:
        """Resend API keys cannot be carried in the agent attachment JSONB."""
        from src.voice_agents.tool_routes import _validate_native_tool_config

        normalized = _validate_native_tool_config(
            _resend_platform_tool(),
            {
                "api_key": "re_legacy_agent_key",
                "from_email": "noreply@example.com",
                "from_name": "Example Business",
                "routes": [
                    {
                        "route_id": "support",
                        "label": "Support",
                        "recipients": ["support@example.com"],
                    }
                ],
            },
        )

        assert normalized == {
            "from_email": "noreply@example.com",
            "from_name": "Example Business",
            "routes": [
                {
                    "route_id": "support",
                    "label": "Support",
                    "recipients": ["support@example.com"],
                }
            ],
        }
