# Frontend Testing Guide

## Overview

Frontend tests use **Vitest** as the test runner with **React Testing Library** for component testing. API calls are mocked using **MSW (Mock Service Worker)**.

## Test Structure

```
frontend/
├── tests/
│   ├── setup.ts                  # Vitest setup, global mocks
│   ├── conftest.py              # Additional test config
│   │
│   ├── mocks/                   # MSW request handlers
│   │   ├── handlers.ts        # API request handlers
│   │   └── server.ts          # MSW server setup
│   │
│   ├── utils/                   # Test utilities
│   │   ├── test-utils.tsx     # Custom render functions
│   │   └── data-factories.ts   # Sample data generators
│   │
│   ├── lib/                    # Utility function tests
│   │   ├── test-utils.test.ts
│   │   └── test-api-client.test.ts
│   │
│   ├── services/               # Service layer tests
│   │   ├── test-agent-service.test.ts
│   │   ├── test-auth-service.test.ts
│   │   ├── test-billing-service.test.ts
│   │   └── test-organization-service.test.ts
│   │
│   ├── hooks/                  # Custom hook tests
│   │   └── test-use-live-time.test.tsx
│   │
│   └── components/             # Component tests (TODO)
│
├── vitest.config.ts            # Vitest configuration
└── vitest.workspace.ts         # Workspace configuration
```

## Test Infrastructure

### Configuration Files

**`frontend/vitest.config.ts`**
- Test runner configuration
- jsdom environment
- Coverage provider: v8
- Path aliases: `@/` → `./src`

**`frontend/tests/setup.ts`**
- Global mocks (Supabase, Next.js router, etc.)
- MSW server lifecycle
- Cleanup after each test

### Mocking Strategy

**MSW (Mock Service Worker)** - Intercepts HTTP requests
- `tests/mocks/handlers.ts` - API request/response handlers
- `tests/mocks/server.ts` - MSW server setup
- `tests/utils/data-factories.ts` - Sample data for tests

**Test Utilities**
- `tests/utils/test-utils.tsx` - Custom render with React Query provider
- `cn()` utility for merging Tailwind classes

## Running Tests

### Basic Commands

```bash
cd <project-root>/frontend
# Run all tests
npm run test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test -- --watch

# Run with UI
npm run test:ui

# Run specific test file
npm run test -- tests/lib/test-utils.test.ts

# Run specific test
npm run test -- tests/lib/test-utils.test.ts -t "cn utility"

# Run tests in a directory
npm run test -- tests/lib/
npm run test -- tests/services/
npm run test -- tests/hooks/

# Run tests without watching (CI mode)
npm run test:run
```

### Coverage Commands

```bash
# Generate coverage report
npm test:coverage

# Coverage report location
# - CLI: console output
# - HTML: frontend/coverage/index.html
# - LCOV: frontend/coverage/lcov.info
```

## Test Files

### Completed Tests (30 tests, 96% coverage)

#### `tests/lib/test-utils.test.ts` (12 tests)
- `cn()` utility - merges Tailwind CSS classes
- `formatToolName()` - formats snake_case to Title Case
- All tests passing

#### `tests/lib/test-api-client.test.ts` (18 tests)
- `ApiClient` class HTTP methods
- Auth token handling
- Error handling (401, 403, 500)
- Response handling (wrapped vs direct)
- All tests passing
- Uncovered lines: edge cases in token refresh (lines 36, 85)

### In Progress

#### Service Tests
- **Note**: Service tests require MSW handlers for all API endpoints
- Currently 13 tests passing out of 15 written
- Need to add MSW handlers for: `/api/v1/agents/*`, `/api/v1/tools/*`, `/api/v1/billing/*`

#### Hook Tests
- `useLiveTime` hook test in progress
- Simple hook that returns current timestamp
- Formatting utility tests

## Testing Patterns

### Service Test Pattern

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { agentService } from '@/services/agent-service'
import { http } from 'msw'
import { server } from '../mocks/server'
import { createMockAgent } from '../utils/data-factories'

describe('AgentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getMyAgents returns list of agents', async () => {
    const result = await agentService.getMyAgents()
    expect(result).toHaveLength(1)
    expect(result[0]).toMatchObject({
      name: expect.any(String),
      system_prompt: expect.any(String),
    })
  })

  it('handles errors gracefully', async () => {
    // Override handler to return error
    server.use(
      http.get('/api/v1/agents/my-agents', () => {
        return HttpResponse.json({ error: 'Not found' }, { status: 404 })
      })
    )

    await expect(agentService.getMyAgents()).rejects.toThrow()
  })
})
```

### Hook Test Pattern

```typescript
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useLiveTime } from '@/hooks/use-live-time'

describe('useLiveTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('returns current timestamp', () => {
    const { result } = renderHook(() => useLiveTime())
    expect(result.current).toBeTypeOf('number')
  })

  it('updates time every second', () => {
    const { result } = renderHook(() => useLiveTime())
    const initialTime = result.current

    act(() => {
      vi.advanceTimersByTime(1000) // 1 second
    })

    expect(result.current).toBeGreaterThan(initialTime)
  })
})
```

### Component Test Pattern

```typescript
import { renderWithProviders, screen } from '../utils/test-utils'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('renders button text', () => {
    renderWithProviders(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })

  it('calls onClick handler', async () => {
    const handleClick = vi.fn()
    renderWithProviders(<Button onClick={handleClick}>Click me</Button>)

    const button = screen.getByRole('button')
    await userEvent.click(button)

    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
```

## Best Practices

### 1. Arrange-Act-Assert Pattern

```typescript
it('test description', async () => {
  // Arrange
  const mockData = createMockAgent()
  const handleClick = vi.fn()

  // Act
  renderWithProviders(<AgentCard onClick={handleClick} agent={mockData} />)
  await userEvent.click(screen.getByRole('button'))

  // Assert
  expect(handleClick).toHaveBeenCalledTimes(1)
})
```

### 2. Test Descriptions

- **Good**: "returns empty list when no agents exist"
- **Bad**: "tests the function"

### 3. Test Edge Cases

- Success cases (happy path)
- Error cases (401, 403, 500)
- Loading states
- Empty data states

### 4. Use Descriptive Assertions

```typescript
expect(result).toHaveLength(1)  // More specific than toBeTruthy()
expect(result[0]).toMatchObject({ id: 'agent-1' })  // Check structure
expect(screen.getByText('Loading')).toBeInTheDocument()  // Check UI state
```

### 5. Mock External Dependencies

- **Don't** test Supabase internals - mock at auth layer
- **Don't** test Stripe internals - mock at API layer
- **Do** test error handling in your code
- **Don't** use `any` unless absolutely necessary

## Common Issues and Solutions

### Issue: MSW Handler Not Matching

**Problem**: "intercepted a request without a matching request handler"

**Solution**: Ensure URL pattern matches exactly:
```typescript
// Wrong
http.get('/api/v1/agents/:id', () => {...})

// Right - if service calls `/api/v1/agents/agent-1`
http.get('/api/v1/agents/:id', ({ params }) => {
  expect(params.id).toBe('agent-1')
  return HttpResponse.json({ data: mockAgent })
})
```

### Issue: Token Refresh Not Working

**Problem**: `TypeError: Cannot destructure property 'data' of '(intermediate value)'`

**Solution**: Mock refreshSession to return proper structure:
```typescript
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      refreshSession: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'mock-token',
            user: { id: 'user-1' },
          },
        },
      }),
    },
  },
}))
```

### Issue: Tests Failing in CI

**Problem**: Tests pass locally but fail in CI

**Solution**: Ensure deterministic tests:
- Use fixed data from factories
- Don't rely on `Date.now()` for comparisons
- Clear mocks before each test

## Coverage Goals

### Current Status
- **Lib utilities**: 96% coverage (30/30 tests passing)
- **Services**: In progress (MSW setup complexity)
- **Hooks**: Starting
- **Components**: TODO

### Target Coverage
- Week 1: ~20% (Lib + basic services)
- Week 2: ~40% (Services + hooks)
- Week 3: ~60% (Hooks + components)
- Week 4: ~80% (Components + edge cases)
- Week 5: ~90%+ (Full coverage)

## Debugging Tests

### Vitest UI

```bash
npm run test:ui
# Opens browser interface to:
# - Run tests interactively
# - View test output
# - Debug failing tests
```

### Console Logging

```typescript
// Add console.log in tests for debugging
it('troubleshooting', async () => {
  console.log('Input data:', testData)
  const result = await service.method(testData)
  console.log('Result:', result)

  expect(result).toBeDefined()
})
```

### Error Messages

Check actual error messages in assertions:
```typescript
// Good - shows what went wrong
expect(result).toEqual({ id: '123' })
// Expected: { id: '123' }
// Received: { id: '456' }

// Bad - too generic
expect(result).toBeTruthy()
// Error: Expected truthy but received { id: '456' }
```

## References

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [MSW Documentation](https://mswjs.io/)
- [Testing Library User Event](https://testing-library.com/docs/user-event/)
- [Vitest UI](https://vitest.dev/guide/ui)
