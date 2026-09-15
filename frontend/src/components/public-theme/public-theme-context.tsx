"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ThemeProvider,
  useTheme as useSiteTheme,
} from "@/contexts/theme-context";

/** Public-pages name for the shared theme: night ink blue or day paper blue. */
export type PublicTheme = "day" | "night";

/**
 * The single site-wide theme lives in `contexts/theme-context` under the
 * "theme" key ("light"/"dark"/"system"). This constant keeps that canonical
 * key importable from public-pages code and tests.
 */
export { THEME_STORAGE_KEY as PUBLIC_THEME_STORAGE_KEY } from "@/contexts/theme-context";

export { ThemeProvider };

interface PublicThemeValue {
  theme: PublicTheme;
  toggleTheme: () => void;
}

/** Reads the visitor's explicit stored choice, if any. */
function readStoredChoice(): string | null {
  try {
    return localStorage.getItem("theme");
  } catch {
    return null;
  }
}
/**
 * Public-pages view of the single site-wide theme. An explicit choice made
 * anywhere (public toggle, dashboard settings) is honored everywhere:
 * "dark" shows night, "light" shows day. With no explicit choice yet, the
 * public pages keep their historical night default while the dashboard
 * follows the OS — the moment anyone toggles, both surfaces move together.
 *
 * Before hydration the night default is shown so the server render and
 * first paint match without a flash.
 */
export function usePublicTheme(): PublicThemeValue {
  const { theme, resolvedTheme, setTheme } = useSiteTheme();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  let night = true;
  if (hydrated) {
    const stored = readStoredChoice();
    if (stored === "light" || stored === "dark") {
      night = resolvedTheme === "dark";
    } else if (theme === "dark") {
      night = true;
    } else if (theme === "light") {
      night = false;
    }
    // Stored "system" (or nothing, or unreadable storage) with in-memory
    // "system" keeps the night showcase default.
  }

  const toggleTheme = useCallback(() => {
    setTheme(night ? "light" : "dark");
  }, [night, setTheme]);

  return { theme: night ? "night" : "day", toggleTheme };
}
