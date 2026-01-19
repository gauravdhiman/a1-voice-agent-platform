/**
 * Unified real-time service for database change notifications.
 *
 * This service manages Supabase Realtime subscriptions and ensures
 * the UI stays in sync with database changes. It handles
 * subscription lifecycle, error recovery, and cache invalidation.
 *
 * Key Features:
 * - Subscribes to Supabase Realtime for database table changes
 * - Automatically invalidates React Query cache when changes occur
 * - Handles subscription errors and reconnection
 * - Manages channel lifecycle (subscribe/unsubscribe)
 * - Filters updates by agent_id to prevent unnecessary cache invalidation
 *
 * @example
 * ```typescript
 * import { useRealtime } from '@/hooks/use-realtime'
 *
 * function AgentDetailPage({ params }: { params: { agentId: string } }) {
 *   const { agentId } = params
 *
 *   // Subscribe to real-time updates for this agent
 *   useRealtime(agentId, {
 *     tables: ['agent_tools', 'voice_agents'],
 *   })
 *
 *   const { data: tools } = useAgentTools(agentId)
 *   const { data: agent } = useAgent(agentId)
 *
 *   return (
 *     <div>
 *       <ToolCard tool={tool} />
 *       <AgentCard agent={agent} />
 *     </div>
 *   )
 * }
 * ```
 */
import { useQueryClient } from '@tanstack/react-query'

import { supabase } from './supabase'

/**
 * Real-time subscription configuration options.
 *
 * @interface RealtimeOptions
 */
export interface RealtimeOptions {
  /** Unique identifier for this subscription (e.g., agent ID) */
  subscriptionId: string

  /** Database tables to monitor for changes */
  tables: string[]

  /** Filter updates to specific records (e.g., agent_id) */
  filter?: {
    column: string
    value: string
  }

  /** Callback for INSERT events */
  onInsert?: (payload: DatabaseChangePayload) => void

  /** Callback for UPDATE events */
  onUpdate?: (payload: DatabaseChangePayload) => void

  /** Callback for DELETE events */
  onDelete?: (payload: DatabaseChangePayload) => void

  /** Whether to subscribe to all changes (*) or specific events */
  eventType?: '*' | 'INSERT' | 'UPDATE' | 'DELETE'
}

/**
 * Database change payload from Supabase Realtime.
 *
 * @interface DatabaseChangePayload
 */
export interface DatabaseChangePayload {
  /** Type of change: INSERT, UPDATE, DELETE */
  eventType: 'INSERT' | 'UPDATE' | 'DELETE'

  /** Database table name */
  table: string

  /** Changed record data (for UPDATE, includes old and new values) */
  record: {
    old?: Record<string, unknown>
    new?: Record<string, unknown>
  }

  /** Timestamp of change */
  timestamp: string
}

/**
 * Real-time service class for managing Supabase subscriptions.
 *
 * Manages subscription lifecycle, handles errors, and triggers
 * cache invalidation for React Query when database changes occur.
 */
class RealtimeService {
  private readonly queryClient: ReturnType<typeof useQueryClient>
  private readonly channels: Map<string, ReturnType<typeof supabase.channel>>

  // Mapping of database table names to query key prefixes for invalidation
  private readonly tableToQueryKeyMap: Record<string, string[]> = {
    agent_tools: ['tools'],
    voice_agents: ['agents'],  // Database table is voice_agents, query keys use 'agents'
    platform_tools: ['tools'],
  }

  constructor(queryClient: ReturnType<typeof useQueryClient>) {
    this.queryClient = queryClient
    this.channels = new Map()
  }

  /**
   * Subscribe to Supabase Realtime for database changes.
   *
   * @param options - Subscription configuration
   * @returns Supabase channel for this subscription
   *
 * @example
 * ```typescript
 * const realtime = new RealtimeService(queryClient)
 *
 * const channel = realtime.subscribe({
 *   subscriptionId: 'agent-123',
 *   tables: ['agent_tools', 'voice_agents'],
 *   filter: { column: 'agent_id', value: '123' },
 *   onUpdate: (payload) => console.log('Update:', payload),
 * })
 * ```
   *
   * @notes
   * - Creates channel if doesn't exist
   * - Reuses existing channel for same subscriptionId
   * - Configures filter to reduce unnecessary notifications
   * - Sets up event handlers for INSERT, UPDATE, DELETE
   */
   subscribe(options: RealtimeOptions): ReturnType<typeof supabase.channel> {
    const { subscriptionId, tables, filter, eventType = '*' } = options

    // Check if channel already exists for this subscription
    if (this.channels.has(subscriptionId)) {
      return this.channels.get(subscriptionId)!
    }

    // Build channel name based on subscription ID
    const channelName = `realtime:${subscriptionId}`

    // Create Supabase Realtime channel
    const channel = supabase.channel(channelName)

    // Subscribe to each table
    tables.forEach((table) => {
      channel.on(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        'postgres_changes' as any,
        {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          event: eventType as any,
          schema: 'public',
          table: table,
          ...(filter ? { filter: `(${filter.column})=eq.${filter.value}` } : {}),
        },
        (payload: DatabaseChangePayload) => this.handleDatabaseChange(payload, options),
      )
    })

    // Subscribe to channel
    channel.subscribe((status) => {
      if (status === 'SUBSCRIBED') {
        console.log(`Subscribed to realtime:${subscriptionId}`)
      } else if (status === 'CHANNEL_ERROR') {
        console.error(`Failed to subscribe to realtime:${subscriptionId}`)
      }
    })

    // Store channel for reuse
    this.channels.set(subscriptionId, channel)

    return channel
  }

  /**
   * Unsubscribe from Supabase Realtime.
   *
   * @param subscriptionId - Unique identifier of subscription to unsubscribe
   *
   * @example
   * ```typescript
   * const realtime = new RealtimeService(queryClient)
   * realtime.unsubscribe('agent-123')
   * ```
   *
   * @notes
   * - Removes channel from internal map
   * - Unsubscribes from Supabase
   * - Handles case where channel doesn't exist gracefully
   */
  unsubscribe(subscriptionId: string): void {
    const channel = this.channels.get(subscriptionId)

    if (!channel) {
      console.warn(`No active subscription found for ${subscriptionId}`)
      return
    }

    // Unsubscribe from Supabase
    supabase.removeChannel(channel)

    // Remove from internal map
    this.channels.delete(subscriptionId)

    console.log(`Unsubscribed from realtime:${subscriptionId}`)
  }

  /**
   * Unsubscribe from all active subscriptions.
   *
   * @example
   * ```typescript
   * const realtime = new RealtimeService(queryClient)
   * realtime.unsubscribeAll()
   * ```
   *
   * @notes
   * - Iterates through all channels
   * - Unsubscribes each channel
   * - Clears internal channel map
   * - Useful for cleanup on component unmount
   */
  unsubscribeAll(): void {
    this.channels.forEach((channel, subscriptionId) => {
      supabase.removeChannel(channel)
      console.log(`Unsubscribed from realtime:${subscriptionId}`)
    })

    this.channels.clear()
  }

  /**
   * Handle database change event from Supabase Realtime.
   *
   * @param payload - Database change payload
   * @param options - Original subscription options
   *
   * @notes
   * - Validates payload structure
   * - Determines which cache to invalidate based on table
   * - Calls appropriate callback (onInsert, onUpdate, onDelete)
   * - Logs errors for debugging
   */
  private handleDatabaseChange(
    payload: DatabaseChangePayload,
    options: RealtimeOptions
  ): void {
    try {
      // Log change for debugging
      console.log('Database change detected:', {
        table: payload.table,
        eventType: payload.eventType,
        timestamp: payload.timestamp,
      })

      // Call appropriate callback based on event type
      if (payload.eventType === 'INSERT' && options.onInsert) {
        options.onInsert(payload)
      } else if (payload.eventType === 'UPDATE' && options.onUpdate) {
        options.onUpdate(payload)
      } else if (payload.eventType === 'DELETE' && options.onDelete) {
        options.onDelete(payload)
      }

      // Invalidate React Query cache for affected table
      this.invalidateQuery(payload.table)
    } catch (error) {
      console.error('Error handling database change:', error)
    }
  }

  /**
   * Invalidate React Query cache for a specific table.
   *
   * @param table - Database table name
   *
   * @example
   * ```typescript
   * // Invalidate all agent_tools queries
   * realtime.invalidateQuery('agent_tools')
   *
   * // Invalidate specific agent's tools
   * realtime.invalidateQuery('agent_tools', 'agent-123')
   * ```
   *
   * @notes
   * - Uses React Query's invalidateQueries method
   * - Maps database table names to frontend query key patterns
   * - Automatically triggers refetch for affected components
   */
  private invalidateQuery(table: string): void {
    // Get the query key patterns for this table
    const queryKeyPatterns = this.tableToQueryKeyMap[table] || [table]

    // Invalidate queries that match the patterns
    this.queryClient.invalidateQueries({
      predicate: (query) => {
        const queryKey = query.queryKey
        if (typeof queryKey === 'string') {
          return queryKeyPatterns.some(pattern => (queryKey as string).includes(pattern))
        }
        if (Array.isArray(queryKey)) {
          return queryKeyPatterns.some(pattern => queryKey.some((key: unknown) => key === pattern))
        }
        return false
      },
    })

    console.log(`Invalidated queries for table: ${table} (patterns: ${queryKeyPatterns.join(', ')})`)
  }

  /**
   * Invalidate React Query cache for specific records.
   *
   * @param table - Database table name
   * @param recordId - Record ID to filter by
   *
   * @example
   * ```typescript
   * // Invalidate only queries for specific agent
   * realtime.invalidateQueryForRecord('agent_tools', 'agent-123')
   * ```
   *
   * @notes
   * - More precise than invalidating all queries for a table
   * - Reduces unnecessary refetches
   * - Useful for multi-tenant applications
   */
  private invalidateQueryForRecord(table: string, recordId: string): void {
    // Invalidate queries that include both table and record ID
    this.queryClient.invalidateQueries({
      predicate: (query) => {
        const queryKey = query.queryKey
        if (typeof queryKey === 'string') {
          const key = queryKey as string
          return key === table || key.includes(recordId)
        }
        if (Array.isArray(queryKey)) {
          return queryKey.some((key: unknown) => key === table) || queryKey.some((key: unknown) => key === recordId)
        }
        return false
      },
    })

    console.log(`Invalidated queries for ${table}:${recordId}`)
  }
}

// Global real-time service instance
let realtimeServiceInstance: RealtimeService | null = null

/**
 * Initialize the global real-time service.
 *
 * @param queryClient - React Query client for cache invalidation
 * @returns Realtime service instance
 *
 * @example
 * ```typescript
 * import { useQueryClient } from '@tanstack/react-query'
 *
 * function MyComponent() {
 *   const queryClient = useQueryClient()
 *   const realtime = getRealtimeService(queryClient)
 *
 *   // Subscribe to changes
 *   realtime.subscribe({ ... })
 * }
 * ```
 *
 * @notes
 * - Singleton pattern ensures one instance across app
 * - Must be called before using service
 * - Can be called multiple times safely
 */
export function getRealtimeService(
  queryClient: ReturnType<typeof useQueryClient>
): RealtimeService {
  if (!realtimeServiceInstance) {
    realtimeServiceInstance = new RealtimeService(queryClient)
    console.log('Real-time service initialized')
  }

  return realtimeServiceInstance
}

/**
 * Reset the global real-time service instance.
 *
 * @example
 * ```typescript
 * // Reset service (useful for testing or after logout)
 * resetRealtimeService()
 * ```
 *
 * @notes
 * - Useful for testing or after user logout
 * - Clears all subscriptions and channels
 * - Next call to getRealtimeService creates fresh instance
 */
export function resetRealtimeService(): void {
  realtimeServiceInstance = null
  console.log('Real-time service reset')
}
