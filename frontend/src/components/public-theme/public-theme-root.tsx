"use client";

import type { ReactNode } from "react";
import { PublicThemeProvider, usePublicTheme } from "./public-theme-context";
import styles from "./public-theme.module.css";

/**
 * Inner themed wrapper. The `dark` class switches every Tailwind `dark:`
 * style and shadcn token inside, so the visitor's toggle drives the whole
 * page — not just the token-based chrome.
 */
function ThemedShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const { theme } = usePublicTheme();
  return (
    <div
      className={`${styles.root}${theme === "night" ? " dark" : ""}${className ? ` ${className}` : ""}`}
      data-theme={theme}
    >
      {children}
    </div>
  );
}

/**
 * Shared public-site theme root. Provides the persisted day/night choice
 * (same storage key as the homepage) and scopes the atmosphere tokens to
 * the wrapped marketing pages. Dashboard styling is unaffected.
 */
export function PublicThemeRoot({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <PublicThemeProvider>
      <ThemedShell className={className}>{children}</ThemedShell>
    </PublicThemeProvider>
  );
}
