"use client";

import { AudioLines, Check, Copy, Globe, Mic, Phone } from "lucide-react";
import styles from "./platform-tour.module.css";
import { Beam, CallCard, Cursor, SceneNote } from "./scene-ui";

/** Chapter 02 · Answer everywhere. Each scene isolates its own story. */

/** Step 1 — number only: type it, save it, watch a call come in and get
 * answered. No website elements anywhere in this scene. */
export function NumberScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>Business phone number</span>
        <span className={`${styles.mockField} ${styles.mockMono}`}>
          <span className={styles.typeDigits}>(555) 014-2200</span>
          <i className={styles.caret} />
        </span>
      </div>
      <div className={styles.mockFoot}>
        <span className={`${styles.mockBtn} ${styles.fillAt32}`}>
          Save number
          <Cursor motionClass={`${styles.cursorOnBtn} ${styles.cursorDelayLong}`} />
        </span>
        <span className={`${styles.mockSavedPill} ${styles.delaySave}`}>
          Number saved ✓
        </span>
      </div>
      <div className={`${styles.swapWrap} ${styles.delayCall}`}>
        <div className={styles.ringLate}>
          <CallCard
            caller="Incoming call…"
            detail="(555) 014-2200 · ringing"
            state="ringing"
          />
        </div>
        <div className={styles.liveLate}>
          <CallCard
            caller="Front desk"
            detail="Answered in 3s · handling it"
            state="live"
          />
        </div>
      </div>
    </div>
  );
}

/** Step 2 — embed in a natural copy → paste → publish flow: copy the
 * snippet up top, paste it into the website panel below, save, and the
 * voice button lights up. */
export function EmbedScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>Website voice button</span>
        <span className={`${styles.mockField} ${styles.mockMono} ${styles.mockCode}`}>
          &lt;script src=“…/voice.js” data-agent=“front-desk”&gt;
        </span>
      </div>
      <div className={styles.mockFoot}>
        <span className={styles.mockBtn}>
          <Copy size={13} /> Copy snippet
          <Cursor motionClass={styles.cursorOnBtn} />
        </span>
        <span className={`${styles.mockSavedPill} ${styles.delay17}`}>
          <Check size={12} /> Copied
        </span>
        <span className={`${styles.hintPill} ${styles.delayHint}`}>
          Paste it on your website ↓
        </span>
      </div>
      <div className={styles.pasteSlot}>
        <Cursor motionClass={`${styles.cursorOnBtn} ${styles.cursorLate}`} />
        <span className={styles.pasteEmpty}>Waiting for the snippet…</span>
        <span className={`${styles.mockField} ${styles.mockMono} ${styles.mockCode} ${styles.pasteCode}`}>
          &lt;script src=“…/voice.js” data-agent=“front-desk”&gt;
        </span>
        <span className={`${styles.mockSavedPill} ${styles.delayLive}`}>Saved ✓</span>
      </div>
      <div className={`${styles.mockBrowser} ${styles.delayLive}`}>
        <span className={styles.mockBrowserDots}>
          <i />
          <i />
          <i />
        </span>
        <span className={`${styles.mockSiteBtn} ${styles.mockGlowIn}`}>
          <Mic size={13} /> Talk to us
        </span>
        <small>maple-street-dental.com</small>
      </div>
    </div>
  );
}

/** Step 3 — both lines ring one agent: inbound flows from the website
 * and from the phone number into the front desk. */
export function BothScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.beamRow}>
        <span className={styles.beamNode}>
          <span className={styles.beamNodeIcon}>
            <Globe size={15} />
          </span>
          <small>Website visitor calling…</small>
        </span>
        <Beam id="tour-both" />
        <span className={`${styles.beamNode} ${styles.beamCore}`}>
          <span className={styles.beamNodeIcon}>
            <AudioLines size={15} />
          </span>
          <small>Front desk</small>
        </span>
        <Beam id="tour-both2" reverse />
        <span className={styles.beamNode}>
          <span className={styles.beamNodeIcon}>
            <Phone size={15} strokeWidth={1.75} />
          </span>
          <small>(555) 014-2200 calling…</small>
        </span>
      </div>
      <SceneNote>Same agent answers both lines — at the same time</SceneNote>
    </div>
  );
}
