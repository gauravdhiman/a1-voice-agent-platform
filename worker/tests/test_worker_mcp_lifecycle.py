"""Tests for the worker's MCP client session-lifecycle (Phase 3a regression).

``worker._integrate_mcp_agent_tool`` builds the LiveKit tools and returns the
open :class:`McpClient` for the caller to keep alive. The bug these tests pin:
the worker entrypoint used to close those clients in its own ``finally`` block,
but the entrypoint **returns right after ``agent_session.start()``** while the
LiveKit session keeps running autonomously. So ``finally`` fired at setup time
and closed every MCP client ~14s before the model invoked a tool, producing
``RuntimeError: McpClient is closed`` at call time (observed in worker logs).

The fix splits cleanup into two testable helpers:

- :func:`worker._hand_off_mcp_clients_to_session` — once the LiveKit session has
  started, register a shutdown callback on the ``JobContext`` that closes the
  clients when the **job** ends (the real session lifetime). This is the
  LiveKit-idiomatic cleanup hook (``ctx.add_shutdown_callback``).
- :func:`worker._cleanup_mcp_clients` — the entrypoint's ``finally`` calls this.
  It closes the clients **only when setup failed before handoff** (so a
  half-open client on the error path is not leaked). When the session owns the
  clients (``handed_off=True``) it does nothing — they are closed later by the
  shutdown callback.

Contract pinned here:
  - Handoff registers exactly one async shutdown callback on ``ctx``; before it
    fires the clients stay OPEN (the regression), and after it fires they are
    closed.
  - Cleanup with ``handed_off=True`` leaves the clients OPEN.
  - Cleanup with ``handed_off=False`` (error path) closes the clients.
  - Handoff with no clients is a no-op (no callback registered).
"""
import asyncio

import worker
from shared.voice_agents.tools.mcp.client import McpClient
from shared.voice_agents.tools.mcp.models import McpServerConfig


def _client() -> McpClient:
    """A McpClient that never connects — only its local close() flag is used."""
    return McpClient(McpServerConfig(url="http://127.0.0.1:1/mcp", name="test"))


class _FakeJobContext:
    """Stand-in for ``livekit.agents.JobContext`` recording shutdown callbacks."""

    def __init__(self) -> None:
        self.shutdown_callbacks: list = []

    def add_shutdown_callback(self, callback) -> None:
        self.shutdown_callbacks.append(callback)

    async def run_shutdown(self, reason: str = "participant_disconnected") -> None:
        for cb in self.shutdown_callbacks:
            res = cb(reason) if cb.__code__.co_argcount else cb()
            if asyncio.iscoroutine(res):
                await res


class TestHandOffMcpClientsToSession:
    """``worker._hand_off_mcp_clients_to_session`` — register shutdown cleanup."""

    async def test_registers_one_shutdown_callback_that_closes_clients(self):
        ctx = _FakeJobContext()
        clients = [_client(), _client()]

        worker._hand_off_mcp_clients_to_session(ctx, clients)

        # Exactly one callback registered.
        assert len(ctx.shutdown_callbacks) == 1
        # Regression: clients stay OPEN until the callback fires (the entrypoint
        # has already returned; the session is still live).
        assert all(not c._closed for c in clients)

        # When the job shuts down, the callback closes every client.
        await ctx.run_shutdown()
        assert all(c._closed for c in clients)

    async def test_no_clients_is_a_noop(self):
        ctx = _FakeJobContext()
        worker._hand_off_mcp_clients_to_session(ctx, [])
        assert ctx.shutdown_callbacks == []


class TestCleanupMcpClients:
    """``worker._cleanup_mcp_clients`` — the entrypoint ``finally`` path."""

    async def test_does_not_close_when_handed_off(self):
        # Session owns the clients (closed later by the shutdown callback).
        clients = [_client(), _client()]
        await worker._cleanup_mcp_clients(clients, handed_off=True)
        assert all(not c._closed for c in clients)

    async def test_closes_when_not_handed_off(self):
        # Setup failed before the session took ownership -> finally must close
        # the half-open clients so they are not leaked.
        clients = [_client(), _client()]
        await worker._cleanup_mcp_clients(clients, handed_off=False)
        assert all(c._closed for c in clients)

    async def test_close_exception_is_swallowed(self):
        # A client whose close() raises must not abort cleanup of the others.
        bad = _client()
        bad.close = _raise
        good = _client()
        await worker._cleanup_mcp_clients([bad, good], handed_off=False)
        assert good._closed is True


async def _raise(*_a, **_kw):
    raise RuntimeError("boom")