# Setup Guide

This guide provides detailed instructions on how to set up and configure the AI Voice Agent Platform for both local development and containerized environments.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose**: For containerized development and deployment
- **Python 3.11+**: For the FastAPI backend (if running non-containerized)
- **Node.js 18+ & npm/yarn**: For the Next.js frontend (if running non-containerized)
- **Supabase Account**: For database, authentication, and storage services
- **New Relic Account (Optional)**: For OpenTelemetry observability

## Environment Configuration

The project uses different environment files depending on your development approach:

### Local Development (Non-containerized)
- **Backend**: `backend/.env` (copy from `backend/.env.example`)
- **Frontend**: `frontend/.env.local` (copy from `frontend/.env.local.example`)

### Containerized Development
- **Root**: `.env` (copy from `.env.example`)

**Important**: The service-specific environment files (`backend/.env` and `frontend/.env.local`) are **only for non-containerized local development**. When running services in Docker containers, the root `.env` file is used instead.

### Supabase Configuration

#### Required Keys

The Supabase configuration requires different environment variables for frontend and backend:

1. **SUPABASE_SERVICE_KEY**: Used only by the backend for administrative operations (service role key)
2. **SUPABASE_ANON_KEY**: Used by the backend for certain operations (anon key)
3. **NEXT_PUBLIC_SUPABASE_URL**: Used by the frontend (must be prefixed with NEXT_PUBLIC_ to be accessible in browser)
4. **NEXT_PUBLIC_SUPABASE_ANON_KEY**: Used by the frontend (must be prefixed with NEXT_PUBLIC_ to be accessible in browser)

#### Getting Your Supabase Database Password

To configure the `DATABASE_URL` environment variable for Alembic migrations, you'll need your Supabase database password:

1. Go to your Supabase project dashboard
2. Navigate to "Settings" → "Database"
3. Under "Connection Info", you'll see:
   - **Host**: Your project reference followed by `.supabase.co`
   - **Port**: 5432
   - **User**: postgres
   - **Password**: This is your database password (different from your Supabase project password)
4. Use this information to construct your `DATABASE_URL`:
   ```
   postgresql://postgres:[DATABASE-PASSWORD]@[PROJECT-REF].supabase.co:5432/postgres
   ```

#### OAuth Providers

To enable OAuth providers like Google, you need to:

1. **Configure the OAuth provider in your Supabase project dashboard**:
   - Go to Authentication → Providers
   - Enable the desired provider (e.g., Google)
   - Configure the provider settings with your OAuth credentials

2. **Set the redirect URLs in your OAuth provider's dashboard**:
   - Use the Supabase callback URL: `https://YOUR_SUPABASE_PROJECT_ID.supabase.co/auth/v1/callback`
   - You can find this URL in your Supabase dashboard under Authentication → Settings

**Note**: You do not need to create any custom callback endpoints in your frontend or backend. Supabase handles the entire OAuth flow for you.

For detailed instructions on setting up OAuth providers, see [OAuth Setup](../02_core_systems/oauth_setup.md).

### OpenTelemetry Configuration

The project uses OpenTelemetry for observability with New Relic as the backend. For detailed information about the OpenTelemetry implementation, see [OpenTelemetry Implementation](../02_core_systems/opentelemetry_implementation.md).

#### New Relic License Key

All environments require a New Relic license key:

```
NEW_RELIC_LICENSE_KEY=your-new-relic-license-key-here
NEW_RELIC_APP_NAME=AI Voice Agent Platform
```

#### Backend OpenTelemetry Configuration

The backend uses gRPC to communicate with the OpenTelemetry Collector:

```bash
# OpenTelemetry Configuration
OTEL_ENABLED=true
OTEL_SERVICE_NAME=ai-voice-agent-platform-backend

# Traces
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_TRACES_INSECURE=true

# Metrics
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_METRICS_INSECURE=true

# Logs
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_LOGS_INSECURE=true

# OpenTelemetry Configuration - FastAPI Instrumentation
# Exclude health check endpoints from tracing to reduce noise
OTEL_PYTHON_FASTAPI_EXCLUDED_URLS=/health,/health/ready,/health/live
```

#### Frontend OpenTelemetry Configuration

The frontend uses HTTP/protobuf to communicate with the OpenTelemetry Collector:

```bash
# OpenTelemetry Configuration (Optional for local development)
NEXT_PUBLIC_OTEL_ENABLED=true
NEXT_PUBLIC_OTEL_SERVICE_NAME=ai-voice-agent-platform-frontend

# Frontend OpenTelemetry Configuration - Traces
# Use HTTP/protobuf for frontend since it runs in browser
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:4318/v1/traces
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf

# Frontend OpenTelemetry Configuration - Metrics
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://127.0.0.1:4318/v1/metrics

# Frontend OpenTelemetry Configuration - Logs
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://127.0.0.1:4318/v1/logs

# Next.js OpenTelemetry Controls
# Set to 1 to see more detailed Next.js internal spans (increases noise)
# Set to 0 to reduce Next.js internal tracing (recommended for production)
NEXT_OTEL_VERBOSE=0

# Disable Next.js fetch instrumentation if using custom fetch tracing
NEXT_OTEL_FETCH_DISABLED=1
```

#### Containerized Environment OpenTelemetry Configuration

In containerized environments, both frontend and backend send telemetry to the OpenTelemetry Collector:

```bash
# New Relic Configuration for OpenTelemetry
NEW_RELIC_LICENSE_KEY=your-new-relic-license-key-here
NEW_RELIC_APP_NAME=AI Voice Agent Platform

# OpenTelemetry Configuration - Traces
OTEL_ENABLED=true
OTEL_SERVICE_NAME=ai-voice-agent-platform
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_TRACES_INSECURE=true

# OpenTelemetry Configuration - Metrics
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_METRICS_INSECURE=true

# OpenTelemetry Configuration - Logs
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_LOGS_INSECURE=true

# OpenTelemetry Configuration - FastAPI Instrumentation
OTEL_PYTHON_FASTAPI_EXCLUDED_URLS=/health,/health/ready,/health/live

# Frontend OpenTelemetry Configuration
NEXT_PUBLIC_OTEL_ENABLED=true
NEXT_PUBLIC_OTEL_SERVICE_NAME=ai-voice-agent-platform-frontend
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318/v1/traces
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://localhost:4318/v1/metrics
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://localhost:4318/v1/logs
NEXT_OTEL_VERBOSE=0
NEXT_OTEL_FETCH_DISABLED=1
```

## Local Development Setup

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor

# Run the application
python main.py
```

The API will be available at [http://localhost:8000](http://localhost:8000)

API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment configuration
cp .env.local.example .env.local

# Edit .env.local with your configuration
nano .env.local  # or use your preferred editor

# Run the development server
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000)

### Worker Setup

```bash
# Navigate to worker directory
cd worker

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your configuration
nano .env

# Run the worker
python src/worker.py
```

### Database Migrations

```bash
# Navigate to backend directory
cd backend

# Apply all pending migrations
alembic upgrade head

# Rollback the last migration
alembic downgrade -1

# Create a new migration
alembic revision -m "Description of the migration"
```

## Docker Development Setup

The project includes a `start.sh` script that simplifies starting, stopping, and managing Docker containers.

### Development Mode

Starts the frontend, backend, worker, Supabase Studio, and OpenTelemetry Collector with hot reloading for active development.

```bash
./start.sh start dev
```

**Access URLs (Development Mode)**:
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Backend API Docs**: `http://localhost:8000/docs`
- **Supabase Studio**: `http://localhost:54323`
- **OpenTelemetry Collector**: `http://localhost:4318` (HTTP/protobuf)

### Production Mode

Starts the frontend, backend, and worker in a production-like environment.

```bash
./start.sh start prod
```

**Access URLs (Production Mode)**:
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Backend API Docs**: `http://localhost:8000/docs`

### Other Useful Commands

```bash
# Stop services
./start.sh stop dev
./start.sh stop prod

# Restart services
./start.sh restart dev
./start.sh restart prod

# Build images
./start.sh build dev
./start.sh build prod

# View logs
./start.sh logs dev
./start.sh logs prod

# Check status
./start.sh status

# Show help
./start.sh help
```

### Running Database Migrations in Docker

#### Development Environment
```bash
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic upgrade head
```

#### Production Environment
```bash
docker compose -f docker-compose.yml run --rm backend alembic upgrade head
```

## Stripe Configuration

To enable billing functionality:

1. **Create a Stripe account** at [stripe.com](https://stripe.com)

2. **Get your API keys**:
   - Go to Stripe Dashboard → Developers → API keys
   - Copy your **Publishable key** and **Secret key**

3. **Configure webhooks**:
   - Go to Stripe Dashboard → Developers → Webhooks
   - Add endpoint: `https://your-domain.com/api/billing/webhooks`
   - Select events: `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`

4. **Add keys to `.env`**:
   ```bash
   STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key
   STRIPE_SECRET_KEY=sk_live_your_secret_key
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
   ```

For detailed information about the billing system, see [Billing System](../02_core_systems/billing_system.md).

## LiveKit Configuration

The platform uses LiveKit for real-time voice communication.

1. **Create a LiveKit account** at [livekit.io](https://livekit.io)

2. **Get your API keys**:
   - Go to LiveKit Dashboard → Projects → API Keys
   - Copy your **API Key** and **API Secret**

3. **Add keys to `.env`**:
   ```bash
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
   ```

4. **Configure phone numbers** (for outbound calling):
   - Purchase a phone number in LiveKit Dashboard
   - Configure the number to route to your agent room

## Email Configuration

The platform uses Resend.com for email notifications.

1. **Create a Resend account** at [resend.com](https://resend.com)

2. **Get your API key**:
   - Go to Resend Dashboard → API Keys
   - Create a new API key

3. **Add key to `.env`**:
   ```bash
   RESEND_API_KEY=re_your_api_key
   RESEND_FROM_EMAIL=noreply@yourdomain.com
   RESEND_FROM_NAME=AI Voice Agent Platform
   ```

For detailed information about the notification system, see [Notification System](../02_core_systems/notification_system.md).

## Verification Steps

After setup, verify your installation:

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00.000Z",
  "version": "1.0.0",
  "environment": "development"
}
```

### 2. Check Frontend
Navigate to `http://localhost:3000` in your browser.

### 3. Check Database Connection
```bash
# From backend directory
python -c "from config.supabase import get_supabase_client; print('Connected!' if get_supabase_client() else 'Failed')"
```

### 4. Check Worker Logs
```bash
# In Docker
./start.sh logs dev | grep worker

# Local
tail -f worker/logs/worker.log
```

### 5. Test Voice Agent
1. Create an account and organization
2. Create a voice agent with a system prompt
3. Add a tool (e.g., Google Calendar)
4. Make a test call to verify functionality

## Troubleshooting

### Common Issues

#### Port Conflicts
If you encounter port conflicts on ports 3000, 8000, 54323, or 4318:
```bash
# Find and kill the process using the port
lsof -ti:3000 | xargs kill -9

# Or use a different port by modifying .env
```

#### Docker Issues
If Docker commands fail:
```bash
# Restart Docker daemon
# (macOS) Restart Docker Desktop
# (Linux) sudo systemctl restart docker

# Clean up Docker resources
docker system prune -a

# Rebuild images
./start.sh build dev
```

#### Database Connection Issues
If you can't connect to Supabase:
- Verify DATABASE_URL in `.env` is correct
- Check Supabase project is active
- Ensure your IP is allowed in Supabase settings
- Verify database password is correct

#### Migration Failures
If Alembic migrations fail:
```bash
# Check current migration state
alembic current

# Check migration history
alembic history

# Force a specific version (use with caution)
alembic stamp <revision_id>

# Fix migration by editing the file
# Then try again
alembic upgrade head
```

#### Worker Not Connecting to LiveKit
If the worker can't connect to LiveKit:
- Verify LIVEKIT_API_KEY and LIVEKIT_API_SECRET are correct
- Check LIVEKIT_URL is accessible
- Ensure your IP is allowed in LiveKit security settings
- Check firewall settings

#### OpenTelemetry Not Sending Data
If telemetry isn't showing up in New Relic:
- Verify NEW_RELIC_LICENSE_KEY is correct
- Check OTEL_ENABLED is set to true
- Verify collector is running: `docker ps | grep otel-collector`
- Check collector logs: `./start.sh logs dev | grep otel-collector`

## Next Steps

- Read [Architecture Overview](../01_architecture/) to understand system design
- Learn about [Voice Agents](../01_architecture/voice_agents.md)
- Understand [Tool System](../03_implementation/tool_system.md)
- Review [Development Guidelines](../../AGENTS.md)
- Check [Testing Guide](../04_development_guides/testing.md)

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [LiveKit Documentation](https://docs.livekit.io/)
- [Stripe Documentation](https://stripe.com/docs)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
