"""Voice templates module."""

from src.voice_templates.routes import (
    platform_router as platform_voice_templates_router,
)
from src.voice_templates.routes import router as voice_templates_router

__all__ = ["platform_voice_templates_router", "voice_templates_router"]
