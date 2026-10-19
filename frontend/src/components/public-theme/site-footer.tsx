"use client";

import Link from "next/link";
import { ArrowUpRight, Moon, MoveUpRight, Sun } from "lucide-react";
import { usePublicTheme } from "./public-theme-context";
import {
  SITE_AI_SERVICES_URL,
  SITE_NAME,
  SITE_SALES_EMAIL,
} from "@/lib/site-config";
import styles from "../home/home-page.module.css";

/**
 * Shared site footer — the canonical footer from the homepage, extracted so
 * the blog (and other public pages) render the exact same footer, including
 * its mobile-optimized responsive styles.
 */
export function SiteFooter() {
  const { theme, toggleTheme } = usePublicTheme();

  return (
    <footer className={styles.footer}>
      <div className={styles.footerTop}>
        <Link className={styles.brand} href="/">
          {SITE_NAME}
          <span className={styles.statusDot} />
        </Link>
        <p>Always there for your business.</p>
        <a href={`mailto:${SITE_SALES_EMAIL}`}>
          Say hello <MoveUpRight size={15} />
        </a>
      </div>
      <div className={styles.footerBottom}>
        <span>
          © {new Date().getFullYear()} {SITE_NAME}
        </span>
        <span className={styles.footerAttribution}>
          Built by an AI solutions company:{" "}
          <a
            href={SITE_AI_SERVICES_URL}
            target="_blank"
            rel="noreferrer"
            aria-label="Visit Cognitive Entities LLC"
          >
            Cognitive Entities LLC <ArrowUpRight size={12} aria-hidden="true" />
          </a>
        </span>
        <div>
          <a href="#demos">Live demos</a>
          <a href="#pricing">Pricing</a>
          <Link href="/auth/signin">Sign in</Link>
          <button onClick={toggleTheme}>
            {theme === "night" ? <Sun size={13} /> : <Moon size={13} />}{" "}
            {theme === "night" ? "Try the day shift" : "Try the night shift"}
          </button>
        </div>
        <span>ALWAYS ON. ALWAYS YOURS.</span>
      </div>
    </footer>
  );
}
