/**
 * Tests for API client
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiClient } from '@/lib/api/client'
import { supabase } from '@/lib/supabase'

// Mock Supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      refreshSession: vi.fn(),
    },
  },
}))

describe('ApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('setAuthToken and clearAuthToken', () => {
    it('sets authorization header', () => {
      apiClient.setAuthToken('test-token-123')
      const headers = (apiClient as any).headers
      expect(headers['Authorization']).toBe('Bearer test-token-123')
    })

    it('clears authorization header', () => {
      apiClient.setAuthToken('test-token')
      apiClient.clearAuthToken()
      const headers = (apiClient as any).headers
      expect(headers['Authorization']).toBeUndefined()
    })
  })

  describe('HTTP methods', () => {
    beforeEach(() => {
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: { session: null },
      })
    })

    it('makes GET request', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'test' }),
        } as Response)
      )

      await apiClient.get('/test')

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      )
    })

    it('makes POST request with JSON body', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'test' }),
        } as Response)
      )

      await apiClient.post('/test', { name: 'test' })

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ name: 'test' }),
        })
      )
    })

    it('makes PUT request with JSON body', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'test' }),
        } as Response)
      )

      await apiClient.put('/test', { name: 'updated' })

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ name: 'updated' }),
        })
      )
    })

    it('makes DELETE request', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'test' }),
        } as Response)
      )

      await apiClient.delete('/test')

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      )
    })
  })

  describe('auth token handling', () => {
    it('includes auth token from session', async () => {
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: {
          session: {
            access_token: 'session-token-123',
            user: { id: 'user-1' },
          },
        },
      })

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'test' }),
        } as Response)
      )

      await apiClient.get('/test')

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer session-token-123',
          }),
        })
      )
    })

    it('refreshes token on 401 and retries', async () => {
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: { session: { access_token: 'old-token' } },
      })

      vi.mocked(supabase.auth.refreshSession).mockResolvedValue({
        data: { session: { access_token: 'new-token' } },
      })

      let callCount = 0
      global.fetch = vi.fn(() => {
        callCount++
        if (callCount === 1) {
          return Promise.resolve({
            ok: false,
            status: 401,
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ error: 'Unauthorized' }),
          } as Response)
        }
        return Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'test' }),
        } as Response)
      })

      await apiClient.get('/test')

      expect(fetch).toHaveBeenCalledTimes(2)
      expect(supabase.auth.refreshSession).toHaveBeenCalled()
    })

    it('throws error after failed token refresh', async () => {
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: { session: { access_token: 'old-token' } },
      })

      vi.mocked(supabase.auth.refreshSession).mockResolvedValue({
        error: { message: 'Refresh failed' },
      })

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 401,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ error: 'Unauthorized' }),
        } as Response)
      )

      await expect(apiClient.get('/test')).rejects.toThrow(
        'Authentication required. Please sign in.'
      )
    })
  })

  describe('error handling', () => {
    it('throws error for 401 status', async () => {
      vi.mocked(supabase.auth.getSession).mockResolvedValue({
        data: { session: null },
      })

      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 401,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({}),
        } as Response)
      )

      await expect(apiClient.get('/test')).rejects.toThrow(
        'Authentication required. Please sign in.'
      )
    })

    it('throws error for 403 status', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 403,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({}),
        } as Response)
      )

      await expect(apiClient.get('/test')).rejects.toThrow(
        'Access denied. You do not have permission to perform this action.'
      )
    })

    it('throws error with message from response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 400,
          headers: { get: () => 'application/json' },
          json: () =>
            Promise.resolve({ message: 'Invalid input data' }),
        } as Response)
      )

      await expect(apiClient.get('/test')).rejects.toThrow(
        'Invalid input data'
      )
    })

    it('throws error with detail from response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 400,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ detail: 'Bad request' }),
        } as Response)
      )

      await expect(apiClient.get('/test')).rejects.toThrow('Bad request')
    })

    it('throws error with error field from response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 400,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ error: 'Server error' }),
        } as Response)
      )

      await expect(apiClient.get('/test')).rejects.toThrow('Server error')
    })

    it('handles network errors', async () => {
      global.fetch = vi.fn(() =>
        Promise.reject(new Error('Network error'))
      )

      await expect(apiClient.get('/test')).rejects.toThrow('Network error')
    })
  })

  describe('response handling', () => {
    it('returns data from wrapped response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'response-data' }),
        } as Response)
      )

      const result = await apiClient.get('/test')

      // Wrapped response: returns just the data
      expect(result).toEqual({ data: 'response-data' })
    })

    it('returns data from direct response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ id: '1', name: 'test' }),
        } as Response)
      )

      const result = await apiClient.get('/test')

      // Direct response: wraps in { data, success }
      expect(result).toEqual({ data: { id: '1', name: 'test' }, success: true })
    })

    it('handles text response', async () => {
      global.fetch = vi.fn(() =>
        Promise.resolve({
          ok: true,
          headers: { get: () => 'text/plain' },
          text: () => Promise.resolve('plain text'),
        } as Response)
      )

      const result = await apiClient.get('/test')

      expect(result).toEqual({ data: 'plain text', success: true })
    })
  })
})
