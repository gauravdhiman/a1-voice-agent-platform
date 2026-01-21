/**
 * Tests for useUserProfile hook
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useUserProfile } from '@/hooks/use-user-profile'

vi.mock('@/services/auth-service', () => ({
  authService: {
    getCurrentUser: vi.fn().mockResolvedValue({
      success: true,
      user: {
        id: 'user-1',
        email: 'user@example.com',
        full_name: 'Test User',
        roles: [
          {
            id: 'role-1',
            organization_id: 'org-1',
            user_id: 'user-1',
            role: 'admin',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      },
      error: null,
    }),
  },
}))

import { authService } from '@/services/auth-service'

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

describe('useUserProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches user profile when userId is provided', async () => {
    const { result } = renderHook(() => useUserProfile('user-1'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toMatchObject([
      {
        id: 'role-1',
        user_id: 'user-1',
        role: 'admin',
      },
    ])
  })

  it('calls auth service', async () => {
    renderHook(() => useUserProfile('user-1'), {
      wrapper: TestWrapper,
    })

    await waitFor(() => {
      expect(authService.getCurrentUser).toHaveBeenCalled()
    })
  })
})
