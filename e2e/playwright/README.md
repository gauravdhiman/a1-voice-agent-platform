# E2E Tests

End-to-end testing using Playwright.

## Setup

Install dependencies:
```bash
pip install playwright
playwright install chromium
```

## Running Tests

Start servers and run tests:
```bash
python e2e/playwright/test_playwright.py
python e2e/playwright/test_all_pages.py
```

## Test Files

- `test_playwright.py` - Basic backend and frontend health checks
- `test_all_pages.py` - Comprehensive testing of all public and protected pages
