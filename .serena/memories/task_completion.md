# Task Completion Checklist

When a coding task is considered done, verify ALL:

## Python (backend/shared/worker)
1. Syntax check: `python -m py_compile <file>` on every changed .py file
2. Format: `black .` and `isort .`
3. Lint: `flake8 src/ --max-line-length=88 --extend-ignore=E203,W503`
4. Tests: `pytest tests/` — all pass
5. Pre-commit: `pre-commit run --all-files`

## Frontend
1. Type check: `docker exec a1-voice-agent-platform-frontend-dev-1 npx tsc --noEmit`
2. Lint: `docker exec a1-voice-agent-platform-frontend-dev-1 npm run lint`
3. Tests (on host): `cd frontend && npx vitest run`
4. NEVER run `npm run build` or `next build` in dev container (overwrites .next, causes ENOENT)

## Database
1. If migration created: `alembic upgrade head` (with user permission)
2. Update `docs/DATABASE_SCHEMA.md` with new tables/columns/ER diagram
3. Add migration to migration history section

## Documentation
1. Update relevant `docs/` files if API/feature/architecture changed
2. Update `AGENTS.md` if new conventions discovered
3. Keep cross-references accurate

## Browser validation (if UI changed)
1. Open `http://localhost:3000`
2. Login: `test@cogninets.local` / `Password123!`
3. Verify the change works from user perspective
