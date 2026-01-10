"""
Configuration package for the application.
"""

from .settings import Settings, settings
from .supabase import supabase_config

__all__ = ["settings", "Settings", "supabase_config"]
