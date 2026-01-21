/**
 * Tests for useBillingInfo hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useBillingInfo } from '@/hooks/use-billing-info'

vi.mock('@/services/billing-service', () => ({
  billingService: {
    getOrganizationSubscription: vi.fn().mockResolvedValue({
      id: 'sub-1',
      organization_id: 'org-1',
      plan_id: 'plan-1',
      status: 'active',
      current_period_start: new Date().toISOString(),
      current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
    getCreditBalance: vi.fn().mockResolvedValue({
      id: 'balance-1',
      organization_id: 'org-1',
      balance: 1000,
      currency: 'USD',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }),
  },
}))

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

describe('useBillingInfo', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches billing info', async () => {
    const { result } = renderHook(() => useBillingInfo('org-1'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toMatchObject({
      subscription: expect.any(Object),
      creditBalance: expect.any(Object),
    })
  })

  it('calls billing service with correct org ID', async () => {
    renderHook(() => useBillingInfo('org-1'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(billingService.getOrganizationSubscription).toHaveBeenCalledWith('org-1')
      expect(billingService.getCreditBalance).toHaveBeenCalledWith('org-1')
    })
  })
})
