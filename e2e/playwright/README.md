# E2E Tests

End-to-end testing using Playwright.

## Setup

Install dependencies:
```bash
pip install playwright
playwright install chromium
```

## Running Tests

The supported runner builds an isolated Docker stack, initializes a disposable
database, applies all migrations, runs the full suite, and tears the stack down:

```bash
./scripts/run-e2e.sh
```

Use `--video-on` when every test needs a browser recording. For quick collection
or a focused local check, run pytest directly after the stack is available:

```bash
pytest -q e2e/tests/test_public_agent_pages.py
```

## Test Files

- `test_playwright.py` - Basic backend and frontend health checks
- `test_all_pages.py` - Comprehensive testing of all public and protected pages
- `../tests/test_public_agent_pages.py` - Organization publishing, passphrase-gated public pages, demo pages, visualizer selection, and dashboard demo/public controls
