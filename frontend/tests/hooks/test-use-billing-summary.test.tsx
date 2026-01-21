/**
 * Tests for use-billing-summary hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Use vi.hoisted() to define mock data
const { mockBillingSummary, mockOrganization } = vi.hoisted(() => ({
  mockBillingSummary: {
    subscription: {
      id: 'sub-1',
      status: 'active',
      plan: {
        id: 'plan-1',
        name: 'Pro Plan',
        price_amount: 4900,
      },
    },
    credit_balance: {
      total_credits: 1000,
      subscription_credits: 800,
      purchased_credits: 200,
      expiring_soon: 50,
    },
    billing_history: [],
  },
  mockOrganization: {
    id: 'org-1',
    name: 'Test Organization',
  },
}))

vi.mock('@/services/billing-service', () => ({
  billingService: {
    getBillingSummary: vi.fn().mockResolvedValue(mockBillingSummary),
  },
}))

vi.mock('@/contexts/organization-context', () => ({
  useOrganization: () => ({
    currentOrganization: mockOrganization,
  }),
}))

import { useBillingSummary } from '@/hooks/use-billing-summary'
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

describe('useBillingSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches billing summary for current organization', async () => {
    const { result } = renderHook(() => useBillingSummary(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toMatchObject({
      credit_balance: {
        total_credits: expect.any(Number),
      },
    })
  })

  it('fetches billing summary with provided org ID', async () => {
    const { result } = renderHook(() => useBillingSummary('custom-org-id'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(billingService.getBillingSummary).toHaveBeenCalledWith('custom-org-id')
  })

  it('calls billing service with organization ID', async () => {
    renderHook(() => useBillingSummary(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(billingService.getBillingSummary).toHaveBeenCalledWith('org-1')
    })
  })
})
