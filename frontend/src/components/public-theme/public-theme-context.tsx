"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

/** Shared public theme: night ink blue or day paper blue. */
export type PublicTheme = "day" | "night";

/** Single storage key shared by the homepage and every public page, so the
 * visitor's day/night choice persists across the whole marketing site. */
export const PUBLIC_THEME_STORAGE_KEY = "247ai-home-theme";

interface PublicThemeValue {
  theme: PublicTheme;
  toggleTheme: () => void;
}

const PublicThemeContext = createContext<PublicThemeValue | null>(null);

/**
 * Holds the visitor's public-site theme. Reads the persisted choice on
 * mount (night until then, matching server render) and syncs across tabs.
 * Storage failures fall back to memory-only switching.
 */
export function PublicThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<PublicTheme>("night");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(PUBLIC_THEME_STORAGE_KEY);
      if (saved === "day" || saved === "night") setTheme(saved);
    } catch {
      /* Storage may be unavailable; the switch still works in memory. */
    }
    const onStorage = (event: StorageEvent) => {
      if (
        event.key === PUBLIC_THEME_STORAGE_KEY &&
        (event.newValue === "day" || event.newValue === "night")
      ) {
        setTheme(event.newValue);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((previous) => {
      const next = previous === "night" ? "day" : "night";
      try {
        localStorage.setItem(PUBLIC_THEME_STORAGE_KEY, next);
      } catch {
        /* Optional persistence. */
      }
      return next;
    });
  }, []);

  return (
    <PublicThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </PublicThemeContext.Provider>
  );
}

/** Reads the shared public theme. Must be used inside PublicThemeProvider. */
export function usePublicTheme(): PublicThemeValue {
  const value = useContext(PublicThemeContext);
  if (!value)
    throw new Error("usePublicTheme must be used inside PublicThemeProvider");
  return value;
}
