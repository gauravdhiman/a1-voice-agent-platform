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
 * - Reconnects after CHANNEL_ERROR / TIMED_OUT (idle JWT / WebSocket drops)
 * - Refreshes the Realtime auth token before (re)subscribe
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

/** Base delay (ms) before the first realtime reconnect attempt. */
const REALTIME_RECONNECT_BASE_MS = 1000

/** Cap for exponential backoff between reconnect attempts. */
const REALTIME_RECONNECT_MAX_MS = 30_000

/**
 * Whether a Supabase channel status should trigger a resubscribe.
 *
 * CHANNEL_ERROR and TIMED_OUT are the statuses seen after idle JWT expiry
 * or silent WebSocket disconnect. CLOSED is intentional (unsubscribe).
 *
 * @param status - Status string from channel.subscribe callback
 * @returns True when the service should tear down and resubscribe
 */
export function shouldReconnectRealtimeChannel(status: string): boolean {
  return status === 'CHANNEL_ERROR' || status === 'TIMED_OUT'
}

/**
 * Exponential backoff delay for realtime reconnect attempts.
 *
 * @param attempt - 1-based attempt number
 * @param baseMs - Delay for attempt 1
 * @param maxMs - Maximum delay cap
 * @returns Delay in milliseconds
 */
export function realtimeReconnectDelayMs(
  attempt: number,
  baseMs: number = REALTIME_RECONNECT_BASE_MS,
  maxMs: number = REALTIME_RECONNECT_MAX_MS
): number {
  const safeAttempt = Math.max(1, attempt)
  return Math.min(baseMs * 2 ** (safeAttempt - 1), maxMs)
}

/**
 * Push the current Supabase session JWT into the Realtime client.
 *
 * Needed so postgres_changes (RLS) and reconnects use a non-expired token
 * after TOKEN_REFRESHED or after an idle CHANNEL_ERROR.
 *
 * @returns Access token that was applied, or null if no session
 */
export async function syncRealtimeAuth(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    return null
  }

  await supabase.realtime.setAuth(session.access_token)
  return session.access_token
}

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
  private readonly optionsById: Map<string, RealtimeOptions>
  private readonly reconnectAttempts: Map<string, number>
  private readonly reconnectTimers: Map<string, ReturnType<typeof setTimeout>>
  private readonly intentionalClose: Set<string>
  /** Prevents CLOSED-from-removeChannel from double-scheduling reconnect */
  private readonly reconnecting: Set<string>

  // Mapping of database table names to query key prefixes for invalidation
  private readonly tableToQueryKeyMap: Record<string, string[]> = {
    agent_tools: ['tools'],
    voice_agents: ['agents'], // Database table is voice_agents, query keys use 'agents'
    platform_tools: ['tools'],
  }

  constructor(queryClient: ReturnType<typeof useQueryClient>) {
    this.queryClient = queryClient
    this.channels = new Map()
    this.optionsById = new Map()
    this.reconnectAttempts = new Map()
    this.reconnectTimers = new Map()
    this.intentionalClose = new Set()
    this.reconnecting = new Set()
  }

  /**
   * Subscribe to Supabase Realtime for database changes.
   *
   * Starts the channel asynchronously after syncing the auth token so
   * RLS-backed postgres_changes bindings use a valid JWT. Returns the
   * existing channel if one is already tracked for subscriptionId.
   *
   * @param options - Subscription configuration
   * @returns Existing channel if present; otherwise null while connect starts
   */
  subscribe(options: RealtimeOptions): ReturnType<typeof supabase.channel> | null {
    const { subscriptionId } = options

    this.optionsById.set(subscriptionId, options)
    this.intentionalClose.delete(subscriptionId)

    // Reuse live channel for the same subscription id
    if (this.channels.has(subscriptionId)) {
      return this.channels.get(subscriptionId)!
    }

    void this.startChannel(options)
    return this.channels.get(subscriptionId) ?? null
  }

  /**
   * Create the Supabase channel, attach postgres_changes listeners, and subscribe.
   *
   * @param options - Subscription configuration (must match optionsById)
   */
  private async startChannel(options: RealtimeOptions): Promise<void> {
    const { subscriptionId, tables, filter, eventType = '*' } = options

    // Bail if unsubscribed while awaiting auth, or a channel was created meanwhile
    if (this.intentionalClose.has(subscriptionId) || this.channels.has(subscriptionId)) {
      return
    }

    try {
      await syncRealtimeAuth()
    } catch (error) {
      console.warn(
        `Unable to sync realtime auth before subscribe:${subscriptionId}`,
        error
      )
    }

    if (this.intentionalClose.has(subscriptionId) || this.channels.has(subscriptionId)) {
      return
    }

    const channelName = `realtime:${subscriptionId}`
    const channel = supabase.channel(channelName)

    tables.forEach((table) => {
      channel.on(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        'postgres_changes' as any,
        {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          event: eventType as any,
          schema: 'public',
          table: table,
          ...(filter ? { filter: `${filter.column}=eq.${filter.value}` } : {}),
        },
        (payload: DatabaseChangePayload) => this.handleDatabaseChange(payload, options)
      )
    })

    this.channels.set(subscriptionId, channel)

    channel.subscribe((status, err) => {
      if (status === 'SUBSCRIBED') {
        this.reconnectAttempts.set(subscriptionId, 0)
        console.log(`Subscribed to realtime:${subscriptionId}`)
        return
      }

      if (shouldReconnectRealtimeChannel(status)) {
        // Recoverable: warn only — console.error triggers Next.js / React overlays
        console.warn(
          `Failed to subscribe to realtime:${subscriptionId}`,
          status,
          err ?? undefined
        )
        this.scheduleReconnect(subscriptionId)
        return
      }

      if (status === 'CLOSED' && !this.intentionalClose.has(subscriptionId)) {
        console.warn(`Realtime channel closed unexpectedly:${subscriptionId}`)
        this.scheduleReconnect(subscriptionId)
      }
    })
  }

  /**
   * Tear down the current channel (if any) and schedule a resubscribe.
   *
   * @param subscriptionId - Subscription to reconnect
   */
  private scheduleReconnect(subscriptionId: string): void {
    if (this.intentionalClose.has(subscriptionId)) {
      return
    }

    if (
      this.reconnectTimers.has(subscriptionId) ||
      this.reconnecting.has(subscriptionId)
    ) {
      return
    }

    const options = this.optionsById.get(subscriptionId)
    if (!options) {
      return
    }

    this.reconnecting.add(subscriptionId)

    const existing = this.channels.get(subscriptionId)
    if (existing) {
      supabase.removeChannel(existing)
      this.channels.delete(subscriptionId)
    }

    const attempt = (this.reconnectAttempts.get(subscriptionId) ?? 0) + 1
    this.reconnectAttempts.set(subscriptionId, attempt)
    const delayMs = realtimeReconnectDelayMs(attempt)

    const timer = setTimeout(() => {
      this.reconnectTimers.delete(subscriptionId)
      this.reconnecting.delete(subscriptionId)
      if (this.intentionalClose.has(subscriptionId)) {
        return
      }
      void this.startChannel(options)
    }, delayMs)

    this.reconnectTimers.set(subscriptionId, timer)
  }

  /**
   * Unsubscribe from Supabase Realtime.
   *
   * @param subscriptionId - Unique identifier of subscription to unsubscribe
   */
  unsubscribe(subscriptionId: string): void {
    this.intentionalClose.add(subscriptionId)
    this.optionsById.delete(subscriptionId)
    this.reconnectAttempts.delete(subscriptionId)
    this.reconnecting.delete(subscriptionId)

    const timer = this.reconnectTimers.get(subscriptionId)
    if (timer) {
      clearTimeout(timer)
      this.reconnectTimers.delete(subscriptionId)
    }

    const channel = this.channels.get(subscriptionId)
    if (!channel) {
      return
    }

    supabase.removeChannel(channel)
    this.channels.delete(subscriptionId)
    console.log(`Unsubscribed from realtime:${subscriptionId}`)
  }

  /**
   * Unsubscribe from all active subscriptions.
   */
  unsubscribeAll(): void {
    const ids = Array.from(this.optionsById.keys())
    ids.forEach((subscriptionId) => this.unsubscribe(subscriptionId))

    // Also clear any orphan channels
    this.channels.forEach((channel, subscriptionId) => {
      this.intentionalClose.add(subscriptionId)
      supabase.removeChannel(channel)
    })
    this.channels.clear()
    this.reconnectTimers.forEach((timer) => clearTimeout(timer))
    this.reconnectTimers.clear()
  }

  /**
   * Handle database change event from Supabase Realtime.
   *
   * @param payload - Database change payload
   * @param options - Original subscription options
   */
  private handleDatabaseChange(
    payload: DatabaseChangePayload,
    options: RealtimeOptions
  ): void {
    try {
      console.log('Database change detected:', {
        table: payload.table,
        eventType: payload.eventType,
        timestamp: payload.timestamp,
      })

      if (payload.eventType === 'INSERT' && options.onInsert) {
        options.onInsert(payload)
      } else if (payload.eventType === 'UPDATE' && options.onUpdate) {
        options.onUpdate(payload)
      } else if (payload.eventType === 'DELETE' && options.onDelete) {
        options.onDelete(payload)
      }

      this.invalidateQuery(payload.table)
    } catch (error) {
      console.error('Error handling database change:', error)
    }
  }

  /**
   * Invalidate React Query cache for a specific table.
   *
   * @param table - Database table name
   */
  private invalidateQuery(table: string): void {
    const queryKeyPatterns = this.tableToQueryKeyMap[table] || [table]

    this.queryClient.invalidateQueries({
      predicate: (query) => {
        const queryKey = query.queryKey
        if (typeof queryKey === 'string') {
          return queryKeyPatterns.some((pattern) =>
            (queryKey as string).includes(pattern)
          )
        }
        if (Array.isArray(queryKey)) {
          return queryKeyPatterns.some((pattern) =>
            queryKey.some((key: unknown) => key === pattern)
          )
        }
        return false
      },
    })

    console.log(
      `Invalidated queries for table: ${table} (patterns: ${queryKeyPatterns.join(', ')})`
    )
  }
}

// Global real-time service instance
let realtimeServiceInstance: RealtimeService | null = null

/**
 * Initialize the global real-time service.
 *
 * @param queryClient - React Query client for cache invalidation
 * @returns Realtime service instance
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
 * Clears reconnect timers and channels when an instance exists.
 */
export function resetRealtimeService(): void {
  if (realtimeServiceInstance) {
    realtimeServiceInstance.unsubscribeAll()
  }
  realtimeServiceInstance = null
  console.log('Real-time service reset')
}
