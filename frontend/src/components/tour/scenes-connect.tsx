"use client";

import { Bell, CalendarCheck, Check, Mail, Phone } from "lucide-react";
import styles from "./platform-tour.module.css";
import { Beam, Cursor, SceneNote } from "./scene-ui";

/** Chapter 03 · Connect tools. */

const tools = [
  { name: "Business calendar", detail: "Google Calendar" },
  { name: "Email", detail: "Confirmations & follow-ups" },
  { name: "Records & CRM", detail: "Sheets · HubSpot" },
];

/** Step 1 — pick tools: the cursor clicks Connect on the calendar row,
 * which flips to Connected. */
export function ToolsPickScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      {tools.map((tool, index) => (
        <div
          key={tool.name}
          className={`${styles.mockTool} ${index === 0 ? styles.connectRow : styles.mockDim}`}
        >
          <span className={styles.mockToolIcon}>
            <CalendarCheck size={index === 0 ? 16 : 14} />
          </span>
          <span className={styles.mockToolText}>
            <strong>{tool.name}</strong>
            <small>{tool.detail}</small>
          </span>
          <span className={styles.mockPill}>
            {index === 0 ? (
              <>
                <Cursor motionClass={styles.cursorOnBtn} />
                <Check size={12} /> <span className={styles.pillFlip}>Connected</span>
              </>
            ) : (
              <>
                <Check size={12} /> Connect
              </>
            )}
          </span>
        </div>
      ))}
      <SceneNote>Connected during setup; change anytime</SceneNote>
    </div>
  );
}

/** Step 2 — the full flow with entities: a caller rings the agent, the
 * agent writes the booking to the calendar. */
export function BookingFlowScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.flowTrio}>
        <span className={styles.flowCaller}>
          <i>MG</i>
          <small>Maria G. calling…</small>
        </span>
        <Beam id="tour-book-call" />
        <span className={`${styles.beamNode} ${styles.beamCore}`}>
          <span className={styles.beamNodeIcon}>
            <Phone size={15} strokeWidth={1.75} />
          </span>
          <small>Front desk</small>
        </span>
        <Beam id="tour-book-cal" />
        <span className={styles.flowCal}>
          <CalendarCheck size={15} />
          <small>Thu 2:00 PM booked</small>
        </span>
      </div>
      <SceneNote>Checks availability to prevent double-booking</SceneNote>
    </div>
  );
}

/** Step 3 — confirmations and reminders go out on their own. */
export function ConfirmScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockTools}>
        <div className={`${styles.mockTool} ${styles.mockConnected} ${styles.delay1}`}>
          <span className={styles.mockToolIcon}>
            <Mail size={15} />
          </span>
          <span className={styles.mockToolText}>
            <strong>Confirmation sent</strong>
            <small>Maria G. · “See you Thursday at 2”</small>
          </span>
          <span className={styles.mockPill}>
            <Check size={12} /> Sent
          </span>
        </div>
        <div className={`${styles.mockTool} ${styles.mockConnected} ${styles.delay2}`}>
          <span className={styles.mockToolIcon}>
            <Bell size={15} />
          </span>
          <span className={styles.mockToolText}>
            <strong>Reminder set</strong>
            <small>Day-before text · morning-of call</small>
          </span>
          <span className={styles.mockPill}>
            <Check size={12} /> Set
          </span>
        </div>
      </div>
      <SceneNote>Fewer no-shows, without lifting a finger</SceneNote>
    </div>
  );
}
