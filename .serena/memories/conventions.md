# Conventions

## Python
- Type hints always; Pydantic for data models
- Service methods return `tuple[Result, Optional[str]]` (value, error)
- Use `async/await` for all async operations
- `@tracer.start_as_current_span("module.method")` for OpenTelemetry spans
- Classes PascalCase, functions/methods snake_case, constants UPPER_SNAKE_CASE
- Docstrings: comprehensive (purpose, args, returns, raises, example)
- Imports: standard lib → third-party → local (blank lines between)
- Formatter: Black (88-char lines), isort (black profile), flake8

## TypeScript/Frontend
- Interface for component props, `cn()` utility for className
- Service methods return `{success, error?, data?}` object
- Components PascalCase, hooks camelCase with "use" prefix
- Types/interfaces PascalCase, constants UPPER_SNAKE_CASE
- JSDoc on components, hooks, services, utility functions
- No `window.confirm()`/`window.alert()` — use modal Dialog components
- Tailwind CSS v4: plugins via `@plugin` in CSS, NOT in tailwind.config.js

## Testing
- TDD red-green REQUIRED: write failing test first, then implement
- Unit tests: mock DB/HTTP/external services
- Coverage: 100% of changed/added code paths
- pytest markers: `unit`, `integration`, `slow`

## DB/Migrations
- Alembic for all schema changes
- Never run migrations without user permission
- Update `docs/DATABASE_SCHEMA.md` after any migration
- Use Mermaid for all diagrams

## Documentation
- Keep `docs/` organized in sub-folders per module
- Cross-references must be accurate
- Mermaid syntax for diagrams (validated at mermaid.live)

## Files
- Never add comments unless asked
- Never commit without explicit user approval
- Always run lint/typecheck after changes
