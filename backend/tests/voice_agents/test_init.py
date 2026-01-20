"""
Tests for voice_agents module initialization.
"""
import pytest

from src.voice_agents import agent_router, tool_router, voice_router


def test_voice_agents_imports():
    """Test that all routers are properly imported."""
    assert agent_router is not None
    assert tool_router is not None
    assert voice_router is not None

    # Check that routers have the expected prefixes
    assert agent_router.prefix == "/api/v1/agents"
    assert tool_router.prefix == "/api/v1/tools"
    assert voice_router.prefix == "/api/v1/voice"