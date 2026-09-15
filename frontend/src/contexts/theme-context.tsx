"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

type Theme = "light" | "dark" | "system";

/** Storage key for the single site-wide theme choice. */
export const THEME_STORAGE_KEY = "theme";

/**
 * Legacy public-pages key from before the site-wide unification. Migrated
 * once into THEME_STORAGE_KEY so returning visitors keep their choice.
 */
const LEGACY_PUBLIC_THEME_KEY = "247ai-home-theme";

function readStoredTheme(): Theme | null {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    if (saved && ["light", "dark", "system"].includes(saved)) return saved;
    // One-time migration from the old public-pages key.
    const legacy = localStorage.getItem(LEGACY_PUBLIC_THEME_KEY);
    if (legacy === "night" || legacy === "day") {
      const migrated = legacy === "night" ? "dark" : "light";
      localStorage.setItem(THEME_STORAGE_KEY, migrated);
      localStorage.removeItem(LEGACY_PUBLIC_THEME_KEY);
      return migrated;
    }
  } catch {
    /* Storage may be unavailable; fall back to the default. */
  }
  return null;
}

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: "light" | "dark"; // The actual theme being used (system resolves to light or dark)
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("system");
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");
  // Tracks whether the apply effect below has run at least once. On mount
  // the load effect above only queues its update, so this effect still sees
  // the "system" default — writing it would clobber a stored choice before
  // the queued update is processed.
  const applyRan = useRef(false);

  useEffect(() => {
    // Load theme from localStorage on initialization, migrating the legacy
    // public-pages key when this is a returning visitor's first load.
    const savedTheme = readStoredTheme();
    if (savedTheme) {
      setTheme(savedTheme);
    }
    // Pick up choices made in another open tab on any page of the site.
    const onStorage = (event: StorageEvent) => {
      if (
        event.key === THEME_STORAGE_KEY &&
        event.newValue &&
        ["light", "dark", "system"].includes(event.newValue)
      ) {
        setTheme(event.newValue as Theme);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    const root = window.document.documentElement;

    // Remove previous theme classes
    root.classList.remove("light", "dark");

    let effectiveTheme: "light" | "dark";

    if (theme === "system") {
      // Use system preference
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
        .matches
        ? "dark"
        : "light";
      effectiveTheme = systemTheme;
    } else {
      effectiveTheme = theme;
    }

    // Apply the theme
    root.classList.add(effectiveTheme);
    setResolvedTheme(effectiveTheme);

    // Save to localStorage, but never clobber a stored choice on the first
    // run: the load effect's update is still queued at that point, so a
    // blind write would overwrite a real choice with the "system" default.
    // Later runs always persist (including an explicit "system" pick).
    try {
      const firstRun = !applyRan.current;
      applyRan.current = true;
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      const storedDiffers =
        stored &&
        stored !== theme &&
        ["light", "dark", "system"].includes(stored);
      if (!(firstRun && storedDiffers)) {
        localStorage.setItem(THEME_STORAGE_KEY, theme);
      }
    } catch {
      /* Storage may be unavailable; the choice still applies in memory. */
    }
  }, [theme]);

  useEffect(() => {
    // Listen for system theme changes when using system theme
    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

      const handleChange = (e: MediaQueryListEvent) => {
        const root = window.document.documentElement;
        root.classList.remove("light", "dark");
        const newTheme = e.matches ? "dark" : "light";
        root.classList.add(newTheme);
        setResolvedTheme(newTheme);
      };

      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
  }, [theme]);

  const value = {
    theme,
    setTheme,
    resolvedTheme,
  };

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}

/**
 * Reads the shared theme without throwing when no provider is above (e.g.
 * standalone component tests). Production pages always render under the
 * root layout provider; PublicThemeRoot uses this to avoid nesting a
 * second provider there while still rendering standalone.
 */
export function useOptionalTheme() {
  return useContext(ThemeContext);
}
