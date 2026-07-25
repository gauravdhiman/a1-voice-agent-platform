#!/usr/bin/env bash
# Dev entrypoint for the LiveKit voice worker.
#
# Starts the local Google Calendar REST connector (a FastMCP server that wraps
# Google's Calendar REST API) as a co-process, then execs the worker. Co-locating
# the connector with the worker means it auto-starts whenever the worker container
# starts or restarts — so the MCP Calendar path no longer breaks on a worker
# restart (the previous approach ran it detached via `docker exec -d`, which dies
# when the container restarts).
#
# The connector binds 127.0.0.1:8733 INSIDE this container, and the
# `Google_calendar_mcp` platform_tools row points at http://127.0.0.1:8733/mcp.
# This is Path A (personal-Gmail, no Workspace Preview) — see
# shared/voice_agents/tools/mcp/README.md. Production uses Google's remote
# Calendar MCP server (Path B), not this connector, so this dev-only wrapper is
# intentionally not baked into Dockerfile.dev's CMD.
set -e

export MCP_HOST="${MCP_HOST:-127.0.0.1}"
export MCP_PORT="${MCP_PORT:-8733}"

# Launch the connector in the background. Do NOT let a connector failure abort
# worker startup — the worker only contacts it when an agent actually invokes a
# tool, well after startup, and a broken connector already fails soft (skipped +
# logged) in the dispatch layer.
python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest &
CONNECTOR_PID=$!

# Best-effort readiness wait (up to ~5s). Non-blocking: if the connector is slow
# or fails, the worker still starts.
for _ in $(seq 1 10); do
  if python -c "import os,socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1', int(os.getenv('MCP_PORT','8733'))))==0 else 1)" 2>/dev/null; then
    echo "[entrypoint] google-calendar-rest connector ready on 127.0.0.1:${MCP_PORT}/mcp (pid ${CONNECTOR_PID})"
    break
  fi
  sleep 0.5
done

# exec so the worker becomes PID 1 and receives docker's SIGTERM on stop. The
# connector is a child of this same PID, so it is torn down with the container.
exec python src/worker.py "$@"