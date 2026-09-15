"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Home, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabase";
import { authService } from "@/services/auth-service";
import { exchangeOAuthSessionHandoff } from "@/services/oauth-session-service";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import pt from "@/components/public-theme/public-theme.module.css";

let handoffCompletionPromise: Promise<void> | null = null;

/** Test-only reset for module-level handoff guard. */
export function __resetOAuthSessionHandoffForTests(): void {
  handoffCompletionPromise = null;
}

function readQueryParam(
  name: string,
  searchParams: URLSearchParams,
): string | null {
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

        window.history.replaceState(
          {},
          document.title,
          window.location.pathname,
        );

        const invitationToken = readQueryParam(
          "invitation_token",
          searchParams,
        );
        const organizationIdFromQuery = readQueryParam(
          "organization_id",
          searchParams,
        );
        const organizationNameFromQuery = readQueryParam(
          "organization_name",
          searchParams,
        );
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (user && (invitationToken || organizationIdFromQuery)) {
          const { markInviteWelcomePending } =
            await import("@/lib/invite-welcome");
          let organizationId = organizationIdFromQuery;
          let organizationName = organizationNameFromQuery;

          if (invitationToken) {
            const inviteResult = await authService.processInvitation(
              invitationToken,
              user.id,
            );
            if (!inviteResult.success) {
              throw new Error(
                inviteResult.error || "Failed to process invitation.",
              );
            }
            if (inviteResult.data && typeof inviteResult.data === "object") {
              const data = inviteResult.data as {
                organization_name?: unknown;
                organization_id?: unknown;
              };
              if (typeof data.organization_id === "string") {
                organizationId = data.organization_id;
              }
              if (typeof data.organization_name === "string") {
                organizationName = data.organization_name;
              }
            }
          }

          // Backend OAuth already processes the invite before provisioning; a
          // frontend "already accepted" response still warrants selecting the
          // invited org (from query params) and showing a welcome toast.
          markInviteWelcomePending({ organizationId, organizationName });
        }

        window.location.replace("/dashboard");
      })().catch(() => {
        setError("Authentication could not be completed.");
      });
    }

    void handoffCompletionPromise;
  }, [router, searchParams]);

  if (error) {
    const inviteOnly = /invite-only|request a demo/i.test(error);
    return (
      <PublicThemeRoot>
        <div className={pt.page}>
          <PublicHeader />
          <main className="flex-1 flex items-center justify-center p-6">
            <div className="w-full max-w-md space-y-6 text-center">
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
              {inviteOnly ? (
                <>
                  <p className="text-sm text-muted-foreground">
                    We onboard every business personally — request a demo and we
                    will invite you, usually within one business day.
                  </p>
                  <div className="flex flex-col gap-3">
                    <Button
                      asChild
                      className="bg-blue-600 hover:bg-blue-700 h-12"
                    >
                      <Link href="/request-demo">Request a demo</Link>
                    </Button>
                    <Button asChild variant="ghost">
                      <Link href="/">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to home
                      </Link>
                    </Button>
                  </div>
                </>
              ) : (
                <div className="flex flex-col gap-3">
                  <Button asChild className="h-12">
                    <Link href="/auth/signin">Try signing in again</Link>
                  </Button>
                  <Button asChild variant="ghost">
                    <Link href="/">
                      <Home className="mr-2 h-4 w-4" />
                      Back to home
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          </main>
          <PublicFooter />
        </div>
      </PublicThemeRoot>
    );
  }

  return (
    <PublicThemeRoot>
      <div className="mx-auto flex min-h-[50vh] w-full max-w-md flex-col items-center justify-center gap-3 p-6 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p>Completing sign-in...</p>
      </div>
    </PublicThemeRoot>
  );
}
