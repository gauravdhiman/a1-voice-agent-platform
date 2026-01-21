/**
 * Tests for use-live-time hook and formatTimeUntilExpiry utility
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useLiveTime, formatTimeUntilExpiry } from '@/hooks/use-live-time'

describe('useLiveTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns current time', () => {
    const now = Date.now()
    vi.setSystemTime(now)
    
    const { result } = renderHook(() => useLiveTime())
    
    expect(result.current).toBe(now)
  })

  it('updates time every second', () => {
    const startTime = new Date('2024-01-15T12:00:00Z').getTime()
    vi.setSystemTime(startTime)
    
    const { result } = renderHook(() => useLiveTime())
    
    expect(result.current).toBe(startTime)
    
    // Advance by 1 second
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    
    expect(result.current).toBe(startTime + 1000)
  })

  it('clears interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
    
    const { unmount } = renderHook(() => useLiveTime())
    
    unmount()
    
    expect(clearIntervalSpy).toHaveBeenCalled()
  })
})

describe('formatTimeUntilExpiry', () => {
  it('returns null for null expiry', () => {
    expect(formatTimeUntilExpiry(null, Date.now())).toBe(null)
  })

  it('returns "Expired" for past time', () => {
    const pastTime = Date.now() / 1000 - 100 // 100 seconds ago
    const currentTime = Date.now()
    
    expect(formatTimeUntilExpiry(pastTime, currentTime)).toBe('Expired')
  })

  it('returns "< 1 minute" for less than 60 seconds', () => {
    const currentTime = Date.now()
    const expiresAt = currentTime / 1000 + 30 // 30 seconds from now
    
    expect(formatTimeUntilExpiry(expiresAt, currentTime)).toBe('< 1 minute')
  })

  it('returns minutes for 1-59 minutes', () => {
    const currentTime = Date.now()
    const expiresAt = currentTime / 1000 + 300 // 5 minutes from now
    
    expect(formatTimeUntilExpiry(expiresAt, currentTime)).toBe('5 minutes')
  })

  it('returns hours for 1-23 hours', () => {
    const currentTime = Date.now()
    const expiresAt = currentTime / 1000 + 7200 // 2 hours from now
    
    expect(formatTimeUntilExpiry(expiresAt, currentTime)).toBe('2 hours')
  })

  it('returns days for 24+ hours', () => {
    const currentTime = Date.now()
    const expiresAt = currentTime / 1000 + 172800 // 2 days from now
    
    expect(formatTimeUntilExpiry(expiresAt, currentTime)).toBe('2 days')
  })
})
