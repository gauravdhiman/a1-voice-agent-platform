/**
 * Tests for use-organization-members hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Use vi.hoisted() to define mock data
const { mockMember, mockOrganization } = vi.hoisted(() => ({
  mockMember: {
    id: 'member-1',
    email: 'member@example.com',
    first_name: 'Member',
    last_name: 'User',
    is_verified: true,
    created_at: new Date().toISOString(),
    roles: [],
  },
  mockOrganization: {
    id: 'org-1',
    name: 'Test Organization',
  },
}))

vi.mock('@/services/organization-service', () => ({
  organizationService: {
    getOrganizationMembers: vi.fn().mockResolvedValue([mockMember]),
  },
}))

vi.mock('@/contexts/organization-context', () => ({
  useOrganization: () => ({
    currentOrganization: mockOrganization,
  }),
}))

import { useOrganizationMembers } from '@/hooks/use-organization-members'
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

describe('useOrganizationMembers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches organization members', async () => {
    const { result } = renderHook(() => useOrganizationMembers(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toHaveLength(1)
    expect(result.current.data?.[0]).toMatchObject({
      id: expect.any(String),
      email: expect.any(String),
    })
  })

  it('calls organization service with org ID', async () => {
    renderHook(() => useOrganizationMembers(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(organizationService.getOrganizationMembers).toHaveBeenCalledWith('org-1')
    })
  })

  it('transforms member data correctly', async () => {
    const { result } = renderHook(() => useOrganizationMembers(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data?.[0]).toMatchObject({
      id: 'member-1',
      email: 'member@example.com',
      first_name: 'Member',
      last_name: 'User',
      is_verified: true,
      roles: [],
    })
  })
})
