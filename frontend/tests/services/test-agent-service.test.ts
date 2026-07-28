/**
 * Tests for AgentService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { agentService } from '@/services/agent-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
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

    it('discoverMcpTools returns sanitized tool list', async () => {
      const result = await agentService.discoverMcpTools({
        url: 'https://example.com/mcp',
      })
      expect(Array.isArray(result)).toBe(true)
      expect(result.length).toBeGreaterThan(0)
      expect(result[0]).toMatchObject({
        name: expect.any(String),
        description: expect.any(String),
      })
    })

    it('discoverMcpTools throws on SSRF rejection', async () => {
      await expect(
        agentService.discoverMcpTools({ url: 'http://127.0.0.1/mcp' }),
      ).rejects.toThrow()
    })

    it('discoverMcpTools forwards headers in the request', async () => {
      // Headers are sent as part of the body; the mock echoes a tools list
      // regardless, so this just confirms no throw + result shape.
      const result = await agentService.discoverMcpTools({
        url: 'https://example.com/mcp',
        headers: { Authorization: 'Bearer abc' },
      })
      expect(result.length).toBeGreaterThan(0)
    })

    it('parseMcpServersJson returns servers and errors', async () => {
      const result = await agentService.parseMcpServersJson(
        JSON.stringify({
          mcpServers: {
            'my-server': {
              url: 'https://example.com/mcp',
              headers: { 'X-Key': 'v' },
            },
          },
        }),
      )
      expect(result.servers).toHaveLength(1)
      expect(result.servers[0].url).toBe('https://example.com/mcp')
      expect(result.errors).toHaveLength(0)
    })

    it('createPlatformTool returns the created platform tool', async () => {
      const result = await agentService.createPlatformTool({
        name: 'my-mcp',
        tool_source: 'mcp',
        mcp_server_url: 'https://example.com/mcp',
        mcp_secret_headers_input: { Authorization: 'Bearer x' },
      })
      expect(result).toMatchObject({
        id: 'new-mcp-tool',
        name: 'my-mcp',
        tool_source: 'mcp',
        mcp_server_url: 'https://example.com/mcp',
      })
      // Secret headers never come back as plaintext — only a configured flag.
      expect(result.mcp_secret_headers_configured).toBe(true)
      expect((result as any).mcp_secret_headers_input).toBeUndefined()
    })

    it('getPlatformTools sends include_drafts when requested', async () => {
      // Override the default handler to echo back the query params it received
      // so we can assert the service forwards include_drafts to the backend.
      let capturedParams = ''
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, ({ request }) => {
          capturedParams = new URL(request.url).searchParams.toString()
          return HttpResponse.json({ success: true, data: [] })
        }),
      )
      await agentService.getPlatformTools(false, { includeDrafts: true })
      expect(capturedParams).toContain('only_active=false')
      expect(capturedParams).toContain('include_drafts=true')
    })

    it('publishPlatformTool posts to the publish endpoint and returns the tool', async () => {
      const result = await agentService.publishPlatformTool('tool-9', true)
      expect(result).toMatchObject({ id: 'tool-9', is_published: true })
    })

    it('unpublishPlatformTool posts to the unpublish endpoint and returns the tool', async () => {
      const result = await agentService.publishPlatformTool('tool-9', false)
      expect(result).toMatchObject({ id: 'tool-9', is_published: false })
    })

    it('updatePlatformTool PUTs to the platform endpoint and returns the tool', async () => {
      const result = await agentService.updatePlatformTool('tool-9', {
        name: 'renamed',
        tool_source: 'mcp',
        mcp_server_url: 'https://example.com/mcp',
      } as any)
      expect(result).toMatchObject({ id: 'tool-9', name: 'renamed' })
    })

    it('deletePlatformTool deletes the platform tool', async () => {
      const result = await agentService.deletePlatformTool('tool-9')
      expect(result).toMatchObject({ deleted: true })
    })

    it('deletePlatformTool sends ?force=true when force is set', async () => {
      let calledUrl = ''
      server.use(
        http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, ({ request }) => {
          calledUrl = request.url
          return HttpResponse.json({ deleted: true })
        }),
      )
      const result = await agentService.deletePlatformTool('tool-9', true)
      expect(result).toMatchObject({ deleted: true })
      expect(calledUrl).toContain('force=true')
    })

    it('getPlatformToolUsage returns count + agents', async () => {
      const result = await agentService.getPlatformToolUsage('tool-9')
      expect(result).toMatchObject({ count: expect.any(Number), agents: expect.any(Array) })
    })
  })

  describe('Test Token Methods', () => {
    it('getTestToken returns test token data', async () => {
      const result = await agentService.getTestToken('agent-1')
      expect(result).toMatchObject({
        token: expect.any(String),
        serverUrl: expect.any(String),
        roomName: expect.any(String),
      })
      // Verify room name format
      expect(result.roomName).toContain('test_')
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
