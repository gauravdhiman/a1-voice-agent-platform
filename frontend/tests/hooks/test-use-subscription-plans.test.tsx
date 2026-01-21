/**
 * Tests for useSubscriptionPlans hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useSubscriptionPlans } from '@/hooks/use-subscription-plans'
import { billingService } from '@/services/billing-service'

vi.mock('@/services/billing-service', () => ({
  billingService: {
    getSubscriptionPlans: vi.fn().mockResolvedValue([
      {
        id: 'plan-1',
        name: 'Pro Plan',
        description: 'Professional plan',
        price_amount: 2900,
        price_currency: 'USD',
        billing_interval: 'monthly',
        features: ['Feature 1', 'Feature 2'],
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]),
  },
}))

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

function TestWrapper({ children }: { children: React.ReactNode }) {
  const testQueryClient = createTestQueryClient()
  return <QueryClientProvider client={testQueryClient}>{children}</QueryClientProvider>
}

describe('useSubscriptionPlans', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches subscription plans', async () => {
    const { result } = renderHook(() => useSubscriptionPlans(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toHaveLength(1)
    expect(result.current.data?.[0]).toMatchObject({
      name: expect.any(String),
      price_amount: expect.any(Number),
    })
  })

  it('calls billing service', async () => {
    renderHook(() => useSubscriptionPlans(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(billingService.getSubscriptionPlans).toHaveBeenCalled()
    })
  })
})
