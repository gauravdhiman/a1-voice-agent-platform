"""
Tests for process_invitation permission gating (Task #31 — N1 follow-up #4).

Closes the CRIT gap in `backend/src/auth/routes.py:process_invitation`:

  The endpoint accepts a body-supplied ``user_id`` and passes it to
  ``organization_service.process_invitation(token, user_id)`` WITHOUT
  verifying that ``user_id`` matches the authenticated caller. An
  attacker who intercepts an invitation token could substitute any
  other user's UUID and have the new member be linked to the
  attacker's account — or, more simply, an authenticated user could
  process someone else's invitation under their own identity.

Contract:
  - Caller authenticated, body.user_id == current_user_id → 200.
  - Caller authenticated, body.user_id != current_user_id → 403.
  - Caller unauthenticated → 401 (handled by ``get_authenticated_user``,
    not exercised here).
  - organization_service.process_invitation is NEVER called when the
    caller and body user_id disagree (rejects before reaching the service).
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from fastapi import HTTPException

CALLER_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
ATTACKER_USER_ID = UUID("00000000-0000-0000-0000-0000000000ff")
TEST_TOKEN = "test-invitation-token-abc123"


def _make_user_profile():
    """A regular authenticated user (no admin role needed here)."""
    profile = Mock()
    profile.has_role = Mock(return_value=False)
    profile.has_permission = Mock(return_value=False)
    return profile


class TestProcessInvitationAuth:
    """The caller must match the body's user_id."""

    @pytest.mark.asyncio
    async def test_caller_matching_user_id_is_allowed(self):
        """Body.user_id == current_user_id → 200, service is called."""
        from src.auth.routes import process_invitation
        from src.auth.routes import ProcessInvitationRequest

        profile = _make_user_profile()
        profile.email = "caller@example.com"
        profile.first_name = "Caller"
        profile.last_name = "User"
        request = ProcessInvitationRequest(token=TEST_TOKEN, user_id=CALLER_USER_ID)

        with patch("src.auth.routes.organization_service") as mock_org_svc, patch(
            "src.auth.routes.signup_notifier.notify_new_user",
            new=AsyncMock(),
        ):
            # Service returns a successful response (invitation object, no error).
            mock_invitation = Mock()
            mock_invitation.organization_id = UUID(
                "22222222-2222-2222-2222-222222222222"
            )
            mock_invitation.organization_name = "Acme"
            mock_invitation.id = UUID("33333333-3333-3333-3333-333333333333")
            mock_org_svc.process_invitation = AsyncMock(
                return_value=(mock_invitation, None)
            )

            result = await process_invitation(
                request=request,
                user_data=(CALLER_USER_ID, profile),
            )

            assert result is not None
            mock_org_svc.process_invitation.assert_called_once_with(
                TEST_TOKEN, CALLER_USER_ID, "caller@example.com"
            )

    @pytest.mark.asyncio
    async def test_caller_with_mismatched_user_id_is_forbidden(self):
        """Body.user_id != current_user_id → 403, service is NOT called."""
        from src.auth.routes import process_invitation
        from src.auth.routes import ProcessInvitationRequest

        profile = _make_user_profile()
        request = ProcessInvitationRequest(token=TEST_TOKEN, user_id=ATTACKER_USER_ID)

        with patch("src.auth.routes.organization_service") as mock_org_svc:
            mock_org_svc.process_invitation = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await process_invitation(
                    request=request,
                    user_data=(CALLER_USER_ID, profile),
                )

            assert exc_info.value.status_code == 403
            # CRIT: the service must not have been called with the
            # attacker's user_id, otherwise the invitation would be
            # linked to the wrong account.
            mock_org_svc.process_invitation.assert_not_called()
