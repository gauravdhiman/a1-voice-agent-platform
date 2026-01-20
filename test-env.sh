#!/bin/bash
# Test helper script for AI Voice Agent Platform
# Source this file to enable simple test commands:
#   source ./test-env.sh
#   pytest backend/tests/organization/
#   pytest --cov

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up Python paths (use absolute paths to avoid shadowing)
export PYTHONPATH="${PROJECT_ROOT}/backend:${PROJECT_ROOT}/shared:${PYTHONPATH}"

# Add pytest to PATH
export PATH="${PROJECT_ROOT}/backend/.venv-backend/bin:${PATH}"

echo "✅ Test environment configured"
echo "   PYTHONPATH includes: backend/src, shared"
echo "   Virtual env: backend/.venv-backend/bin"
echo ""
echo "🚀 Now you can run:"
echo "   pytest                          # Run all tests"
echo "   pytest backend/tests/            # Run backend tests"
echo "   pytest backend/tests/organization/ # Run specific module"
echo "   pytest --cov                   # Run with coverage"
echo ""
echo "Example usage:"
echo "   pytest backend/tests/organization/test_service.py::TestOrganizationService::test_create_organization_success -v"
