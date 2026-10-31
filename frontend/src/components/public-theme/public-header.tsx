"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { SITE_NAME } from "@/lib/site-config";
import { usePublicTheme } from "./public-theme-context";
import { ThemeSwitch } from "./theme-switch";
import styles from "./public-theme.module.css";

/**
 * Shared public-site header: voice-call brand, homepage anchors, the shared
 * day/night switch, sign-in, and the request-demo CTA. The same component is
 * used by the homepage, landing pages, and demo pages so public navigation
 * never drifts between routes.
 */
export function PublicHeader() {
  const { theme, toggleTheme } = usePublicTheme();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [menuOpen]);

  const closeMenu = () => setMenuOpen(false);

  return (
    <header className={styles.header}>
      <Link href="/" className={styles.brand} aria-label={`${SITE_NAME} home`}>
        <span className={styles.brandMark} aria-hidden="true" />
        <span>{SITE_NAME}</span>
      </Link>
      <nav className={styles.nav} aria-label="Main navigation">
        <Link href="/#features">Use cases</Link>
        <Link href="/#demos">Live demos</Link>
        <Link href="/how-it-works">How it works</Link>
        <Link href="/#industries">For your business</Link>
        <Link href="/#integrations">Integrations</Link>
        <Link href="/pricing">Pricing</Link>
        <Link href="/blog">Blog</Link>
        <Link href="/ai-tools">AI Tools</Link>
      </nav>
      <div className={styles.headerActions}>
        <ThemeSwitch dark={theme === "night"} onToggle={toggleTheme} />
        <Link className={styles.signIn} href="/auth/signin">
          Sign in <ArrowUpRight size={13} />
        </Link>
        <Link className={styles.headerCta} href="/request-demo">
          Request demo <ArrowUpRight size={14} />
        </Link>
        <button
          ref={menuButtonRef}
          type="button"
          className={styles.menuToggle}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={menuOpen}
          aria-controls="public-mobile-nav"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
      </div>
      {menuOpen ? (
        <>
          <button
            type="button"
            className={styles.mobileNavScrim}
            aria-label="Close navigation"
            onClick={closeMenu}
          />
          <nav
            id="public-mobile-nav"
            className={styles.mobileNav}
            aria-label="Mobile navigation"
          >
            <p className={styles.mobileNavEyebrow}>EXPLORE 24x7 AI</p>
            <Link href="/#features" onClick={closeMenu}>
              Use cases
            </Link>
            <Link href="/#industries" onClick={closeMenu}>
              For your business
            </Link>
            <Link href="/#integrations" onClick={closeMenu}>
              Integrations
            </Link>
            <Link href="/#demos" onClick={closeMenu}>
              Live demos
            </Link>
            <Link href="/how-it-works" onClick={closeMenu}>
              How it works
            </Link>
            <Link href="/pricing" onClick={closeMenu}>
              Pricing
            </Link>
            <Link href="/blog" onClick={closeMenu}>
              Blog
            </Link>
            <Link href="/ai-tools" onClick={closeMenu}>
              AI Tools
            </Link>
            <Link href="/auth/signin" onClick={closeMenu}>
              Sign in
            </Link>
          </nav>
        </>
      ) : null}
    </header>
  );
}
