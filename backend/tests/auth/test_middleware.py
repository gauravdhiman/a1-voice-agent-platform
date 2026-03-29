"""
Tests for auth middleware JWT security fixes (COG-28).

Verifies that:
- JWT signature verification is enforced
- Mock bypass is restricted to test environment only
- Forged tokens are rejected with 401
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException

from src.auth.middleware import _decode_jwt_verified, get_authenticated_user, get_current_user_id
from src.auth.models import UserProfile


# --- Helpers ---

TEST_SECRET = "super-secret-test-key"
TEST_USER_ID = str(uuid4())


def make_token(payload: dict, secret: str = TEST_SECRET, algorithm: str = "HS256") -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


# --- Tests for _decode_jwt_verified ---


class TestDecodeJwtVerified:
    """Unit tests for the JWT verification helper."""

    def test_valid_token_decoded_successfully(self):
        token = make_token({"sub": TEST_USER_ID})
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.jwt_secret_key = TEST_SECRET
            payload = _decode_jwt_verified(token)
        assert payload["sub"] == TEST_USER_ID

    def test_missing_secret_raises_500(self):
        """Server misconfiguration must return 500, not 401 — never expose internals."""
        token = make_token({"sub": TEST_USER_ID})
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.jwt_secret_key = None
            with pytest.raises(HTTPException) as exc_info:
                _decode_jwt_verified(token)
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Authentication service unavailable"

    def test_wrong_secret_raises_401(self):
        token = make_token({"sub": TEST_USER_ID}, secret="wrong-secret")
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                _decode_jwt_verified(token)
        assert exc_info.value.status_code == 401
        assert "signature" in exc_info.value.detail.lower()

    def test_malformed_token_raises_401(self):
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                _decode_jwt_verified("not.a.jwt")
        assert exc_info.value.status_code == 401

    def test_unsigned_token_rejected(self):
        """A token signed with 'verify_signature: False' pattern must be rejected."""
        unsigned_payload = {"sub": TEST_USER_ID, "role": "admin"}
        forged = make_token(unsigned_payload, secret="attacker-key")
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                _decode_jwt_verified(forged)
        assert exc_info.value.status_code == 401


# --- Tests for get_current_user_id mock bypass security ---


class TestMockBypassSecurity:
    """Verify the mock-jwt-token bypass is restricted to test environment only."""

    @pytest.mark.asyncio
    async def test_mock_token_accepted_in_test_env(self):
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "test"
            mock_settings.jwt_secret_key = TEST_SECRET
            result = await get_current_user_id("Bearer mock-jwt-token")
        assert result == UUID("00000000-0000-0000-0000-000000000000")

    @pytest.mark.asyncio
    async def test_mock_token_rejected_in_production(self):
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id("Bearer mock-jwt-token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_mock_token_rejected_in_development(self):
        """Mock bypass must NOT work in development — only in test."""
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "development"
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id("Bearer mock-jwt-token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_signed_token_accepted(self):
        token = make_token({"sub": TEST_USER_ID})
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = TEST_SECRET
            result = await get_current_user_id(f"Bearer {token}")
        assert str(result) == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_forged_token_rejected(self):
        forged = make_token({"sub": TEST_USER_ID}, secret="attacker-key")
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_id(f"Bearer {forged}")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_authorization_header_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_authorization_header_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id("Token abc123")
        assert exc_info.value.status_code == 401


# --- Tests for get_authenticated_user mock bypass ---


class TestGetAuthenticatedUserMockBypass:
    """Verify the mock-jwt-token bypass is restricted to test environment for get_authenticated_user."""

    @pytest.mark.asyncio
    async def test_mock_token_accepted_in_test_env(self):
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "test"
            mock_settings.jwt_secret_key = TEST_SECRET
            user_id, user_profile = await get_authenticated_user("Bearer mock-jwt-token")
        assert user_id == UUID("00000000-0000-0000-0000-000000000000")
        assert user_profile.email == "test@gmail.com"

    @pytest.mark.asyncio
    async def test_mock_token_rejected_in_production(self):
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                await get_authenticated_user("Bearer mock-jwt-token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_mock_token_rejected_in_development(self):
        """Mock bypass must NOT work in development — only in test."""
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "development"
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                await get_authenticated_user("Bearer mock-jwt-token")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_authorization_header_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user(None)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_authorization_header_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_user("Token abc123")
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_forged_token_rejected(self):
        forged = make_token({"sub": TEST_USER_ID}, secret="attacker-key")
        with patch("src.auth.middleware.settings") as mock_settings:
            mock_settings.environment = "production"
            mock_settings.jwt_secret_key = TEST_SECRET
            with pytest.raises(HTTPException) as exc_info:
                await get_authenticated_user(f"Bearer {forged}")
        assert exc_info.value.status_code == 401
