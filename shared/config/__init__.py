"""
Configuration package for the application.
"""

from .settings import Settings, settings
from .supabase import SupabaseConfig, create_isolated_supabase_client, supabase_config

__all__ = [
    "settings",
    "Settings",
    "supabase_config",
    "SupabaseConfig",
    "create_isolated_supabase_client",
]
