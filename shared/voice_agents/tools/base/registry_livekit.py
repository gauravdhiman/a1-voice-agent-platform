"""
LiveKit Native Tool Registry

This registry extracts function schemas directly from decorated function objects
without parsing source files or using AST.

This is the preferred approach over AST-based registry.
"""

import importlib
import inspect
import logging
import pkgutil
from typing import Any, Callable, Dict, List, Optional, Type

from livekit.agents import RunContext

from shared.voice_agents.tool_models import PlatformToolCreate
from shared.voice_agents.tool_service import ToolService
from shared.voice_agents.tools.base.base_tool import BaseTool

logger = logging.getLogger(__name__)


class LiveKitToolRegistry:
    """
    Tool registry that uses LiveKit's native @function_tool decorator
    to extract schemas directly from function objects.

    No AST parsing or source file reading needed.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._functions: Dict[str, List[Callable]] = {}

    def register_tools_from_package(self, package_path: str) -> None:
        """
        Dynamically discover and register all BaseTool subclasses in a package.
        Extracts @function_tool decorated methods by inspecting function objects.
        """
        logger.info(f"LiveKit Registry: Registering tools from package: {package_path}")
        package = importlib.import_module(package_path)
        for loader, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + "."
        ):
            module = importlib.import_module(module_name)
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

                    # Extract @function_tool decorated methods
                    function_methods = self._extract_function_methods(tool_instance)
                    self._functions[tool_name] = function_methods

                    logger.info(
                        f"LiveKit Registry: Registered tool class: {tool_name} with {len(function_methods)} functions"  # noqa: E501
                    )

    def _extract_function_methods(self, tool_instance: BaseTool) -> List[Callable]:
        """
        Extract all @function_tool decorated methods from a tool instance.
        Uses LiveKit's function_tool decorator metadata on function objects.
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

            # Check if function has LiveKit function_tool decorator
            # LiveKit's @function_tool decorator adds attributes to function
            if self._is_livekit_function_tool(func):
                methods.append(func)
                logger.debug(f"LiveKit Registry: Found @function_tool method: {name}")

        return methods

    def _is_livekit_function_tool(self, func: Callable) -> bool:
        """
        Check if a function is decorated with LiveKit's @function_tool.
        LiveKit adds specific attributes to decorated functions.
        """
        # Debug: Log all attributes
        attrs = [attr for attr in dir(func) if not attr.startswith("_")]
        logger.debug(
            f"LiveKit Registry: Function {func.__name__} has attributes: {attrs[:10]}"
        )

        # LiveKit's function_tool decorator sets these attributes
        livekit_attributes = ["function_tool", "type", "description", "parameters"]

        # Check if any LiveKit-specific attribute is present
        for attr in livekit_attributes:
            if hasattr(func, attr):
                logger.debug(
                    f"LiveKit Registry: Function {func.__name__} has attribute {attr}"
                )
                return True

        # Fallback: Check if it's an async method (most tool functions are async)
        if inspect.iscoroutinefunction(func):
            # If it has RunContext as any parameter, it's likely a tool function
            sig = inspect.signature(func)
            params = list(sig.parameters.values())
            if params:
                # Check if ANY parameter is typed as RunContext
                for param in params:
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation is RunContext:
                            logger.debug(
                                f"LiveKit Registry: Function {func.__name__} looks like a tool function (has a parameter of type RunContext)"  # noqa: E501
                            )
                            return True

        return False

    async def sync_with_db(self, tool_service: ToolService) -> None:
        """
        Sync registered tools with the platform_tools table.
        Extracts schemas from LiveKit function_tool decorators.
        """
        logger.info(
            f"LiveKit Registry: Starting sync of {len(self._tools)} registered tools to database"  # noqa: E501
        )

        for name, tool_class in self._tools.items():
            tool_instance = tool_class()
            metadata = tool_instance.metadata

            logger.info(f"LiveKit Registry: Syncing tool: {name}")

            # Extract function schemas from LiveKit decorated methods
            function_methods = self._functions.get(name, [])
            function_schemas = []

            for func in function_methods:
                schema = self._extract_schema_from_function(func)
                if schema:
                    function_schemas.append(schema)
                    logger.info(
                        f"LiveKit Registry: Extracted schema for function: {schema['name']}"  # noqa: E501
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
                )

                # Upsert to database (create or update by name)
                result, error = await tool_service.upsert_platform_tool(tool_data)
                if error:
                    logger.error(
                        f"LiveKit Registry: Failed to upsert tool {name}: {error}"
                    )
                else:
                    logger.info(
                        f"LiveKit Registry: Successfully upserted tool {name} with {len(function_schemas)} functions: {[s['name'] for s in function_schemas]}"  # noqa: E501
                    )
            else:
                logger.warning(
                    f"LiveKit Registry: No function schemas found for tool {name}, skipping"  # noqa: E501
                )

    def _extract_schema_from_function(self, func: Callable) -> Optional[Dict[str, Any]]:
        """
        Extract function schema from a LiveKit @function_tool decorated function.
        Reads schema directly from function attributes if available.
        """
        try:
            # Try to get schema from LiveKit's attributes
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
            parameters = {"type": "object", "properties": {}, "required": []}

            for param_name, param in sig.parameters.items():
                # Skip 'self' parameter and RunContext parameters
                if param_name == "self":
                    continue

                # Check if parameter is typed as RunContext
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation is RunContext:
                        continue

                param_info = {"type": "string"}

                # Try to get type annotation
                if param.annotation != inspect.Parameter.empty:
                    annotation = param.annotation
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
                f"LiveKit Registry: Failed to extract schema from function {func.__name__}: {e}"  # noqa: E501
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
livekit_tool_registry = LiveKitToolRegistry()
