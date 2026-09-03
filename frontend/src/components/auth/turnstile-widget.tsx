"use client";

import React, { useEffect, useRef } from "react";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: Record<string, unknown>,
      ) => string;
      remove: (widgetId: string) => void;
    };
    __turnstileLoading?: Promise<void>;
  }
}

const SCRIPT_SRC =
  "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

function loadTurnstileScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.turnstile) return Promise.resolve();
  if (!window.__turnstileLoading) {
    window.__turnstileLoading = new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () =>
        reject(new Error("Could not load the captcha widget."));
      document.head.appendChild(script);
    });
  }
  return window.__turnstileLoading;
}

interface TurnstileWidgetProps {
  /** Called with the verification token on each successful challenge. */
  onVerify: (token: string) => void;
  /** Called when the token expires (caller should clear it). */
  onExpire?: () => void;
  /** Called when the widget fails to load or render. */
  onError?: () => void;
}

/**
 * Cloudflare Turnstile checkbox widget.
 *
 * Renders nothing when `NEXT_PUBLIC_TURNSTILE_SITE_KEY` is unset (local
 * dev runs without a Cloudflare account; the backend skips verification
 * in that case too). Never blocks form submission on its own — callers
 * decide whether a missing token may submit.
 */
export function TurnstileWidget({
  onVerify,
  onExpire,
  onError,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const callbacksRef = useRef({ onVerify, onExpire, onError });
  callbacksRef.current = { onVerify, onExpire, onError };

  const siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

  useEffect(() => {
    if (!siteKey || !containerRef.current) return;
    let widgetId: string | null = null;
    let cancelled = false;

    loadTurnstileScript().then(
      () => {
        if (cancelled || !containerRef.current || !window.turnstile) return;
        try {
          widgetId = window.turnstile.render(containerRef.current, {
            sitekey: siteKey,
            callback: (token: string) => callbacksRef.current.onVerify(token),
            "expired-callback": () => callbacksRef.current.onExpire?.(),
            "error-callback": () => callbacksRef.current.onError?.(),
          });
        } catch {
          callbacksRef.current.onError?.();
        }
      },
      () => {
        if (!cancelled) callbacksRef.current.onError?.();
      },
    );

    return () => {
      cancelled = true;
      if (widgetId && window.turnstile) {
        try {
          window.turnstile.remove(widgetId);
        } catch {
          // Widget teardown is best-effort during unmount.
        }
      }
    };
  }, [siteKey]);

  if (!siteKey) return null;
  return <div ref={containerRef} data-testid="turnstile-widget" />;
}
