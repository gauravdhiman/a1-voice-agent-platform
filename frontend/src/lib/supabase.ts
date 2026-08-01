/**
 * Supabase client configuration for frontend authentication and database access.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// For development without Supabase configuration, we'll show warnings
if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    "Supabase environment variables not set. Authentication features will not work.",
  );
}

/**
 * Shared Supabase browser client.
 *
 * Realtime uses a Web Worker for heartbeats so background tabs are less likely
 * to silently drop the WebSocket (browser timer throttling). heartbeatCallback
 * explicitly reconnects if the heartbeat still reports disconnected.
 */
// Let creates assign into a const binding via a mutable holder for the callback.
const supabaseHolder: {
  client: ReturnType<typeof createClient> | null;
} = { client: null };

supabaseHolder.client = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder-key",
  {
    auth: {
      autoRefreshToken: true, // Auto-refresh tokens before expiry (network call)
      persistSession: true, // Store session in localStorage for fast restoration
      detectSessionInUrl: true, // Handle OAuth redirect callbacks
    },
    realtime: {
      // Keep heartbeats off the main thread so idle/background tabs stay alive longer
      worker: true,
      heartbeatCallback: (status) => {
        if (status === "disconnected" && supabaseHolder.client) {
          supabaseHolder.client.realtime.connect();
        }
      },
    },
  },
);

export const supabase = supabaseHolder.client;

/**
 * Resend verification email for a user
 * @param email The email address to send verification to
 * @returns Promise with error if any
 */
export async function resendVerificationEmail(email: string) {
  const { error } = await supabase.auth.resend({
    type: "signup",
    email: email,
  });

  if (error) {
    console.error("Error resending verification email:", error);
    throw error;
  }

  return { error: null };
}

// Import auth types from centralized location
import type {
  AuthUser,
  AuthSession,
  SignUpData,
  SignInData,
} from "@/types/auth";

// Re-export for backward compatibility
export type { AuthUser, AuthSession, SignUpData, SignInData };
