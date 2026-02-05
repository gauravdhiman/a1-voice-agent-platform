/**
 * Sample data factories for tests
 */

import { type UserProfile } from '@/types/auth'
import { type VoiceAgent, type AgentTool, type PlatformTool } from '@/types/agent'
import { type Organization } from '@/types/organization'
import { type SubscriptionPlan } from '@/types/billing'
import { type CreditBalance } from '@/types/billing'
import { type Role, type Permission, type RoleWithPermissions } from '@/types/rbac'

export const createMockUser = (overrides: Partial<UserProfile> = {}): UserProfile => ({
  id: 'user-1',
  email: 'test@example.com',
  first_name: 'Test',
  last_name: 'User',
  email_confirmed_at: new Date().toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  roles: [],
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
  is_active: true,
  phone_number: null,
  organization_id: 'org-1',
  created_by: 'user-1',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  persona: null,
  tone: null,
  mission: null,
  custom_instructions: null,
  ...overrides,
})

export const createMockPlatformTool = (overrides: Partial<PlatformTool> = {}): PlatformTool => ({
  id: 'tool-1',
  name: 'test_tool',
  description: 'A test tool',
  requires_auth: true,
  auth_type: 'oauth2',
  is_active: true,
  config_schema: {},
  tool_functions_schema: null,
  auth_config: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockAgentTool = (overrides: Partial<AgentTool> = {}): AgentTool => ({
  id: 'agent-tool-1',
  agent_id: 'agent-1',
  tool_id: 'tool-1',
  config: {},
  sensitive_config: null,
  unselected_functions: null,
  is_enabled: true,
  connection_status: 'connected' as any,
  auth_status: 'authenticated' as any,
  token_expires_at: null,
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
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockSubscriptionPlan = (overrides: Partial<SubscriptionPlan> = {}): SubscriptionPlan => ({
  id: 'plan-1',
  name: 'Pro Plan',
  description: 'Professional tier',
  price_amount: 4900,
  currency: 'usd',
  interval: 'monthly',
  interval_count: 1,
  stripe_price_id: 'price_test123',
  stripe_product_id: 'prod_test123',
  included_credits: 1000,
  max_users: 5,
  features: {},
  trial_period_days: 14,
  is_active: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockCreditBalance = (overrides: Partial<CreditBalance> = {}): CreditBalance => ({
  total_credits: 1000,
  subscription_credits: 800,
  purchased_credits: 200,
  expiring_soon: 50,
  expires_at: null,
  ...overrides,
})

export const createMockRole = (overrides: Partial<RoleWithPermissions> = {}): RoleWithPermissions => ({
  id: 'role-1',
  name: 'org_admin',
  description: 'Organization administrator',
  is_system_role: false,
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
