/**
 * Sample data factories for tests
 */

import { type UserProfile } from '@/types/auth'
import { type VoiceAgent, type AgentTool, type PlatformTool } from '@/types/agent'
import { type Organization } from '@/types/organization'
import { type SubscriptionPlan } from '@/types/billing'
import { type CreditBalance } from '@/types/billing'
import { type Role, type Permission } from '@/types/rbac'

export const createMockUser = (overrides: Partial<UserProfile> = {}): UserProfile => ({
  id: 'user-1',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  email_confirmed_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockAgent = (overrides: Partial<VoiceAgent> = {}): VoiceAgent => ({
  id: 'agent-1',
  name: 'Test Agent',
  description: 'A test voice agent',
  system_prompt: 'You are a helpful assistant',
  voice_settings: {
    provider: 'openai',
    voice: 'alloy',
  },
  organization_id: 'org-1',
  created_by: 'user-1',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockPlatformTool = (overrides: Partial<PlatformTool> = {}): PlatformTool => ({
  id: 'tool-1',
  name: 'test_tool',
  display_name: 'Test Tool',
  description: 'A test tool',
  requires_auth: true,
  auth_type: 'oauth2',
  is_active: true,
  config_schema: {},
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockAgentTool = (overrides: Partial<AgentTool> = {}): AgentTool => ({
  id: 'agent-tool-1',
  agent_id: 'agent-1',
  platform_tool_id: 'tool-1',
  config: {},
  connection_status: 'connected',
  auth_status: 'authenticated',
  selected_functions: ['function1'],
  tool: createMockPlatformTool(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockOrganization = (overrides: Partial<Organization> = {}): Organization => ({
  id: 'org-1',
  name: 'Test Organization',
  description: 'A test organization',
  slug: 'test-org',
  website: 'https://example.com',
  is_active: true,
  business_details: { industry: 'Technology' },
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockSubscriptionPlan = (overrides: Partial<SubscriptionPlan> = {}): SubscriptionPlan => ({
  id: 'plan-1',
  name: 'Pro Plan',
  description: 'Professional tier',
  price_amount: 4900,
  price_currency: 'usd',
  billing_period: 'monthly',
  included_credits: 1000,
  trial_period_days: 14,
  is_active: true,
  stripe_price_id: 'price_test123',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockCreditBalance = (overrides: Partial<CreditBalance> = {}): CreditBalance => ({
  total_credits: 1000,
  subscription_credits: 800,
  purchased_credits: 200,
  expiring_soon: 50,
  ...overrides,
})

export const createMockRole = (overrides: Partial<Role> = {}): Role => ({
  id: 'role-1',
  name: 'org_admin',
  description: 'Organization administrator',
  permissions: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockPermission = (overrides: Partial<Permission> = {}): Permission => ({
  id: 'perm-1',
  name: 'agents:read',
  description: 'Read agents',
  resource: 'agents',
  action: 'read',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})
