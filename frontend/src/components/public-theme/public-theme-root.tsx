"use client";

import type { ReactNode } from "react";
import { ThemeProvider, useOptionalTheme } from "@/contexts/theme-context";
import { usePublicTheme } from "./public-theme-context";
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
 * Shared public-site theme root. Consumes the single site-wide theme from
 * the root layout provider (same state as the dashboard) and scopes the
 * atmosphere tokens to the wrapped marketing pages — never nesting a
 * second provider there. Standalone renders (component tests) self-provide
 * so pages keep rendering outside the full app shell. Dashboard styling is
 * unaffected.
 */
export function PublicThemeRoot({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const outer = useOptionalTheme();
  if (outer) {
    return <ThemedShell className={className}>{children}</ThemedShell>;
  }
  return (
    <ThemeProvider>
      <ThemedShell className={className}>{children}</ThemedShell>
    </ThemeProvider>
  );
}
