import Link from "next/link";
import { SITE_NAME } from "@/lib/site-config";
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
          <Link href="/auth/signin">Sign in</Link>
        </div>
      </div>
      <div className={styles.footerBottom}>
        <span>
          © {new Date().getFullYear()} {SITE_NAME}
        </span>
        <span>ALWAYS ON. ALWAYS YOURS.</span>
      </div>
    </footer>
  );
}
