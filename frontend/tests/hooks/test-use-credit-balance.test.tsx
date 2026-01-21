/**
 * Tests for useCreditBalance hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useCreditBalance } from '@/hooks/use-credit-balance'

vi.mock('@/contexts/organization-context', () => ({
  useOrganization: vi.fn().mockReturnValue({
    currentOrganization: {
      id: 'org-1',
      name: 'Test Organization',
    },
  }),
}))

vi.mock('@/services/billing-service', () => ({
  billingService: {
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

describe('useCreditBalance', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches credit balance', async () => {
    const { result } = renderHook(() => useCreditBalance(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toMatchObject({
      id: 'balance-1',
      organization_id: 'org-1',
      balance: 1000,
    })
  })

  it('calls billing service with correct org ID', async () => {
    renderHook(() => useCreditBalance(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(billingService.getCreditBalance).toHaveBeenCalledWith('org-1')
    })
  })
})
