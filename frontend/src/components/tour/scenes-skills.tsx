"use client";

import { Mic, Sparkles } from "lucide-react";
import styles from "./platform-tour.module.css";
import { Beam, CallCard, Cursor, SceneNote } from "./scene-ui";

/** Chapter 04 · Teach skills. */

/** Step 1 — write the rule in plain words and save the skill. */
export function SkillWriteScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>Skill name</span>
        <span className={styles.mockField}>After-hours intake</span>
      </div>
      <div className={styles.mockRow}>
        <span className={styles.mockLabel}>The rule · plain words</span>
        <span className={styles.mockArea}>
          <span className={styles.mockTyped}>
            After 6 PM, capture name, number, reason. Flag urgent leaks.
            <i className={styles.caret} />
          </span>
        </span>
      </div>
      <div className={styles.mockFoot}>
        <span className={`${styles.mockBtn} ${styles.fillAt20}`}>
          Save skill
          <Cursor motionClass={`${styles.cursorOnBtn} ${styles.cursorDelayMid}`} />
        </span>
        <span className={`${styles.mockSavedPill} ${styles.delayCheck}`}>
          Skill saved ✓
        </span>
      </div>
    </div>
  );
}

/** Step 2 — the skill chip flies onto the agent card and attaches. */
export function SkillAttachScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.attachStage}>
        <span className={`${styles.mockChip} ${styles.chipFly}`}>
          <Sparkles size={12} /> After-hours intake
        </span>
        <span className={styles.attachArrow} aria-hidden="true">
          ↓
        </span>
        <span className={styles.agentSlot}>
          <span className={styles.mockToolIcon}>
            <Mic size={15} />
          </span>
          <span className={styles.mockToolText}>
            <strong>Front desk</strong>
            <small>1 skill attached</small>
          </span>
          <span className={`${styles.mockToggle} ${styles.delay1}`} data-on="true">
            <i />
          </span>
        </span>
      </div>
      <SceneNote>One click to attach · edit once, every agent follows</SceneNote>
    </div>
  );
}

/** Step 3 — on a live call the skill applies itself, over a beam to the
 * captured outcome. */
export function SkillFollowedScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <CallCard
        caller="Sam R. · 9:14 PM"
        detail="Live call · after hours"
        state="live"
      />
      <div className={`${styles.skillApplied} ${styles.delay1}`}>
        <Sparkles size={13} />
        After-hours intake applied
      </div>
      <Beam id="tour-skill" label="name, number, reason captured…" />
      <div className={`${styles.mockTool} ${styles.mockConnected} ${styles.delay2}`}>
        <span className={styles.mockToolText}>
          <strong>Urgent job flagged</strong>
          <small>Sent to you in seconds</small>
        </span>
      </div>
    </div>
  );
}
