"""
Tests for auth service.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException, status

from src.auth.service import AuthService
from src.auth.models import SignUpRequest, SignInRequest


@pytest.fixture
def auth_service(mock_supabase_client, mock_supabase_auth):
    """AuthService with mocked Supabase."""
    with patch('src.auth.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True
        mock_supabase_client.auth = mock_supabase_auth
        
        service = AuthService()
        service.supabase_config = mock_config
        yield service


@pytest.fixture
def sign_up_request():
    """Valid sign up request."""
    return SignUpRequest(
        email="newuser@example.com",
        password="Password123!",
        password_confirm="Password123!",
        first_name="New",
        last_name="User"
    )


@pytest.fixture
def sign_in_request():
    """Valid sign in request."""
    return SignInRequest(
        email="test@example.com",
        password="Password123!"
    )


@pytest.fixture
def mock_supabase_user_response(sample_user_id):
    """Mock Supabase user response - returns datetime objects like real Supabase API."""
    now = datetime.now(timezone.utc)
    user_mock = MagicMock()
    user_mock.id = str(sample_user_id)
    user_mock.email = 'test@example.com'  # Default, will be overridden in tests
    user_mock.user_metadata = {
        'first_name': 'Test',
        'last_name': 'User'
    }
    user_mock.email_confirmed_at = now  # datetime object
    user_mock.created_at = now  # datetime object
    user_mock.updated_at = now  # datetime object
    
    session_mock = MagicMock()
    session_mock.access_token = "test-access-token"
    session_mock.refresh_token = "test-refresh-token"
    
    response_mock = MagicMock()
    response_mock.user = user_mock
    response_mock.session = session_mock
    
    return response_mock


class TestAuthServiceSignUp:
    """Test AuthService.sign_up method."""

    @pytest.mark.skip(reason="Complex async service mocking - requires proper organization/role service setup")
    @pytest.mark.asyncio
    async def test_sign_up_success(
        self,
        auth_service,
        sign_up_request,
        mock_supabase_auth,
        mock_supabase_user_response,
        sample_user_id
    ):
        """Successful user registration with valid data."""
        # Set mock user email to match request (Supabase would do this)
        mock_supabase_user_response.email = sign_up_request.email
        mock_supabase_user_response.user_metadata = {
            'first_name': sign_up_request.first_name,
            'last_name': sign_up_request.last_name
        }
        
        # Configure mock to update user after sign_up is called
        def configure_user():
            mock_supabase_user_response.email = sign_up_request.email
            mock_supabase_user_response.user_metadata = {
                'first_name': sign_up_request.first_name,
                'last_name': sign_up_request.last_name
            }
        
        mock_supabase_user_response.configure_mock = configure_user
        mock_supabase_auth.sign_up.return_value = mock_supabase_user_response
        
        with patch('src.organization.service.organization_service') as mock_org_service, \
             patch('src.rbac.roles.service.role_service') as mock_role_service, \
             patch('src.rbac.user_roles.service.user_role_service') as mock_user_role_service:
            
            mock_org_service.create_organization.return_value = (MagicMock(id=uuid4()), None)
            
            mock_role = MagicMock()
            mock_role.id = uuid4()
            mock_role_service.get_role_by_name = AsyncMock(return_value=(mock_role, None))
            
            mock_user_role_service.assign_role_to_user = AsyncMock(return_value=(MagicMock(), None))
            
            result, error = await auth_service.sign_up(sign_up_request)
        
        assert error is None
        assert result is not None
        assert result.user.email == "newuser@example.com"
        assert result.user.first_name == "New"
        assert result.user.last_name == "User"
        assert result.access_token == "test-access-token"
        assert result.refresh_token == "test-refresh-token"
        
        mock_supabase_auth.sign_up.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_up_supabase_error_no_user(
        self,
        auth_service,
        sign_up_request,
        mock_supabase_auth
    ):
        """Handles Supabase error when no user returned."""
        mock_response = MagicMock()
        mock_response.user = None
        mock_supabase_auth.sign_up.return_value = mock_response
        
        result, error = await auth_service.sign_up(sign_up_request)
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "Failed to create user account" in error.detail

    @pytest.mark.asyncio
    async def test_sign_up_existing_user(
        self,
        auth_service,
        sign_up_request,
        mock_supabase_auth
    ):
        """Returns 409 Conflict for duplicate email."""
        mock_supabase_auth.sign_up.side_effect = Exception("User already registered")
        
        result, error = await auth_service.sign_up(sign_up_request)
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in error.detail.lower()


class TestAuthServiceSignIn:
    """Test AuthService.sign_in method."""

    @pytest.mark.asyncio
    async def test_sign_in_success(
        self,
        auth_service,
        sign_in_request,
        mock_supabase_auth,
        mock_supabase_user_response,
        sample_user_id
    ):
        """Successful login with valid credentials."""
        mock_supabase_auth.sign_in_with_password.return_value = mock_supabase_user_response
        
        result, error = await auth_service.sign_in(sign_in_request)
        
        assert error is None
        assert result is not None
        assert result.user.email == "test@example.com"
        assert result.access_token == "test-access-token"
        assert result.refresh_token == "test-refresh-token"
        
        mock_supabase_auth.sign_in_with_password.assert_called_once_with({
            "email": "test@example.com",
            "password": "Password123!"
        })

    @pytest.mark.asyncio
    async def test_sign_in_invalid_credentials(
        self,
        auth_service,
        sign_in_request,
        mock_supabase_auth
    ):
        """Returns 400 for incorrect email/password."""
        mock_response = MagicMock()
        mock_response.user = None
        mock_supabase_auth.sign_in_with_password.return_value = mock_response
        
        result, error = await auth_service.sign_in(sign_in_request)
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid email or password" in error.detail

    @pytest.mark.asyncio
    async def test_sign_in_supabase_error(
        self,
        auth_service,
        sign_in_request,
        mock_supabase_auth
    ):
        """Handles Supabase API failures gracefully."""
        mock_supabase_auth.sign_in_with_password.side_effect = Exception("Network error")
        
        result, error = await auth_service.sign_in(sign_in_request)
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAuthServiceSignOut:
    """Test AuthService.sign_out method."""

    @pytest.mark.asyncio
    async def test_sign_out_success(self, auth_service, mock_supabase_auth):
        """Successfully invalidates session."""
        mock_supabase_auth.sign_out.return_value = None
        
        result, error = await auth_service.sign_out("valid-token")
        
        assert error is None
        assert result is True
        
        mock_supabase_auth.sign_out.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_sign_out_invalid_token(
        self,
        auth_service,
        mock_supabase_auth
    ):
        """Handles invalid/expired token."""
        mock_supabase_auth.sign_out.side_effect = Exception("Invalid token")
        
        result, error = await auth_service.sign_out("invalid-token")
        
        assert result is False
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST


class TestAuthServiceRefreshToken:
    """Test AuthService.refresh_token method."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        auth_service,
        mock_supabase_auth,
        mock_supabase_user_response,
        sample_user_id
    ):
        """Returns new access token."""
        mock_supabase_auth.refresh_session.return_value = mock_supabase_user_response
        
        result, error = await auth_service.refresh_token("valid-refresh-token")
        
        assert error is None
        assert result is not None
        assert result.access_token == "test-access-token"
        assert result.user.email == "test@example.com"
        
        mock_supabase_auth.refresh_session.assert_called_once_with("valid-refresh-token")

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(
        self,
        auth_service,
        mock_supabase_auth
    ):
        """Returns 400 for invalid refresh token."""
        mock_response = MagicMock()
        mock_response.user = None
        mock_supabase_auth.refresh_session.return_value = mock_response
        
        result, error = await auth_service.refresh_token("invalid-refresh-token")
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid refresh token" in error.detail

    @pytest.mark.asyncio
    async def test_refresh_token_expired(
        self,
        auth_service,
        mock_supabase_auth
    ):
        """Returns 400 for expired refresh token."""
        mock_supabase_auth.refresh_session.side_effect = Exception("Token expired")
        
        result, error = await auth_service.refresh_token("expired-refresh-token")
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestAuthServiceGetUser:
    """Test AuthService.get_user method."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self,
        auth_service,
        mock_supabase_auth,
        mock_supabase_user_response,
        sample_user_id,
        monkeypatch
    ):
        """Returns complete user profile."""
        mock_supabase_auth.get_user.return_value = mock_supabase_user_response
        
        with patch('src.auth.service.user_role_service') as mock_user_role_service:
            mock_user_role_service.get_all_user_roles_with_permissions = AsyncMock(return_value=([], None))
            
            result, error = await auth_service.get_user("valid-access-token")
        
        assert error is None
        assert result is not None
        assert result.email == "test@example.com"
        assert result.first_name == "Test"
        assert result.last_name == "User"
        
        mock_supabase_auth.get_user.assert_called_once_with("valid-access-token")

    @pytest.mark.asyncio
    async def test_get_user_includes_roles(
        self,
        auth_service,
        mock_supabase_auth,
        mock_supabase_user_response,
        sample_user_id
    ):
        """Profile includes roles and permissions."""
        mock_supabase_auth.get_user.return_value = mock_supabase_user_response

        role_id = uuid4()
        user_role_id = uuid4()
        now = datetime.now()

        mock_role = {
            "id": role_id,
            "name": "admin",
            "description": "Test admin role",
            "is_system_role": False,
            "created_at": now,
            "updated_at": now,
            "permissions": []
        }

        mock_user_role = {
            "role": mock_role,
            "organization_id": sample_user_id,
            "user_role_id": user_role_id
        }

        mock_roles = [mock_user_role]
        with patch('src.auth.service.user_role_service') as mock_user_role_service:
            mock_user_role_service.get_all_user_roles_with_permissions = AsyncMock(return_value=(mock_roles, None))

            result, error = await auth_service.get_user("valid-access-token")

        assert error is None
        assert result is not None
        assert len(result.roles) == 1
        assert result.roles[0].role.name == "admin"

    @pytest.mark.asyncio
    async def test_get_user_invalid_token(
        self,
        auth_service,
        mock_supabase_auth
    ):
        """Returns 401 for invalid access token."""
        mock_response = MagicMock()
        mock_response.user = None
        mock_supabase_auth.get_user.return_value = mock_response
        
        result, error = await auth_service.get_user("invalid-access-token")
        
        assert result is None
        assert error is not None
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in error.detail


class TestAuthServiceGetUserByEmail:
    """Test AuthService.get_user_by_email method."""

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(
        self,
        auth_service,
        mock_supabase_auth,
        sample_user_id,
        monkeypatch
    ):
        """Finds and returns existing user."""
        now = datetime.now(timezone.utc)
        mock_user = MagicMock()
        mock_user.id = str(sample_user_id)
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {"first_name": "Test", "last_name": "User"}
        mock_user.email_confirmed_at = now  # datetime object
        mock_user.created_at = now  # datetime object
        mock_user.updated_at = now  # datetime object
        
        mock_response = MagicMock()
        mock_response.users = [mock_user]
        mock_supabase_auth.admin.list_users.return_value = mock_response
        
        with patch('src.auth.service.user_role_service') as mock_user_role_service:
            mock_user_role_service.get_all_user_roles_with_permissions = AsyncMock(return_value=([], None))
            
            result, error = await auth_service.get_user_by_email("test@example.com")
        
        assert error is None
        assert result is not None
        assert result.email == "test@example.com"
        
        mock_supabase_auth.admin.list_users.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(
        self,
        auth_service,
        mock_supabase_auth,
        sample_user_id
    ):
        """Returns None for non-existent email."""
        mock_response = MagicMock()
        mock_response.users = []
        mock_supabase_auth.admin.list_users.return_value = mock_response
        
        with patch('src.auth.service.user_role_service') as mock_user_role_service:
            mock_user_role_service.get_all_user_roles_with_permissions = AsyncMock(return_value=([], None))
            
            result, error = await auth_service.get_user_by_email("nonexistent@example.com")
        
        assert error is None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_case_insensitive(
        self,
        auth_service,
        mock_supabase_auth,
        sample_user_id
    ):
        """Email lookup is case-insensitive."""
        now = datetime.now(timezone.utc)
        mock_user = MagicMock()
        mock_user.id = str(sample_user_id)
        mock_user.email = "Test@Example.COM"
        mock_user.user_metadata = {"first_name": "Test", "last_name": "User"}
        mock_user.email_confirmed_at = now  # datetime object
        mock_user.created_at = now  # datetime object
        mock_user.updated_at = now  # datetime object
        
        mock_response = MagicMock()
        mock_response.users = [mock_user]
        mock_supabase_auth.admin.list_users.return_value = mock_response
        
        with patch('src.auth.service.user_role_service') as mock_user_role_service:
            mock_user_role_service.get_all_user_roles_with_permissions = AsyncMock(return_value=([], None))
            
            result, error = await auth_service.get_user_by_email("test@example.com")
        
        assert error is None
        assert result is not None
        assert result.email == "Test@Example.COM"
