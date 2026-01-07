# Quick Start Guide

This guide provides a rapid way to get the AI Voice Agent Platform up and running using Docker Compose.

## Prerequisites

Ensure you have **Docker & Docker Compose** installed on your system.

## Environment Configuration

1. **Copy the example environment file**:
   ```bash
   cp .env.example .env
   ```

2. **Update `.env` with your Supabase credentials**:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_SERVICE_KEY` - Backend service role key (admin access)
   - `SUPABASE_ANON_KEY` - Anon key for public access
   - `NEXT_PUBLIC_SUPABASE_URL` - Frontend Supabase URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Frontend anon key

3. **Update `DATABASE_URL` in `.env` for Alembic migrations**:
   Replace `your-database-password-here` and `your-project-ref` with your actual Supabase database password and project reference.
   ```
   DATABASE_URL=postgresql://postgres:your-database-password-here@your-project-ref.supabase.co:5432/postgres
   ```

   **To get your database password**:
   1. Go to your Supabase project dashboard
   2. Navigate to "Settings" → "Database"
   3. Under "Connection Info", you'll see your database password (different from your Supabase project password)

4. **Add your New Relic License Key (Optional)**:
   ```
   NEW_RELIC_LICENSE_KEY=your-new-relic-license-key-here
   ```

5. **Configure OAuth providers (Optional)**:
   To enable Google OAuth:
   1. Go to your Supabase project dashboard → Authentication → Providers
   2. Enable Google provider
   3. Configure with your Google OAuth credentials
   4. Set redirect URL: `https://YOUR_PROJECT_ID.supabase.co/auth/v1/callback`

## Running the Application

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
- **OpenTelemetry Collector**: `http://localhost:4318` (HTTP/protobuf), `http://localhost:4317` (gRPC)

### Production Mode

Starts the frontend, backend, and worker in a production-like environment.

```bash
./start.sh start prod
```

**Access URLs (Production Mode)**:
- **Frontend**: `http://localhost:3000`
- **Backend**: `http://localhost:8000`
- **Backend API Docs**: `http://localhost:8000/docs`

## Other Useful Commands

### Stop Services
```bash
./start.sh stop dev    # Stop development containers
./start.sh stop prod   # Stop production containers
```

### Restart Services
```bash
./start.sh restart dev  # Restart development containers
./start.sh restart prod # Restart production containers
```

### Build Images
```bash
./start.sh build dev   # Build development images
./start.sh build prod  # Build production images
```

### View Logs
```bash
./start.sh logs dev    # View development logs
./start.sh logs prod   # View production logs
```

### Check Status
```bash
./start.sh status      # Check container status
./start.sh help        # Show help message
```

## Running Database Migrations

After starting containers, run database migrations:

### Using Docker (Development)
```bash
docker compose -f docker-compose.dev.yml run --rm backend-dev alembic upgrade head
```

### Using Docker (Production)
```bash
docker compose -f docker-compose.yml run --rm backend alembic upgrade head
```

### Using Local Environment
```bash
cd backend
alembic upgrade head
```

## First Steps

Once the application is running:

1. **Create an Account**: Navigate to `http://localhost:3000` and sign up
2. **Create an Organization**: Set up your business organization
3. **Create a Voice Agent**: Configure your first AI voice agent with a system prompt
4. **Add Tools**: Integrate tools (e.g., Google Calendar) to your agent
5. **Test the Agent**: Make a test call to verify functionality

## Troubleshooting

### Docker Issues
- **Port Conflicts**: Ensure no other services are using ports 3000, 8000, 54323, or 4318
- **Docker Not Running**: Start Docker Desktop or Docker daemon
- **Build Failures**: Try `docker system prune -a` to clean up and rebuild

### Database Issues
- **Connection Failures**: Verify DATABASE_URL in `.env` is correct
- **Migration Failures**: Check Supabase is accessible and credentials are valid
- **RLS Issues**: Ensure Row-Level Security policies are applied

### Application Issues
- **Frontend Not Loading**: Check browser console for errors
- **Backend 500 Errors**: Check backend logs with `./start.sh logs dev`
- **Worker Issues**: Worker logs are available via `./start.sh logs dev`

### Common Fixes
```bash
# Rebuild all containers
./start.sh build dev

# Restart all services
./start.sh restart dev

# Clean up Docker resources
docker system prune -a

# View specific service logs
docker compose -f docker-compose.dev.yml logs -f backend-dev
docker compose -f docker-compose.dev.yml logs -f frontend-dev
docker compose -f docker-compose.dev.yml logs -f worker-dev
```

## Next Steps

- Read the complete [Setup Guide](setup.md) for detailed configuration
- Explore [Architecture](../01_architecture/) to understand the system design
- Learn about [Voice Agents](../01_architecture/voice_agents.md)
- Review [Development Guidelines](../../AGENTS.md)

## Getting Help

- Check the [troubleshooting section](../04_operations/troubleshooting.md) for common issues
- Review [Environment Configuration](setup.md#environment-configuration) for detailed setup
- See [Development Setup](../04_development_guides/development_setup.md) for local development
