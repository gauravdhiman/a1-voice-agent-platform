# Testing Guidelines

## Overview

This document outlines the testing strategy and best practices for ensuring the quality and reliability of the application.

For agent/tool robustness evaluations, use the dedicated
[Agent Evaluation System](./agent-evaluations.md). It runs deterministic
model-facing workflows without real OAuth or provider writes and can replay
captured model/tool traces. Manual voice calls and live provider tests remain
the final integration layer, not the only regression mechanism.

## Types of Tests

- **Unit Tests**: Focus on individual components or functions in isolation.

  - **Frameworks**: `pytest` (Python), `Jest` (JavaScript/TypeScript)
  - **Best Practices**: Test small, isolated units; mock external dependencies.

- **Integration Tests**: Verify the interaction between different components or services.

  - **Frameworks**: `pytest` (Python), `React Testing Library` (JavaScript/TypeScript)
  - **Best Practices**: Test common workflows; use real dependencies where appropriate.

- **End-to-End (E2E) Tests**: Simulate user interactions with the entire application.
  - **Frameworks**: `Cypress`, `Playwright`
  - **Best Practices**: Cover critical user journeys; run on a deployed environment.

## Testing Workflow

1.  **Write Tests First (TDD)**: Consider writing tests before implementing features.
2.  **Run Tests Locally**: Execute tests frequently during development.
3.  **CI/CD Integration**: Ensure tests are run automatically in the continuous integration pipeline.
4.  **Code Coverage**: Aim for high code coverage, but prioritize meaningful tests over coverage percentage.

## Public agent and demo-page coverage

The public-agent feature is intentionally tested across the same boundaries it
uses in production:

| Layer | Coverage |
| --- | --- |
| Shared model | Defaults, slug normalization/validation, and public-description handling |
| Shared service | Active/published filtering, demo slug uniqueness checks, demo enable/disable transitions |
| Backend routes | Public organization access/list/token endpoints, demo metadata/token endpoints, and platform-admin-only demo writes |
| Frontend services | Public metadata, access-token, call-token, and safe error contracts |
| Browser E2E | Open/protected organization pages, public demo page, visualizer default/selection, and dashboard controls |

Run the isolated browser suite with:

```bash
./scripts/run-e2e.sh
```

The relevant Playwright scenarios are in
[`e2e/tests/test_public_agent_pages.py`](../../e2e/tests/test_public_agent_pages.py).
They use boundary mocks for auth and public API responses, while the runner
still builds the real frontend/backend stack and applies the real migrations.

## Best Practices

- **Clear and Concise Tests**: Tests should be easy to read and understand.
- **Maintainable Tests**: Avoid brittle tests that break with minor code changes.
- **Fast Feedback**: Tests should run quickly to provide rapid feedback.
- **Descriptive Test Names**: Test names should clearly indicate what they are testing.
- **Mocking and Stubbing**: Use mocks and stubs for external services and complex dependencies.

## Example (Python - Pytest)

```python
# tests/test_example.py

def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2
```

## Example (JavaScript - Jest)

```javascript
// frontend/src/components/__tests__/Button.test.js
import { render, screen } from "@testing-library/react";
import Button from "../Button";

describe("Button", () => {
  it("renders with correct text", () => {
    render(<Button>Click Me</Button>);
    expect(screen.getByText("Click Me")).toBeInTheDocument();
  });
});
```
