import { ArrowDown } from "lucide-react";
import styles from "./scroll-cue.module.css";

export interface ScrollCueProps {
  /** Fragment link for the next section on the current page. */
  href: `#${string}`;
  /** Short instruction shown beside the arrow. */
  label: string;
  /** Optional page-specific placement or sizing class. */
  className?: string;
}

/** Small, keyboard-accessible prompt that points visitors to the next section. */
export function ScrollCue({ href, label, className }: ScrollCueProps) {
  return (
    <a
      className={`${styles.cue}${className ? ` ${className}` : ""}`}
      href={href}
    >
      <span className={styles.arrow} aria-hidden="true">
        <ArrowDown size={14} />
      </span>
      <span>{label}</span>
    </a>
  );
}
