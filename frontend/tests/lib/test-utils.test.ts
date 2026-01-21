/**
 * Tests for utility functions
 */

import { describe, it, expect } from 'vitest'
import { cn, formatToolName } from '@/lib/utils'

describe('cn utility', () => {
  it('merges class names correctly', () => {
    expect(cn('px-4', 'py-2')).toBe('px-4 py-2')
  })

  it('dedupes duplicate Tailwind classes', () => {
    expect(cn('p-4', 'p-4', 'bg-red')).toBe('p-4 bg-red')
  })

  it('handles conditional classes with undefined', () => {
    expect(cn('px-4', undefined, 'py-2')).toBe('px-4 py-2')
  })

  it('handles conditional classes with false', () => {
    expect(cn('px-4', false, 'py-2')).toBe('px-4 py-2')
  })

  it('handles conditional classes with true', () => {
    expect(cn('px-4', true && 'bg-red', 'py-2')).toBe('px-4 bg-red py-2')
  })

  it('handles empty input', () => {
    expect(cn()).toBe('')
  })
})

describe('formatToolName utility', () => {
  it('formats snake_case to Title Case', () => {
    expect(formatToolName('google_calendar')).toBe('Google Calendar')
  })

  it('handles single word', () => {
    expect(formatToolName('calendar')).toBe('Calendar')
  })

  it('handles multiple underscores', () => {
    expect(formatToolName('google_mail_api_tool')).toBe('Google Mail Api Tool')
  })

  it('handles uppercase letters', () => {
    expect(formatToolName('GMAIL_API')).toBe('Gmail Api')
  })

  it('handles empty string', () => {
    expect(formatToolName('')).toBe('')
  })

  it('handles single letter words', () => {
    expect(formatToolName('a_b_c')).toBe('A B C')
  })
})
