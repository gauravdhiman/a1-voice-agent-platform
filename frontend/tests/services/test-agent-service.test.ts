/**
 * Tests for AgentService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { agentService } from '@/services/agent-service'
import { server } from '../mocks/server'
import { http } from 'msw'
import { createMockAgent, createMockPlatformTool, createMockAgentTool } from '../utils/data-factories'

// Import mocked supabase to ensure it's available
describe('AgentService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Voice Agent Methods', () => {
    it('getMyAgents returns list of agents', async () => {
      const result = await agentService.getMyAgents()
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        name: expect.any(String),
        system_prompt: expect.any(String),
      })
    })

    it('getOrgAgents returns agents for organization', async () => {
      const result = await agentService.getOrgAgents('org-1')
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        organization_id: 'org-1',
      })
    })

    it('getAgentById returns single agent', async () => {
      const result = await agentService.getAgentById('agent-1')
      expect(result).toMatchObject({
        id: 'agent-1',
        name: expect.any(String),
      })
    })

    it('createAgent creates new agent', async () => {
      const newAgentData = {
        name: 'New Agent',
        system_prompt: 'You are helpful',
        voice_settings: {
          provider: 'openai',
          voice: 'alloy',
        },
      }

      const result = await agentService.createAgent(newAgentData as any)
      expect(result).toMatchObject({
        name: 'New Agent',
        system_prompt: 'You are helpful',
      })
    })

    it('updateAgent updates existing agent', async () => {
      const updateData = {
        name: 'Updated Agent',
        system_prompt: 'You are very helpful',
      }

      const result = await agentService.updateAgent('agent-1', updateData as any)
      expect(result).toMatchObject({
        id: 'agent-1',
        name: 'Updated Agent',
        system_prompt: 'You are very helpful',
      })
    })

    it('deleteAgent deletes agent', async () => {
      await expect(agentService.deleteAgent('agent-1')).resolves.not.toThrow()
    })
  })

  describe('Tool Methods', () => {
    it('getPlatformTools returns list of tools', async () => {
      const result = await agentService.getPlatformTools()
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        name: expect.any(String),
        requires_auth: expect.any(Boolean),
      })
    })

    it('getPlatformTools with onlyActive=false', async () => {
      const result = await agentService.getPlatformTools(false)
      expect(Array.isArray(result)).toBe(true)
    })

    it('getAgentTools returns tools for agent', async () => {
      const result = await agentService.getAgentTools('agent-1')
      expect(result).toHaveLength(1)
      expect(result[0]).toMatchObject({
        agent_id: 'agent-1',
        connection_status: expect.any(String),
      })
    })

    it('configureAgentTool configures tool', async () => {
      const toolData = {
        agent_id: 'agent-1',
        tool_id: 'tool-1',
        config: {},
      }

      const result = await agentService.configureAgentTool(toolData as any)
      expect(result).toBeDefined()
    })

    it('updateAgentTool updates tool configuration', async () => {
      const updateData = {
        config: { updated: true },
      }

      const result = await agentService.updateAgentTool('agent-tool-1', updateData as any)
      expect(result).toBeDefined()
    })

    it('startOAuth returns auth URL', async () => {
      const result = await agentService.startOAuth('google_calendar', 'agent-1')
      expect(result).toMatchObject({
        auth_url: expect.any(String),
      })
    })

    it('deleteAgentTool deletes tool', async () => {
      // Should call delete endpoint
      await expect(agentService.deleteAgentTool('agent-tool-1')).resolves.not.toThrow()
    })
  })

  describe('Error Handling', () => {
    it('handles 404 errors gracefully', async () => {
      server.resetHandlers()
      server.use(
        http.get('http://localhost:8000/api/v1/agents/:id', () => {
          return new HttpResponse(null, { status: 404 })
        })
      )

      await expect(agentService.getAgentById('invalid-id')).rejects.toThrow()
    })

    it('handles 500 errors gracefully', async () => {
      server.resetHandlers()
      server.use(
        http.get('http://localhost:8000/api/v1/agents/my-agents', () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(agentService.getMyAgents()).rejects.toThrow()
    })
  })
})
