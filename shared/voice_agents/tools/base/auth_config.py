"""Authentication configuration models for OAuth tools.

This module provides Pydantic models for different OAuth providers,
ensuring type safety and proper validation for authentication configurations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BaseAuthConfig(BaseModel):
    """Base authentication configuration for OAuth tools.
    
    All OAuth providers must extend this base class and provide
    the required OAuth 2.0 endpoints and scopes.
    """
    provider: str = Field(..., description="OAuth provider name (e.g., 'google', 'microsoft')")
    scopes: List[str] = Field(..., description="List of OAuth scopes required")
    auth_url: str = Field(..., description="OAuth authorization endpoint URL")
    token_url: str = Field(..., description="OAuth token endpoint URL")


class GoogleAuthConfig(BaseAuthConfig):
    """Google OAuth 2.0 configuration.
    
    Google-specific OAuth configuration including the required
    access_type and prompt parameters for refresh tokens.
    """
    provider: str = "google"
    access_type: str = Field(default="offline", description="OAuth access type (offline for refresh tokens)")
    prompt: str = Field(default="consent", description="OAuth prompt (consent for refresh tokens)")


class MicrosoftAuthConfig(BaseAuthConfig):
    """Microsoft OAuth 2.0 configuration.
    
    Microsoft Graph API OAuth configuration.
    """
    provider: str = "microsoft"
    # Microsoft-specific fields can be added here as needed


class GitHubAuthConfig(BaseAuthConfig):
    """GitHub OAuth 2.0 configuration.
    
    GitHub API OAuth configuration.
    """
    provider: str = "github"
    # GitHub-specific fields can be added here as needed


# Registry of auth config classes for provider lookup
AUTH_CONFIG_REGISTRY = {
    "google": GoogleAuthConfig,
    "microsoft": MicrosoftAuthConfig,
    "github": GitHubAuthConfig,
}


def get_auth_config_for_provider(provider: str) -> type[BaseAuthConfig]:
    """Get the appropriate AuthConfig class for a provider.
    
    Args:
        provider: The OAuth provider name
        
    Returns:
        The AuthConfig class for the provider
        
    Raises:
        ValueError: If provider is not supported
    """
    auth_config_class = AUTH_CONFIG_REGISTRY.get(provider.lower())
    if not auth_config_class:
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    return auth_config_class