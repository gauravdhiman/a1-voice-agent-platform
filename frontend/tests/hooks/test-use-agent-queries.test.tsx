/**
 * Tests for use-agent-queries hooks
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { 
  useMyAgents, 
  useOrgAgents, 
  useAgent, 
  usePlatformTools, 
  useAgentTools,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useConfigureAgentTool,
  useUpdateAgentTool,
  useDeleteAgentTool,
} from '@/hooks/use-agent-queries'

// Use vi.hoisted() to define mock data that will be available when vi.mock() is hoisted
const { mockAgent, mockPlatformTool, mockAgentTool } = vi.hoisted(() => ({
  mockAgent: {
    id: 'agent-1',
    name: 'Test Agent',
    description: 'A test voice agent',
    system_prompt: 'You are a helpful assistant',
    organization_id: 'org-1',
    created_by: 'user-1',
    voice_settings: {
      provider: 'openai',
      voice: 'alloy',
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  mockPlatformTool: {
    id: 'tool-1',
    name: 'Google Calendar',
    description: 'Calendar integration',
    config_schema: {},
    auth_type: 'oauth2',
    auth_config: {},
    tool_functions_schema: [],
    requires_auth: true,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  mockAgentTool: {
    id: 'agent-tool-1',
    agent_id: 'agent-1',
    platform_tool_id: 'tool-1',
    config: {},
    connection_status: 'connected',
    auth_status: 'authenticated',
    selected_functions: ['function1'],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
}))

vi.mock('@/services/agent-service', () => ({
  agentService: {
    getMyAgents: vi.fn().mockResolvedValue([mockAgent]),
    getOrgAgents: vi.fn().mockResolvedValue([mockAgent]),
    getAgentById: vi.fn().mockResolvedValue(mockAgent),
    getPlatformTools: vi.fn().mockResolvedValue([mockPlatformTool]),
    getAgentTools: vi.fn().mockResolvedValue([{
      ...mockAgentTool,
      tool: mockPlatformTool,
    }]),
    createAgent: vi.fn().mockResolvedValue({ ...mockAgent, id: 'new-agent-1' }),
    updateAgent: vi.fn().mockResolvedValue({ ...mockAgent, name: 'Updated Agent' }),
    deleteAgent: vi.fn().mockResolvedValue(undefined),
    configureAgentTool: vi.fn().mockResolvedValue(mockAgentTool),
    updateAgentTool: vi.fn().mockResolvedValue(mockAgentTool),
    deleteAgentTool: vi.fn().mockResolvedValue(undefined),
    startOAuth: vi.fn().mockResolvedValue({ auth_url: 'https://oauth.com/auth' }),
    logoutAgentTool: vi.fn().mockResolvedValue(undefined),
  },
}))

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

import { agentService } from '@/services/agent-service'
import { toast } from 'sonner'

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

describe('use-agent-queries', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('useMyAgents', () => {
    it('fetches user agents', async () => {
      const { result } = renderHook(() => useMyAgents(), {
        wrapper: TestWrapper,
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toHaveLength(1)
      expect(result.current.data?.[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })

    it('calls agent service', async () => {
      renderHook(() => useMyAgents(), {
        wrapper: TestWrapper,
      })

      await waitFor(() => {
        expect(agentService.getMyAgents).toHaveBeenCalled()
      })
    })
  })

  describe('useOrgAgents', () => {
    it('fetches agents for organization', async () => {
      const { result } = renderHook(() => useOrgAgents('org-1'), {
        wrapper: TestWrapper,
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toHaveLength(1)
    })

    it('calls agent service with org ID', async () => {
      renderHook(() => useOrgAgents('org-1'), {
        wrapper: TestWrapper,
      })

      await waitFor(() => {
        expect(agentService.getOrgAgents).toHaveBeenCalledWith('org-1')
      })
    })
  })

  describe('useAgent', () => {
    it('fetches single agent by ID', async () => {
      const { result } = renderHook(() => useAgent('agent-1'), {
        wrapper: TestWrapper,
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data?.id).toBe('agent-1')
    })

    it('calls agent service with agent ID', async () => {
      renderHook(() => useAgent('agent-1'), {
        wrapper: TestWrapper,
      })

      await waitFor(() => {
        expect(agentService.getAgentById).toHaveBeenCalledWith('agent-1')
      })
    })
  })

  describe('usePlatformTools', () => {
    it('fetches platform tools', async () => {
      const { result } = renderHook(() => usePlatformTools(), {
        wrapper: TestWrapper,
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toHaveLength(1)
      expect(result.current.data?.[0]).toMatchObject({
        name: expect.any(String),
        requires_auth: expect.any(Boolean),
      })
    })

    it('calls agent service with default onlyActive=true', async () => {
      renderHook(() => usePlatformTools(), {
        wrapper: TestWrapper,
      })

      await waitFor(() => {
        expect(agentService.getPlatformTools).toHaveBeenCalledWith(true)
      })
    })
  })

  describe('useAgentTools', () => {
    it('fetches tools for an agent', async () => {
      const { result } = renderHook(() => useAgentTools('agent-1'), {
        wrapper: TestWrapper,
      })

      await waitFor(() => expect(result.current.isSuccess).toBe(true))

      expect(result.current.data).toHaveLength(1)
      expect(result.current.data?.[0]).toMatchObject({
        agent_id: 'agent-1',
        connection_status: expect.any(String),
      })
    })

    it('calls agent service with agent ID', async () => {
      renderHook(() => useAgentTools('agent-1'), {
        wrapper: TestWrapper,
      })

      await waitFor(() => {
        expect(agentService.getAgentTools).toHaveBeenCalledWith('agent-1')
      })
    })
  })

  describe('useCreateAgent', () => {
    it('creates agent and shows success toast', async () => {
      const { result } = renderHook(() => useCreateAgent(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        await result.current.mutateAsync({
          name: 'New Agent',
          system_prompt: 'You are helpful',
          organization_id: 'org-1',
          voice_settings: { provider: 'openai', voice: 'alloy' },
        } as any)
      })

      expect(agentService.createAgent).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Agent created successfully')
    })

    it('shows error toast on failure', async () => {
      vi.mocked(agentService.createAgent).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useCreateAgent(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        try {
          await result.current.mutateAsync({
            name: 'New Agent',
            system_prompt: 'You are helpful',
            organization_id: 'org-1',
            voice_settings: { provider: 'openai', voice: 'alloy' },
          } as any)
        } catch (e) {
          // Expected to fail
        }
      })

      expect(toast.error).toHaveBeenCalledWith('Failed to create agent')
    })
  })

  describe('useUpdateAgent', () => {
    it('updates agent and shows success toast', async () => {
      const { result } = renderHook(() => useUpdateAgent(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        await result.current.mutateAsync({
          agentId: 'agent-1',
          data: { name: 'Updated Agent' },
        })
      })

      expect(agentService.updateAgent).toHaveBeenCalledWith('agent-1', { name: 'Updated Agent' })
      expect(toast.success).toHaveBeenCalledWith('Agent updated successfully')
    })

    it('shows error toast on failure', async () => {
      vi.mocked(agentService.updateAgent).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useUpdateAgent(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        try {
          await result.current.mutateAsync({
            agentId: 'agent-1',
            data: { name: 'Updated Agent' },
          })
        } catch (e) {
          // Expected to fail
        }
      })

      expect(toast.error).toHaveBeenCalledWith('Failed to update agent')
    })
  })

  describe('useDeleteAgent', () => {
    it('deletes agent and shows success toast', async () => {
      const { result } = renderHook(() => useDeleteAgent(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        await result.current.mutateAsync('agent-1')
      })

      expect(agentService.deleteAgent).toHaveBeenCalledWith('agent-1')
      expect(toast.success).toHaveBeenCalledWith('Agent deleted successfully')
    })

    it('shows error toast on failure', async () => {
      vi.mocked(agentService.deleteAgent).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useDeleteAgent(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        try {
          await result.current.mutateAsync('agent-1')
        } catch (e) {
          // Expected to fail
        }
      })

      expect(toast.error).toHaveBeenCalledWith('Failed to delete agent')
    })
  })

  describe('useConfigureAgentTool', () => {
    it('configures tool and shows success toast', async () => {
      const { result } = renderHook(() => useConfigureAgentTool(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        await result.current.mutateAsync({
          agent_id: 'agent-1',
          platform_tool_id: 'tool-1',
          config: {},
        } as any)
      })

      expect(agentService.configureAgentTool).toHaveBeenCalled()
      expect(toast.success).toHaveBeenCalledWith('Tool connected successfully')
    })

    it('shows error toast on failure', async () => {
      vi.mocked(agentService.configureAgentTool).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useConfigureAgentTool(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        try {
          await result.current.mutateAsync({
            agent_id: 'agent-1',
            platform_tool_id: 'tool-1',
            config: {},
          } as any)
        } catch (e) {
          // Expected to fail
        }
      })

      expect(toast.error).toHaveBeenCalledWith('Failed to connect tool')
    })
  })

  describe('useUpdateAgentTool', () => {
    it('updates tool configuration', async () => {
      const { result } = renderHook(() => useUpdateAgentTool(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        await result.current.mutateAsync({
          agentToolId: 'agent-tool-1',
          data: { config: { updated: true } },
        })
      })

      expect(agentService.updateAgentTool).toHaveBeenCalledWith('agent-tool-1', { config: { updated: true } })
    })

    it('shows error toast on failure', async () => {
      vi.mocked(agentService.updateAgentTool).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useUpdateAgentTool(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        try {
          await result.current.mutateAsync({
            agentToolId: 'agent-tool-1',
            data: { config: { updated: true } },
          })
        } catch (e) {
          // Expected to fail
        }
      })

      expect(toast.error).toHaveBeenCalledWith('Failed to update tool')
    })
  })

  describe('useDeleteAgentTool', () => {
    it('deletes tool and shows success toast', async () => {
      const { result } = renderHook(() => useDeleteAgentTool(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        await result.current.mutateAsync('agent-tool-1')
      })

      expect(agentService.deleteAgentTool).toHaveBeenCalledWith('agent-tool-1')
      expect(toast.success).toHaveBeenCalledWith('Tool disconnected successfully')
    })

    it('shows error toast on failure', async () => {
      vi.mocked(agentService.deleteAgentTool).mockRejectedValueOnce(new Error('Failed'))

      const { result } = renderHook(() => useDeleteAgentTool(), {
        wrapper: TestWrapper,
      })

      await act(async () => {
        try {
          await result.current.mutateAsync('agent-tool-1')
        } catch (e) {
          // Expected to fail
        }
      })

      expect(toast.error).toHaveBeenCalledWith('Failed to disconnect tool')
    })
  })
})
