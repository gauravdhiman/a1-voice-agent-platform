#!/usr/bin/env bash
# Dev entrypoint for the Pipecat voice-ws worker.
#
# Starts the local Google Calendar REST connector (FastMCP) as a co-process,
# then execs uvicorn. This matches the voice-ws-dev pattern so agents that
# use `Google_calendar_mcp` (http://127.0.0.1:8733/mcp) keep working when
# VOICE_TRANSPORT=pipecat and the voice-ws profile is not running.
#
# See shared/voice_agents/tools/mcp/README.md (Path A).
set -e

export MCP_HOST="${MCP_HOST:-127.0.0.1}"
export MCP_PORT="${MCP_PORT:-8733}"

# Launch the connector in the background. Do NOT let a connector failure abort
# voice-ws startup — assemble_agent_tools already fails soft per MCP tool.
python -m shared.voice_agents.tools.mcp.reference_servers.google_calendar_rest &
CONNECTOR_PID=$!

# Best-effort readiness wait (up to ~5s).
for _ in $(seq 1 10); do
  if python -c "import os,socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1', int(os.getenv('MCP_PORT','8733'))))==0 else 1)" 2>/dev/null; then
    echo "[entrypoint] google-calendar-rest connector ready on 127.0.0.1:${MCP_PORT}/mcp (pid ${CONNECTOR_PID})"
    break
  fi
  sleep 0.5
done

# exec so uvicorn becomes PID 1 and receives docker's SIGTERM on stop.
exec uvicorn src.main:app --host 0.0.0.0 --port 7860 --reload
