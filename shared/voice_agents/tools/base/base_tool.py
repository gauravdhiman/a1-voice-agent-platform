from abc import ABC, abstractmethod
from typing import Any, Optional, Union

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
