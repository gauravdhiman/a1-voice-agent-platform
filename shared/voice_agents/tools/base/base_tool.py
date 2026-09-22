from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel

from .auth_config import BaseAuthConfig


class BaseConfig(BaseModel):
    pass


class BaseSensitiveConfig(BaseModel):
    pass


class ToolMetadata(BaseModel):
    name: str
    description: str
    config_schema: dict[str, Any]
    requires_auth: bool = False
    auth_type: Optional[str] = None
    auth_config: Optional[dict[str, Any]] = None


class BaseTool(ABC):
    Config: type[BaseConfig] = BaseConfig
    AuthConfig: type[BaseAuthConfig] = BaseAuthConfig
    SensitiveConfig: type[BaseSensitiveConfig] = BaseSensitiveConfig

    def __init__(
        self,
        config: Optional[BaseConfig | dict[str, Any]] = None,
        sensitive_config: Optional[BaseSensitiveConfig | dict[str, Any]] = None,
    ) -> None:
        if config is None:
            self.config = self.Config()
        elif isinstance(config, dict):
            self.config = self.Config(**config)
        elif isinstance(config, BaseModel):
            self.config = config
        else:
            raise ValueError(f"config must be dict or BaseModel, got {type(config)}")

        if sensitive_config is None:
            self.sensitive_config = self.SensitiveConfig()
        elif isinstance(sensitive_config, dict):
            self.sensitive_config = self.SensitiveConfig(**sensitive_config)
        elif isinstance(sensitive_config, BaseModel):
            self.sensitive_config = sensitive_config
        else:
            raise ValueError(
                f"sensitive_config must be dict or BaseModel, got {type(sensitive_config)}"
            )

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        pass

    def check_configuration(self) -> list[str]:
        """List human-readable gaps that stop this tool from working.

        Only attachment configuration is inspected here (never secrets or
        live provider state). Each entry names one missing piece in plain
        words, e.g. ``"spreadsheet destination is not set"``. An empty
        list means the stored configuration is complete; authentication
        is reported separately through token status.

        Returns:
            Human-readable issue strings, empty when complete.
        """
        return []

    def model_function_guidance(self, function_name: str) -> str:
        """Return attachment-specific guidance for a model-facing function.

        Native tools normally expose a stable function schema from their
        method signature.  A configured attachment may add safe, non-secret
        guidance (for example, the business columns an agent may use) without
        exposing provider credentials or changing the function contract.

        Args:
            function_name: The function name being assembled for the model.

        Returns:
            Additional plain-text guidance, or an empty string when the tool
            has no configuration-specific guidance.
        """
        del function_name
        return ""

    def model_function_properties(
        self,
        function_name: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Return an optional attachment-specific function property schema.

        A configured native tool may narrow a generic catalog schema using
        trusted attachment settings. The default preserves the catalog schema
        so existing tools remain unchanged.
        """
        del function_name
        return properties
