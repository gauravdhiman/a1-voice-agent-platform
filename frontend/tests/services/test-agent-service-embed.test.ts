/**
 * Tests for agent service embed configuration methods
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { agentService, EmbedConfig, EmbedConfigCreate } from '@/services/agent-service'

// Mock the api client
vi.mock('@/lib/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { apiClient } from '@/lib/api/client'

const mockEmbedConfigResponse = {
  id: 'config-1',
  agent_id: 'agent-1',
  button_text: 'Call Us',
  button_color: '#3b82f6',
  button_text_color: '#ffffff',
  button_border_radius: 8,
  button_size: 'medium',
  button_position: 'bottom-right',
  button_style: 'filled',
  allowed_domains: ['example.com'],
  custom_css: null,
  is_active: true,
  daily_call_limit: 100,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
}

const expectedEmbedConfig: EmbedConfig = {
  id: 'config-1',
  agentId: 'agent-1',
  buttonText: 'Call Us',
  buttonColor: '#3b82f6',
  buttonTextColor: '#ffffff',
  buttonBorderRadius: 8,
  buttonSize: 'medium',
  buttonPosition: 'bottom-right',
  buttonStyle: 'filled',
  allowedDomains: ['example.com'],
  customCss: null,
  isActive: true,
  dailyCallLimit: 100,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
}

describe('agentService embed configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getEmbedConfig', () => {
    it('fetches embed config and transforms snake_case to camelCase', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockEmbedConfigResponse })

      const result = await agentService.getEmbedConfig('agent-1')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/agents/agent-1/embed-config')
      expect(result).toEqual(expectedEmbedConfig)
    })

    it('returns null when no config exists', async () => {
      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: null })

      const result = await agentService.getEmbedConfig('agent-1')

      expect(result).toBeNull()
    })

    it('handles outline button style', async () => {
      const outlineResponse = {
        ...mockEmbedConfigResponse,
        button_style: 'outline',
        button_color: '#F73B7D',
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: outlineResponse })

      const result = await agentService.getEmbedConfig('agent-1')

      expect(result?.buttonStyle).toBe('outline')
      expect(result?.buttonColor).toBe('#F73B7D')
    })
  })

  describe('createEmbedConfig', () => {
    it('creates embed config with transformed data', async () => {
      const createData: EmbedConfigCreate = {
        buttonText: 'Contact Us',
        buttonColor: '#22c55e',
        buttonTextColor: '#ffffff',
        buttonBorderRadius: 12,
        buttonSize: 'large',
        buttonPosition: 'bottom-left',
        buttonStyle: 'filled',
        allowedDomains: ['mysite.com'],
        customCss: '.button { font-weight: bold; }',
        isActive: true,
        dailyCallLimit: 50,
      }

      const createResponse = {
        ...mockEmbedConfigResponse,
        button_text: 'Contact Us',
        button_color: '#22c55e',
        button_border_radius: 12,
        button_size: 'large',
        button_position: 'bottom-left',
        allowed_domains: ['mysite.com'],
        custom_css: '.button { font-weight: bold; }',
        daily_call_limit: 50,
      }

      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: createResponse })

      const result = await agentService.createEmbedConfig('agent-1', createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/agents/agent-1/embed-config',
        expect.objectContaining({
          button_text: 'Contact Us',
          button_color: '#22c55e',
          button_text_color: '#ffffff',
          button_border_radius: 12,
          button_size: 'large',
          button_position: 'bottom-left',
          button_style: 'filled',
          allowed_domains: ['mysite.com'],
          custom_css: '.button { font-weight: bold; }',
          is_active: true,
          daily_call_limit: 50,
        })
      )

      expect(result?.buttonText).toBe('Contact Us')
      expect(result?.buttonColor).toBe('#22c55e')
      expect(result?.buttonBorderRadius).toBe(12)
    })

    it('handles optional fields correctly', async () => {
      const createData: EmbedConfigCreate = {
        buttonText: 'Call',
        buttonColor: '#3b82f6',
        buttonTextColor: '#ffffff',
        buttonBorderRadius: 8,
        buttonSize: 'medium',
        buttonPosition: 'bottom-right',
        isActive: true,
        dailyCallLimit: 100,
      }

      vi.mocked(apiClient.post).mockResolvedValueOnce({ data: mockEmbedConfigResponse })

      await agentService.createEmbedConfig('agent-1', createData)

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/agents/agent-1/embed-config',
        expect.objectContaining({
          button_style: undefined,
          allowed_domains: undefined,
          custom_css: undefined,
        })
      )
    })
  })

  describe('deleteEmbedConfig', () => {
    it('deletes embed config for an agent', async () => {
      vi.mocked(apiClient.delete).mockResolvedValueOnce({ data: undefined })

      await agentService.deleteEmbedConfig('agent-1')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/agents/agent-1/embed-config')
    })
  })

  describe('transformEmbedConfigResponse', () => {
    it('handles null allowed_domains', async () => {
      const responseWithNullDomains = {
        ...mockEmbedConfigResponse,
        allowed_domains: null,
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: responseWithNullDomains })

      const result = await agentService.getEmbedConfig('agent-1')

      expect(result?.allowedDomains).toBeNull()
    })

    it('handles empty allowed_domains array', async () => {
      const responseWithEmptyDomains = {
        ...mockEmbedConfigResponse,
        allowed_domains: [],
      }

      vi.mocked(apiClient.get).mockResolvedValueOnce({ data: responseWithEmptyDomains })

      const result = await agentService.getEmbedConfig('agent-1')

      expect(result?.allowedDomains).toEqual([])
    })

    it('handles all button positions', async () => {
      const positions = [
        'bottom-right',
        'bottom-left',
        'bottom-center',
        'top-right',
        'top-left',
        'top-center',
        'center',
      ]

      for (const position of positions) {
        const response = { ...mockEmbedConfigResponse, button_position: position }
        vi.mocked(apiClient.get).mockResolvedValueOnce({ data: response })

        const result = await agentService.getEmbedConfig('agent-1')

        expect(result?.buttonPosition).toBe(position as EmbedConfig['buttonPosition'])
      }
    })

    it('handles all button sizes', async () => {
      const sizes = ['small', 'medium', 'large']

      for (const size of sizes) {
        const response = { ...mockEmbedConfigResponse, button_size: size }
        vi.mocked(apiClient.get).mockResolvedValueOnce({ data: response })

        const result = await agentService.getEmbedConfig('agent-1')

        expect(result?.buttonSize).toBe(size as EmbedConfig['buttonSize'])
      }
    })
  })
})
