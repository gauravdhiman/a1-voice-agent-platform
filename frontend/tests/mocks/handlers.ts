/**
 * MSW request handlers for API mocking
 */

import { http, HttpResponse } from 'msw'
import { createMockUser, createMockAgent, createMockPlatformTool, createMockOrganization, createMockSubscriptionPlan, createMockCreditBalance, createMockRole, createMockPermission } from '../utils/data-factories'

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

  http.put(`${API_BASE_URL}/api/v1/organizations/:id`, async ({ params, request }) => {
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
]
