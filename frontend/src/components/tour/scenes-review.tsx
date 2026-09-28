"use client";

import { Check, Clock, Download, Play } from "lucide-react";
import styles from "./platform-tour.module.css";
import { Cursor, SceneNote, Waveform } from "./scene-ui";

/** Chapter 05 · Review calls. */

const calls = [
  { time: "7:42 PM", caller: "Maria G.", source: "Phone", status: "Booked", duration: "2:14" },
  { time: "6:05 PM", caller: "Sam R.", source: "Phone", status: "Lead flagged", duration: "3:01" },
  { time: "4:18 PM", caller: "Priya K.", source: "Web embed", status: "Booked", duration: "1:47" },
];

/** Step 1 — the cursor picks the Phone filter, which activates. */
export function LogScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockFilters}>
        <span>All sources</span>
        <span className={styles.filterFlip}>
          Phone
          <Cursor motionClass={styles.cursorOnEdge} />
        </span>
        <span>Web embed</span>
      </div>
      <div className={styles.mockTable}>
        {calls.slice(0, 2).map((call) => (
          <div key={call.caller} className={styles.mockCallRow}>
            <span className={styles.mockCallMain}>
              <strong>{call.caller}</strong>
              <small>
                {call.time} · {call.duration}
              </small>
            </span>
            <span className={styles.mockSource}>{call.source}</span>
            <span className={styles.mockStatus}>{call.status}</span>
          </div>
        ))}
      </div>
      <SceneNote>When it came in · through what source · what happened</SceneNote>
    </div>
  );
}

/** Step 2 — the recording plays with waveform and transcript lines. */
export function PlaybackScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.mockTable}>
        <div className={styles.mockCallRow}>
          <span className={styles.mockCallMain}>
            <strong>Maria G.</strong>
            <small>7:42 PM · 2:14</small>
          </span>
          <span className={styles.mockSource}>Phone</span>
          <span className={styles.mockStatus}>Booked</span>
        </div>
        <div className={styles.playerPane}>
          <span className={styles.playerBtn}>
            <Play size={12} fill="currentColor" />
          </span>
          <span className={styles.playerTrack}>
            <i className={styles.mockProgress} />
          </span>
          <Waveform bars={9} />
        </div>
        <div className={styles.transcript}>
          <p className={styles.tLine1}>
            <strong>Maria:</strong> What are your prices for a deep cleaning?
          </p>
          <p className={styles.tLine2}>
            <strong>Front desk:</strong> Deep cleanings start at $149…
          </p>
        </div>
      </div>
    </div>
  );
}

/** Step 3 — the month in one report card: kept 30 days, downloadable. */
export function KeepScene() {
  return (
    <div className={styles.scene} aria-hidden="true">
      <div className={styles.reportCard}>
        <span className={styles.mockLabel}>This week · Maple Street Dental</span>
        <div className={styles.reportStats}>
          <span>
            <strong>34</strong>
            <small>calls</small>
          </span>
          <span>
            <strong>31</strong>
            <small>booked</small>
          </span>
          <span>
            <strong>3</strong>
            <small>flagged</small>
          </span>
        </div>
        <span className={styles.mockBtn}>
          <Download size={13} /> Download report
          <Cursor motionClass={styles.cursorOnBtn} />
        </span>
      </div>
      <div className={styles.mockFootRow}>
        <span className={styles.mockRetention}>
          <Clock size={12} /> Recordings kept 30 days
        </span>
        <span className={styles.mockDoneTick}>
          <Check size={12} /> Reviewed
        </span>
      </div>
    </div>
  );
}
