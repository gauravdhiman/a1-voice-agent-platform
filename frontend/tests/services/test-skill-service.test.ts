/**
 * Tests for SkillService
 *
 * Covers: organization skill CRUD, agent skill assignment/unassignment,
 * skill seeding, reference file CRUD, skill import, 204 No Content handling.
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
        category: 'custom',
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
      await expect(
        skillService.deleteSkill('org-1', 'skill-3')
      ).resolves.not.toThrow()
    })

    it('listPlatformSkills returns platform skill summaries', async () => {
      const result = await skillService.listPlatformSkills()
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        slug: 'appointment-booking',
        name: 'Appointment Booking',
      })
    })
  })

  describe('Platform Skills (admin CRUD)', () => {
    it('listPlatformSkills with [active, deprecated] returns all skills incl. deprecated', async () => {
      const result = await skillService.listPlatformSkills(['active', 'deprecated'])
      expect(result).toHaveLength(2)
      expect(result[1]).toMatchObject({ status: 'deprecated' })
    })

    it('getPlatformSkill returns full skill with content', async () => {
      const result = await skillService.getPlatformSkill('platform-skill-1')
      expect(result).toMatchObject({ slug: 'appointment-booking' })
      expect(result.content).toContain('# Appointment Booking')
    })

    it('createPlatformSkill POSTs and returns created skill', async () => {
      const result = await skillService.createPlatformSkill({
        slug: 'new-skill',
        name: 'New Skill',
        content: '# New',
      })
      expect(result).toMatchObject({ slug: 'new-skill', name: 'New Skill' })
    })

    it('updatePlatformSkill PUTs partial update (name only — status transitions are dedicated)', async () => {
      const result = await skillService.updatePlatformSkill('platform-skill-1', { name: 'Renamed' })
      expect(result.name).toBe('Renamed')
    })

    it('deletePlatformSkill handles 204 (deprecate)', async () => {
      await expect(skillService.deletePlatformSkill('platform-skill-1')).resolves.toBeUndefined()
    })

    it('listPlatformSkillFiles returns file summaries', async () => {
      const result = await skillService.listPlatformSkillFiles('platform-skill-1')
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({ file_path: 'references/faqs.md' })
    })

    it('getPlatformSkillFile returns full file with content', async () => {
      const result = await skillService.getPlatformSkillFile('platform-skill-1', 'platform-file-1')
      expect(result.content).toContain('# FAQs')
    })

    it('createPlatformSkillFile POSTs and returns created file', async () => {
      const result = await skillService.createPlatformSkillFile('platform-skill-1', {
        file_path: 'references/new.md',
        content: '# New file',
      })
      expect(result).toMatchObject({ file_path: 'references/new.md' })
    })

    it('updatePlatformSkillFile PUTs updated content', async () => {
      const result = await skillService.updatePlatformSkillFile('platform-skill-1', 'platform-file-1', {
        file_path: 'references/faqs.md',
        content: '# Updated',
      })
      expect(result.content).toBe('# Updated')
    })

    it('restorePlatformSkill POSTs to /platform/skills/:id/restore', async () => {
      const result = await skillService.restorePlatformSkill('platform-skill-1')
      expect(result.status).toBe('active')
    })

    it('listPlatformSkills with [active, deprecated, deleted] returns all incl. deleted', async () => {
      const result = await skillService.listPlatformSkills(['active', 'deprecated', 'deleted'])
      expect(result).toHaveLength(3)
      expect(result[2]).toMatchObject({ slug: 'deleted-skill', status: 'deleted' })
    })

        it('importPlatformSkill POSTs to /platform/skills/import and returns results', async () => {
      const result = await skillService.importPlatformSkill('https://github.com/o/r')
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({ source_url: 'https://github.com/o/r' })
      expect(result[0].skill).toMatchObject({ slug: 'imported-platform-skill' })
    })

        it('deletePlatformSkillFile handles 204', async () => {
      await expect(
        skillService.deletePlatformSkillFile('platform-skill-1', 'platform-file-1'),
      ).resolves.toBeUndefined()
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

  describe('Skill Reference Files', () => {
    it('getSkillFiles returns file summaries', async () => {
      const result = await skillService.getSkillFiles('org-1', 'skill-1')
      expect(result).toHaveLength(3)
      expect(result[0]).toMatchObject({
        file_path: 'references/policies.md',
        file_kind: 'reference',
      })
      expect(result[2]).toMatchObject({
        file_path: 'scripts/validate.py',
        file_kind: 'script',
      })
    })

    it('createSkillFile creates a new reference file', async () => {
      const result = await skillService.createSkillFile('org-1', 'skill-1', {
        file_path: 'references/new-policy.md',
        content: '# New Policy\n\nFollow this.',
        file_kind: 'reference',
      })

      expect(result).toMatchObject({
        file_path: 'references/new-policy.md',
        content: '# New Policy\n\nFollow this.',
      })
    })

    it('updateSkillFile updates file content', async () => {
      const result = await skillService.updateSkillFile(
        'org-1', 'skill-1', 'file-1',
        { content: '# Updated content' },
      )

      expect(result).toMatchObject({
        content: '# Updated content',
      })
    })

    it('deleteSkillFile handles 204 No Content', async () => {
      await expect(
        skillService.deleteSkillFile('org-1', 'skill-1', 'file-1')
      ).resolves.not.toThrow()
    })

    it('getAgentsUsingSkill returns agent list', async () => {
      const result = await skillService.getAgentsUsingSkill('org-1', 'skill-1')
      expect(result).toHaveLength(2)
      expect(result[0]).toMatchObject({ name: 'Support Agent' })
      expect(result[1]).toMatchObject({ name: 'Sales Agent', is_active: false })
    })

    it('getSkillFileContent returns file content string', async () => {
      const result = await skillService.getSkillFileContent(
        '00000000-0000-0000-0000-000000000001', 'appointment-booking', 'references/policies.md'
      )
      expect(result).toContain('Booking Policies')
      expect(result).toContain('Confirm insurance')
    })
  })

  describe('Skill Import', () => {
    it('importSkill returns import results with file counts', async () => {
      const result = await skillService.importSkill(
        'org-1',
        'https://github.com/owner/repo/tree/main/my-skill',
      )

      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        files_imported: 3,
        source_url: 'https://github.com/owner/repo/tree/main/my-skill',
      })
      expect(result[0].skill).toMatchObject({
        slug: 'imported-skill',
        name: 'Imported Skill',
      })
    })
  })
})
