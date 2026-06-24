# Suggested Commands

## Dev servers (via Docker from project root)
```
./start.sh build dev    # Build images
./start.sh start dev    # Start containers
./start.sh stop dev     # Stop containers
./start.sh restart dev  # Restart containers
./start.sh logs dev     # View logs
```

## Backend (inside backend container)
```
docker exec a1-voice-agent-platform-backend-dev-1 pytest backend/tests/
docker exec a1-voice-agent-platform-backend-dev-1 pytest backend/tests/path/to/test.py
docker exec a1-voice-agent-platform-backend-dev-1 black .
docker exec a1-voice-agent-platform-backend-dev-1 isort .
docker exec a1-voice-agent-platform-backend-dev-1 flake8 src/ --max-line-length=88 --extend-ignore=E203,W503
docker exec a1-voice-agent-platform-backend-dev-1 alembic upgrade head
docker exec a1-voice-agent-platform-backend-dev-1 alembic revision --autogenerate -m "description"
```

## Backend (local venv — from backend/ dir)
```
cd backend && source .venv/bin/activate
pytest tests/
black .
isort .
```

## Frontend (inside frontend container — type checking only)
```
docker exec a1-voice-agent-platform-frontend-dev-1 npx tsc --noEmit
docker exec a1-voice-agent-platform-frontend-dev-1 npm run lint
```

## Frontend (on host — tests)
```
cd frontend && npx vitest run
cd frontend && npx vitest run path/to/test.ts
```

## Pre-commit (from project root)
```
pre-commit run --all-files
```

## Git
```
git status
git diff --cached
git log --oneline -10
```
