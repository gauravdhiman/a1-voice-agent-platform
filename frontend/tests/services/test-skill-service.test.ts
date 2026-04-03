/**
 * Tests for SkillService
 *
 * Covers: organization skill CRUD, agent skill assignment/unassignment,
 * skill seeding, and proper handling of 204 No Content responses.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { skillService } from '@/services/skill-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockOrganizationSkill, createMockAgentSkill } from '../utils/data-factories'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

describe('SkillService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Organization Skills', () => {
    it('getOrganizationSkills returns list of skills', async () => {
      const result = await skillService.getOrganizationSkills('org-1')
      expect(result).toHaveLength(3)
      expect(result[0]).toMatchObject({
        slug: 'appointment-booking',
        name: 'Appointment Booking',
        category: 'built_in',
      })
    })

    it('createSkill creates a new custom skill', async () => {
      const result = await skillService.createSkill('org-1', {
        organization_id: 'org-1',
        slug: 'my-new-skill',
        name: 'My New Skill',
        content: '# My New Skill\n\nProcedure here.',
      })

      expect(result).toMatchObject({
        slug: 'my-new-skill',
        name: 'My New Skill',
        category: 'custom',
      })
    })

    it('updateSkill updates an existing skill', async () => {
      const result = await skillService.updateSkill('org-1', 'skill-1', {
        name: 'Updated Name',
        content: '# Updated Content',
      })

      expect(result).toMatchObject({
        name: 'Updated Name',
      })
    })

    it('deleteSkill handles 204 No Content response', async () => {
      // This should not throw — 204 means success with no body
      await expect(
        skillService.deleteSkill('org-1', 'skill-3')
      ).resolves.not.toThrow()
    })

    it('seedSkills returns seeded count', async () => {
      const result = await skillService.seedSkills('org-1')
      expect(result).toEqual({ seeded: 6 })
    })
  })

  describe('Agent Skills', () => {
    it('getAgentSkills returns assigned skills with full skill data', async () => {
      const result = await skillService.getAgentSkills('agent-1')
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        agent_id: 'agent-1',
        skill_id: 'skill-1',
        is_active: true,
      })
      expect(result[0].skill).toMatchObject({
        slug: 'appointment-booking',
        name: 'Appointment Booking',
      })
    })

    it('assignSkill sends POST and handles 201', async () => {
      await expect(
        skillService.assignSkill('agent-1', 'skill-2')
      ).resolves.not.toThrow()
    })

    it('unassignSkill handles 204 No Content response', async () => {
      // This is the critical test — 204 responses caused crashes before the fix
      await expect(
        skillService.unassignSkill('agent-1', 'skill-1')
      ).resolves.not.toThrow()
    })
  })

  describe('Error Handling', () => {
    it('getOrganizationSkills handles server error', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/organizations/:orgId/skills`, () => {
          return HttpResponse.json(
            { detail: 'Internal server error' },
            { status: 500 }
          )
        })
      )

      await expect(
        skillService.getOrganizationSkills('org-1')
      ).rejects.toThrow()
    })

    it('createSkill handles validation error', async () => {
      server.use(
        http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills`, () => {
          return HttpResponse.json(
            { detail: 'Slug must be lowercase kebab-case' },
            { status: 400 }
          )
        })
      )

      await expect(
        skillService.createSkill('org-1', {
          organization_id: 'org-1',
          slug: 'INVALID SLUG',
          name: 'Test',
          content: '# Test',
        })
      ).rejects.toThrow()
    })

    it('assignSkill handles permission error', async () => {
      server.use(
        http.post(`${API_BASE_URL}/api/v1/agents/:agentId/skills`, () => {
          return HttpResponse.json(
            { detail: 'Only platform admins or organization admins can assign skills' },
            { status: 403 }
          )
        })
      )

      await expect(
        skillService.assignSkill('agent-1', 'skill-1')
      ).rejects.toThrow()
    })
  })
})
