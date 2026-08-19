#!/usr/bin/env bash
# Run the platform-owned MCP connectors and voice worker in one deployable
# voice-ws unit.  The MCP endpoint is loopback-only and is not published.
set -euo pipefail

export MCP_HOST="${MCP_HOST:-127.0.0.1}"
export MCP_PORT="${MCP_PORT:-8733}"

python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest &
mcp_pid=$!

for _ in $(seq 1 20); do
  if python -c "import os,socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex((os.getenv('MCP_HOST','127.0.0.1'), int(os.getenv('MCP_PORT','8733'))))==0 else 1)" 2>/dev/null; then
    echo "[entrypoint] google-calendar-appointment MCP ready on ${MCP_HOST}:${MCP_PORT}/mcp (pid ${mcp_pid})"
    break
  fi
  if ! kill -0 "${mcp_pid}" 2>/dev/null; then
    echo "[entrypoint] Google Calendar Appointment MCP exited during startup" >&2
    exit 1
  fi
  sleep 0.5
done

uvicorn src.main:app --host 0.0.0.0 --port 7860 --workers "${VOICE_WS_WORKERS:-1}" &
voice_pid=$!

shutdown() {
  kill "${voice_pid}" "${mcp_pid}" 2>/dev/null || true
  wait "${voice_pid}" "${mcp_pid}" 2>/dev/null || true
}
trap shutdown TERM INT

# If either the connector or the worker exits, terminate the unit so the
# orchestrator restarts both together instead of silently serving without the
# appointment MCP.
set +e
wait -n "${voice_pid}" "${mcp_pid}"
status=$?
set -e
shutdown
exit "${status}"
