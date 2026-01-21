/**
 * Tests for use-user-organizations hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Use vi.hoisted() to define mock data
const { mockOrganization, mockUser } = vi.hoisted(() => ({
  mockOrganization: {
    id: 'org-1',
    name: 'Test Organization',
    description: 'A test organization',
    slug: 'test-org',
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  mockUser: {
    id: 'user-1',
    email: 'test@example.com',
  },
}))

vi.mock('@/services/organization-service', () => ({
  organizationService: {
    getUserOrganizations: vi.fn().mockResolvedValue([mockOrganization]),
  },
}))

vi.mock('@/contexts/auth-context', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    user: mockUser,
  }),
}))

import { useUserOrganizations } from '@/hooks/use-user-organizations'
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

describe('useUserOrganizations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches user organizations when authenticated', async () => {
    const { result } = renderHook(() => useUserOrganizations(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toHaveLength(1)
    expect(result.current.data?.[0]).toMatchObject({
      id: expect.any(String),
      name: expect.any(String),
    })
  })

  it('calls organization service', async () => {
    renderHook(() => useUserOrganizations(), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(organizationService.getUserOrganizations).toHaveBeenCalled()
    })
  })
})
