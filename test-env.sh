#!/bin/bash
# Test helper script for AI Voice Agent Platform
# Source this file to enable simple test commands:
#   source ./test-env.sh
#   pytest backend/tests/organization/
#   pytest --cov

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up Python paths (use absolute paths to avoid shadowing)
export PYTHONPATH="${PROJECT_ROOT}/backend:${PROJECT_ROOT}/shared:${PROJECT_ROOT}/voice-ws:${PYTHONPATH}"

# Add pytest to PATH
export PATH="${PROJECT_ROOT}/backend/.venv/bin:${PATH}"

echo "✅ Test environment configured"
echo "   PYTHONPATH includes: backend, shared, voice-ws"
echo "   Virtual env: backend/.venv/bin"
echo ""
echo "🚀 Now you can run:"
echo "   pytest                          # Run all tests"
echo "   pytest backend/tests/           # Run backend tests"
echo "   pytest voice-ws/tests/          # Run voice-ws tests"
echo "   pytest backend/tests/organization/ # Run specific module"
echo "   pytest --cov                    # Run with coverage"
echo ""
echo "📌 Examples:"
echo "   pytest backend/tests/shared/voice_agents/test_platform_tool_registry.py"
echo "   pytest voice-ws/tests/test_speech_factory.py -v"
