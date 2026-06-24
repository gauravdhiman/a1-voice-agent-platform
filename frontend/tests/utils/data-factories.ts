/**
 * Sample data factories for tests
 */

import { type UserProfile } from '@/types/auth'
import { type VoiceAgent, type AgentTool, type PlatformTool } from '@/types/agent'
import { type Organization } from '@/types/organization'
import { type SubscriptionPlan } from '@/types/billing'
import { type CreditBalance } from '@/types/billing'
import { type Role, type Permission, type RoleWithPermissions } from '@/types/rbac'
import { type PhoneNumber, type PhoneNumberWithAgent, type AvailablePhoneNumber, type PhoneNumberType, type PhoneNumberStatus } from '@/types/phone-number'
import { type OrganizationSkill, type AgentSkill, type SkillFile, type SkillFileSummary, type SkillImportResult } from '@/types/skill'

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
  use_platform_credits: true,
  instructions_markdown: null,
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
  onboarding_completed: false,
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

export const createMockPhoneNumber = (overrides: Partial<PhoneNumber> = {}): PhoneNumber => ({
  id: 'phone-1',
  phone_number: '+14155551234',
  provider: 'twilio',
  provider_sid: 'PN123',
  phone_number_type: 'local' as PhoneNumberType,
  country_code: 'US',
  area_code: '415',
  monthly_cost_credits: 200,
  status: 'active' as PhoneNumberStatus,
  assigned_agent_id: null,
  is_incoming_enabled: true,
  is_outgoing_enabled: true,
  organization_id: 'org-1',
  purchased_at: new Date().toISOString(),
  cancelled_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockPhoneNumberWithAgent = (overrides: Partial<PhoneNumberWithAgent> = {}): PhoneNumberWithAgent => ({
  ...createMockPhoneNumber(),
  agent_name: null,
  ...overrides,
})

export const createMockAvailablePhoneNumber = (overrides: Partial<AvailablePhoneNumber> = {}): AvailablePhoneNumber => ({
  phone_number: '+14155551234',
  phone_number_type: 'local' as PhoneNumberType,
  country_code: 'US',
  area_code: '415',
  monthly_cost_credits: 200,
  capabilities: {
    voice: true,
    sms: true,
    mms: false,
  },
  locality: 'San Francisco',
  postal_code: '94102',
  ...overrides,
})

export const createMockOrganizationSkill = (overrides: Partial<OrganizationSkill> = {}): OrganizationSkill => ({
  id: 'skill-1',
  organization_id: 'org-1',
  slug: 'appointment-booking',
  name: 'Appointment Booking',
  description: 'Handle scheduling, rescheduling, and cancellation of appointments.',
  content: '# Appointment Booking\n\n## When to Use\n- Caller asks to book\n\n## Procedure\n1. Ask for date',
  category: 'custom' as const,
  is_active: true,
  version: '1.0.0',
  author: 'Platform',
  content_hash: 'abc123def456',
  is_visible: true,
  source_skill_id: null,
  source_version: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockPlatformSkillSummary = (overrides: Partial<import("@/types/skill").PlatformSkillSummary> = {}): import("@/types/skill").PlatformSkillSummary => ({
  id: 'platform-skill-1',
  slug: 'appointment-booking',
  name: 'Appointment Booking',
  description: 'Handle scheduling, rescheduling, and cancellation of appointments.',
  version: '2026.01.01_1',
  status: 'active',
  ...overrides,
})

export const createMockPlatformSkill = (overrides: Partial<import("@/types/skill").PlatformSkill> = {}): import("@/types/skill").PlatformSkill => ({
  id: 'platform-skill-1',
  slug: 'appointment-booking',
  name: 'Appointment Booking',
  description: 'Handle scheduling, rescheduling, and cancellation of appointments.',
  content: '# Appointment Booking\n\n## When to use\n...',
  version: '2026.01.01_1',
  author: 'Platform',
  content_hash: 'hash-platform-skill-1',
  status: 'active',
  files: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockPlatformSkillFileSummary = (overrides: Partial<import("@/types/skill").PlatformSkillFileSummary> = {}): import("@/types/skill").PlatformSkillFileSummary => ({
  id: 'platform-file-1',
  skill_id: 'platform-skill-1',
  file_path: 'references/faqs.md',
  file_kind: 'reference',
  content_hash: 'hash-file-1',
  ...overrides,
})

export const createMockPlatformSkillImportResult = (overrides: Partial<import("@/types/skill").PlatformSkillImportResult> = {}): import("@/types/skill").PlatformSkillImportResult => ({
  skill: createMockPlatformSkill(),
  files_imported: 2,
  source_url: 'https://github.com/owner/repo',
  ...overrides,
})

export const createMockPlatformSkillFile = (overrides: Partial<import("@/types/skill").PlatformSkillFile> = {}): import("@/types/skill").PlatformSkillFile => ({
  id: 'platform-file-1',
  skill_id: 'platform-skill-1',
  file_path: 'references/faqs.md',
  content: '# FAQs\n\nCommon questions.',
  file_kind: 'reference',
  content_hash: 'hash-file-1',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockAgentSkill = (overrides: Partial<AgentSkill> = {}): AgentSkill => ({
  id: 'agent-skill-1',
  agent_id: 'agent-1',
  skill_id: 'skill-1',
  skill: createMockOrganizationSkill(),
  is_active: true,
  created_at: new Date().toISOString(),
  ...overrides,
})

export const createMockSkillFileSummary = (overrides: Partial<SkillFileSummary> = {}): SkillFileSummary => ({
  id: 'file-summary-1',
  file_path: 'references/policies.md',
  file_kind: 'reference',
  content_hash: 'filehash123',
  ...overrides,
})

export const createMockSkillFile = (overrides: Partial<SkillFile> = {}): SkillFile => ({
  id: 'file-1',
  skill_id: 'skill-1',
  file_path: 'references/policies.md',
  content: '# Policies\n\n- Be respectful\n- Verify identity',
  file_kind: 'reference' as const,
  content_hash: 'filehash123',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides,
})

export const createMockSkillImportResult = (overrides: Partial<SkillImportResult> = {}): SkillImportResult => ({
  skill: createMockOrganizationSkill({ slug: 'imported-skill', name: 'Imported Skill' }),
  files_imported: 3,
  source_url: 'https://github.com/owner/repo/tree/main/my-skill',
  ...overrides,
})
