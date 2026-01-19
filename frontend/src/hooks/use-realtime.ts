/**
 * Custom hook for subscribing to real-time database updates.
 *
 * This hook manages Supabase Realtime subscriptions to automatically refresh
 * UI components when database changes occur. It handles subscription
 * cleanup on component unmount to prevent memory leaks.
 *
 * @param agentId - The UUID of the agent to subscribe to updates for
 * @param options - Optional configuration for subscription behavior
 * @returns Object containing realtime methods and subscription status
 *
 * @example
 * ```tsx
 * function AgentDetailPage({ params }: { params: { agentId: string } }) {
 *   const { agentId } = params
 *
 *   // Subscribe to real-time updates for this agent
 *   const realtime = useRealtime(agentId, {
 *     tables: ['agent_tools', 'voice_agents'],
 *     onToolInsert: (payload) => console.log('Tool added:', payload),
 *     onToolUpdate: (payload) => console.log('Tool updated:', payload),
 *   onAgentUpdate: (payload) => console.log('Agent updated:', payload),
 *   })
 *
 *   const { data: agent } = useAgent(agentId)
 *   const { data: tools } = useAgentTools(agentId)
 *
 *   // ... component renders with automatic updates
 * }
 * ```
 */
import { useEffect, useRef, useState } from 'react'

import { getRealtimeService } from '@/lib/realtime'
import { useQueryClient } from '@tanstack/react-query'
import type { DatabaseChangePayload } from '@/lib/realtime'

interface UseRealtimeOptions {
  /** Tables to monitor for changes (default: ['agent_tools', 'voice_agents']) */
  tables?: string[]

  /** Filter updates to specific records (e.g., agent_id) */
  filter?: {
    column: string
    value: string
  }

  /** Callback when a tool is INSERTed */
  onToolInsert?: (payload: DatabaseChangePayload) => void

  /** Callback when a tool is UPDATEd */
  onToolUpdate?: (payload: DatabaseChangePayload) => void

  /** Callback when a tool is DELETEd */
  onToolDelete?: (payload: DatabaseChangePayload) => void

  /** Callback when agent data is INSERTed */
  onAgentInsert?: (payload: DatabaseChangePayload) => void

  /** Callback when agent data is UPDATEd */
  onAgentUpdate?: (payload: DatabaseChangePayload) => void

  /** Callback when agent data is DELETEd */
  onAgentDelete?: (payload: DatabaseChangePayload) => void

  /** Callback for any database change */
  onChange?: (payload: DatabaseChangePayload) => void
}

export function useRealtime(subscriptionId: string, options: UseRealtimeOptions = {}) {
  const queryClient = useQueryClient()
  const realtimeServiceRef = useRef(getRealtimeService(queryClient))
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Extract options with defaults
  const {
    tables = ['agent_tools', 'voice_agents'],  // Database table is voice_agents, not agents
    filter,
    onChange,
  } = options

  useEffect(() => {
    const realtimeService = realtimeServiceRef.current

    // Subscribe to real-time updates
    realtimeService.subscribe({
      subscriptionId,
      tables,
      filter,
      onInsert: (payload) => {
        if (payload.table === 'agent_tools') {
          console.log('Tool added:', payload)
        } else if (payload.table === 'voice_agents') {
          console.log('Agent added:', payload)
        }
        onChange?.(payload)
      },
      onUpdate: (payload) => {
        if (payload.table === 'agent_tools') {
          console.log('Tool updated in database:', payload.record)
        } else if (payload.table === 'voice_agents') {
          console.log('Agent updated in database:', payload.record)
        }
        onChange?.(payload)
      },
      onDelete: (payload) => {
        if (payload.table === 'agent_tools') {
          console.log('Tool removed:', payload.record)
        } else if (payload.table === 'voice_agents') {
          console.log('Agent removed:', payload.record)
        }
        onChange?.(payload)
      },
    })

    // Update subscription status
    setIsSubscribed(true)
    setError(null)

    // Cleanup on unmount
    return () => {
      console.log(`Cleaning up realtime subscription: ${subscriptionId}`)
      realtimeService.unsubscribe(subscriptionId)
      setIsSubscribed(false)
    }
  }, [subscriptionId, tables, filter, onChange])

  return {
    /** Whether subscription is active */
    isSubscribed,

    /** Subscription error, if any */
    error,

    /** Manually trigger a re-fetch (useful for testing) */
    refetch: () => {
      tables.forEach((table) => {
        queryClient.invalidateQueries({
          predicate: (query) => {
            const queryKey = query.queryKey
            if (typeof queryKey === 'string') {
              return (queryKey as string).includes(table)
            }
            if (Array.isArray(queryKey) && queryKey.some((key: unknown) => key === table)) {
              return true
            }
            return false
          },
        })
      })
    },
  }
}
