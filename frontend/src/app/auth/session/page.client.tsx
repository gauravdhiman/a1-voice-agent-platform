"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { supabase } from "@/lib/supabase";
import { authService } from "@/services/auth-service";
import { exchangeOAuthSessionHandoff } from "@/services/oauth-session-service";

let handoffCompletionPromise: Promise<void> | null = null;

/** Test-only reset for module-level handoff guard. */
export function __resetOAuthSessionHandoffForTests(): void {
  handoffCompletionPromise = null;
}

function readQueryParam(name: string, searchParams: URLSearchParams): string | null {
  if (typeof window !== "undefined") {
    const fromLocation = new URLSearchParams(window.location.search).get(name);
    if (fromLocation) {
      return fromLocation;
    }
  }
  return searchParams.get(name);
}

/**
 * Completes backend OAuth by exchanging a one-time handoff token for a session.
 */
export default function OAuthSessionPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!handoffCompletionPromise) {
      handoffCompletionPromise = (async () => {
        setError(null);

        const queryError = readQueryParam("error", searchParams);
        if (queryError) {
          setError(queryError);
          return;
        }

        const {
          data: { session: existingSession },
        } = await supabase.auth.getSession();
        if (existingSession) {
          window.location.replace("/dashboard");
          return;
        }

        const handoff = readQueryParam("handoff", searchParams);
        if (!handoff) {
          setError("Authentication could not be completed.");
          return;
        }

        const handoffResult = await exchangeOAuthSessionHandoff(handoff);
        if (!handoffResult.success || !handoffResult.data) {
          const {
            data: { session: recoveredSession },
          } = await supabase.auth.getSession();
          if (recoveredSession) {
            window.location.replace("/dashboard");
            return;
          }

          setError(
            handoffResult.error || "Authentication could not be completed.",
          );
          return;
        }

        const { error: sessionError } = await supabase.auth.setSession({
          access_token: handoffResult.data.access_token,
          refresh_token: handoffResult.data.refresh_token,
        });

        if (sessionError) {
          setError(
            sessionError.message || "Authentication could not be completed.",
          );
          return;
        }

        window.history.replaceState({}, document.title, window.location.pathname);

        const invitationToken = readQueryParam("invitation_token", searchParams);
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (user && invitationToken) {
          await authService.processInvitation(invitationToken, user.id);
        }

        window.location.replace("/dashboard");
      })().catch(() => {
        setError("Authentication could not be completed.");
      });
    }

    void handoffCompletionPromise;
  }, [router, searchParams]);

  if (error) {
    return (
      <div className="mx-auto flex min-h-[50vh] w-full max-w-md items-center justify-center p-6">
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-[50vh] w-full max-w-md flex-col items-center justify-center gap-3 p-6 text-muted-foreground">
      <Loader2 className="h-6 w-6 animate-spin" />
      <p>Completing sign-in...</p>
    </div>
  );
}
