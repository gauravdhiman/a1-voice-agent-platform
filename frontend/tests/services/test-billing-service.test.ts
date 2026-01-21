/**
 * Tests for BillingService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { billingService } from '@/services/billing-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

describe('BillingService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Subscription Plans', () => {
    it('getSubscriptionPlans returns list of plans', async () => {
      const result = await billingService.getSubscriptionPlans()
      
      expect(result.length).toBeGreaterThan(0)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
        price_amount: expect.any(Number),
      })
    })

    it('getSubscriptionPlans with activeOnly=false', async () => {
      const result = await billingService.getSubscriptionPlans(false)
      
      expect(Array.isArray(result)).toBe(true)
    })

    it('getSubscriptionPlan returns single plan', async () => {
      const result = await billingService.getSubscriptionPlan('plan-1')
      
      expect(result).toMatchObject({
        id: 'plan-1',
        name: expect.any(String),
      })
    })

    it('createSubscriptionPlan creates new plan', async () => {
      const planData = {
        name: 'New Plan',
        description: 'A new subscription plan',
        price_amount: 1999,
        price_currency: 'usd',
        billing_period: 'monthly' as const,
        included_credits: 500,
        is_active: true,
      }

      const result = await billingService.createSubscriptionPlan(planData)
      
      expect(result).toMatchObject({
        name: 'New Plan',
      })
    })

    it('updateSubscriptionPlan updates plan', async () => {
      const updateData = { name: 'Updated Plan' }
      
      const result = await billingService.updateSubscriptionPlan('plan-1', updateData)
      
      expect(result).toMatchObject({
        id: 'plan-1',
        name: 'Updated Plan',
      })
    })
  })

  describe('Organization Subscriptions', () => {
    it('getOrganizationSubscription returns subscription', async () => {
      const result = await billingService.getOrganizationSubscription('org-1')
      
      expect(result).toMatchObject({
        organization_id: 'org-1',
        status: expect.any(String),
      })
    })

    it('createCustomerPortal returns portal URL', async () => {
      const result = await billingService.createCustomerPortal('org-1', 'https://example.com/return')
      
      expect(result).toMatchObject({
        portal_url: expect.any(String),
      })
    })

    it('cancelSubscription cancels subscription', async () => {
      const result = await billingService.cancelSubscription('org-1')
      
      expect(result).toMatchObject({
        message: expect.any(String),
      })
    })

    it('reactivateSubscription reactivates subscription', async () => {
      const result = await billingService.reactivateSubscription('org-1')
      
      expect(result).toMatchObject({
        message: expect.any(String),
      })
    })
  })

  describe('Credits', () => {
    it('getCreditBalance returns balance', async () => {
      const result = await billingService.getCreditBalance('org-1')
      
      expect(result).toMatchObject({
        total_credits: expect.any(Number),
      })
    })

    it('consumeCredits consumes credits', async () => {
      const request = {
        organization_id: 'org-1',
        event_type: 'voice_call',
        units: 10,
      }

      const result = await billingService.consumeCredits(request)
      
      expect(result).toMatchObject({
        remaining_credits: expect.any(Number),
      })
    })

    it('getCreditEvents returns events', async () => {
      const result = await billingService.getCreditEvents()
      
      expect(result.length).toBeGreaterThan(0)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
      })
    })

    it('getCreditProducts returns products', async () => {
      const result = await billingService.getCreditProducts()
      
      expect(result.length).toBeGreaterThan(0)
      expect(result[0]).toMatchObject({
        id: expect.any(String),
        name: expect.any(String),
        credits: expect.any(Number),
      })
    })

    it('createCreditPurchaseCheckout returns checkout URL', async () => {
      const result = await billingService.createCreditPurchaseCheckout(
        'org-1',
        'product-1',
        'https://example.com/success',
        'https://example.com/cancel'
      )
      
      expect(result).toMatchObject({
        checkout_url: expect.any(String),
        session_id: expect.any(String),
      })
    })
  })

  describe('Billing History', () => {
    it('getBillingHistory returns history', async () => {
      const result = await billingService.getBillingHistory('org-1')
      
      expect(Array.isArray(result)).toBe(true)
    })

    it('getBillingHistory with limit', async () => {
      const result = await billingService.getBillingHistory('org-1', 5)
      
      expect(Array.isArray(result)).toBe(true)
    })
  })

  describe('Billing Summary', () => {
    it('getBillingSummary returns summary', async () => {
      const result = await billingService.getBillingSummary('org-1')
      
      expect(result).toBeDefined()
    })
  })

  describe('Checkout Methods', () => {
    it('createSubscriptionCheckout returns checkout info', async () => {
      const result = await billingService.createSubscriptionCheckout('plan-1', 'org-1')
      
      expect(result).toMatchObject({
        session_url: expect.any(String),
        session_id: expect.any(String),
      })
    })

    it('createCreditsCheckout returns checkout info', async () => {
      const result = await billingService.createCreditsCheckout('product-1', 'org-1')
      
      expect(result).toMatchObject({
        session_url: expect.any(String),
        session_id: expect.any(String),
      })
    })
  })

  describe('Utility Methods', () => {
    it('formatCurrency formats correctly', () => {
      expect(billingService.formatCurrency(4900)).toBe('$49.00')
      expect(billingService.formatCurrency(999)).toBe('$9.99')
    })

    it('formatCredits formats correctly', () => {
      expect(billingService.formatCredits(1000)).toBe('1,000')
      expect(billingService.formatCredits(1000000)).toBe('1,000,000')
    })

    it('formatDate formats correctly', () => {
      const date = '2024-01-15T12:00:00Z'
      const result = billingService.formatDate(date)
      expect(result).toContain('2024')
      expect(result).toContain('January')
    })

    it('formatDateTime formats correctly', () => {
      const date = '2024-01-15T12:00:00Z'
      const result = billingService.formatDateTime(date)
      expect(result).toContain('2024')
    })

    it('calculateAnnualSavings calculates correctly', () => {
      // Monthly $49, Annual $490 = $98 savings
      expect(billingService.calculateAnnualSavings(4900, 49000)).toBe(9800)
    })

    it('calculateSavingsPercentage calculates correctly', () => {
      // 10% savings
      const percentage = billingService.calculateSavingsPercentage(1000, 10800)
      expect(percentage).toBe(10)
    })

    it('getDaysUntilExpiry calculates correctly', () => {
      const futureDate = new Date()
      futureDate.setDate(futureDate.getDate() + 5)
      const result = billingService.getDaysUntilExpiry(futureDate.toISOString())
      expect(result).toBe(5)
    })

    it('isTrialExpiringSoon returns true when trial expires soon', () => {
      const futureDate = new Date()
      futureDate.setDate(futureDate.getDate() + 2)
      expect(billingService.isTrialExpiringSoon(futureDate.toISOString(), 3)).toBe(true)
    })

    it('isTrialExpiringSoon returns false when trial has time', () => {
      const futureDate = new Date()
      futureDate.setDate(futureDate.getDate() + 10)
      expect(billingService.isTrialExpiringSoon(futureDate.toISOString(), 3)).toBe(false)
    })

    it('isTrialExpiringSoon returns false for null', () => {
      expect(billingService.isTrialExpiringSoon(null)).toBe(false)
    })

    it('isSubscriptionActive returns true for active', () => {
      expect(billingService.isSubscriptionActive({ status: 'active' } as any)).toBe(true)
      expect(billingService.isSubscriptionActive({ status: 'trial' } as any)).toBe(true)
    })

    it('isSubscriptionActive returns false for inactive', () => {
      expect(billingService.isSubscriptionActive({ status: 'cancelled' } as any)).toBe(false)
      expect(billingService.isSubscriptionActive(null)).toBe(false)
    })

    it('getUsagePercentage calculates correctly', () => {
      expect(billingService.getUsagePercentage(50, 100)).toBe(50)
      expect(billingService.getUsagePercentage(150, 100)).toBe(100) // capped at 100
      expect(billingService.getUsagePercentage(50, 0)).toBe(0)
    })

    it('isUsageNearLimit detects near limit', () => {
      expect(billingService.isUsageNearLimit(85, 100)).toBe(true)
      expect(billingService.isUsageNearLimit(50, 100)).toBe(false)
      expect(billingService.isUsageNearLimit(75, 100, 70)).toBe(true)
    })
  })

  describe('Error Handling', () => {
    it('handles 404 errors', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/billing/plans/:planId`, () => {
          return new HttpResponse(null, { status: 404 })
        })
      )

      await expect(billingService.getSubscriptionPlan('invalid-id')).rejects.toThrow()
    })

    it('handles 500 errors', async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/billing/plans`, () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(billingService.getSubscriptionPlans()).rejects.toThrow()
    })
  })
})
