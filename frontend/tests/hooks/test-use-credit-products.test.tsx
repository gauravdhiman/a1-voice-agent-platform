/**
 * Tests for use-credit-products hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Use vi.hoisted() to define mock data
const { mockCreditProduct } = vi.hoisted(() => ({
  mockCreditProduct: {
    id: 'product-1',
    name: '1000 Credits',
    credits: 1000,
    price_amount: 999,
    price_currency: 'usd',
    is_active: true,
  },
}))

vi.mock('@/services/billing-service', () => ({
  billingService: {
    getCreditProducts: vi.fn().mockResolvedValue([mockCreditProduct]),
  },
}))

import { useCreditProducts } from '@/hooks/use-credit-products'
import { billingService } from '@/services/billing-service'

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

describe('useCreditProducts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches credit products', async () => {
    const { result } = renderHook(() => useCreditProducts(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toHaveLength(1)
    expect(result.current.data?.[0]).toMatchObject({
      id: expect.any(String),
      name: expect.any(String),
      credits: expect.any(Number),
    })
  })

  it('calls billing service', async () => {
    renderHook(() => useCreditProducts(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(billingService.getCreditProducts).toHaveBeenCalled()
    })
  })
})
