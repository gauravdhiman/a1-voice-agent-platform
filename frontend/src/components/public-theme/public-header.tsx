"use client";

import Link from "next/link";
import { ArrowUpRight, Moon, Sun } from "lucide-react";
import { SITE_NAME } from "@/lib/site-config";
import { usePublicTheme } from "./public-theme-context";
import styles from "./public-theme.module.css";

/**
 * Shared public-site header: dot-grid brand, homepage anchors, the shared
 * day/night switch, sign-in, and the demo CTA. Anchors point at the
 * homepage sections so they work from every public page.
 */
export function PublicHeader() {
  const { theme, toggleTheme } = usePublicTheme();

  return (
    <header className={styles.header}>
      <Link href="/" className={styles.brand} aria-label={`${SITE_NAME} home`}>
        <span className={styles.brandMark} aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
        </span>
        <span>{SITE_NAME}</span>
      </Link>
      <nav className={styles.nav} aria-label="Main navigation">
        <Link href="/#features">Use cases</Link>
        <Link href="/#demos">Live demos</Link>
        <Link href="/#industries">For your business</Link>
        <Link href="/#integrations">Integrations</Link>
        <Link href="/#pricing">Pricing</Link>
      </nav>
      <div className={styles.headerActions}>
        <button
          className={styles.themeSwitch}
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "night" ? "day" : "night"} mode`}
        >
          <Sun size={14} />
          <span className={styles.switchTrack}>
            <span />
          </span>
          <Moon size={13} />
        </button>
        <Link className={styles.signIn} href="/auth/signin">
          Sign in <ArrowUpRight size={13} />
        </Link>
        <Link className={styles.headerCta} href="/request-demo">
          Request a demo <ArrowUpRight size={14} />
        </Link>
      </div>
    </header>
  );
}
