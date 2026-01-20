"""Tests for DynamicAgent class in worker.py."""
import pytest


class TestDynamicAgent:
    """Test cases for DynamicAgent class."""

    def test_initialization(self):
        """Test DynamicAgent initialization."""
        from worker import DynamicAgent

        instructions = "You are a helpful assistant."
        agent = DynamicAgent(instructions=instructions)
        assert agent.instructions == "You are a helpful assistant."

    def test_initialization_with_empty_instructions(self):
        """Test DynamicAgent initialization with empty instructions."""
        from worker import DynamicAgent

        agent = DynamicAgent(instructions="")
        assert agent.instructions == ""

    def test_initialization_with_long_instructions(self):
        """Test DynamicAgent initialization with long instructions."""
        from worker import DynamicAgent

        long_instructions = "You are a helpful assistant. " * 100
        agent = DynamicAgent(instructions=long_instructions)
        assert agent.instructions == long_instructions

    def test_inherits_from_agent(self):
        """Test DynamicAgent inherits from LiveKit Agent."""
        from worker import DynamicAgent
        from livekit.agents import Agent

        agent = DynamicAgent(instructions="Test")
        assert isinstance(agent, Agent)

    def test_instructions_property(self):
        """Test instructions property is accessible."""
        from worker import DynamicAgent

        agent = DynamicAgent(instructions="Test")
        assert hasattr(agent, 'instructions')
        assert isinstance(agent.instructions, str)

    def test_update_tools_method_exists(self):
        """Test update_tools method exists (inherited from Agent)."""
        from worker import DynamicAgent

        agent = DynamicAgent(instructions="Test")
        assert hasattr(agent, 'update_tools')
        assert callable(agent.update_tools)
