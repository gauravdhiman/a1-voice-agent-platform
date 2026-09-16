"""Workspace dashboard agent-count endpoint authorization and failure behavior."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from src.auth.middleware import get_authenticated_user
from src.voice_agents.routes import agent_router


class AgentCountQuery:
    """Tiny PostgREST stand-in that keeps active filters query-local."""

    def __init__(self, fail: bool = False):
        self.active_only = False
        self.organization_id = None
        self.fail = fail

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, field, value):
        if field == "is_active":
            self.active_only = value is True
        elif field == "organization_id":
            self.organization_id = value
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("private database detail")
        return SimpleNamespace(count=2 if self.active_only else 5)


class AgentCountDatabase:
    """Create a separately scoped query for each summary count."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.queries = []

    def table(self, name):
        assert name == "voice_agents"
        query = AgentCountQuery(fail=self.fail)
        self.queries.append(query)
        return query


def make_client(profile):
    app = FastAPI()
    app.include_router(agent_router)
    app.dependency_overrides[get_authenticated_user] = lambda: (uuid4(), profile)
    return TestClient(app)


def test_agent_summary_returns_counts_only_for_the_selected_organization():
    org = uuid4()
    profile = MagicMock()
    client = make_client(profile)
    database = AgentCountDatabase()
    with patch("src.voice_agents.routes.assert_has_permission") as permission, patch(
        "src.voice_agents.routes.voice_agent_service",
        SimpleNamespace(supabase=database),
    ):
        response = client.get(f"/api/v1/agents/organization/{org}/summary")

    assert response.status_code == 200
    assert response.json() == {"total_agents": 5, "active_agents": 2}
    assert all(query.organization_id == str(org) for query in database.queries)
    assert sum(query.active_only for query in database.queries) == 1
    permission.assert_called_once_with(
        profile,
        "agent",
        "read",
        org,
        error_message="Insufficient permissions to view agents for this organization",
    )


def test_agent_summary_denies_users_without_agent_read_access_before_querying():
    org = uuid4()
    profile = MagicMock()
    client = make_client(profile)
    database = AgentCountDatabase()
    with patch(
        "src.voice_agents.routes.assert_has_permission",
        side_effect=HTTPException(status_code=403, detail="Forbidden"),
    ) as permission, patch(
        "src.voice_agents.routes.voice_agent_service",
        SimpleNamespace(supabase=database),
    ):
        response = client.get(f"/api/v1/agents/organization/{org}/summary")

    assert response.status_code == 403
    assert database.queries == []
    permission.assert_called_once()


def test_agent_summary_provider_failure_returns_a_safe_error():
    org = uuid4()
    profile = MagicMock()
    client = make_client(profile)
    database = AgentCountDatabase(fail=True)
    with patch("src.voice_agents.routes.assert_has_permission"), patch(
        "src.voice_agents.routes.voice_agent_service",
        SimpleNamespace(supabase=database),
    ):
        response = client.get(f"/api/v1/agents/organization/{org}/summary")

    assert response.status_code == 503
    assert response.json()["detail"] == "Agent summary unavailable"
    assert "private database detail" not in response.text
