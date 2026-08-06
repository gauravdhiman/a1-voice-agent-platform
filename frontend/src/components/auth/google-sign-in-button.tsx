"use client";

import React, { useCallback, useEffect, useRef } from "react";
import Script from "next/script";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type GoogleButtonText = "signin_with" | "signup_with";

interface GoogleCredentialResponse {
  credential?: string;
}

interface GoogleIdentityButtonOptions {
  theme: "outline";
  size: "large";
  text: GoogleButtonText;
  shape: "rectangular";
  logo_alignment: "left";
  width: number;
}

interface GoogleIdentityConfiguration {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  nonce: string;
  ux_mode: "popup";
  use_fedcm_for_prompt: boolean;
}

interface GoogleIdentityServices {
  accounts: {
    id: {
      initialize: (configuration: GoogleIdentityConfiguration) => void;
      renderButton: (
        parent: HTMLElement,
        options: GoogleIdentityButtonOptions,
      ) => void;
      cancel: () => void;
    };
  };
}

declare global {
  interface Window {
    google?: GoogleIdentityServices;
  }
}

/**
 * Generates a raw nonce and its SHA-256 hash for Google ID-token sign-in.
 *
 * Google receives the hashed nonce while Supabase receives the raw nonce. The
 * pair binds the ID token to this browser authentication attempt and lets
 * Supabase validate the token's nonce claim.
 *
 * @returns Promise resolving to the raw and hashed nonce values.
 * @throws Error when the browser does not provide Web Crypto support.
 */
async function generateGoogleNonce(): Promise<{
  rawNonce: string;
  hashedNonce: string;
}> {
  if (!globalThis.crypto?.getRandomValues || !globalThis.crypto.subtle) {
    throw new Error("Web Crypto is required for Google sign-in.");
  }

  const randomBytes = globalThis.crypto.getRandomValues(new Uint8Array(32));
  const rawNonce = Array.from(randomBytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  const hashBuffer = await globalThis.crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(rawNonce),
  );
  const hashedNonce = Array.from(new Uint8Array(hashBuffer), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");

  return { rawNonce, hashedNonce };
}

/**
 * Props for the Google Identity Services popup button.
 */
interface GoogleSignInButtonProps {
  /** Receives the Google ID token and the raw nonce for Supabase exchange. */
  onCredential: (credential: string, nonce: string) => void | Promise<void>;
  /** Receives a user-safe error when Google cannot provide a credential. */
  onError: (message: string) => void;
  /** Changes the official button between sign-in and sign-up copy. */
  text: GoogleButtonText;
  /** Prevents another authentication action while the exchange is pending. */
  disabled?: boolean;
  /** Optional classes applied to the button container. */
  className?: string;
}

/**
 * Renders Google's official branded button using the popup UX.
 *
 * Unlike Supabase's redirect-based OAuth helper, this flow keeps the current
 * page on the application domain. Google returns an ID token to the callback,
 * which the parent exchanges with Supabase using `signInWithIdToken`.
 *
 * @example
 * ```tsx
 * <GoogleSignInButton
 *   text="signin_with"
 *   onCredential={(token, nonce) =>
 *     signInWithGoogleIdToken({ token, nonce })
 *   }
 *   onError={setError}
 * />
 * ```
 */
export function GoogleSignInButton({
  onCredential,
  onError,
  text,
  disabled = false,
  className,
}: GoogleSignInButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const hasInitializedRef = useRef(false);
  const onCredentialRef = useRef(onCredential);
  const onErrorRef = useRef(onError);
  onCredentialRef.current = onCredential;
  onErrorRef.current = onError;

  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim();

  const initializeGoogleButton = useCallback(async () => {
    if (
      !clientId ||
      hasInitializedRef.current ||
      !containerRef.current ||
      !window.google?.accounts?.id
    ) {
      return;
    }

    hasInitializedRef.current = true;

    try {
      const { rawNonce, hashedNonce } = await generateGoogleNonce();
      const googleId = window.google.accounts.id;
      const container = containerRef.current;

      if (!container) {
        hasInitializedRef.current = false;
        return;
      }

      googleId.initialize({
        client_id: clientId || "",
        callback: (response) => {
          if (!response.credential) {
            onErrorRef.current(
              "Google did not return an ID token. Please try again.",
            );
            return;
          }

          void onCredentialRef.current(response.credential, rawNonce);
        },
        nonce: hashedNonce,
        ux_mode: "popup",
        use_fedcm_for_prompt: true,
      });
      googleId.renderButton(container, {
        theme: "outline",
        size: "large",
        text,
        shape: "rectangular",
        logo_alignment: "left",
        width: Math.min(container.clientWidth || 400, 400),
      });
    } catch (error) {
      hasInitializedRef.current = false;
      onErrorRef.current(
        error instanceof Error
          ? error.message
          : "Google sign-in could not be initialized. Please try again.",
      );
    }
  }, [clientId, text]);

  useEffect(() => {
    const container = containerRef.current;
    void initializeGoogleButton();

    return () => {
      if (hasInitializedRef.current) {
        window.google?.accounts.id.cancel();
      }
      hasInitializedRef.current = false;
      container?.replaceChildren();
    };
  }, [initializeGoogleButton]);

  if (!clientId) {
    return (
      <p
        role="status"
        aria-label="Google sign-in is not configured"
        className={cn("text-center text-sm text-muted-foreground", className)}
      >
        Google sign-in is not configured.
      </p>
    );
  }

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={() => void initializeGoogleButton()}
        onError={() =>
          onErrorRef.current(
            "Google sign-in could not load. Please check your connection and try again.",
          )
        }
      />
      <div
        className={cn(
          "relative flex min-h-11 justify-center",
          disabled && "pointer-events-none opacity-60",
          className,
        )}
        aria-disabled={disabled}
        data-testid="google-sign-in-button"
      >
        <div ref={containerRef} />
        {disabled && (
          <div
            className="absolute inset-0 flex items-center justify-center gap-2 bg-background/60 text-sm text-muted-foreground"
            aria-live="polite"
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            Signing in with Google...
          </div>
        )}
      </div>
    </>
  );
}
