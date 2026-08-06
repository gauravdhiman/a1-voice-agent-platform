"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { linkedinAuthService } from "@/services/linkedin-auth-service";

type CallbackStatus = "processing" | "error" | "complete";

/**
 * Completes the direct LinkedIn popup flow on an app-owned origin.
 *
 * LinkedIn redirects here with a short-lived authorization code. This page
 * immediately removes the code from the address bar, asks the backend to
 * exchange it, and posts the resulting Supabase session to the opening window.
 */
export default function LinkedInCallbackPage() {
  const [status, setStatus] = useState<CallbackStatus>("processing");
  const [message, setMessage] = useState("");

  const searchParams = useSearchParams();

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setStatus("error");
      setMessage("LinkedIn did not return a valid authentication response.");
      return;
    }

    // Remove one-time credentials from browser history before exchanging them.
    window.history.replaceState({}, document.title, window.location.pathname);

    let cancelled = false;
    const completeAuthentication = async () => {
      const result = await linkedinAuthService.exchangeCode(code, state);
      if (cancelled) return;

      if (!result.success || !result.data) {
        const errorMessage =
          result.error || "LinkedIn authentication could not be completed.";
        setStatus("error");
        setMessage(errorMessage);
        window.opener?.postMessage(
          {
            type: "linkedin-oauth-error",
            state,
            message: "LinkedIn authentication could not be completed.",
          },
          window.location.origin,
        );
        window.close();
        return;
      }

      if (!window.opener || window.opener.closed) {
        setStatus("complete");
        setMessage(
          "Authentication completed. You can close this window and return to the app.",
        );
        return;
      }

      window.opener.postMessage(
        {
          type: "linkedin-oauth-success",
          state,
          session: result.data,
        },
        window.location.origin,
      );
      setStatus("complete");
      setMessage("Authentication completed. This window can now close.");
      window.close();
    };

    completeAuthentication().catch(() => {
      if (cancelled) return;
      setStatus("error");
      setMessage("LinkedIn authentication could not be completed.");
      window.opener?.postMessage(
        {
          type: "linkedin-oauth-error",
          state,
          message: "LinkedIn authentication could not be completed.",
        },
        window.location.origin,
      );
      window.close();
    });

    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-secondary/30 p-4">
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-8 text-center shadow-lg">
        {status === "processing" ? (
          <Loader2
            className="mx-auto mb-4 h-8 w-8 animate-spin text-primary"
            aria-label="Completing LinkedIn sign in"
          />
        ) : (
          <div className="mx-auto mb-4 h-8 w-8 rounded-full bg-primary/10" />
        )}
        <h1 className="mb-2 text-2xl font-bold text-foreground">
          {status === "processing"
            ? "Completing LinkedIn sign in..."
            : status === "error"
              ? "LinkedIn sign in failed"
              : "LinkedIn sign in complete"}
        </h1>
        <p className="text-muted-foreground">
          {message ||
            "Please wait while we securely finish authentication in the app."}
        </p>
      </div>
    </main>
  );
}
