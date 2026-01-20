"""Tests for tool wrapper function in worker.py."""
import inspect
from typing import Any

import pytest

from worker import _create_tool_wrapper


class DummyTool:
    """Dummy tool class for testing."""

    async def simple_method(
        self, context: Any, param1: str, param2: int = 42
    ) -> dict[str, Any]:
        """Simple method with required and optional params."""
        return {"param1": param1, "param2": param2}

    async def complex_method(
        self,
        context: Any,
        name: str,
        age: int,
        email: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Method with complex types."""
        return {
            "name": name,
            "age": age,
            "email": email,
            "tags": tags or [],
        }

    async def no_default_method(
        self, context: Any, required_param: str, another_required: int
    ) -> dict[str, Any]:
        """Method with no default values."""
        return {"required_param": required_param, "another_required": another_required}

    async def string_default_method(
        self, context: Any, param: str = "default_value"
    ) -> dict[str, Any]:
        """Method with string default value."""
        return {"param": param}

    async def none_default_method(
        self, context: Any, optional_param: str | None = None
    ) -> dict[str, Any]:
        """Method with None as default value."""
        return {"optional_param": optional_param}


class TestToolWrapperCreation:
    """Test cases for _create_tool_wrapper function."""

    def test_wrapper_creation_simple_method(self):
        """Test wrapper creation for simple method."""
        tool = DummyTool()
        bound_method = tool.simple_method

        # Get original function signature
        original_func = DummyTool.simple_method
        sig = inspect.signature(original_func)

        # Get type hints
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        # Create wrapper
        wrapper = _create_tool_wrapper(
            bound_method, "simple_method", sig, type_hints
        )

        # Verify wrapper is callable
        assert callable(wrapper)
        assert wrapper.__name__ == "simple_method"

        # Verify type hints are preserved
        assert "context" in wrapper.__annotations__
        assert "param1" in wrapper.__annotations__
        assert "param2" in wrapper.__annotations__

    def test_wrapper_signature_with_defaults(self):
        """Test wrapper preserves default values."""
        tool = DummyTool()
        bound_method = tool.simple_method

        original_func = DummyTool.simple_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "simple_method", sig, type_hints
        )

        # Check signature has default for param2
        wrapper_sig = inspect.signature(wrapper)
        param2 = wrapper_sig.parameters["param2"]
        assert param2.default == 42

    def test_wrapper_signature_no_defaults(self):
        """Test wrapper signature when no defaults exist."""
        tool = DummyTool()
        bound_method = tool.no_default_method

        original_func = DummyTool.no_default_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "no_default_method", sig, type_hints
        )

        # Check signature has no defaults
        wrapper_sig = inspect.signature(wrapper)
        required_param = wrapper_sig.parameters["required_param"]
        another_required = wrapper_sig.parameters["another_required"]
        assert required_param.default == inspect.Parameter.empty
        assert another_required.default == inspect.Parameter.empty

    def test_wrapper_complex_types(self):
        """Test wrapper handles complex type hints."""
        tool = DummyTool()
        bound_method = tool.complex_method

        original_func = DummyTool.complex_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "complex_method", sig, type_hints
        )

        # Verify type hints for complex types
        wrapper_sig = inspect.signature(wrapper)
        assert "name" in wrapper_sig.parameters
        assert "age" in wrapper_sig.parameters
        assert "email" in wrapper_sig.parameters
        assert "tags" in wrapper_sig.parameters

    @pytest.mark.asyncio
    async def test_wrapper_delegation(self, mock_run_context):
        """Test wrapper correctly delegates to bound method."""
        tool = DummyTool()
        bound_method = tool.simple_method

        original_func = DummyTool.simple_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "simple_method", sig, type_hints
        )

        # Call wrapper
        result = await wrapper(mock_run_context, param1="test_value")

        # Verify delegation worked
        assert result == {"param1": "test_value", "param2": 42}

    @pytest.mark.asyncio
    async def test_wrapper_with_optional_params(self, mock_run_context):
        """Test wrapper handles optional parameters correctly."""
        tool = DummyTool()
        bound_method = tool.complex_method

        original_func = DummyTool.complex_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "complex_method", sig, type_hints
        )

        # Call with only required params
        result = await wrapper(
            mock_run_context, name="John", age=30
        )

        assert result == {"name": "John", "age": 30, "email": None, "tags": []}

        # Call with all params
        result = await wrapper(
            mock_run_context,
            name="Jane",
            age=25,
            email="jane@example.com",
            tags=["tag1", "tag2"],
        )

        assert result == {
            "name": "Jane",
            "age": 25,
            "email": "jane@example.com",
            "tags": ["tag1", "tag2"],
        }

    @pytest.mark.asyncio
    async def test_wrapper_with_string_default(self, mock_run_context):
        """Test wrapper handles string default values correctly."""
        tool = DummyTool()
        bound_method = tool.string_default_method

        original_func = DummyTool.string_default_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "string_default_method", sig, type_hints
        )

        # Call with default
        result = await wrapper(mock_run_context)
        assert result == {"param": "default_value"}

        # Call with custom value
        result = await wrapper(mock_run_context, param="custom")
        assert result == {"param": "custom"}

    @pytest.mark.asyncio
    async def test_wrapper_with_none_default(self, mock_run_context):
        """Test wrapper handles None default values correctly."""
        tool = DummyTool()
        bound_method = tool.none_default_method

        original_func = DummyTool.none_default_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "none_default_method", sig, type_hints
        )

        # Call with default (None)
        result = await wrapper(mock_run_context)
        assert result == {"optional_param": None}

        # Call with value
        result = await wrapper(mock_run_context, optional_param="test")
        assert result == {"optional_param": "test"}

    def test_wrapper_metadata(self):
        """Test wrapper preserves metadata."""
        tool = DummyTool()
        bound_method = tool.simple_method

        original_func = DummyTool.simple_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "simple_method", sig, type_hints
        )

        # Verify metadata
        assert wrapper.__name__ == "simple_method"
        assert wrapper.__qualname__ == "simple_method"
        # Note: Wrapper has its own docstring, not the original
        assert "simple_method" in wrapper.__doc__

    def test_wrapper_excludes_self(self):
        """Test wrapper excludes 'self' from parameters."""
        tool = DummyTool()
        bound_method = tool.simple_method

        original_func = DummyTool.simple_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "simple_method", sig, type_hints
        )

        # Verify 'self' is not in wrapper signature
        wrapper_sig = inspect.signature(wrapper)
        assert "self" not in wrapper_sig.parameters

    def test_wrapper_type_hint_preservation(self):
        """Test wrapper preserves type hints correctly."""
        tool = DummyTool()
        bound_method = tool.complex_method

        original_func = DummyTool.complex_method
        sig = inspect.signature(original_func)
        type_hints = {
            k: v
            for k, v in original_func.__annotations__.items()
            if k != "self"
        }

        wrapper = _create_tool_wrapper(
            bound_method, "complex_method", sig, type_hints
        )

        # Verify type hints
        assert wrapper.__annotations__["name"] == str
        assert wrapper.__annotations__["age"] == int
        # Note: complex types may be converted to strings
        assert "email" in wrapper.__annotations__
        assert "tags" in wrapper.__annotations__
