"use client";

/**
 * Email verification landing page.
 *
 * Users arrive here from the verification link sent via Resend.
 * The token query param is exchanged with the backend to confirm
 * the email address in Supabase.
 */

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle, Loader2, XCircle } from "lucide-react";
import { authService } from "@/services/auth-service";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";

type VerifyState = "loading" | "success" | "error";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams?.get("token") || "";
  const [state, setState] = useState<VerifyState>("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("Missing verification token.");
      return;
    }

    let cancelled = false;

    async function verify() {
      const result = await authService.verifyEmail(token);
      if (cancelled) return;

      if (result.success) {
        setState("success");
        setMessage(result.message || "Email verified successfully.");
      } else {
        setState("error");
        setMessage(result.error || "Verification failed.");
      }
    }

    void verify();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <PublicThemeRoot>
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="max-w-md w-full space-y-6 text-center">
          {state === "loading" && (
            <>
              <Loader2 className="h-12 w-12 animate-spin mx-auto text-purple-600" />
              <p className="text-gray-600">Verifying your email address...</p>
            </>
          )}

          {state === "success" && (
            <Alert className="bg-green-50 border-green-200 text-left">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                <strong>Email verified!</strong>
                <p className="mt-2 text-sm">{message}</p>
                <Button asChild className="mt-4" size="sm">
                  <Link href="/auth/signin">Sign in</Link>
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {state === "error" && (
            <Alert className="bg-red-50 border-red-200 text-left">
              <XCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">
                <strong>Verification failed</strong>
                <p className="mt-2 text-sm">{message}</p>
                <p className="mt-2 text-sm text-red-700">
                  If you requested multiple verification emails, open the{" "}
                  <strong>most recent</strong> message. Older links stop working
                  after a new one is sent.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button asChild variant="outline" size="sm">
                    <Link href="/auth/signin">Back to sign in</Link>
                  </Button>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </div>
      </div>
    </PublicThemeRoot>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <PublicThemeRoot>
          <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <div className="max-w-md w-full space-y-6 text-center">
              <Loader2 className="h-12 w-12 animate-spin mx-auto text-purple-600" />
              <p className="text-gray-600">Verifying your email address...</p>
            </div>
          </div>
        </PublicThemeRoot>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
