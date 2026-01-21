/**
 * Tests for AuthService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authService } from '@/services/auth-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('processInvitation', () => {
    it('processes invitation successfully', async () => {
      const result = await authService.processInvitation('test-token', 'user-1')
      
      expect(result.success).toBe(true)
      expect(result.data).toBeDefined()
    })

    it('handles errors gracefully', async () => {
      server.use(
        http.post(`${API_BASE_URL}/api/v1/auth/process-invitation`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Invalid token' }), { status: 400 })
        })
      )

      const result = await authService.processInvitation('invalid-token', 'user-1')
      
      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })
  })

  describe('getCurrentUser', () => {
    it('returns current user profile', async () => {
      const result = await authService.getCurrentUser()
      
      expect(result.success).toBe(true)
      expect(result.user).toMatchObject({
        id: expect.any(String),
        email: expect.any(String),
      })
    })

    it('handles 401 unauthorized', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/auth/me`, () => {
          return new HttpResponse(null, { status: 401 })
        })
      )

      const result = await authService.getCurrentUser()
      
      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })
  })

  describe('refreshToken', () => {
    it('refreshes token successfully', async () => {
      const result = await authService.refreshToken('old-refresh-token')
      
      expect(result.success).toBe(true)
      expect(result.data).toBeDefined()
    })

    it('handles invalid refresh token', async () => {
      server.use(
        http.post(`${API_BASE_URL}/api/v1/auth/refresh`, () => {
          return new HttpResponse(JSON.stringify({ detail: 'Invalid refresh token' }), { status: 401 })
        })
      )

      const result = await authService.refreshToken('invalid-token')
      
      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })
  })

  describe('signOut', () => {
    it('signs out successfully', async () => {
      const result = await authService.signOut()
      
      expect(result.success).toBe(true)
    })

    it('handles sign out errors', async () => {
      server.use(
        http.post(`${API_BASE_URL}/api/v1/auth/signout`, () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      const result = await authService.signOut()
      
      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })
  })
})
