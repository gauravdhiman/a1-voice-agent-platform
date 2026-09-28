"use client";

import { AudioLines, Check, Mic, Phone } from "lucide-react";
import styles from "./platform-tour.module.css";
import { Beam, CallCard, CheckBadge, Cursor, SceneNote, Waveform } from "./scene-ui";

/** Chapter 01 · Create. Each step is a timed event sequence:
 * type → move → click → confirm. */

/** Step 1 — instructions type out, then the cursor moves to the plain
 * Save button, clicks, and it fills blue with an "Agent saved" pill. */
export function CreateWriteScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>Business name</span>
        <span className={styles.mockField}>Maple Street Dental</span>
      </div>
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>Agent name</span>
        <span className={styles.mockField}>Front desk</span>
      </div>
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>Instructions · plain words</span>
        <span className={styles.mockArea}>
          <span className={styles.typeSlow}>
            Open Mon–Sat, 8 AM to 6 PM. Cleanings from $149. After hours,
            capture name, number, reason.
            <i className={styles.caret} />
          </span>
        </span>
      </div>
      <div className={styles.mockFoot}>
        <span className={`${styles.mockBtn} ${styles.fillAt32}`}>
          Save
          <Cursor motionClass={`${styles.cursorOnBtn} ${styles.cursorDelayLong}`} />
        </span>
        <span className={`${styles.mockSavedPill} ${styles.delaySave}`}>
          <Check size={12} /> Agent saved
        </span>
      </div>
    </div>
  );
}

/** Step 2 — cursor clicks Test call inside the agent card: an incoming
 * call rings, connects live, and the conversation appears line by line. */
export function CreateTestScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.agentTestCard}>
        <span className={styles.mockToolIcon}>
          <Mic size={16} />
        </span>
        <span className={styles.mockToolText}>
          <strong>Front desk</strong>
          <small>Maple Street Dental</small>
        </span>
        <span className={styles.mockBtn}>
          Test call
          <Cursor motionClass={styles.cursorOnBtn} />
        </span>
      </div>
      <div className={`${styles.swapWrap} ${styles.incomingIn}`}>
        <div className={styles.swapA}>
          <CallCard
            caller="Incoming test call…"
            detail="Dialing the agent"
            state="ringing"
          />
        </div>
        <div className={styles.swapB}>
          <CallCard
            caller="Front desk · test line"
            detail="Live test call · 00:23"
            state="live"
          />
        </div>
      </div>
      <div className={styles.transcript}>
        <p className={styles.tLate1}>
          <strong>Front desk:</strong> Thanks for calling Maple Street Dental. How can I help?
        </p>
        <p className={styles.tLate2}>
          <strong>Caller:</strong> Do you take new patients?
        </p>
        <p className={styles.tLate3}>
          <strong>Front desk:</strong> We do — want me to hold a slot for you?
        </p>
      </div>
      <div className={`${styles.sceneCenter} ${styles.delayWave}`}>
        <Waveform bars={9} />
      </div>
      <div className={`${styles.beamRow} ${styles.delayBeam}`}>
        <span className={styles.beamNode}>
          <span className={styles.beamNodeIcon}>
            <Phone size={15} strokeWidth={1.75} />
          </span>
          <small>Caller</small>
        </span>
        <Beam id="tour-testcall" />
        <span className={`${styles.beamNode} ${styles.beamCore}`}>
          <span className={styles.beamNodeIcon}>
            <AudioLines size={15} />
          </span>
          <small>24/7 front desk</small>
        </span>
      </div>
    </div>
  );
}

/** Step 3 — the toggle starts off and gray; cursor clicks Approve, the
 * button fills, the toggle flips green, and the live pill appears. */
export function CreateApproveScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.agentLiveCard}>
        <span className={styles.mockToolIcon}>
          <Mic size={16} />
        </span>
        <span className={styles.mockToolText}>
          <strong>Front desk</strong>
          <small>Maple Street Dental</small>
        </span>
        <span className={`${styles.enabledToggle} ${styles.toggleOn}`}>
          <i />
        </span>
      </div>
      <div className={styles.sceneCenter}>
        <span className={`${styles.mockBtn} ${styles.fillAt20}`}>
          Approve & go live
          <Cursor motionClass={`${styles.cursorOnBtn} ${styles.cursorDelayMid}`} />
        </span>
      </div>
      <div className={`${styles.sceneCenter} ${styles.delayCheck}`}>
        <CheckBadge label="Live, able to answer now" />
      </div>
      <SceneNote>Approved by you · live in about 48 hours</SceneNote>
    </div>
  );
}
