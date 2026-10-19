import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { SITE_AI_SERVICES_URL, SITE_NAME } from "@/lib/site-config";
import styles from "./public-theme.module.css";

/** Shared public-site footer: brand, tagline, and funnel links. */
export function PublicFooter() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerTop}>
        <Link className={styles.brand} href="/">
          {SITE_NAME}
          <span className={styles.statusDot} />
        </Link>
        <p>Always there for your business.</p>
        <div className={styles.footerLinks}>
          <Link href="/#demos">Live demos</Link>
          <Link href="/#pricing">Pricing</Link>
          <Link href="/blog">Blog</Link>
          <Link href="/auth/signin">Sign in</Link>
          <Link href="/terms">Terms &amp; Conditions</Link>
          <Link href="/privacy">Privacy Policy</Link>
        </div>
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
        <span>ALWAYS ON. ALWAYS YOURS.</span>
      </div>
    </footer>
  );
}
