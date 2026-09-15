"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/contexts/theme-context";
import styles from "./public-theme.module.css";

interface ThemeSwitchProps {
  /** True when the dark side is active; drives the knob and the label. */
  dark: boolean;
  /** Flips to the other side. */
  onToggle: () => void;
}

/**
 * The single theme switch visual for the whole site: sun, sliding knob,
 * moon. It is presentational on purpose — each surface wires the `dark`
 * flag to what it actually shows (public pages to their night default,
 * the dashboard to the resolved site-wide theme), so the control never
 * disagrees with the page around it.
 */
export function ThemeSwitch({ dark, onToggle }: ThemeSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label={`Switch to ${dark ? "day" : "night"} mode`}
      data-dark={dark}
      className={styles.themeSwitch}
      onClick={onToggle}
    >
      <Sun size={14} aria-hidden="true" />
      <span className={styles.switchTrack} aria-hidden="true">
        <span />
      </span>
      <Moon size={13} aria-hidden="true" />
    </button>
  );
}

/**
 * Dashboard wiring for the shared switch: follows the resolved site-wide
 * theme and writes an explicit choice back to it, so the public pages
 * follow too.
 */
export function SiteThemeSwitch() {
  const { resolvedTheme, setTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  return (
    <ThemeSwitch
      dark={dark}
      onToggle={() => setTheme(dark ? "light" : "dark")}
    />
  );
}
