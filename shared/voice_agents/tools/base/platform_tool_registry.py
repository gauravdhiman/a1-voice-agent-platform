"""
Platform Tool Registry

This registry extracts function schemas directly from decorated function objects
without parsing source files or using AST.

This is the preferred approach over AST-based registry.
"""

import importlib
import inspect
import logging
import pkgutil
from typing import Any, Callable, Dict, List, Optional, Type, get_type_hints

from shared.voice_agents.tool_models import PlatformToolCreate
from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tools.base.base_tool import BaseTool
from shared.voice_agents.tools.base.tool_context import ToolContext

logger = logging.getLogger(__name__)


class PlatformToolRegistry:
    """
    Tool registry that uses decorated BaseTool methods
    to extract schemas directly from function objects.

    No AST parsing or source file reading needed.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._functions: Dict[str, List[Callable]] = {}

    def register_tools_from_package(self, package_path: str) -> None:
        """
        Dynamically discover and register all BaseTool subclasses in a package.
        Extracts public tool methods by inspecting function objects.
        """
        logger.info(
            f"Platform Registry: Registering tools from package: {package_path}"
        )
        package = importlib.import_module(package_path)
        for loader, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001 - skip broken optional tool deps
                # One missing optional dependency (e.g. beautifulsoup4 for Gmail)
                # must not prevent other tools — or the voice session — from loading.
                logger.warning(
                    "Platform Registry: Skipping tool module %s due to import error: %s",
                    module_name,
                    exc,
                )
                continue
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseTool)
                    and obj is not BaseTool
                ):
                    # Create instance first to access metadata property
                    tool_instance = obj()
                    tool_name = tool_instance.metadata.name

                    self._tools[tool_name] = obj

                    # Extract callable tool methods
                    function_methods = self._extract_function_methods(tool_instance)
                    self._functions[tool_name] = function_methods

                    logger.info(
                        f"Platform Registry: Registered tool class: {tool_name} with {len(function_methods)} functions"  # noqa: E501
                    )

    def _extract_function_methods(self, tool_instance: BaseTool) -> List[Callable]:
        """
        Extract public async tool methods that accept ``ToolContext``.
        """
        methods = []

        # Get all callable members of the class
        for name, member in inspect.getmembers(tool_instance):
            # Skip non-callables and private methods
            if not inspect.ismethod(member) and not inspect.isfunction(member):
                continue

            if name.startswith("_"):
                continue

            # Skip property getters
            if name == "metadata":
                continue

            # Get the underlying function for methods
            if inspect.ismethod(member):
                func = member.__func__
            else:
                func = member

            if self._is_tool_method(func):
                methods.append(func)
                logger.debug(f"Platform Registry: Found tool method: {name}")

        return methods

    def _is_tool_method(self, func: Callable) -> bool:
        """Return True when ``func`` looks like a shared ``BaseTool`` method."""
        if inspect.iscoroutinefunction(func):
            sig = inspect.signature(func)
            try:
                type_hints = get_type_hints(func)
            except Exception:  # noqa: BLE001 - optional annotations may not resolve
                type_hints = {}
            for name, param in sig.parameters.items():
                if type_hints.get(name, param.annotation) is ToolContext:
                    return True

        # Legacy decorator metadata (optional third-party markers).
        legacy_attributes = ["function_tool", "type", "description", "parameters"]
        for attr in legacy_attributes:
            if hasattr(func, attr):
                return True

        return False

    async def sync_with_db(self, tool_service: ToolService) -> None:
        """
        Sync registered tools with the platform_tools table.
        Extracts schemas from registered tool method signatures.
        """
        logger.info(
            f"Platform Registry: Starting sync of {len(self._tools)} registered tools to database"  # noqa: E501
        )

        for name, tool_class in self._tools.items():
            tool_instance = tool_class()
            metadata = tool_instance.metadata

            logger.info(f"Platform Registry: Syncing tool: {name}")

            # Extract function schemas from tool methods
            function_methods = self._functions.get(name, [])
            function_schemas = []

            for func in function_methods:
                schema = self._extract_schema_from_function(func)
                if schema:
                    function_schemas.append(schema)
                    logger.info(
                        f"Platform Registry: Extracted schema for function: {schema['name']}"  # noqa: E501
                    )

            if function_schemas:
                tool_data = PlatformToolCreate(
                    name=metadata.name,
                    description=metadata.description,
                    config_schema=metadata.config_schema,
                    tool_functions_schema={"functions": function_schemas},
                    requires_auth=metadata.requires_auth,
                    auth_type=metadata.auth_type,
                    auth_config=metadata.auth_config,
                    is_active=True,
                    # In-tree native tools are code-owned catalog entries,
                    # not draft MCP servers. Keep them visible to org admins
                    # whenever the registry materializes or refreshes them.
                    is_published=True,
                )

                # Upsert to database (create or update by name)
                result, error = await tool_service.upsert_platform_tool(tool_data)
                if error:
                    logger.error(
                        f"Platform Registry: Failed to upsert tool {name}: {error}"
                    )
                else:
                    logger.info(
                        f"Platform Registry: Successfully upserted tool {name} with {len(function_schemas)} functions: {[s['name'] for s in function_schemas]}"  # noqa: E501
                    )
            else:
                logger.warning(
                    f"Platform Registry: No function schemas found for tool {name}, skipping"  # noqa: E501
                )

    def _extract_schema_from_function(self, func: Callable) -> Optional[Dict[str, Any]]:
        """
        Extract function schema from a tool method docstring and signature.
        """
        try:
            # Optional legacy decorator attributes
            if hasattr(func, "description") and hasattr(func, "parameters"):
                raw_description = getattr(func, "description", "")
                description = self._extract_description_section(raw_description)
                schema = {
                    "type": "function",
                    "name": self._format_function_name(func.__name__),
                    "description": description,
                }

                if hasattr(func, "parameters"):
                    schema["parameters"] = getattr(func, "parameters")

                return schema

            # Fallback: Extract from docstring and signature
            docstring = inspect.getdoc(func)
            if docstring:
                description = self._extract_description_section(docstring)
            else:
                description = ""

            sig = inspect.signature(func)
            try:
                type_hints = get_type_hints(func)
            except Exception:  # noqa: BLE001 - preserve legacy best effort
                type_hints = {}
            parameters = {"type": "object", "properties": {}, "required": []}

            for param_name, param in sig.parameters.items():
                # Skip 'self' and transport context parameters
                if param_name == "self":
                    continue

                annotation = type_hints.get(param_name, param.annotation)
                if annotation != inspect.Parameter.empty:
                    if annotation is ToolContext:
                        continue

                param_info = {"type": "string"}

                # Try to get type annotation
                if annotation != inspect.Parameter.empty:
                    if annotation == int:
                        param_info["type"] = "integer"
                    elif annotation == float:
                        param_info["type"] = "number"
                    elif annotation == bool:
                        param_info["type"] = "boolean"
                    elif annotation == list:
                        param_info["type"] = "array"

                parameters["properties"][param_name] = param_info

                if param.default == inspect.Parameter.empty:
                    parameters["required"].append(param_name)

            schema = {
                "type": "function",
                "name": self._format_function_name(func.__name__),
                "description": description,
            }

            if parameters["properties"]:
                schema["parameters"] = parameters

            return schema

        except Exception as e:
            logger.error(
                f"Platform Registry: Failed to extract schema from function {func.__name__}: {e}"  # noqa: E501
            )
            return None

    def get_tool_class(self, name: str) -> Type[BaseTool] | None:
        return self._tools.get(name)

    def get_tool_functions(self, tool_name: str) -> List[Callable]:
        """
        Get list of function objects for a specific tool.
        Returns actual decorated function objects.
        """
        return self._functions.get(tool_name, [])

    def get_tool_names(self) -> List[str]:
        """
        Get list of all registered tool names.

        Returns:
            List of tool names registered in this registry.
        """
        return list(self._tools.keys())

    def _extract_description_section(self, docstring: str) -> str:
        """
        Extract only the Description: section from docstring for UI display.

        This method extracts the concise Description: section (1-3 lines) for
        display in the UI. The full docstring (including Instructions, Args, Returns)
        is preserved for AI agent use.

        Args:
            docstring: Full docstring from function

        Returns:
            Description text (1-3 lines) for UI display
        """
        if not docstring:
            return ""

        lines = docstring.split("\n")
        description_lines = []
        in_description_section = False
        found_description = False

        for line in lines:
            stripped_line = line.strip()

            # Check if we've reached the Description section
            if stripped_line.lower().startswith("description:"):
                in_description_section = True
                found_description = True
                continue

            # If we're in the description section and hit another section, stop
            if in_description_section and stripped_line.lower().startswith(
                ("instructions:", "args:", "returns:", "raises:", "note:", "example:")
            ):
                break

            # Collect lines while in description section
            if in_description_section and line:
                description_lines.append(line)

        # If no Description section found, fall back to extracting text before Args
        if not found_description:
            return self._extract_before_first_section(docstring)

        # Join lines and clean up
        description = "\n".join(description_lines).strip()
        return description

    def _extract_before_first_section(self, docstring: str) -> str:
        """
        Extract text before the first section header (Description, Instructions, Args, etc.).

        This is a fallback method for backward compatibility with old docstrings that
        don't have explicit Description: section.

        Args:
            docstring: Full docstring from function

        Returns:
            Text before first section header
        """
        if not docstring:
            return ""

        lines = docstring.split("\n")
        description_lines = []

        for line in lines:
            stripped_line = line.strip()

            # Check for any section header
            if stripped_line.lower().startswith(
                (
                    "description:",
                    "instructions:",
                    "args:",
                    "returns:",
                    "raises:",
                    "note:",
                    "example:",
                )
            ):
                break

            description_lines.append(line)

        # Join lines and strip
        return "\n".join(description_lines).strip()

    def _format_function_name(self, name: str) -> str:
        """
        Convert snake_case function name to readable Title Case.

        Replaces underscores (including multiple consecutive ones) with a single space,
        then capitalizes the first letter of each word.

        Args:
            name: Function name in snake_case (e.g., "get_latest_emails")

        Returns:
            Formatted name with spaces and title case (e.g., "Get Latest Emails")

        Example:
            >>> _format_function_name("get_latest_emails")
            "Get Latest Emails"
            >>> _format_function_name("send_email_reply")
            "Send Email Reply"
            >>> _format_function_name("apply_label")
            "Apply Label"
        """
        # Replace multiple consecutive underscores with a single space
        # Then replace single underscores with space
        words = name.replace("__", " ").replace("_", " ").split()

        # Capitalize first letter of each word
        formatted_words = [word.capitalize() for word in words]

        return " ".join(formatted_words)


# Create global instance
platform_tool_registry = PlatformToolRegistry()
