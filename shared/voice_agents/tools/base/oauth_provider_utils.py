"""OAuth Provider utilities for centralized provider handling.

This module provides a singleton class to manage OAuth provider configurations
and operations in a centralized way, avoiding scattered branching code.
"""

import os
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel


class OAuthCredentials(BaseModel):
    """OAuth credentials for a provider."""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


class OAuthProviderManager:
    """Singleton class for managing OAuth provider configurations and operations.
    
    This class provides a single source of truth for OAuth provider handling,
    ensuring consistent behavior across the application. Uses the singleton pattern
    to maintain a single instance throughout the application lifecycle.
    
    Example:
        ```python
        # Get the singleton instance
        oauth_manager = OAuthProviderManager()
        
        # Use it anywhere in the application
        credentials = oauth_manager.get_credentials("google")
        auth_data = oauth_manager.get_auth_data("google", "auth", code="xyz")
        ```
    
    Attributes:
        _instance: Class-level singleton instance
        _initialized: Instance-level flag to prevent reinitialization
        _providers: Dictionary mapping provider names to their configurations
    """
    
    _instance: Optional['OAuthProviderManager'] = None
    
    def __new__(cls):
        """Create singleton instance if not exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize OAuth provider manager with provider configurations.
        
        Only initializes once due to singleton pattern.
        Stores all provider configurations in a single dictionary for easy lookup.
        """
        if hasattr(self, '_initialized'):
            return
        
        self._providers = {
            "google": {
                "client_id_env": "GOOGLE_OAUTH_TOOL_CLIENT_ID",
                "client_secret_env": "GOOGLE_OAUTH_TOOL_CLIENT_SECRET",
                "redirect_uri_env": "GOOGLE_OAUTH_TOOL_REDIRECT_URI",
                "requires_offline_access": True,
                "prompt_consent": True,
            },
            "microsoft": {
                "client_id_env": "MICROSOFT_OAUTH_TOOL_CLIENT_ID",
                "client_secret_env": "MICROSOFT_OAUTH_TOOL_CLIENT_SECRET",
                "redirect_uri_env": "MICROSOFT_OAUTH_TOOL_REDIRECT_URI",
            },
            "github": {
                "client_id_env": "GITHUB_OAUTH_TOOL_CLIENT_ID",
                "client_secret_env": "GITHUB_OAUTH_TOOL_CLIENT_SECRET",
                "redirect_uri_env": "GITHUB_OAUTH_TOOL_REDIRECT_URI",
            },
        }
        self._initialized = True
    
    def get_credentials(self, provider: str) -> OAuthCredentials:
        """Get OAuth credentials from environment variables for a provider.
        
        Args:
            provider: The OAuth provider name (e.g., 'google', 'microsoft', 'github')
            
        Returns:
            OAuthCredentials: The credentials for provider
            
        Raises:
            ValueError: If provider is not supported
            
        Example:
            ```python
            oauth_manager = OAuthProviderManager()
            credentials = oauth_manager.get_credentials("google")
            ```
        """
        provider = provider.lower()
        
        if provider not in self._providers:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = self._providers[provider]
        
        return OAuthCredentials(
            client_id=os.getenv(config["client_id_env"]),
            client_secret=os.getenv(config["client_secret_env"]),
            redirect_uri=os.getenv(config["redirect_uri_env"]),
        )
    
    def get_auth_data(
        self,
        provider: str,
        flow: str,
        code: str = "",
        refresh_token: str = "",
        redirect_uri: str = "",
    ) -> Dict[str, str]:
        """Get OAuth data dictionary for token exchange or refresh.

        This method automatically includes client_id and client_secret from environment variables.

        Args:
            provider: The OAuth provider name
            flow: The OAuth flow type ('auth' or 'refresh')
            code: Authorization code from OAuth callback (for 'auth' flow)
            refresh_token: The refresh token (for 'refresh' flow)
            redirect_uri: Redirect URI for provider (for 'auth' flow)

        Returns:
            Dictionary with OAuth data for token exchange or refresh, including client credentials

        Raises:
            ValueError: If provider is not supported

        Example:
            ```python
            # Authorization code flow
            auth_data = oauth_manager.get_auth_data("google", "auth", code="xyz", redirect_uri="http://localhost/callback")

            # Token refresh flow
            auth_data = oauth_manager.get_auth_data("google", "refresh", refresh_token="abc")
            ```
        """
        provider = provider.lower()

        if provider not in self._providers:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        # Get credentials for this provider
        credentials = self.get_credentials(provider)

        config = self._providers[provider]

        if flow == "refresh":
            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": credentials.client_id,
            }
            # Some providers require client_secret for refresh
            if credentials.client_secret:
                data["client_secret"] = credentials.client_secret
        else:  # flow == "auth"
            data = {
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
            }

            # Add provider-specific parameters for authorization flow
            if config.get("requires_offline_access"):
                data["access_type"] = "offline"
            if config.get("prompt_consent"):
                data["prompt"] = "consent"

        return data
    
    def validate_provider(self, provider: str) -> Tuple[bool, List[str]]:
        """Validate OAuth provider and return required environment variables.
        
        Args:
            provider: The OAuth provider name to validate
            
        Returns:
            Tuple of (is_valid, required_env_vars)
            - is_valid: Whether provider is supported
            - required_env_vars: List of required environment variable names
            
        Example:
            ```python
            is_valid, env_vars = oauth_manager.validate_provider("google")
            if is_valid:
                print(f"Required env vars: {', '.join(env_vars)}")
            ```
        """
        provider = provider.lower()
        
        if provider in self._providers:
            config = self._providers[provider]
            required_vars = [
                config["client_id_env"],
                config["client_secret_env"],
                config["redirect_uri_env"],
            ]
            return True, required_vars
        
        return False, []
    
    def extract_oauth_config(
        self,
        auth_config: Dict[str, str] | BaseModel,
    ) -> Tuple[str, str]:
        """Extract provider and token_url from auth_config.
        
        Handles both dict and Pydantic BaseAuthConfig types for backward compatibility.
        
        Args:
            auth_config: OAuth configuration (dict or Pydantic object)
            
        Returns:
            Tuple of (provider, token_url)
            
        Example:
            ```python
            # With dict
            provider, token_url = oauth_manager.extract_oauth_config({"provider": "google", ...})
            
            # With Pydantic object
            provider, token_url = oauth_manager.extract_oauth_config(google_auth_config_obj)
            ```
        """
        if isinstance(auth_config, dict):
            provider = auth_config.get("provider", "google")
            token_url = auth_config.get("token_url", "")
        else:
            # Pydantic BaseAuthConfig object
            provider = getattr(auth_config, "provider", "google")
            token_url = getattr(auth_config, "token_url", "")
        
        return provider, token_url
    
    def get_all_providers(self) -> List[str]:
        """Get list of all supported OAuth providers.
        
        Returns:
            List of supported provider names
            
        Example:
            ```python
            providers = oauth_manager.get_all_providers()
            # Returns: ["google", "microsoft", "github"]
            ```
        """
        return list(self._providers.keys())


# Module-level singleton instance for easy access
_oauth_manager: Optional[OAuthProviderManager] = None


def get_oauth_manager() -> OAuthProviderManager:
    """Get the OAuth provider manager singleton instance.
    
    Returns:
        OAuthProviderManager: The singleton instance
        
    Example:
        ```python
        from shared.voice_agents.tools.base.oauth_provider_utils import get_oauth_manager
        
        oauth_manager = get_oauth_manager()
        credentials = oauth_manager.get_credentials("google")
        ```
    """
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthProviderManager()
    return _oauth_manager