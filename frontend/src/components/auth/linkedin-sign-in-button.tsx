"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { linkedinAuthService } from "@/services/linkedin-auth-service";
import type { LinkedInSessionData } from "@/types/auth";

type LinkedInButtonText = "signin_with" | "signup_with";

interface LinkedInSignInButtonProps extends Omit<
  React.ButtonHTMLAttributes<HTMLButtonElement>,
  "onClick" | "onError"
> {
  /** Text variant shown in the LinkedIn-branded button. */
  text: LinkedInButtonText;
  /** Called after the backend returns a Supabase session. */
  onSession: (session: LinkedInSessionData) => void;
  /** Called when the popup, callback, or backend exchange fails. */
  onError: (message: string) => void;
  /** Notifies the parent form so its other controls can be disabled. */
  onLoadingChange?: (loading: boolean) => void;
}

interface LinkedInSuccessMessage {
  type: "linkedin-oauth-success";
  state: string;
  session: LinkedInSessionData;
}

interface LinkedInErrorMessage {
  type: "linkedin-oauth-error";
  state: string;
  message: string;
}

/**
 * Opens LinkedIn directly in a popup and receives the app session securely.
 *
 * The callback page is hosted by this application, not Supabase. It exchanges
 * the authorization code through the backend and posts the resulting session
 * to this window only after the signed state has been checked.
 */
export function LinkedInSignInButton({
  text,
  onSession,
  onError,
  onLoadingChange,
  className,
  disabled,
  ...props
}: LinkedInSignInButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const popupRef = useRef<Window | null>(null);
  const stateRef = useRef<string | null>(null);
  const pollRef = useRef<number | null>(null);
  const callbacksRef = useRef({
    onError,
    onSession,
    onLoadingChange,
  });

  useEffect(() => {
    callbacksRef.current = { onError, onSession, onLoadingChange };
  }, [onError, onSession, onLoadingChange]);

  const setLoading = useCallback((loading: boolean) => {
    setIsLoading(loading);
    callbacksRef.current.onLoadingChange?.(loading);
  }, []);

  const clearFlow = useCallback(
    (closePopup: boolean) => {
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }

      if (closePopup && popupRef.current && !popupRef.current.closed) {
        popupRef.current.close();
      }

      popupRef.current = null;
      stateRef.current = null;
      setLoading(false);
    },
    [setLoading],
  );

  useEffect(() => {
    const handleMessage = (event: MessageEvent<unknown>) => {
      if (event.origin !== window.location.origin) return;
      if (event.source !== popupRef.current) return;

      const message = event.data as
        | LinkedInSuccessMessage
        | LinkedInErrorMessage
        | undefined;
      if (
        !message ||
        (message.type !== "linkedin-oauth-success" &&
          message.type !== "linkedin-oauth-error")
      ) {
        return;
      }
      if (!stateRef.current || message.state !== stateRef.current) return;

      if (message.type === "linkedin-oauth-success") {
        const session = message.session;
        clearFlow(true);
        callbacksRef.current.onSession(session);
        return;
      }

      const errorMessage =
        typeof message.message === "string"
          ? message.message
          : "LinkedIn authentication could not be completed.";
      clearFlow(true);
      callbacksRef.current.onError(errorMessage);
    };

    window.addEventListener("message", handleMessage);
    return () => {
      window.removeEventListener("message", handleMessage);
      clearFlow(true);
    };
  }, [clearFlow]);

  const handleClick = async () => {
    if (disabled || isLoading) return;

    const popup = window.open(
      "",
      "linkedin-oauth",
      "popup,width=520,height=680,resizable=yes,scrollbars=yes",
    );
    if (!popup) {
      onError("Please allow popups to sign in with LinkedIn.");
      return;
    }

    popupRef.current = popup;
    setLoading(true);

    try {
      const result = await linkedinAuthService.getAuthorizationUrl();
      if (!result.success || !result.data) {
        throw new Error(
          result.error || "LinkedIn authentication is not configured.",
        );
      }

      stateRef.current = result.data.state;
      popup.location.href = result.data.authorizationUrl;
      pollRef.current = window.setInterval(() => {
        if (popup.closed) {
          clearFlow(false);
          callbacksRef.current.onError(
            "The LinkedIn sign-in window was closed.",
          );
        }
      }, 500);
    } catch (error) {
      clearFlow(true);
      onError(
        error instanceof Error
          ? error.message
          : "LinkedIn authentication could not be started.",
      );
    }
  };

  const label =
    text === "signin_with" ? "Sign in with LinkedIn" : "Sign up with LinkedIn";

  return (
    <Button
      {...props}
      type="button"
      variant="outline"
      onClick={handleClick}
      disabled={disabled || isLoading}
      className={cn(
        "flex h-11 w-full items-center justify-center cursor-pointer",
        className,
      )}
      aria-label={label}
    >
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          {text === "signin_with"
            ? "Signing in with LinkedIn..."
            : "Signing up with LinkedIn..."}
        </>
      ) : (
        <div className="flex items-center justify-center gap-3">
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="#0077B5"
            aria-hidden="true"
          >
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774.792 0 0 1.729z" />
          </svg>
          <span>{label}</span>
        </div>
      )}
    </Button>
  );
}
