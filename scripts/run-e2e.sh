#!/bin/bash
set -e

# AI Voice Agent Platform E2E Test Runner
# This script spins up an isolated Docker stack, runs migrations, executes tests, and tears down.

# Determine video recording setting
VIDEO_SETTING="retain-on-failure"
PYTEST_ARGS=()
while (($#)); do
    case "$1" in
        --video-on)
            VIDEO_SETTING="on"
            ;;
        --)
            shift
            PYTEST_ARGS+=("$@")
            break
            ;;
        *)
            PYTEST_ARGS+=("$1")
            ;;
    esac
    shift
done

# Determine docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose -p e2e-stack"
else
    DOCKER_COMPOSE="docker-compose -p e2e-stack"
fi

echo "🚀 Starting E2E Isolated Stack using $DOCKER_COMPOSE..."
if [ "$VIDEO_SETTING" == "on" ]; then
    echo "📹 Video recording is ENABLED for all tests."
else
    echo "📹 Video recording is ENABLED for FAILED tests only (default)."
fi

# 1. Spin up the stack
$DOCKER_COMPOSE -f docker-compose.e2e.yml up -d --build

# Function to teardown on exit
cleanup() {
    echo "🧹 Tearing down E2E stack..."
    $DOCKER_COMPOSE -f docker-compose.e2e.yml down -v
}
trap cleanup EXIT

# 2. Wait for the backend process to be live. The disposable E2E stack uses
#    PostgreSQL directly and deliberately has no Supabase REST service, so the
#    dependency-aware /health endpoint is not the right readiness probe here.
echo "⏳ Waiting for Backend to be live on port 8001..."
MAX_RETRIES=30
COUNT=0
while ! curl -s -f http://localhost:8001/health/live > /dev/null; do
    printf '.'
    sleep 2
    COUNT=$((COUNT+1))
    if [ $COUNT -eq $MAX_RETRIES ]; then
        echo "❌ Backend failed to start"
        exit 1
    fi
done
echo "✅ Backend process is live!"

# 3. Initialize Database Schema (Supabase Mocks)
echo "🔧 Initializing Database Schema..."
cat scripts/init-test-db.sql | $DOCKER_COMPOSE exec -T db_e2e psql -U postgres -d test_db

# 4. Run Migrations
echo "🔄 Running Database Migrations..."
$DOCKER_COMPOSE exec -T backend_e2e alembic upgrade head

# 5. Seed Test Data
echo "🌱 Seeding Platform Tools..."
# Seed ONLY system-level platform tools (required for the app to function)
$DOCKER_COMPOSE exec -T db_e2e psql -U postgres -d test_db -c "INSERT INTO platform_tools (id, name, description, is_active, requires_auth, auth_type, tool_functions_schema) VALUES ('00000000-0000-0000-0000-000000000001', 'Gmail', 'Send and read emails', true, true, 'oauth2', '{\"functions\": [{\"name\": \"send_email\", \"description\": \"Send an email\", \"parameters\": {\"type\": \"object\", \"properties\": {}}}]}') ON CONFLICT (name) DO NOTHING;"

# Note: We NO LONGER seed organizations or agents here globally.
# This ensures onboarding tests start from a truly empty state.

# 6. Run Playwright Tests
echo "🎭 Running Playwright E2E Tests..."
# Set environment variables for the test runner
export E2E_BASE_URL=http://localhost:3001
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}${PWD}:${PWD}/e2e/tests"

# Determine which pytest to use
PYTEST_BIN="pytest"
if [ -f "backend/.venv-backend/bin/pytest" ]; then
    PYTEST_BIN="backend/.venv-backend/bin/pytest"
fi

# Create report directory if not exists (redundant but safe)
mkdir -p e2e/reports

$PYTEST_BIN e2e/tests/ "${PYTEST_ARGS[@]}" -s \
    --html=e2e/reports/report.html \
    --self-contained-html \
    --tracing retain-on-failure \
    --video $VIDEO_SETTING \
    --output=e2e/reports/test-artifacts

echo "🎉 E2E Tests Completed Successfully!"
echo "📊 Test report available at: e2e/reports/report.html"
