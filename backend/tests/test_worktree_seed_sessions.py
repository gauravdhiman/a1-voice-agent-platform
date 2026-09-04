"""Session-preserving fixture users: reruns must not revoke live logins."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.src.worktree_seed import WORKTREE_TEST_PASSWORD, _ensure_auth_user

EMAIL = "org-admin@247ai.local"
USER_ID = "00000000-0000-0000-0000-000000000001"


def _existing_user_client(*, password_valid: bool) -> MagicMock:
    """Fake service client with one pre-existing fixture account."""
    client = MagicMock()
    existing = SimpleNamespace(id=USER_ID, email=EMAIL)

    client.auth.admin.create_user.side_effect = Exception("User already registered")

    list_response = MagicMock()
    list_response.users = [existing]
    client.auth.admin.list_users.return_value = list_response

    if password_valid:
        session = SimpleNamespace(access_token="probe-jwt")
        client.auth.sign_in_with_password.return_value = SimpleNamespace(
            session=session
        )
    else:
        client.auth.sign_in_with_password.side_effect = Exception(
            "Invalid login credentials"
        )
    return client


def _update_payloads(client: MagicMock) -> list[dict]:
    """Return every update_user_by_id payload applied by the seed."""
    return [call.args[1] for call in client.auth.admin.update_user_by_id.call_args_list]


class TestEnsureAuthUserPreservesSessions:
    def test_healthy_account_keeps_password_untouched(self) -> None:
        """Reruns refresh metadata only; live sessions survive."""
        client = _existing_user_client(password_valid=True)

        assert _ensure_auth_user(client, EMAIL, "wt-1") == USER_ID

        payloads = _update_payloads(client)
        assert len(payloads) == 1
        assert "password" not in payloads[0]
        assert payloads[0]["email_confirm"] is True
        # Local-scope sign-out drops only the probe session: global scope
        # would revoke every live login (the outage under test).
        client.auth.sign_out.assert_called_once_with({"scope": "local"})

    def test_broken_credential_is_repaired(self) -> None:
        """A drifted password is reset without touching anything else."""
        client = _existing_user_client(password_valid=False)

        assert _ensure_auth_user(client, EMAIL, "wt-1") == USER_ID

        payloads = _update_payloads(client)
        assert len(payloads) == 2
        assert "password" not in payloads[0]
        assert payloads[1] == {"password": WORKTREE_TEST_PASSWORD}

    def test_probe_failure_never_blocks_metadata_refresh(self) -> None:
        """Even a failing probe path still refreshes metadata first."""
        client = _existing_user_client(password_valid=False)
        client.auth.sign_in_with_password.side_effect = RuntimeError("network")

        assert _ensure_auth_user(client, EMAIL, "wt-1") == USER_ID

        payloads = _update_payloads(client)
        assert payloads[0]["email_confirm"] is True
