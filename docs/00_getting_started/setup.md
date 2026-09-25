# Setup Guide

This guide provides detailed instructions on how to set up and configure the AI Voice Agent Platform for both local development and containerized environments.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose**: For containerized development and deployment
- **Python 3.11+**: For the FastAPI backend (if running non-containerized)
- **Node.js 18+ & npm/yarn**: For the Next.js frontend (if running non-containerized)
- **Supabase Account**: For database, authentication, and storage services

## Environment Configuration

The project has three canonical root environment files:

- `.env.local` — local Supabase; default for `./start.sh start dev`
- `.env.staging` — cloud staging Supabase; use `./start.sh start dev --env staging`
- `.env.prod` — production Supabase; default for `./start.sh start prod` and deployment

Create each from its matching `.example` template. Do not copy any file into a
root `.env`; the startup script and Compose files select the correct file.

The supported development workflow is containerized. The service-specific
`backend/.env` and `frontend/.env.local` files are compatibility files for
advanced non-containerized workflows only.

### Supabase Configuration

#### Required Keys

The Supabase configuration requires different environment variables for frontend and backend:

1. **SUPABASE_SERVICE_KEY**: Used only by the backend for administrative operations (service role key)
2. **SUPABASE_ANON_KEY**: Used by the backend for certain operations (anon key)
3. **NEXT_PUBLIC_SUPABASE_URL**: Used by the frontend (must be prefixed with NEXT*PUBLIC* to be accessible in browser)
4. **NEXT_PUBLIC_SUPABASE_ANON_KEY**: Used by the frontend (must be prefixed with NEXT*PUBLIC* to be accessible in browser)
5. **NEXT_PUBLIC_GOOGLE_CLIENT_ID**: Google Web Client ID for popup sign-in

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

The current contract is documented in the
[observability operator guide](../05_operations/observability.md). The
canonical local and staging templates keep `OTEL_ENABLED=false`; the isolated
worktree launcher enables its private collector for telemetry testing. The
production template is also disabled until the authenticated cloud collector,
Grafana Cloud project and Langfuse project have been provisioned. Frontend
telemetry remains disabled; browser requests carry only a content-free W3C
trace context for correlation.

The detailed production and local workflow is in the operator guide.

Do not add legacy provider credentials or send prompts, transcripts, audio, or
tool payloads to an observability backend. The operator guide describes the
metadata-only call trace and the production rollout.

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

# From the repository root, create .env.local once from .env.local.example.
# Select staging instead with: ENV_FILE=.env.staging python backend/main.py
cd ..

# Run the application
python backend/main.py
```

The API will be available at [http://localhost:8000](http://localhost:8000)

API documentation will be available at [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend Setup (advanced direct workflow)

The recommended frontend workflow is to run the complete stack from the
repository root with `./start.sh`. The nested file below is a Next.js
compatibility file for running only the frontend outside Docker; it is not an
environment selector.

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy the frontend-only compatibility configuration
cp .env.local.example .env.local

# Edit .env.local with your configuration
nano .env.local  # or use your preferred editor

# Run the development server
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000)

### voice-ws Setup

```bash
# Navigate to voice-ws directory
cd voice-ws

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Use the root selected environment file. The supported workflow is Docker;
# for a direct worker process, export variables from that selected file first.
# Example: ./start.sh start voice-ws dev --env local

# Run voice-ws
uvicorn src.main:app --host 0.0.0.0 --port 7860 --reload
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

Starts the frontend, backend, voice-ws and Supabase Studio with hot reloading.
Application telemetry is disabled in the regular stack. Use the isolated
worktree launcher when you need a private collector and Grafana for a trace.

```bash
./start.sh start dev
```

**Access URLs (Development Mode)**:

- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Backend API Docs**: `http://localhost:8000/docs`
- **Supabase Studio**: `http://localhost:54323`
- **OpenTelemetry Collector**: started only by `./scripts/worktree-stack.sh up`
  on the ports printed by `./scripts/worktree-stack.sh config`

### Production Mode

Starts the frontend, backend, and voice-ws in a production-like environment.

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

4. **Add keys to the selected environment file** (normally `.env.local`):
   ```bash
   STRIPE_PUBLISHABLE_KEY=pk_live_your_publishable_key
   STRIPE_SECRET_KEY=sk_live_your_secret_key
   STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
   ```

For detailed information about the billing system, see [Billing System](../02_core_systems/billing_system.md).

## voice-ws Configuration

The platform uses **`voice-ws`** (Pipecat WebSocket) for browser test calls and Twilio Media Streams phone calls.

1. **Ensure voice-ws is running** (default with `./start.sh start dev`)

2. **Add to the selected root environment file** (backend + voice-ws share `JWT_SECRET_KEY`):

   ```bash
   JWT_SECRET_KEY=<openssl rand -hex 32>
   VOICE_WS_PUBLIC_URL=ws://localhost:7860
   GEMINI_API_KEY=your_gemini_key
   ```

3. **Phone calls (Twilio Media Streams)** — Twilio must reach a public WebSocket:

   ```bash
   VOICE_WS_TWILIO_URL=wss://<your-ngrok-or-prod-host>
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   ```

   Tunnel example: `ngrok http 7860` → set `VOICE_WS_TWILIO_URL=wss://<ngrok-host>`.

4. **Configure phone numbers**:
   - Platform admins configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and a public `API_BASE_URL`.
   - Users can search and purchase a number in the 24x7 AI dashboard; the backend configures the voice and status callbacks in the same Twilio purchase request.
   - Users who already own a Twilio number can use **Connect Existing Number**. The returned tokenized voice and status URLs must be saved on that Twilio number once. The platform never needs the customer's Twilio auth token in v1.
   - Set `PHONE_NUMBER_BILLING_GRACE_PERIOD_DAYS=7` for the deployment fallback. `PHONE_NUMBER_BILLING_CHECK_INTERVAL_HOURS` and `PHONE_NUMBER_RELEASE_RETRY_INTERVAL_HOURS` default to daily. After migration, platform administrators can manage these values in **Platform → Settings → Phone numbers**.
   - For outbound calling design, see **[Outbound phone calls](../03_implementation/outbound_phone_calls.md)**

## Email Configuration

The platform uses Resend.com for email notifications.

1. **Create a Resend account** at [resend.com](https://resend.com)

2. **Get your API key**:

   - Go to Resend Dashboard → API Keys
   - Create a new API key

3. **Add the key to the selected root environment file**:
   ```bash
   RESEND_API_KEY=re_your_api_key
   RESEND_FROM_EMAIL=noreply@yourdomain.com
   RESEND_FROM_NAME=24x7 AI
   ```

For detailed information about the notification system, see [Notification System](../02_core_systems/notification_system.md).

## Verification Steps

After setup, verify your installation:

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response when Supabase is ready:

```json
{
  "status": "ready"
}
```

### 2. Check Frontend

Navigate to `http://localhost:3000` in your browser.

### 3. Check Database Connection

```bash
# From backend directory
python -c "from config.supabase import get_supabase_client; print('Connected!' if get_supabase_client() else 'Failed')"
```

### 4. Check voice-ws Logs

```bash
# In Docker
./start.sh logs dev | grep voice-ws

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

# Or use a different port by modifying the selected root environment file
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

- Verify DATABASE_URL in the selected root environment file is correct
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

#### voice-ws Not Accepting WebSocket Connections

If browser test calls or phone Media Streams fail:

- Verify `JWT_SECRET_KEY` matches on backend and voice-ws
- Check `curl http://localhost:7860/health`
- For phone: ensure `VOICE_WS_TWILIO_URL` is a public `wss://` URL (not localhost)
- Confirm Twilio voice webhook points at the backend `/api/v1/voice/twilio/incoming`
- Check firewall settings

#### OpenTelemetry Not Sending Data

If telemetry isn't showing up in Grafana:

- Verify the selected environment has `OTEL_ENABLED=true` and all three OTLP
  endpoints and headers point at the authenticated collector
- For local traces, verify the isolated stack is running with
  `./scripts/worktree-stack.sh status` and inspect its collector logs.
- For production, check the collector host and Grafana Cloud exporter health;
  application containers never receive Grafana or Langfuse credentials.

## Next Steps

- Read [Architecture Overview](../01_architecture/) to understand system design
- Learn about [Voice Agents](../01_architecture/voice_agents.md)
- Understand [Tool System](../03_implementation/tool_system.md)
- Review [Development Guidelines](../../AGENTS.md)
- Check [Testing Guide](../04_development_guides/testing.md)

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Pipecat Documentation](https://docs.pipecat.ai/)
- [Stripe Documentation](https://stripe.com/docs)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
