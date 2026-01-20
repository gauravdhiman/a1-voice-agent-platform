#!/bin/bash
# Test runner script for AI Voice Agent Platform
# Simple interface to run tests from project root

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AI Voice Agent Platform Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "📋 Setup: Source the test environment first"
echo -e "   ${GREEN}source ./test-env.sh${NC}"
echo ""
echo "🎯 Then run tests with simple commands:"
echo ""
echo "   Run all tests:"
echo "     pytest"
echo ""
echo "   Run backend tests:"
echo "     pytest backend/tests/"
echo ""
echo "   Run specific module:"
echo "     pytest backend/tests/organization/"
echo "     pytest backend/tests/notifications/"
echo ""
echo "   Run with coverage:"
echo "     pytest --cov"
echo ""
echo "   Run specific test:"
echo "     pytest backend/tests/organization/test_service.py::TestOrganizationService::test_create_organization_success -v"
echo ""
echo -e "${GREEN}✅ Current Status:${NC}"
echo "   • Organization: 11/11 passing ✅"
echo "   • Notifications: 11/15 passing (4 skipped) ✅"
echo "   • Billing: 1/17 passing (needs fixes) ⚠️"
echo "   • Other modules: Needs work 🚧"
echo ""
echo "💡 Quick Start:"
echo -e "   ${GREEN}source ./test-env.sh && pytest backend/tests/organization/ backend/tests/notifications/${NC}"
