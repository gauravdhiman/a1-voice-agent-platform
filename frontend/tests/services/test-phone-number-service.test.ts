/**
 * Tests for PhoneNumberService
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { phoneNumberService } from '@/services/phone-number-service'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockPhoneNumber, createMockAvailablePhoneNumber, createMockPhoneNumberWithAgent } from '../utils/data-factories'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

describe('PhoneNumberService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('searchAvailable', () => {
    it('searches available phone numbers with default params', async () => {
      const result = await phoneNumberService.searchAvailable({
        country_code: 'US',
        phone_number_type: 'local',
      })
      expect(result).toMatchObject({
        items: expect.any(Array),
        total_count: expect.any(Number),
        page: expect.any(Number),
        page_size: expect.any(Number),
        total_pages: expect.any(Number),
      })
    })

    it('searches with area code filter', async () => {
      const result = await phoneNumberService.searchAvailable({
        country_code: 'US',
        phone_number_type: 'local',
        area_code: '415',
      })
      expect(result).toBeDefined()
    })

    it('searches with contains filter', async () => {
      const result = await phoneNumberService.searchAvailable({
        country_code: 'US',
        contains: '555',
      })
      expect(result).toBeDefined()
    })

    it('searches with pagination', async () => {
      const result = await phoneNumberService.searchAvailable({
        country_code: 'US',
        page: 2,
        page_size: 10,
      })
      expect(result).toMatchObject({
        page: 2,
        page_size: 10,
      })
    })
  })

  describe('purchaseNumber', () => {
    it('purchases a phone number successfully', async () => {
      const result = await phoneNumberService.purchaseNumber('org-1', {
        phone_number: '+14155551234',
        country_code: 'US',
        phone_number_type: 'local',
      })
      expect(result).toMatchObject({
        success: true,
        phone_number: expect.any(Object),
        message: expect.any(String),
        credit_balance_after: expect.any(Number),
      })
    })
  })

  describe('getOrganizationNumbers', () => {
    it('gets organization phone numbers', async () => {
      const result = await phoneNumberService.getOrganizationNumbers('org-1')
      expect(result).toMatchObject({
        items: expect.any(Array),
        total_count: expect.any(Number),
        unused_count: expect.any(Number),
      })
    })
  })

  describe('assignToAgent', () => {
    it('assigns phone number to agent', async () => {
      const result = await phoneNumberService.assignToAgent('phone-1', {
        agent_id: 'agent-1',
      })
      expect(result).toMatchObject({
        success: true,
        phone_number: expect.any(Object),
      })
    })
  })

  describe('cancelNumber', () => {
    it('cancels phone number successfully', async () => {
      const result = await phoneNumberService.cancelNumber('phone-1')
      expect(result).toMatchObject({
        success: true,
        message: expect.any(String),
      })
    })
  })

  describe('formatPhoneNumber', () => {
    it('formats 11-digit number starting with 1', () => {
      const result = phoneNumberService.formatPhoneNumber('14155551234')
      expect(result).toBe('+1 (415) 555-1234')
    })

    it('formats 10-digit number', () => {
      const result = phoneNumberService.formatPhoneNumber('4155551234')
      expect(result).toBe('+1 (415) 555-1234')
    })

    it('returns original for invalid format', () => {
      const result = phoneNumberService.formatPhoneNumber('invalid')
      expect(result).toBe('invalid')
    })
  })

  describe('formatCredits', () => {
    it('formats credits with commas', () => {
      const result = phoneNumberService.formatCredits(1000)
      expect(result).toBe('1,000')
    })

    it('formats large numbers', () => {
      const result = phoneNumberService.formatCredits(1000000)
      expect(result).toBe('1,000,000')
    })
  })

  describe('Error Handling', () => {
    it('handles 404 errors gracefully', async () => {
      server.resetHandlers()
      server.use(
        http.get(`${API_BASE_URL}/api/v1/phone-numbers/available`, () => {
          return new HttpResponse(null, { status: 404 })
        })
      )

      await expect(
        phoneNumberService.searchAvailable({ country_code: 'US' })
      ).rejects.toThrow()
    })

    it('handles 500 errors gracefully', async () => {
      server.resetHandlers()
      server.use(
        http.get(`${API_BASE_URL}/api/v1/phone-numbers`, () => {
          return new HttpResponse(null, { status: 500 })
        })
      )

      await expect(
        phoneNumberService.getOrganizationNumbers('org-1')
      ).rejects.toThrow()
    })
  })
})
