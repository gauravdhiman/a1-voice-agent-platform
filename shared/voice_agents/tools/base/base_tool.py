from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel


class ToolMetadata(BaseModel):
    name: str
    description: str
    config_schema: Dict[str, Any]
    requires_auth: bool = False
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        pass
