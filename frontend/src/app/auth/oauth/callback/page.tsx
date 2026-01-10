"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { organizationService } from "@/services/organization-service";
import { supabase } from "@/lib/supabase";
import { extractFirstLastName } from "@/lib/user-utils";
import { authService } from "@/services/auth-service";
import { Button } from "@/components/ui/button";

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading, refreshUserProfile } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  const [hasRun, setHasRun] = useState(false);
  const [invitationProcessed, setInvitationProcessed] = useState(false);
  const [invitationError, setInvitationError] = useState<string | null>(null);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      // Prevent multiple executions
      if (hasRun) {
        return;
      }

      // Wait for auth to fully initialize
      if (authLoading) {
        return;
      }

      // Mark as running to prevent multiple executions
      setHasRun(true);

      // If no user after auth is done loading, it's an auth failure
      if (!user) {
        // Give a bit more time for potential delayed auth state updates
        await new Promise((resolve) => setTimeout(resolve, 1000));
        if (!user) {
          setError("Authentication failed. Please try signing in again.");
          setIsProcessing(false);
          return;
        }
      }

      // Process invitation if token is present in URL
      const invitationToken = searchParams?.get("token");
      if (invitationToken && user) {
        try {
          console.log(
            "Processing invitation for user:",
            user.id,
            "with token:",
            invitationToken,
          );
          const result = await authService.processInvitation(
            invitationToken,
            user.id,
          );
          if (!result.success) {
            console.warn("Failed to process invitation:", result.error);
            setInvitationError(result.error || "Failed to process invitation");
            // Don't throw error here - user can still sign up, invitation will be processed later
          } else {
            console.log("Invitation processed successfully:", result.data);
            setInvitationProcessed(true);
          }
        } catch (inviteError) {
          console.warn("Error processing invitation:", inviteError);
          const errorMessage =
            inviteError instanceof Error
              ? inviteError.message
              : "Failed to process invitation";
          setInvitationError(errorMessage);
          // Don't throw error - user can still sign up
        }
      }

      // Update user metadata to ensure first_name and last_name are properly set
      try {
        const currentUser = await supabase.auth.getUser();
        if (currentUser.data?.user) {
          const userMetadata = currentUser.data.user.user_metadata || {};

          // Always extract first_name and last_name using utility function to ensure consistency
          const { firstName: extractedFirstName, lastName: extractedLastName } =
            extractFirstLastName(userMetadata);

          // Update user metadata with extracted names if they differ from current values
          const currentFirstName = userMetadata.first_name || "";
          const currentLastName = userMetadata.last_name || "";

          if (
            extractedFirstName !== currentFirstName ||
            extractedLastName !== currentLastName
          ) {
            const { error: updateError } = await supabase.auth.updateUser({
              data: {
                ...userMetadata,
                first_name: extractedFirstName,
                last_name: extractedLastName,
              },
            });

            if (updateError) {
              console.error("Error updating user metadata:", updateError);
            } else {
              // Refresh the user profile to get the updated data
              await refreshUserProfile();
            }
          }
        }
      } catch (updateError) {
        console.error("Error processing OAuth user metadata:", updateError);
      }

      // Add a small delay to ensure auth is fully settled
      await new Promise((resolve) => setTimeout(resolve, 300));

      // Check if user already has organizations
      try {
        const organizations = await organizationService.getUserOrganizations();

        // If user already has organizations, redirect to dashboard
        if (organizations.length > 0) {
          router.replace("/dashboard");
          return;
        }

        // If user has no organizations, redirect to organization creation
        router.replace("/auth/create-organization");
      } catch (err) {
        console.error("Error handling OAuth callback:", err);

        // Check if it's an auth-related error (token not ready, etc.)
        const errorMessage = err instanceof Error ? err.message : String(err);
        if (
          errorMessage.includes("session") ||
          errorMessage.includes("token") ||
          errorMessage.includes("auth")
        ) {
          // Likely an auth timing issue, wait a bit longer and retry
          console.log("Auth-related error, retrying...");
          await new Promise((resolve) => setTimeout(resolve, 1000));
          try {
            const retryOrganizations =
              await organizationService.getUserOrganizations();
            if (retryOrganizations.length > 0) {
              router.replace("/dashboard");
            } else {
              router.replace("/auth/create-organization");
            }
            return;
          } catch (retryErr) {
            console.error("Retry failed:", retryErr);
          }
        }

        setError("Failed to set up your organization. Please contact support.");
        setIsProcessing(false);
      }
    };

    handleOAuthCallback();
  }, [user, authLoading, router, hasRun, refreshUserProfile, searchParams]);

  // Show invitation processing status if there was an invitation token
  if (invitationError) {
    return (
      <div className="min-h-screen bg-secondary/30 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-card rounded-xl border border-border shadow-lg p-8 text-center">
            <div className="mx-auto bg-yellow-100 dark:bg-yellow-900/30 rounded-full p-3 w-16 h-16 flex items-center justify-center mb-4">
              <AlertTriangle className="h-8 w-8 text-yellow-600 dark:text-yellow-500" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              Invitation Processing
            </h1>
            <p className="text-muted-foreground mb-4">
              Your account has been created successfully!
            </p>
            <p className="text-destructive mb-6 font-medium">
              {invitationError}
            </p>
            <p className="text-muted-foreground text-sm mb-6">
              You can still access the platform. Contact your organization admin
              if you believe there was an error.
            </p>
            <Button
              onClick={() => router.replace("/dashboard")}
              className="w-full"
            >
              Go to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (invitationProcessed) {
    return (
      <div className="min-h-screen bg-secondary/30 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-card rounded-xl border border-border shadow-lg p-8 text-center">
            <div className="mx-auto bg-green-100 dark:bg-green-900/30 rounded-full p-3 w-16 h-16 flex items-center justify-center mb-4">
              <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-500" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              Welcome!
            </h1>
            <p className="text-muted-foreground mb-4">
              Your account has been created successfully!
            </p>
            <p className="text-green-600 dark:text-green-500 mb-6 font-medium">
              You have been added to the organization successfully.
            </p>
            <Button
              onClick={() => router.replace("/dashboard")}
              className="w-full"
            >
              Go to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-secondary/30 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-card rounded-xl border border-border shadow-lg p-8 text-center">
            <div className="mx-auto bg-red-100 dark:bg-red-900/30 rounded-full p-3 w-16 h-16 flex items-center justify-center mb-4">
              <XCircle className="h-8 w-8 text-destructive" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              OAuth Error
            </h1>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button
              onClick={() => router.push("/auth/signin")}
              className="w-full"
            >
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Show loading state while processing
  if (isProcessing) {
    return (
      <div className="min-h-screen bg-secondary/30 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="bg-card rounded-xl border border-border shadow-lg p-8 text-center">
            <div className="mx-auto bg-primary/10 rounded-full p-3 w-16 h-16 flex items-center justify-center mb-4">
              <Loader2 className="h-8 w-8 text-primary animate-spin" />
            </div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              Completing Sign In...
            </h1>
            <p className="text-muted-foreground">
              Please wait while we complete your sign in and set up your
              account.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // This should rarely be reached since we redirect on success
  return null;
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-secondary/30 flex items-center justify-center p-4">
          <div className="w-full max-w-md">
            <div className="bg-card rounded-xl border border-border shadow-lg p-8 text-center">
              <div className="mx-auto bg-primary/10 rounded-full p-3 w-16 h-16 flex items-center justify-center mb-4">
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
              </div>
              <h1 className="text-2xl font-bold text-foreground mb-2">
                Loading...
              </h1>
            </div>
          </div>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
