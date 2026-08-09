#!/bin/bash

# 24x7 AI environment-aware Docker startup script.
#
# Environment selection is explicit and never requires copying into .env:
#   ./start.sh start dev                    # local Supabase, .env.local
#   ./start.sh start dev --env staging      # cloud staging Supabase, .env.staging
#   ./start.sh start prod                   # production Supabase, .env.prod
#
# Use --env-file PATH when working with a temporary or generated env file.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default values
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE_PROD="docker-compose.yml"
COMPOSE_FILE_DEV="docker-compose.dev.yml"
ENV_FILE_OVERRIDE="${ENV_FILE:-}"
ENV_FILE=""
REQUESTED_ENV="${APP_ENV:-}"
ENVIRONMENT_NAME=""
COMPOSE_PROJECT_NAME=""
PORT_OFFSET_OVERRIDE=""
PROJECT_NAME_OVERRIDE=""
HOST_FRONTEND_PORT=""
HOST_BACKEND_PORT=""
HOST_VOICE_WS_PORT=""
HOST_OTEL_GRPC_PORT=""
HOST_OTEL_HTTP_PORT=""
HOST_OTEL_HEALTH_PORT=""

# Required environment variables
REQUIRED_ENV_VARS=(
    "NEXT_PUBLIC_SUPABASE_URL"
    "NEXT_PUBLIC_SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_KEY"
)

# Function to print usage
print_usage() {
    echo -e "${BLUE}24x7 AI environment-aware startup script${NC}"
    echo ""
    echo "Usage: ./start.sh [OPTIONS] ACTION [MODE]"
    echo ""
    echo "Options:"
    echo "  --env NAME    Select local, staging, or production environment"
    echo "  --env-file PATH"
    echo "                Select a custom environment file"
    echo "  --port-offset N"
    echo "                Shift the default host-port set by N"
    echo "  --project-name NAME"
    echo "                Override the Docker Compose project name"
    echo ""
    echo "Actions:"
    echo "  start dev     - Start containers in development mode"
    echo "  start prod    - Start containers in production mode"
    echo "  start voice-ws dev - Start voice-ws in development mode"
    echo "  start voice-ws prod - Start voice-ws in production mode"
    echo "  stop dev      - Stop development containers"
    echo "  stop prod     - Stop production containers"
    echo "  stop voice-ws dev - Stop development voice-ws"
    echo "  stop voice-ws prod - Stop production voice-ws"
    echo "  restart dev   - Restart development containers"
    echo "  restart prod  - Restart production containers"
    echo "  logs dev      - View development container logs"
    echo "  logs prod     - View production container logs"
    echo "  status        - Show status of all containers"
    echo "  build dev     - Build development images"
    echo "  build prod    - Build production images"
    echo "  config        - Show the selected env file and safe connection metadata"
    echo "  help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./start.sh start dev"
    echo "  ./start.sh start dev --env staging"
    echo "  ./start.sh restart dev --env-file .env.staging"
    echo "  ./start.sh start prod"
    echo "  ./start.sh config --env staging"
    echo "  ./start.sh start dev --env staging --port-offset 20"
}

# Parse environment options wherever they appear in the command line.
parse_options() {
    CLI_ARGS=()

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --env)
                [[ $# -ge 2 ]] || { echo "Missing value for --env" >&2; exit 1; }
                REQUESTED_ENV="$2"
                shift 2
                ;;
            --env-file)
                [[ $# -ge 2 ]] || { echo "Missing value for --env-file" >&2; exit 1; }
                ENV_FILE_OVERRIDE="$2"
                shift 2
                ;;
            --port-offset)
                [[ $# -ge 2 ]] || { echo "Missing value for --port-offset" >&2; exit 1; }
                PORT_OFFSET_OVERRIDE="$2"
                shift 2
                ;;
            --project-name)
                [[ $# -ge 2 ]] || { echo "Missing value for --project-name" >&2; exit 1; }
                PROJECT_NAME_OVERRIDE="$2"
                shift 2
                ;;
            --)
                shift
                CLI_ARGS+=("$@")
                break
                ;;
            *)
                CLI_ARGS+=("$1")
                shift
                ;;
        esac
    done
}

# Read a simple KEY=value setting without sourcing secrets into this shell.
read_env_setting() {
    local key="$1"
    awk -F= -v name="$key" '$1 == name {
        sub(/^[^=]*=/, "")
        gsub(/^"|"$/, "")
        gsub(/\r$/, "")
        print
        exit
    }' "$ENV_FILE"
}

# Resolve a setting from the process environment first, then the selected file.
get_config_setting() {
    local key="$1"
    local value=""
    value="$(printenv "$key" 2>/dev/null || true)"
    if [[ -n "$value" ]]; then
        printf '%s' "$value"
    else
        read_env_setting "$key"
    fi
}

validate_port() {
    local name="$1"
    local value="$2"
    if ! [[ "$value" =~ ^[0-9]+$ ]] || (( value < 1 || value > 65535 )); then
        echo -e "${RED}Error: $name must be an integer between 1 and 65535 (received '$value')${NC}" >&2
        exit 1
    fi
}

# Resolve all host-facing ports from one offset, with optional explicit overrides.
resolve_port_config() {
    local offset
    offset="${PORT_OFFSET_OVERRIDE:-}"
    if [[ -z "$offset" ]]; then
        offset="$(get_config_setting PORT_OFFSET)"
    fi
    [[ -n "$offset" ]] || offset=0
    if ! [[ "$offset" =~ ^[0-9]+$ ]] || (( offset > 60000 )); then
        echo -e "${RED}Error: PORT_OFFSET must be a non-negative integer no greater than 60000 (received '$offset')${NC}" >&2
        exit 1
    fi

    HOST_FRONTEND_PORT="$(get_config_setting HOST_FRONTEND_PORT)"
    HOST_BACKEND_PORT="$(get_config_setting HOST_BACKEND_PORT)"
    HOST_VOICE_WS_PORT="$(get_config_setting HOST_VOICE_WS_PORT)"
    HOST_OTEL_GRPC_PORT="$(get_config_setting HOST_OTEL_GRPC_PORT)"
    HOST_OTEL_HTTP_PORT="$(get_config_setting HOST_OTEL_HTTP_PORT)"
    HOST_OTEL_HEALTH_PORT="$(get_config_setting HOST_OTEL_HEALTH_PORT)"

    local customized_ports=false
    if (( offset > 0 )) || [[ -n "$HOST_FRONTEND_PORT$HOST_BACKEND_PORT$HOST_VOICE_WS_PORT$HOST_OTEL_GRPC_PORT$HOST_OTEL_HTTP_PORT$HOST_OTEL_HEALTH_PORT" ]]; then
        customized_ports=true
    fi

    [[ -n "$HOST_FRONTEND_PORT" ]] || HOST_FRONTEND_PORT=$((3000 + offset))
    [[ -n "$HOST_BACKEND_PORT" ]] || HOST_BACKEND_PORT=$((8000 + offset))
    [[ -n "$HOST_VOICE_WS_PORT" ]] || HOST_VOICE_WS_PORT=$((7860 + offset))
    [[ -n "$HOST_OTEL_GRPC_PORT" ]] || HOST_OTEL_GRPC_PORT=$((4317 + offset))
    [[ -n "$HOST_OTEL_HTTP_PORT" ]] || HOST_OTEL_HTTP_PORT=$((4318 + offset))
    [[ -n "$HOST_OTEL_HEALTH_PORT" ]] || HOST_OTEL_HEALTH_PORT=$((13133 + offset))

    validate_port HOST_FRONTEND_PORT "$HOST_FRONTEND_PORT"
    validate_port HOST_BACKEND_PORT "$HOST_BACKEND_PORT"
    validate_port HOST_VOICE_WS_PORT "$HOST_VOICE_WS_PORT"
    validate_port HOST_OTEL_GRPC_PORT "$HOST_OTEL_GRPC_PORT"
    validate_port HOST_OTEL_HTTP_PORT "$HOST_OTEL_HTTP_PORT"
    validate_port HOST_OTEL_HEALTH_PORT "$HOST_OTEL_HEALTH_PORT"

    export HOST_FRONTEND_PORT HOST_BACKEND_PORT HOST_VOICE_WS_PORT
    export HOST_OTEL_GRPC_PORT HOST_OTEL_HTTP_PORT HOST_OTEL_HEALTH_PORT

    if [[ "$customized_ports" = true ]]; then
        export APP_BASE_URL="http://localhost:${HOST_FRONTEND_PORT}"
        export API_BASE_URL="http://localhost:${HOST_BACKEND_PORT}"
        export NEXT_PUBLIC_API_URL="http://localhost:${HOST_BACKEND_PORT}"
        export VOICE_WS_PUBLIC_URL="ws://localhost:${HOST_VOICE_WS_PORT}"
        export GOOGLE_OAUTH_TOOL_REDIRECT_URI="http://localhost:${HOST_BACKEND_PORT}/api/v1/tools/callback"
        export CORS_ORIGINS="[\"http://localhost:${HOST_FRONTEND_PORT}\",\"http://127.0.0.1:${HOST_FRONTEND_PORT}\",\"http://frontend:3000\",\"http://frontend-dev:3000\"]"
        export NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="http://localhost:${HOST_OTEL_HTTP_PORT}/v1/traces"
        export NEXT_PUBLIC_OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="http://localhost:${HOST_OTEL_HTTP_PORT}/v1/metrics"
        export NEXT_PUBLIC_OTEL_EXPORTER_OTLP_LOGS_ENDPOINT="http://localhost:${HOST_OTEL_HTTP_PORT}/v1/logs"
    fi

    local project_suffix
    project_suffix="$(get_config_setting COMPOSE_PROJECT_SUFFIX)"
    if [[ -n "$PROJECT_NAME_OVERRIDE" ]]; then
        COMPOSE_PROJECT_NAME="$PROJECT_NAME_OVERRIDE"
    else
        if [[ -z "$project_suffix" ]] && [[ "$customized_ports" = true ]]; then
            if (( offset > 0 )); then
                project_suffix="p$offset"
            else
                project_suffix="p$HOST_FRONTEND_PORT"
            fi
        fi
        if [[ -n "$project_suffix" ]]; then
            COMPOSE_PROJECT_NAME="247ai-${ENVIRONMENT_NAME}-${project_suffix}"
        else
            COMPOSE_PROJECT_NAME="247ai-${ENVIRONMENT_NAME}"
        fi
    fi
    export COMPOSE_PROJECT_NAME
}

# Resolve the selected environment file and Compose project name.
select_environment_file() {
    local action="${1:-}"
    local mode="${2:-}"

    if [[ -n "$ENV_FILE_OVERRIDE" ]]; then
        ENV_FILE="$ENV_FILE_OVERRIDE"
        [[ "$ENV_FILE" = /* ]] || ENV_FILE="$PROJECT_DIR/$ENV_FILE"
        ENVIRONMENT_NAME="custom"
    else
        if [[ -z "$REQUESTED_ENV" ]]; then
            if [[ "$mode" = "prod" ]]; then
                REQUESTED_ENV="production"
            else
                REQUESTED_ENV="local"
            fi
        fi

        case "$(printf '%s' "$REQUESTED_ENV" | tr '[:upper:]' '[:lower:]')" in
            local|dev|development)
                ENVIRONMENT_NAME="local"
                ENV_FILE="$PROJECT_DIR/.env.local"
                ;;
            staging|stage)
                ENVIRONMENT_NAME="staging"
                ENV_FILE="$PROJECT_DIR/.env.staging"
                ;;
            cloud|prod|production)
                ENVIRONMENT_NAME="production"
                ENV_FILE="$PROJECT_DIR/.env.prod"
                ;;
            *)
                echo "Invalid environment '$REQUESTED_ENV'. Use local, staging, or production." >&2
                exit 1
                ;;
        esac
    fi

    export ENV_FILE
}

# Run Docker Compose with the selected env file and isolated project name.
compose() {
    local compose_file="$1"
    shift
    docker compose --env-file "$ENV_FILE" --project-name "$COMPOSE_PROJECT_NAME" \
        -f "$compose_file" "$@"
}

# Show selection metadata without starting Docker containers or exposing secrets.
show_config() {
    validate_env_file
    local supabase_url
    supabase_url="$(awk -F= '/^NEXT_PUBLIC_SUPABASE_URL=/{print $2; exit}' "$ENV_FILE")"

    echo "Environment: $ENVIRONMENT_NAME"
    echo "Env file: $ENV_FILE"
    echo "Supabase: ${supabase_url:-<not set>}"
    echo "Compose project: $COMPOSE_PROJECT_NAME"
    echo "Frontend host port: $HOST_FRONTEND_PORT"
    echo "Backend host port: $HOST_BACKEND_PORT"
    echo "Voice WebSocket host port: $HOST_VOICE_WS_PORT"
    echo "OTEL gRPC host port: $HOST_OTEL_GRPC_PORT"
    echo "OTEL HTTP host port: $HOST_OTEL_HTTP_PORT"
    echo "OTEL health host port: $HOST_OTEL_HEALTH_PORT"
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed or not in PATH${NC}"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Function to validate the selected environment file
validate_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${RED}Error: environment file not found: $ENV_FILE${NC}"
        echo "Create it from the matching example:"
        echo "  .env.local.example   → .env.local"
        echo "  .env.staging.example → .env.staging"
        echo "  .env.prod.example   → .env.prod"
        exit 1
    fi

    # Check for required environment variables
    local missing_vars=()
    for var in "${REQUIRED_ENV_VARS[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE" || grep -q "^${var}=$" "$ENV_FILE"; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required environment variables in $ENV_FILE:${NC}"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Please set these variables in your $ENV_FILE file"
        exit 1
    fi
}

# Function to check if containers are already running
check_containers_running() {
    local mode=$1
    local compose_file=""

    if [ "$mode" = "dev" ]; then
        compose_file="$COMPOSE_FILE_DEV"
    elif [ "$mode" = "prod" ]; then
        compose_file="$COMPOSE_FILE_PROD"
    else
        return 1
    fi

    # Check if any containers are running for this compose file
    if compose "$compose_file" ps --format "table {{.Names}}\t{{.Status}}" | grep -q "Up"; then
        return 0  # Containers are running
    else
        return 1  # Containers are not running
    fi
}

# Function to check if voice-ws is running
check_voice_ws_running() {
    local mode=$1
    local service_name=""

    if [ "$mode" = "dev" ]; then
        service_name="voice-ws-dev"
    elif [ "$mode" = "prod" ]; then
        service_name="voice-ws"
    else
        return 1
    fi

    local compose_file=""
    if [ "$mode" = "dev" ]; then
        compose_file="$COMPOSE_FILE_DEV"
    elif [ "$mode" = "prod" ]; then
        compose_file="$COMPOSE_FILE_PROD"
    else
        return 1
    fi

    # Check if voice-ws service is running
    if compose "$compose_file" ps "$service_name" | grep -q "Up"; then
        return 0  # voice-ws is running
    else
        return 1  # voice-ws is not running
    fi
}

# Function to build development images
build_dev() {
    echo -e "${BLUE}Building development images...${NC}"
    cd "$PROJECT_DIR"
    validate_env_file
    compose "$COMPOSE_FILE_DEV" build
    echo -e "${GREEN}Development images built successfully!${NC}"
}

# Function to build production images
build_prod() {
    echo -e "${BLUE}Building production images...${NC}"
    cd "$PROJECT_DIR"
    validate_env_file
    compose "$COMPOSE_FILE_PROD" build
    echo -e "${GREEN}Production images built successfully!${NC}"
}

# Function to start development voice-ws
start_voice_ws_dev() {
    echo -e "${GREEN}Starting development voice-ws...${NC}"
    cd "$PROJECT_DIR"
    validate_env_file

    # Check if worker is already running
    if check_voice_ws_running "dev"; then
        echo -e "${YELLOW}Development voice-ws is already running${NC}"
        return 0
    fi

    compose "$COMPOSE_FILE_DEV" up -d voice-ws-dev
    echo -e "${GREEN}Development voice-ws started successfully!${NC}"
}

# Function to start production voice-ws
start_voice_ws_prod() {
    echo -e "${GREEN}Starting production voice-ws...${NC}"
    cd "$PROJECT_DIR"
    validate_env_file

    # Check if worker is already running
    if check_voice_ws_running "prod"; then
        echo -e "${YELLOW}Production voice-ws is already running${NC}"
        return 0
    fi

    compose "$COMPOSE_FILE_PROD" up -d voice-ws
    echo -e "${GREEN}Production voice-ws started successfully!${NC}"
}

# Function to start development containers
start_dev() {
    echo -e "${GREEN}Starting development containers...${NC}"
    cd "$PROJECT_DIR"
    validate_env_file

    # Check if containers are already running
    if check_containers_running "dev"; then
        echo -e "${YELLOW}Development containers are already running${NC}"
        show_dev_urls
        return 0
    fi

    compose "$COMPOSE_FILE_DEV" up -d
    echo -e "${GREEN}Development containers started successfully!${NC}"
    show_dev_urls

    # Start voice-ws
    start_voice_ws_dev
}

# Function to start production containers
start_prod() {
    echo -e "${GREEN}Starting production containers...${NC}"
    cd "$PROJECT_DIR"
    validate_env_file

    # Check if containers are already running
    if check_containers_running "prod"; then
        echo -e "${YELLOW}Production containers are already running${NC}"
        show_prod_urls
        return 0
    fi

    compose "$COMPOSE_FILE_PROD" up -d
    echo -e "${GREEN}Production containers started successfully!${NC}"
    show_prod_urls

    # Start voice-ws
    start_voice_ws_prod
}

# Function to show development URLs
show_dev_urls() {
    echo ""
    echo -e "${PURPLE}Development URLs:${NC}"
    echo "Frontend: http://localhost:$HOST_FRONTEND_PORT"
    echo "Backend: http://localhost:$HOST_BACKEND_PORT"
    echo "Health check: http://localhost:$HOST_BACKEND_PORT/health"
    echo ""
}

# Function to show production URLs
show_prod_urls() {
    echo ""
    echo -e "${PURPLE}Production URLs:${NC}"
    echo "Frontend: http://localhost:$HOST_FRONTEND_PORT"
    echo "Backend: http://localhost:$HOST_BACKEND_PORT"
    echo "Health check: http://localhost:$HOST_BACKEND_PORT/health"
    echo ""
}

# Function to stop development voice-ws
stop_voice_ws_dev() {
    echo -e "${YELLOW}Stopping development voice-ws...${NC}"
    cd "$PROJECT_DIR"

    # Check if worker is running
    if ! check_voice_ws_running "dev"; then
        echo -e "${YELLOW}Development voice-ws is not running${NC}"
        return 0
    fi

    compose "$COMPOSE_FILE_DEV" stop voice-ws-dev
    echo -e "${GREEN}Development voice-ws stopped successfully!${NC}"
}

# Function to stop production voice-ws
stop_voice_ws_prod() {
    echo -e "${YELLOW}Stopping production voice-ws...${NC}"
    cd "$PROJECT_DIR"

    # Check if worker is running
    if ! check_voice_ws_running "prod"; then
        echo -e "${YELLOW}Production voice-ws is not running${NC}"
        return 0
    fi

    compose "$COMPOSE_FILE_PROD" stop voice-ws
    echo -e "${GREEN}Production voice-ws stopped successfully!${NC}"
}

# Function to stop development containers
stop_dev() {
    echo -e "${YELLOW}Stopping development containers...${NC}"
    cd "$PROJECT_DIR"

    # Check if containers are running
    if ! check_containers_running "dev"; then
        echo -e "${YELLOW}Development containers are not running${NC}"
        return 0
    fi

    compose "$COMPOSE_FILE_DEV" down
    echo -e "${GREEN}Development containers stopped successfully!${NC}"

    # Stop voice-ws
    stop_voice_ws_dev
}

# Function to stop production containers
stop_prod() {
    echo -e "${YELLOW}Stopping production containers...${NC}"
    cd "$PROJECT_DIR"

    # Check if containers are running
    if ! check_containers_running "prod"; then
        echo -e "${YELLOW}Production containers are not running${NC}"
        return 0
    fi

    compose "$COMPOSE_FILE_PROD" down
    echo -e "${GREEN}Production containers stopped successfully!${NC}"

    # Stop voice-ws
    stop_voice_ws_prod
}

# Function to restart development containers
restart_dev() {
    echo -e "${YELLOW}Restarting development containers...${NC}"
    stop_dev
    sleep 2
    start_dev
}

# Function to restart production containers
restart_prod() {
    echo -e "${YELLOW}Restarting production containers...${NC}"
    stop_prod
    sleep 2
    start_prod
}

# Function to show container logs
show_logs() {
    local mode=$1
    cd "$PROJECT_DIR"

    if [ "$mode" = "dev" ]; then
        echo -e "${BLUE}Showing development container logs...${NC}"
        if ! check_containers_running "dev"; then
            echo -e "${YELLOW}Development containers are not running${NC}"
            return 0
        fi
        compose "$COMPOSE_FILE_DEV" logs -f
    elif [ "$mode" = "prod" ]; then
        echo -e "${BLUE}Showing production container logs...${NC}"
        if ! check_containers_running "prod"; then
            echo -e "${YELLOW}Production containers are not running${NC}"
            return 0
        fi
        compose "$COMPOSE_FILE_PROD" logs -f
    else
        echo -e "${RED}Invalid mode for logs. Use 'dev' or 'prod'.${NC}"
        exit 1
    fi
}

# Function to show container status
show_status() {
    echo -e "${BLUE}Development containers status:${NC}"
    cd "$PROJECT_DIR"
    compose "$COMPOSE_FILE_DEV" ps

    echo -e "\n${BLUE}Production containers status:${NC}"
    cd "$PROJECT_DIR"
    compose "$COMPOSE_FILE_PROD" ps
}

# Validate the selected environment and resolve the complete host-facing port map.
initialize_runtime_config() {
    validate_env_file
    resolve_port_config
}

# Main script logic
main() {
    parse_options "$@"
    set -- "${CLI_ARGS[@]}"

    if [ $# -eq 0 ]; then
        print_usage
        exit 1
    fi

    local action=$1
    local mode="${2:-}"
    local selection_mode="$mode"
    if [ "$mode" = "voice-ws" ]; then
        selection_mode="${3:-}"
    fi
    select_environment_file "$action" "$selection_mode"
    initialize_runtime_config

    if [ "$action" = "config" ]; then
        show_config
        return 0
    fi

    check_docker

    case $action in
        start)
            if [ "$mode" = "dev" ]; then
                start_dev
            elif [ "$mode" = "prod" ]; then
                start_prod
            elif [ "$mode" = "voice-ws" ]; then
                if [ "${3:-}" = "dev" ]; then
                    start_voice_ws_dev
                elif [ "${3:-}" = "prod" ]; then
                    start_voice_ws_prod
                else
                    echo -e "${RED}Invalid voice-ws mode. Use 'dev' or 'prod'.${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}Invalid mode. Use 'dev', 'prod', or 'voice-ws'.${NC}"
                exit 1
            fi
            ;;
        stop)
            if [ "$mode" = "dev" ]; then
                stop_dev
            elif [ "$mode" = "prod" ]; then
                stop_prod
            elif [ "$mode" = "voice-ws" ]; then
                if [ "${3:-}" = "dev" ]; then
                    stop_voice_ws_dev
                elif [ "${3:-}" = "prod" ]; then
                    stop_voice_ws_prod
                else
                    echo -e "${RED}Invalid voice-ws mode. Use 'dev' or 'prod'.${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}Invalid mode. Use 'dev', 'prod', or 'voice-ws'.${NC}"
                exit 1
            fi
            ;;
        restart)
            if [ "$mode" = "dev" ]; then
                restart_dev
            elif [ "$mode" = "prod" ]; then
                restart_prod
            else
                echo -e "${RED}Invalid mode. Use 'dev' or 'prod'.${NC}"
                exit 1
            fi
            ;;
        logs)
            if [ "$mode" = "dev" ] || [ "$mode" = "prod" ]; then
                show_logs "$mode"
            else
                echo -e "${RED}Invalid mode. Use 'dev' or 'prod'.${NC}"
                exit 1
            fi
            ;;
        build)
            if [ "$mode" = "dev" ]; then
                build_dev
            elif [ "$mode" = "prod" ]; then
                build_prod
            else
                echo -e "${RED}Invalid mode. Use 'dev' or 'prod'.${NC}"
                exit 1
            fi
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            print_usage
            ;;
        *)
            echo -e "${RED}Invalid action: $action${NC}"
            print_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
