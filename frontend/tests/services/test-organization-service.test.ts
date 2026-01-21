/**
 * Tests for OrganizationService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { organizationService } from '@/services/organization-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

describe('OrganizationService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getUserOrganizations', () => {
    it('returns list of organizations', async () => {
      const result = await organizationService.getUserOrganizations()
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })
  })

  describe('getOrganizations', () => {
    it('is an alias for getUserOrganizations', async () => {
      const result = await organizationService.getOrganizations()
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })
  })

  describe('getOrganizationById', () => {
    it('returns organization by ID', async () => {
      const result = await organizationService.getOrganizationById('org-1')
      
      expect(result).toMatchObject({
        id: 'org-1',
        name: expect.any(String),
      })
    })

    it('handles 404 not found', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/organizations/:id`, () => {
          return new HttpResponse(null, { status: 404 })
        })
      )

      await expect(organizationService.getOrganizationById('invalid-id')).rejects.toThrow()
    })
  })

  describe('createSelfOrganization', () => {
    it('creates organization for current user', async () => {
      const orgData = { name: 'My New Org' }
      
      const result = await organizationService.createSelfOrganization(orgData)
      
      expect(result).toMatchObject({
        name: 'My New Org',
      })
    })
  })

  describe('createOrganization', () => {
    it('creates organization (admin)', async () => {
      const orgData = { name: 'Admin Created Org' }
      
      const result = await organizationService.createOrganization(orgData)
      
      expect(result).toMatchObject({
        name: expect.any(String),
      })
    })
  })

  describe('updateOrganization', () => {
    it('updates organization', async () => {
      const updateData = { name: 'Updated Org Name' }
      
      const result = await organizationService.updateOrganization('org-1', updateData)
      
      expect(result).toMatchObject({
        id: 'org-1',
        name: 'Updated Org Name',
      })
    })
  })

  describe('deleteOrganization', () => {
    it('deletes organization', async () => {
      await expect(organizationService.deleteOrganization('org-1')).resolves.not.toThrow()
    })
  })

  describe('getOrganizationMembers', () => {
    it('returns list of members', async () => {
      const result = await organizationService.getOrganizationMembers('org-1')
      
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        email: expect.any(String),
      })
    })
  })

  describe('inviteMember', () => {
    it('invites member to organization', async () => {
      const result = await organizationService.inviteMember('org-1', 'newuser@example.com')
      
      expect(result).toMatchObject({
        email: 'newuser@example.com',
        status: 'pending',
      })
    })
  })

  describe('Error Handling', () => {
    it('handles 500 errors', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/organizations`, () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(organizationService.getUserOrganizations()).rejects.toThrow()
    })
  })
})
