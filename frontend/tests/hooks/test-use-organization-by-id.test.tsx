/**
 * Tests for use-organization-by-id hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Use vi.hoisted() to define mock data
const { mockOrganization } = vi.hoisted(() => ({
  mockOrganization: {
    id: 'org-1',
    name: 'Test Organization',
    description: 'A test organization',
    slug: 'test-org',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
}))

vi.mock('@/services/organization-service', () => ({
  organizationService: {
    getOrganizationById: vi.fn().mockResolvedValue(mockOrganization),
  },
}))

vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({
    isAuthenticated: true,
  }),
}))

import { useOrganizationById } from '@/hooks/use-organization-by-id'
import { organizationService } from '@/services/organization-service'

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

describe('useOrganizationById', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches organization by ID', async () => {
    const { result } = renderHook(() => useOrganizationById('org-1'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.isValid).toBe(true)
    expect(result.current.organization).toMatchObject({
      id: 'org-1',
      name: expect.any(String),
    })
  })

  it('calls organization service with org ID', async () => {
    renderHook(() => useOrganizationById('org-1'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(organizationService.getOrganizationById).toHaveBeenCalledWith('org-1')
    })
  })

  it('returns invalid when org ID is not provided', async () => {
    const { result } = renderHook(() => useOrganizationById(null), {
      wrapper: TestWrapper,
    })

    // Should not make API call
    expect(organizationService.getOrganizationById).not.toHaveBeenCalled()
    expect(result.current.isValid).toBe(false)
  })
})
