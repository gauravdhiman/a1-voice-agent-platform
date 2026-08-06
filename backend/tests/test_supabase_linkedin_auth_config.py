"""Regression tests for LinkedIn direct OAuth configuration."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LINKEDIN_DOC_PATH = (
    REPO_ROOT / "docs" / "02_features" / "authentication_rbac" / "linkedin-direct-oidc.md"
)
SETTINGS_PATH = REPO_ROOT / "shared" / "config" / "settings.py"


def test_linkedin_direct_oauth_doc_describes_backend_session_flow() -> None:
    """LinkedIn sign-in should mint Supabase sessions on the backend."""
    assert LINKEDIN_DOC_PATH.is_file()
    doc_text = LINKEDIN_DOC_PATH.read_text(encoding="utf-8")
    assert "setSession" in doc_text
    assert "POST /linkedin/exchange" in doc_text or "/linkedin/exchange" in doc_text


def test_settings_exposes_linkedin_oauth_env_vars() -> None:
    """Backend settings must read LinkedIn OAuth credentials from the environment."""
    settings_text = SETTINGS_PATH.read_text(encoding="utf-8")
    assert "linkedin_oauth_scopes" in settings_text
    assert "SUPABASE_AUTH_EXTERNAL_LINKEDIN_OIDC_CLIENT_ID" in settings_text
