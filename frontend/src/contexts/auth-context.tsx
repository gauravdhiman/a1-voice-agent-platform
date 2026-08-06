"use client";

/**
 * Authentication context using React Context and React Query.
 * Provides authentication state and methods throughout the application.
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import { User, Session } from "@supabase/supabase-js";
import type { Provider } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import type {
  AuthUser,
  SignUpData,
  SignInData,
  GoogleIdTokenSignInData,
  LinkedInSessionSignInData,
  AuthContextType,
  AuthProviderProps,
} from "@/types/auth";
import type { UserRoleAssignment } from "@/types/rbac";
import { useUserProfile } from "@/hooks/use-user-profile";
import { extractFirstLastName } from "@/lib/user-utils";

import { getMeter } from "@/lib/opentelemetry";
import {
  withTelemetrySignUp,
  withTelemetrySignIn,
  withTelemetrySignInWithOAuth,
  withTelemetrySignInWithGoogleIdToken,
  withTelemetrySignInWithLinkedInSession,
  withTelemetrySignOut,
  logInfo,
  recordMetric,
} from "@/lib/opentelemetry-helpers";

// Get meter for authentication operations
const meter = getMeter("auth-context");

// Create metrics only if meter is available
const authAttemptsCounter = meter?.createCounter("auth_attempts", {
  description: "Number of authentication attempts",
});

const authSuccessCounter = meter?.createCounter("auth_success", {
  description: "Number of successful authentications",
});

const authFailureCounter = meter?.createCounter("auth_failures", {
  description: "Number of failed authentications",
});

/**
 * Processes an organization invitation after a user authenticates.
 *
 * Invitation processing is intentionally best effort. Authentication has
 * already succeeded at this point, so a temporary invitation API failure
 * should not prevent the user from reaching the application.
 *
 * @param invitationToken Invitation token supplied by the sign-up URL.
 * @param userId Supabase user ID that should receive the invitation.
 * @returns Promise that resolves after processing or logging the failure.
 */
async function processInvitationForUser(
  invitationToken: string | undefined,
  userId: string,
): Promise<void> {
  if (!invitationToken) return;

  try {
    const { authService } = await import("@/services/auth-service");
    const result = await authService.processInvitation(invitationToken, userId);

    if (!result.success) {
      console.warn("Failed to process invitation:", result.error);
    } else {
      console.log("Invitation processed successfully:", result.data);
    }
  } catch (error) {
    console.warn("Error processing invitation:", error);
  }
}

/**
 * Normalizes Google profile names into the metadata fields used by the app.
 *
 * Google commonly returns `name` or `full_name`, while the platform uses
 * `first_name` and `last_name` for user profiles and organization setup.
 *
 * @param user Authenticated Supabase user returned by Google ID-token exchange.
 * @param refreshUserProfile Callback that refreshes the cached backend profile.
 * @returns Promise that resolves after metadata synchronization.
 */
async function syncOAuthUserMetadata(
  user: User,
  refreshUserProfile: () => Promise<void>,
): Promise<void> {
  try {
    const userMetadata = (user.user_metadata || {}) as Record<
      string,
      string | undefined
    >;
    const { firstName, lastName } = extractFirstLastName(userMetadata);
    const currentFirstName = userMetadata.first_name || "";
    const currentLastName = userMetadata.last_name || "";

    if (firstName === currentFirstName && lastName === currentLastName) {
      return;
    }

    const { error } = await supabase.auth.updateUser({
      data: {
        ...userMetadata,
        first_name: firstName,
        last_name: lastName,
      },
    });

    if (error) {
      console.error("Error updating user metadata:", error);
      return;
    }

    await refreshUserProfile();
  } catch (error) {
    console.error("Error processing OAuth user metadata:", error);
  }
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: AuthProviderProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Transform Supabase user to our AuthUser type
  const transformSupabaseUser = (
    user: User,
    roles?: UserRoleAssignment[],
  ): AuthUser => {
    const metadata = user.user_metadata || {};

    // Extract first_name and last_name using utility function
    const { firstName, lastName } = extractFirstLastName(metadata);

    const authUser: AuthUser = {
      id: user.id,
      email: user.email || "",
      firstName,
      lastName,
      emailConfirmedAt: user.email_confirmed_at || undefined,
      createdAt: user.created_at || "",
      updatedAt: user.updated_at || "",
      roles,
      hasRole: (roleName: string, organizationId?: string) => {
        if (!roles) return false;
        for (const userRole of roles) {
          if (userRole.role.name === roleName) {
            // If organization_id is specified, check if role is for that organization
            if (organizationId) {
              if (userRole.organization_id === organizationId) {
                return true;
              }
            } else {
              // For platform-wide roles (organization_id is null)
              if (
                roleName === "platform_admin" &&
                userRole.organization_id === null
              ) {
                return true;
              }
            }
          }
        }
        return false;
      },
      hasPermission: (permissionName: string, organizationId?: string) => {
        if (!roles) return false;
        for (const userRole of roles) {
          for (const permission of userRole.role.permissions) {
            if (permission.name === permissionName) {
              // If organization_id is specified, check if role is for that organization
              if (organizationId) {
                if (userRole.organization_id === organizationId) {
                  return true;
                }
              } else {
                // For platform-wide permissions
                if (
                  userRole.role.name === "platform_admin" &&
                  userRole.organization_id === null
                ) {
                  return true;
                }
              }
            }
          }
        }
        return false;
      },
    };

    return authUser;
  };

  // Use React Query for user profile data
  const {
    data: userRoles,
    isLoading: profileLoading,
    refetch: refetchProfile,
  } = useUserProfile(session?.user?.id);

  // Derive user state from session and userRoles
  const user =
    session?.user && userRoles !== undefined
      ? transformSupabaseUser(session.user, userRoles)
      : null;

  // Derive loading state - don't show as loaded until auth is initialized
  const loading = !isInitialized || (session?.user ? profileLoading : false);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Get initial session from localStorage (no network call)
        // This only reads from browser storage and validates JWT locally
        const {
          data: { session },
          error,
        } = await supabase.auth.getSession();

        if (!error && session) {
          setSession(session);
          logInfo("Auth session restored from storage", {
            hasSession: true,
            userId: session.user?.id,
            source: "localStorage",
            expiresAt: session.expires_at,
          });
        } else {
          // This is normal for:
          // - First-time visitors
          // - Users who logged out
          // - Expired sessions that were cleared
          logInfo("No valid session in storage - user needs to log in", {
            hasSession: false,
            source: "localStorage",
            reason: error?.message || "No session found",
          });
        }
      } catch (error) {
        // This would only happen if localStorage is unavailable
        console.warn("Failed to access session storage:", error);
        logInfo("Auth session initialization failed", {
          hasSession: false,
          error: error instanceof Error ? error.message : "Storage unavailable",
        });
      } finally {
        // Always mark as initialized so app can show login screen if needed
        setIsInitialized(true);
      }
    };

    // Initialize auth state
    initializeAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setIsInitialized(true);

      // Keep Realtime's JWT in sync after refresh/sign-in. Without this, idle
      // postgres_changes channels often hit CHANNEL_ERROR with an expired token.
      if (
        (_event === "TOKEN_REFRESHED" || _event === "SIGNED_IN") &&
        session?.access_token
      ) {
        void supabase.realtime.setAuth(session.access_token);
      }

      // Log auth state changes with OpenTelemetry logger
      logInfo("Auth state changed", {
        event: _event,
        hasSession: !!session,
        userId: session?.user?.id,
        source: "auth_change",
      });
    });

    return () => subscription.unsubscribe();
  }, []);

  // Sign up with email and password
  const signUp = withTelemetrySignUp(
    async (data: SignUpData) => {
      recordMetric(authAttemptsCounter, 1, {
        operation: "signup",
        source: "frontend",
      });

      // Get the invitation token from URL params if not provided in data
      let invitationToken = data.invitationToken;
      if (!invitationToken) {
        const urlParams = new URLSearchParams(window.location.search);
        invitationToken = urlParams.get("token") || undefined;
      }

      // Use Supabase Auth directly for signup
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: data.email,
        password: data.password,
        options: {
          data: {
            first_name: data.firstName,
            last_name: data.lastName,
          },
        },
      });

      if (authError) {
        recordMetric(authFailureCounter, 1, {
          operation: "signup",
          error: authError.status?.toString() || "unknown",
        });
        throw authError;
      }

      if (!authData.user) {
        recordMetric(authFailureCounter, 1, {
          operation: "signup",
          error: "no_user_returned",
        });
        throw new Error("Failed to create user account");
      }

      recordMetric(authSuccessCounter, 1, { operation: "signup" });

      // If there's an invitation token, process it via backend API
      if (invitationToken && authData.user) {
        try {
          // Import auth service dynamically to avoid circular dependencies
          const { authService } = await import("@/services/auth-service");
          const result = await authService.processInvitation(
            invitationToken,
            authData.user.id,
          );

          if (!result.success) {
            console.warn("Failed to process invitation:", result.error);
            // Don't throw error here - user can still sign up, invitation will be processed later
          } else {
            console.log("Invitation processed successfully:", result.data);
          }
        } catch (inviteError) {
          console.warn("Error processing invitation:", inviteError);
          // Don't throw error - user can still sign up
        }
      }

      // Transform the user for our AuthUser type
      const user = transformSupabaseUser(
        authData.user,
        [], // Empty array - roles will be fetched on sign in
      );

      return { user, error: null };
    },
    { name: "auth.signup", attributes: { operation: "signup" } },
    { operation: "Signup", attributes: { operation: "signup" } },
  );

  // Sign in with email and password
  const signIn = withTelemetrySignIn(
    async (data: SignInData) => {
      recordMetric(authAttemptsCounter, 1, {
        operation: "signin",
        source: "frontend",
      });

      const { error } = await supabase.auth.signInWithPassword({
        email: data.email,
        password: data.password,
      });

      if (error) {
        recordMetric(authFailureCounter, 1, {
          operation: "signin",
          error: error.status || "unknown",
        });
        throw error;
      }

      recordMetric(authSuccessCounter, 1, { operation: "signin" });
      return { error: null };
    },
    { name: "auth.signin", attributes: { operation: "signin" } },
    { operation: "Signin", attributes: { operation: "signin" } },
  );

  // Sign in with OAuth provider
  const signInWithOAuth = withTelemetrySignInWithOAuth(
    async (provider: Provider) => {
      recordMetric(authAttemptsCounter, 1, {
        operation: "oauth_signin",
        source: "frontend",
      });

      // Get the invitation token from URL params if not provided in data
      const invitationToken =
        new URLSearchParams(window.location.search).get("token") || undefined;

      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/oauth/callback${
            invitationToken
              ? "?token=" + encodeURIComponent(invitationToken)
              : ""
          }`,
        },
      });

      if (error) {
        recordMetric(authFailureCounter, 1, {
          operation: "oauth_signin",
          error: error.status || "unknown",
        });
        throw error;
      } else {
        recordMetric(authSuccessCounter, 1, { operation: "oauth_signin" });
      }

      // The OAuth flow will redirect the user, so we don't need to handle the response here
      return { error: null };
    },
    { name: "auth.oauth_signin", attributes: { operation: "oauth_signin" } },
    { operation: "OAuth Signin", attributes: { operation: "oauth_signin" } },
  );

  // Sign in with Google Identity Services ID token
  const signInWithGoogleIdToken = withTelemetrySignInWithGoogleIdToken(
    async (data: GoogleIdTokenSignInData) => {
      recordMetric(authAttemptsCounter, 1, {
        operation: "google_id_token_signin",
        source: "frontend",
      });

      const credentials: {
        provider: "google";
        token: string;
        nonce?: string;
      } = {
        provider: "google",
        token: data.token,
      };
      if (data.nonce) {
        credentials.nonce = data.nonce;
      }

      const { data: authData, error } =
        await supabase.auth.signInWithIdToken(credentials);

      if (error) {
        recordMetric(authFailureCounter, 1, {
          operation: "google_id_token_signin",
          error: error.status || "unknown",
        });
        throw error;
      }

      if (!authData.user) {
        recordMetric(authFailureCounter, 1, {
          operation: "google_id_token_signin",
          error: "no_user_returned",
        });
        throw new Error("Google sign-in did not return a user.");
      }

      const invitationToken =
        data.invitationToken ||
        new URLSearchParams(window.location.search).get("token") ||
        undefined;
      await processInvitationForUser(invitationToken, authData.user.id);
      await syncOAuthUserMetadata(authData.user, refreshUserProfile);

      recordMetric(authSuccessCounter, 1, {
        operation: "google_id_token_signin",
      });
      return { error: null };
    },
    {
      name: "auth.google_id_token_signin",
      attributes: { operation: "google_id_token_signin" },
    },
    {
      operation: "Google ID Token Signin",
      attributes: { operation: "google_id_token_signin" },
    },
  );

  // Complete the direct LinkedIn popup session handoff
  const signInWithLinkedInSession = withTelemetrySignInWithLinkedInSession(
    async (data: LinkedInSessionSignInData) => {
      recordMetric(authAttemptsCounter, 1, {
        operation: "linkedin_session_signin",
        source: "frontend",
      });

      const { data: authData, error } = await supabase.auth.setSession({
        access_token: data.accessToken,
        refresh_token: data.refreshToken,
      });

      if (error) {
        recordMetric(authFailureCounter, 1, {
          operation: "linkedin_session_signin",
          error: error.status || "unknown",
        });
        throw error;
      }

      const authenticatedUser = authData.user;
      if (!authenticatedUser) {
        recordMetric(authFailureCounter, 1, {
          operation: "linkedin_session_signin",
          error: "no_user_returned",
        });
        throw new Error("LinkedIn sign-in did not return a user.");
      }

      const invitationToken =
        data.invitationToken ||
        new URLSearchParams(window.location.search).get("token") ||
        undefined;
      await processInvitationForUser(invitationToken, authenticatedUser.id);
      await syncOAuthUserMetadata(authenticatedUser, refreshUserProfile);

      recordMetric(authSuccessCounter, 1, {
        operation: "linkedin_session_signin",
      });
      return { error: null };
    },
    {
      name: "auth.linkedin_session_signin",
      attributes: { operation: "linkedin_session_signin" },
    },
    {
      operation: "LinkedIn Session Signin",
      attributes: { operation: "linkedin_session_signin" },
    },
  );

  // Sign out
  const signOut = withTelemetrySignOut(
    async () => {
      recordMetric(authAttemptsCounter, 1, {
        operation: "signout",
        source: "frontend",
      });

      const { error } = await supabase.auth.signOut();

      if (error) {
        recordMetric(authFailureCounter, 1, {
          operation: "signout",
          error: error.status || "unknown",
        });
        throw error;
      } else {
        recordMetric(authSuccessCounter, 1, { operation: "signout" });
      }

      return { error };
    },
    { name: "auth.signout", attributes: { operation: "signout" } },
    { operation: "Signout", attributes: { operation: "signout" } },
  );

  // Refresh user profile from backend using React Query
  const refreshUserProfile = async () => {
    if (!session?.user?.id) return;

    try {
      await refetchProfile();
    } catch (error) {
      console.warn("Failed to refresh user profile:", error);
    }
  };

  const value: AuthContextType = {
    user,
    session,
    loading,
    signUp,
    signIn,
    signInWithOAuth,
    signInWithGoogleIdToken,
    signInWithLinkedInSession,
    signOut,
    isAuthenticated: !!user,
    refreshUserProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
