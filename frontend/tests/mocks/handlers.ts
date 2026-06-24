/**
 * MSW request handlers for API mocking
 */

import { http, HttpResponse } from 'msw'
import { createMockUser, createMockAgent, createMockPlatformTool, createMockOrganization, createMockSubscriptionPlan, createMockCreditBalance, createMockRole, createMockPermission, createMockPhoneNumber, createMockPhoneNumberWithAgent, createMockAvailablePhoneNumber, createMockOrganizationSkill, createMockAgentSkill, createMockSkillFileSummary, createMockSkillFile, createMockSkillImportResult, createMockPlatformSkillSummary, createMockPlatformSkill, createMockPlatformSkillFileSummary, createMockPlatformSkillFile, createMockPlatformSkillImportResult } from '../utils/data-factories'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const handlers = [
  // Auth endpoints
  http.get(`${API_BASE_URL}/api/v1/auth/me`, () => {
    return HttpResponse.json({
      success: true,
      data: createMockUser(),
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/auth/process-invitation`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Invitation processed' },
    })
  }),

  // Agent endpoints - more specific patterns first
  http.get(`${API_BASE_URL}/api/v1/agents/my-agents`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockAgent()],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/agents/:id/test-token`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        token: 'test_token_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9',
        serverUrl: 'wss://test.livekit.cloud',
        roomName: 'test_agent-123_abc123',
      },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/agents/organization/:orgId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: [createMockAgent({ organization_id: params.orgId as string })],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/agents/:id`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: createMockAgent({ id: params.id as string }),
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/agents`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockAgent()],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/agents`, async ({ request }) => {
    const body = await request.json() as { name: string; system_prompt: string }
    return HttpResponse.json({
      success: true,
      data: createMockAgent({
        name: body.name,
        system_prompt: body.system_prompt || 'You are a helpful assistant',
      }),
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/agents/:id`, async ({ params, request }) => {
    const body = await request.json() as Record<string, any>
    return HttpResponse.json({
      success: true,
      data: createMockAgent({ id: params.id as string, ...body }),
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/agents/:id`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Agent deleted' },
    })
  }),

  // Tool endpoints
  http.get(`${API_BASE_URL}/api/v1/tools/platform`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockPlatformTool()],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/tools/agent/:agentId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'agent-tool-1',
        agent_id: params.agentId as string,
        platform_tool_id: 'tool-1',
        config: {},
        connection_status: 'connected',
        auth_status: 'authenticated',
        selected_functions: ['function1'],
        tool: createMockPlatformTool(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/tools/agent`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Tool configured' },
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/tools/agent/:agentToolId`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Tool updated' },
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/tools/agent/:agentToolId`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Tool deleted' },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/tools/auth/:toolName`, ({ request, params }) => {
    const url = new URL(request.url)
    const agentId = url.searchParams.get('agent_id')
    return HttpResponse.json({
      success: true,
      data: { auth_url: `https://oauth.com/auth?tool=${params.toolName}&agent=${agentId}` },
    })
  }),

  // Organization endpoints
  http.get(`${API_BASE_URL}/api/v1/organizations`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockOrganization()],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/organizations/:id`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: createMockOrganization({ id: params.id as string }),
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/organizations`, async ({ request }) => {
    const body = await request.json() as { name: string }
    return HttpResponse.json({
      success: true,
      data: createMockOrganization({ name: body.name }),
    })
  }),

  http.patch(`${API_BASE_URL}/api/v1/organizations/:id`, async ({ params, request }) => {
    const body = await request.json() as Record<string, any>
    return HttpResponse.json({
      success: true,
      data: createMockOrganization({ id: params.id as string, ...body }),
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/organizations/:id`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Organization deleted' },
    })
  }),

  // Billing endpoints
  http.get(`${API_BASE_URL}/api/v1/billing/info`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        subscription: createMockSubscriptionPlan(),
        credit_balance: createMockCreditBalance(),
      },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/plans`, ({ request }) => {
    const url = new URL(request.url)
    const activeOnly = url.searchParams.get('active_only') !== 'false'

    const plans = [
      createMockSubscriptionPlan({
        id: 'plan-1',
        name: 'Pro Plan',
        price_amount: 2900,
        is_active: true,
      }),
      createMockSubscriptionPlan({
        id: 'plan-2',
        name: 'Enterprise Plan',
        price_amount: 9900,
        is_active: true,
      }),
    ]

    return HttpResponse.json({
      success: true,
      data: activeOnly ? plans.filter(p => p.is_active) : plans,
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/subscribe`, () => {
    return HttpResponse.json({
      success: true,
      data: { checkout_url: 'https://stripe.com/checkout' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/cancel`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Subscription cancelled' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/credits/purchase`, () => {
    return HttpResponse.json({
      success: true,
      data: { checkout_url: 'https://stripe.com/checkout' },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/credits/balance`, () => {
    return HttpResponse.json({
      success: true,
      data: createMockCreditBalance(),
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/summary`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        subscription: createMockSubscriptionPlan(),
        credit_balance: createMockCreditBalance(),
        billing_history: [],
      },
    })
  }),

  // Additional auth endpoints
  http.post(`${API_BASE_URL}/api/v1/auth/refresh`, () => {
    return HttpResponse.json({
      success: true,
      data: { access_token: 'new-token', refresh_token: 'new-refresh-token' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/auth/signout`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Signed out' },
    })
  }),

  // Organization members endpoint
  http.get(`${API_BASE_URL}/api/v1/organizations/:orgId/members`, () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'member-1',
        email: 'member@example.com',
        first_name: 'Member',
        last_name: 'User',
        is_verified: true,
        created_at: new Date().toISOString(),
        roles: [],
      }],
    })
  }),

  // Organization invite endpoint
  http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/invite`, async ({ request }) => {
    const body = await request.json() as { email: string }
    return HttpResponse.json({
      success: true,
      data: {
        id: 'invite-1',
        email: body.email,
        status: 'pending',
        created_at: new Date().toISOString(),
      },
    })
  }),

  // Organization self endpoint
  http.post(`${API_BASE_URL}/api/v1/organizations/self`, async ({ request }) => {
    const body = await request.json() as { name: string }
    return HttpResponse.json({
      success: true,
      data: createMockOrganization({ name: body.name }),
    })
  }),

  // Additional billing endpoints
  http.get(`${API_BASE_URL}/api/v1/billing/credits/:orgId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: createMockCreditBalance(),
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/subscription/:orgId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: {
        id: 'sub-1',
        organization_id: params.orgId,
        plan: createMockSubscriptionPlan(),
        status: 'active',
        created_at: new Date().toISOString(),
      },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/summary/:orgId`, () => {
    return HttpResponse.json({
      success: true,
      data: {
        subscription: createMockSubscriptionPlan(),
        credit_balance: createMockCreditBalance(),
        billing_history: [],
      },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/history/:orgId`, () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'history-1',
        type: 'subscription',
        amount: 4900,
        currency: 'usd',
        description: 'Pro Plan - Monthly',
        created_at: new Date().toISOString(),
      }],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/credit-events`, () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'event-1',
        name: 'voice_call',
        credits_per_unit: 1,
        is_active: true,
      }],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/credit-products`, () => {
    return HttpResponse.json({
      success: true,
      data: [{
        id: 'product-1',
        name: '1000 Credits',
        credits: 1000,
        price_amount: 999,
        price_currency: 'usd',
        is_active: true,
      }],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/credits/consume`, () => {
    return HttpResponse.json({
      success: true,
      data: { remaining_credits: 900 },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/credit-products/checkout`, () => {
    return HttpResponse.json({
      success: true,
      data: { checkout_url: 'https://stripe.com/checkout', session_id: 'session-1' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/subscription/portal`, () => {
    return HttpResponse.json({
      success: true,
      data: { portal_url: 'https://stripe.com/portal' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/checkout/subscription`, () => {
    return HttpResponse.json({
      success: true,
      data: { session_url: 'https://stripe.com/checkout', session_id: 'session-1' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/checkout/credits`, () => {
    return HttpResponse.json({
      success: true,
      data: { session_url: 'https://stripe.com/checkout', session_id: 'session-1' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/subscription/cancel`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Subscription cancelled' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/subscription/reactivate`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Subscription reactivated' },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/billing/plans/:planId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: createMockSubscriptionPlan({ id: params.planId as string }),
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/billing/plans`, async ({ request }) => {
    const body = await request.json() as { name: string }
    return HttpResponse.json({
      success: true,
      data: createMockSubscriptionPlan({ name: body.name }),
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/billing/plans/:planId`, async ({ params, request }) => {
    const body = await request.json() as Record<string, any>
    return HttpResponse.json({
      success: true,
      data: createMockSubscriptionPlan({ id: params.planId as string, ...body }),
    })
  }),

  // RBAC endpoints
  http.get(`${API_BASE_URL}/api/v1/rbac/roles`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockRole()],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/roles/:roleId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: createMockRole({ id: params.roleId as string }),
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/rbac/roles`, async ({ request }) => {
    const body = await request.json() as { name: string }
    return HttpResponse.json({
      success: true,
      data: createMockRole({ name: body.name }),
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/rbac/roles/:roleId`, async ({ params, request }) => {
    const body = await request.json() as Record<string, any>
    return HttpResponse.json({
      success: true,
      data: createMockRole({ id: params.roleId as string, ...body }),
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/rbac/roles/:roleId`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Role deleted' },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/permissions`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockPermission()],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/permissions/:permissionId`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: createMockPermission({ id: params.permissionId as string }),
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/rbac/permissions`, async ({ request }) => {
    const body = await request.json() as { name: string }
    return HttpResponse.json({
      success: true,
      data: createMockPermission({ name: body.name }),
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/rbac/permissions/:permissionId`, async ({ params, request }) => {
    const body = await request.json() as Record<string, any>
    return HttpResponse.json({
      success: true,
      data: createMockPermission({ id: params.permissionId as string, ...body }),
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/rbac/permissions/:permissionId`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Permission deleted' },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/roles/:roleId/permissions`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockPermission()],
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/rbac/roles/:roleId/permissions`, () => {
    return HttpResponse.json({
      success: true,
      data: { role_id: 'role-1', permission_id: 'perm-1' },
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/rbac/roles/:roleId/permissions/:permissionId`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Permission removed from role' },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/rbac/user-roles`, async ({ request }) => {
    const body = await request.json() as { user_id: string; role_id: string }
    return HttpResponse.json({
      success: true,
      data: {
        id: 'user-role-1',
        user_id: body.user_id,
        role_id: body.role_id,
        created_at: new Date().toISOString(),
      },
    })
  }),

  http.put(`${API_BASE_URL}/api/v1/rbac/user-roles/:userRoleId`, async ({ params, request }) => {
    const body = await request.json() as Record<string, any>
    return HttpResponse.json({
      success: true,
      data: {
        id: params.userRoleId,
        ...body,
        updated_at: new Date().toISOString(),
      },
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/rbac/user-roles/:userRoleId`, () => {
    return HttpResponse.json({
      success: true,
      data: { message: 'Role removed from user' },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/users/:userId/roles`, () => {
    return HttpResponse.json({
      success: true,
      data: [createMockRole()],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/users/:userId/roles-with-permissions`, () => {
    return HttpResponse.json({
      success: true,
      data: [{
        ...createMockRole(),
        permissions: [createMockPermission()],
      }],
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/users/:userId/has-permission`, ({ request }) => {
    return HttpResponse.json({
      success: true,
      data: { has_permission: true },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/rbac/users/:userId/has-role`, ({ request }) => {
    return HttpResponse.json({
      success: true,
      data: { has_role: true },
    })
  }),

  // Phone Number endpoints
  http.get(`${API_BASE_URL}/api/v1/phone-numbers/available`, ({ request }) => {
    const url = new URL(request.url)
    const phoneNumberType = url.searchParams.get('phone_number_type')
    const areaCode = url.searchParams.get('area_code')
    const page = parseInt(url.searchParams.get('page') || '1')
    const pageSize = parseInt(url.searchParams.get('page_size') || '10')

    return HttpResponse.json({
      success: true,
      data: {
        items: [createMockAvailablePhoneNumber({ phone_number_type: phoneNumberType as any, area_code: areaCode })],
        total_count: 1,
        page: page,
        page_size: pageSize,
        total_pages: Math.ceil(1 / pageSize),
      },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/phone-numbers/purchase`, async ({ request }) => {
    const body = await request.json() as { phone_number: string }
    return HttpResponse.json({
      success: true,
      data: {
        success: true,
        phone_number: createMockPhoneNumber({ phone_number: body.phone_number }),
        message: 'Phone number purchased successfully',
        credit_balance_after: 800,
      },
    })
  }),

  http.get(`${API_BASE_URL}/api/v1/phone-numbers`, ({ params, request }) => {
    const url = new URL(request.url)
    const organizationId = url.searchParams.get('organization_id')

    return HttpResponse.json({
      success: true,
      data: {
        items: [createMockPhoneNumberWithAgent({ organization_id: organizationId || 'org-1' })],
        total_count: 1,
        unused_count: 1,
      },
    })
  }),

  http.post(`${API_BASE_URL}/api/v1/phone-numbers/:id/assign`, async ({ params, request }) => {
    const body = await request.json() as { agent_id: string }
    return HttpResponse.json({
      success: true,
      data: {
        success: true,
        phone_number: createMockPhoneNumberWithAgent({ id: params.id as string, assigned_agent_id: body.agent_id, agent_name: 'Test Agent' }),
      },
    })
  }),

  http.delete(`${API_BASE_URL}/api/v1/phone-numbers/:id`, ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: {
        success: true,
        message: 'Phone number cancelled successfully',
      },
    })
  }),

  // Skill endpoints
  http.get(`${API_BASE_URL}/api/v1/organizations/:orgId/skills`, () => {
    return HttpResponse.json([
      createMockOrganizationSkill(),
      createMockOrganizationSkill({
        id: 'skill-2',
        slug: 'call-transfer',
        name: 'Call Transfer',
        description: 'Escalate calls to a human agent.',
        category: 'custom',
      }),
      createMockOrganizationSkill({
        id: 'skill-3',
        slug: 'my-custom-skill',
        name: 'My Custom Skill',
        description: 'A custom skill.',
        category: 'custom',
        author: null,
        version: null,
      }),
    ])
  }),

  http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(
      createMockOrganizationSkill({
        id: 'skill-new',
        slug: body.slug as string,
        name: body.name as string,
        description: body.description as string,
        content: body.content as string,
        category: 'custom',
      }),
      { status: 201 }
    )
  }),

  http.put(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId`, async ({ request, params }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(
      createMockOrganizationSkill({
        id: params.skillId as string,
        name: (body.name as string) || 'Updated Skill',
        content: (body.content as string) || '# Updated',
      })
    )
  }),

  http.delete(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/seed`, () => {
    return HttpResponse.json({ seeded: 0 })
  }),

  // Platform skills endpoints
  http.get(`${API_BASE_URL}/api/v1/platform/skills`, ({ request }) => {
    const url = new URL(request.url)
    const statuses = url.searchParams.getAll('statuses')
    const skillList: ReturnType<typeof createMockPlatformSkillSummary>[] = [createMockPlatformSkillSummary()]
    if (statuses.includes('deprecated')) {
      skillList.push(
        createMockPlatformSkillSummary({
          id: 'platform-skill-2',
          slug: 'old-skill',
          name: 'Old Skill',
          status: 'deprecated',
        }),
      )
    }
    if (statuses.includes('deleted')) {
      skillList.push(
        createMockPlatformSkillSummary({
          id: 'platform-skill-3',
          slug: 'deleted-skill',
          name: 'Deleted Skill',
          status: 'deleted',
        }),
      )
    }
    return HttpResponse.json(skillList)
  }),

  http.post(`${API_BASE_URL}/api/v1/platform/skills/:skillId/restore`, () => {
    return HttpResponse.json(createMockPlatformSkill({ status: 'active' }))
  }),

  http.post(`${API_BASE_URL}/api/v1/platform/skills/:skillId/deprecate`, () => {
    return HttpResponse.json(createMockPlatformSkill({ status: 'deprecated' }))
  }),

  http.post(`${API_BASE_URL}/api/v1/platform/skills/:skillId/reactivate`, () => {
    return HttpResponse.json(createMockPlatformSkill({ status: 'active' }))
  }),

  http.get(`${API_BASE_URL}/api/v1/platform/skills/:skillId`, () => {
    return HttpResponse.json(createMockPlatformSkill())
  }),

  http.post(`${API_BASE_URL}/api/v1/platform/skills`, async ({ request }) => {
    const body = (await request.json()) as { slug: string; name: string }
    return HttpResponse.json(createMockPlatformSkill({ slug: body.slug, name: body.name }), { status: 201 })
  }),

  http.put(`${API_BASE_URL}/api/v1/platform/skills/:skillId`, async ({ request }) => {
    const body = (await request.json()) as { name?: string }
    return HttpResponse.json(createMockPlatformSkill({ name: body.name ?? 'Appointment Booking' }))
  }),

  http.delete(`${API_BASE_URL}/api/v1/platform/skills/:skillId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${API_BASE_URL}/api/v1/platform/skills/:skillId/files`, () => {
    return HttpResponse.json([createMockPlatformSkillFileSummary()])
  }),

  http.get(`${API_BASE_URL}/api/v1/platform/skills/:skillId/files/:fileId`, () => {
    return HttpResponse.json(createMockPlatformSkillFile())
  }),

  http.post(`${API_BASE_URL}/api/v1/platform/skills/:skillId/files`, async ({ request }) => {
    const body = (await request.json()) as { file_path: string }
    return HttpResponse.json(createMockPlatformSkillFile({ file_path: body.file_path }), { status: 201 })
  }),

  http.put(`${API_BASE_URL}/api/v1/platform/skills/:skillId/files/:fileId`, async ({ request }) => {
    const body = (await request.json()) as { file_path: string; content: string }
    return HttpResponse.json(createMockPlatformSkillFile({ file_path: body.file_path, content: body.content }))
  }),

  http.delete(`${API_BASE_URL}/api/v1/platform/skills/:skillId/files/:fileId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/fork`, async ({ request }) => {
    const body = (await request.json()) as { platform_skill_id: string }
    const forked = createMockOrganizationSkill({
      slug: 'appointment-booking',
      name: 'Appointment Booking',
      source_skill_id: body.platform_skill_id,
      source_version: '2026.01.01_1',
    })
    return HttpResponse.json(forked)
  }),

  http.get(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/update-check`, () => {
    return HttpResponse.json({ update_available: true, latest_version: '2026.05.01_2', current_version: null })
  }),

  http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/refresh`, async ({ request }) => {
    const body = (await request.json()) as { confirm_overwrite: boolean }
    if (!body.confirm_overwrite) {
      return HttpResponse.json({ detail: 'confirm_overwrite required' }, { status: 400 })
    }
    return HttpResponse.json(createMockOrganizationSkill())
  }),

  http.get(`${API_BASE_URL}/api/v1/agents/:agentId/skills`, () => {
    return HttpResponse.json([
      createMockAgentSkill(),
    ])
  }),

  http.post(`${API_BASE_URL}/api/v1/agents/:agentId/skills`, () => {
    return HttpResponse.json({ success: true }, { status: 201 })
  }),

  http.delete(`${API_BASE_URL}/api/v1/agents/:agentId/skills/:skillId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  // Skill file endpoints
  http.get(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/files`, () => {
    return HttpResponse.json([
      createMockSkillFileSummary(),
      createMockSkillFileSummary({
        id: 'file-summary-2',
        file_path: 'references/cancellation.md',
        file_kind: 'reference',
        content_hash: 'filehash456',
      }),
      createMockSkillFileSummary({
        id: 'file-summary-3',
        file_path: 'scripts/validate.py',
        file_kind: 'script',
        content_hash: 'filehash789',
      }),
    ])
  }),

  http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/files`, async ({ request }) => {
    const body = await request.json() as { file_path: string; content: string; file_kind?: string }
    return HttpResponse.json(
      createMockSkillFile({
        file_path: body.file_path,
        content: body.content,
        file_kind: body.file_kind as any || 'reference',
      }),
      { status: 201 },
    )
  }),

  http.put(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/files/:fileId`, async ({ request, params }) => {
    const body = await request.json() as { file_path?: string; content?: string }
    return HttpResponse.json(
      createMockSkillFile({
        id: params.fileId as string,
        file_path: body.file_path || 'references/policies.md',
        content: body.content || '# Updated content',
      }),
    )
  }),

  http.delete(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/files/:fileId`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/:skillId/agents`, () => {
    return HttpResponse.json([
      { id: 'agent-1', name: 'Support Agent', is_active: true },
      { id: 'agent-2', name: 'Sales Agent', is_active: false },
    ])
  }),

  http.get(new RegExp(`${API_BASE_URL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/api/v1/skills/[^/]+/[^/]+/files/.*`), () => {
    return HttpResponse.json('# Booking Policies\n\n- Confirm insurance\n- Verify ID')
  }),

  http.post(`${API_BASE_URL}/api/v1/platform/skills/import`, async ({ request }) => {
    const body = await request.json() as { url: string }
    return HttpResponse.json(
      [
        createMockPlatformSkillImportResult({
          source_url: body.url,
          skill: createMockPlatformSkill({ slug: 'imported-platform-skill', name: 'Imported Platform Skill' }),
        }),
      ],
      { status: 201 },
    )
  }),

    http.post(`${API_BASE_URL}/api/v1/organizations/:orgId/skills/import`, async ({ request }) => {
    const body = await request.json() as { url: string }
    return HttpResponse.json(
      [
        createMockSkillImportResult({
          source_url: body.url,
        }),
      ],
      { status: 201 },
    )
  }),
]
