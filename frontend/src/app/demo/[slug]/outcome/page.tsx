"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
  Clock3,
  ContactRound,
  ExternalLink,
  Loader2,
  MailCheck,
  RefreshCw,
  ShieldCheck,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { DemoFeedback } from "@/components/demo/demo-feedback";
import { OutcomeInterest } from "@/components/demo/outcome-interest";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicFooter } from "@/components/public-theme/public-footer";
import pt from "@/components/public-theme/public-theme.module.css";
import {
  demoPublicService,
  type DemoOutcome,
  type DemoOutcomeAction,
} from "@/services/demo-public-service";

const FIELD_LABELS: Record<string, string> = {
  caller_name: "Name",
  caller_email: "Email",
  caller_phone: "Phone",
  service_needed: "Service needed",
  issue_summary: "Issue summary",
  property_address: "Service address",
  urgency: "Urgency",
  preferred_callback_window: "Preferred callback",
  purpose: "Appointment type",
  start_time: "Start time",
  duration_minutes: "Duration",
  notes: "Notes",
};

function labelForField(name: string): string {
  return (
    FIELD_LABELS[name] ||
    name
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

function valueForField(
  name: string,
  value: string | number | boolean | null,
): string {
  if (value === null || value === "") return "—";
  if (name === "duration_minutes" && typeof value === "number") {
    return `${value} minutes`;
  }
  if (name === "start_time" && typeof value === "string") {
    const parsed = new Date(value);
    if (!Number.isNaN(parsed.getTime())) {
      return new Intl.DateTimeFormat("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(parsed);
    }
  }
  return String(value);
}

/** Where the result landed, in the business owner's own words. */
function destinationLabel(action: DemoOutcomeAction): string {
  if (action.provider === "google_sheets") return "your spreadsheet";
  if (action.provider === "hubspot") return "your CRM";
  if (action.provider === "google_calendar") return "your business calendar";
  if (action.provider === "gmail" || action.provider === "resend")
    return "your inbox";
  return "your business tools";
}

function providerLabel(action: DemoOutcomeAction): string {
  if (action.provider === "google_sheets") return "Google Sheets";
  if (action.provider === "hubspot") return "HubSpot CRM";
  if (action.provider === "gmail") return "Gmail";
  if (action.provider === "resend") return "Resend";
  return "Google Calendar";
}

function actionTitle(action: DemoOutcomeAction): string {
  if (action.action_type === "email_delivery") {
    if (action.status === "succeeded") return "Email confirmation sent";
    if (action.status === "pending") return "Email waiting to send";
    return "Email not sent";
  }
  if (action.action_type === "lead_capture") {
    if (action.status === "succeeded") return "New service request saved";
    if (action.status === "pending") return "Service request waiting";
    return "Service request not saved";
  }
  if (action.status === "succeeded") return "Appointment booked";
  if (action.status === "pending") return "Appointment waiting";
  return "Appointment not booked";
}

function outcomeHeading(outcome: DemoOutcome): [string, string] {
  if (outcome.status === "completed") {
    return ["That call just did", "real work."];
  }
  if (outcome.status === "needs_attention") {
    return ["Almost done.", "One thing needs a look."];
  }
  return ["Nothing got saved", "on this call."];
}

function actionIcon(action: DemoOutcomeAction) {
  if (action.action_type === "lead_capture") return ContactRound;
  if (action.action_type === "email_delivery") return MailCheck;
  return CalendarDays;
}

function safeHttpsUrl(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const parsed = new URL(value.trim());
    if (
      parsed.protocol !== "https:" ||
      !parsed.hostname ||
      parsed.username ||
      parsed.password
    ) {
      return null;
    }
    return parsed.toString();
  } catch {
    return null;
  }
}

function statusCopy(outcome: DemoOutcome): {
  title: string;
  description: string;
  tone: string;
} {
  if (outcome.status === "completed") {
    return {
      title: "Confirmed by your tools",
      description:
        "Every result below really happened on the call and was confirmed back. Nothing here is a mockup.",
      tone: "border-emerald-500/30 bg-emerald-500/10 text-emerald-900 dark:text-emerald-100",
    };
  }
  if (outcome.status === "needs_attention") {
    return {
      title: "Needs your attention",
      description:
        "Here is what got captured and exactly where it stopped. Anything unconfirmed is labeled as such.",
      tone: "border-amber-500/30 bg-amber-500/10 text-amber-900 dark:text-amber-100",
    };
  }
  return {
    title: "No result to show",
    description:
      "The call ended before anything was saved. Give the agent the final details and try again.",
    tone: "border-white/10 bg-white/5 text-slate-600 dark:text-slate-300",
  };
}

function statusPill(action: DemoOutcomeAction): {
  label: string;
  className: string;
} {
  if (action.status === "succeeded") {
    return {
      label: "Done",
      className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
    };
  }
  if (action.status === "pending") {
    return {
      label: "Waiting",
      className: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
    };
  }
  return {
    label: "Didn't go through",
    className: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
  };
}

function statusTile(action: DemoOutcomeAction): string {
  if (action.status === "succeeded")
    return "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300";
  if (action.status === "pending")
    return "bg-amber-500/15 text-amber-600 dark:text-amber-300";
  return "bg-rose-500/15 text-rose-600 dark:text-rose-300";
}

function OutcomeActionCard({ action }: { action: DemoOutcomeAction }) {
  const Icon = actionIcon(action);
  const isSuccess = action.status === "succeeded";
  const pill = statusPill(action);
  const configuredResultUrl = isSuccess
    ? action.action_type === "email_delivery"
      ? null
      : safeHttpsUrl(action.public_result_url)
    : null;
  const resultLinkLabel = `Open ${providerLabel(action)} result`;
  const capturedFieldEntries = Object.entries(action.captured_fields);
  return (
    <div className={pt.panel} style={{ padding: 28, overflow: "hidden" }}>
      <div className="flex items-start gap-4">
        <div
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${statusTile(action)}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3
              style={{
                fontSize: 20,
                fontWeight: 400,
                letterSpacing: "-0.03em",
              }}
            >
              {actionTitle(action)}
            </h3>
            <span
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${pill.className}`}
            >
              {pill.label}
            </span>
          </div>
          <p className="mt-1.5 text-sm" style={{ color: "var(--public-muted)" }}>
            Saved to {destinationLabel(action)}{" "}
            <span style={{ opacity: 0.75 }}>via {providerLabel(action)}</span>
          </p>
        </div>
      </div>

      {capturedFieldEntries.length > 0 ? (
        <div className="mt-6">
          <p className={pt.smallDetail}>WHAT WAS COLLECTED</p>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            {capturedFieldEntries.map(([name, value]) => (
              <div
                key={name}
                className="rounded-xl border px-3 py-2.5"
                style={{ borderColor: "var(--line)" }}
              >
                <dt className="text-xs" style={{ color: "var(--public-muted)" }}>
                  {labelForField(name)}
                </dt>
                <dd className="mt-1 whitespace-pre-wrap break-words text-sm font-medium">
                  {valueForField(name, value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      <div
        className="mt-6 flex items-start gap-2.5 border-t pt-5 text-sm"
        style={{ borderColor: "var(--line)" }}
      >
        {isSuccess ? (
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
        ) : (
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
        )}
        <div>
          <p className="font-medium">What your tool confirmed</p>
          <p className="mt-0.5" style={{ color: "var(--public-muted)" }}>
            {String(
              action.provider_result.message ||
                (isSuccess
                  ? "The tool confirmed it saved everything."
                  : "The tool did not confirm anything was saved."),
            )}
          </p>
          {configuredResultUrl && (
            <Button asChild size="sm" variant="outline" className="mt-3">
              <a href={configuredResultUrl} target="_blank" rel="noreferrer">
                <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                {resultLinkLabel}
              </a>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DemoOutcomePage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const searchParams = useSearchParams();
  const receiptToken = searchParams.get("token");
  const [outcome, setOutcome] = React.useState<DemoOutcome | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [attempt, setAttempt] = React.useState(0);

  const loadOutcome = React.useCallback(async () => {
    if (!receiptToken) {
      setError("This summary link is missing its secure session token.");
      setLoading(false);
      return;
    }
    try {
      const next = await demoPublicService.getDemoOutcome(slug, receiptToken);
      setOutcome(next);
      setError(null);
      if (next.status === "no_action" && attempt < 4) {
        setAttempt((current) => current + 1);
      }
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Demo outcome is unavailable",
      );
    } finally {
      setLoading(false);
    }
  }, [attempt, receiptToken, slug]);

  React.useEffect(() => {
    void loadOutcome();
  }, [loadOutcome]);

  React.useEffect(() => {
    if (
      !outcome ||
      outcome.status !== "no_action" ||
      attempt === 0 ||
      attempt > 4
    ) {
      return;
    }
    const timer = window.setTimeout(() => void loadOutcome(), 1200);
    return () => window.clearTimeout(timer);
  }, [attempt, loadOutcome, outcome]);

  if (loading && !outcome) {
    return (
      <PublicThemeRoot>
        <div className={pt.page}>
          <div className={pt.glow} aria-hidden="true" />
          <PublicHeader />
          <div
            className="flex flex-1 items-center justify-center p-6"
            style={{ position: "relative" }}
          >
            <div
              className="flex items-center gap-3 rounded-full border px-4 py-3 text-sm"
              style={{
                borderColor: "var(--line)",
                background: "var(--panel)",
                color: "var(--public-muted)",
              }}
            >
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              Putting your call summary together…
            </div>
          </div>
        </div>
      </PublicThemeRoot>
    );
  }

  if (error && !outcome) {
    return (
      <PublicThemeRoot>
        <div className={pt.page}>
          <div className={pt.glow} aria-hidden="true" />
          <PublicHeader />
          <div
            className="flex flex-1 items-center justify-center p-6 text-center"
            style={{ position: "relative" }}
          >
            <div className="flex max-w-md flex-col items-center gap-5">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-500/15 text-rose-600 dark:text-rose-300">
                <AlertCircle className="h-7 w-7" />
              </div>
              <div>
                <h1
                  className={pt.title}
                  style={{ fontSize: "clamp(28px, 4vw, 40px)" }}
                >
                  Summary unavailable
                </h1>
                <p className="mt-2 text-sm" style={{ color: "var(--public-muted)" }}>
                  {error}
                </p>
              </div>
              <Button asChild variant="outline">
                <Link href={`/demo/${encodeURIComponent(slug)}`}>
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to demo
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </PublicThemeRoot>
    );
  }

  if (!outcome) return null;
  const copy = statusCopy(outcome);
  return (
    <PublicThemeRoot>
      <div className={pt.page}>
        <div className={pt.glow} aria-hidden="true" />
        <PublicHeader />

        <main className={pt.outcomeLayout} style={{ position: "relative" }}>
          <section className={pt.outcomeIntro} aria-label="Call summary">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className={pt.eyebrow}>
                <span className={pt.statusDot} />
                YOUR CALL, PROVEN
              </p>
              <p className={pt.smallDetail}>
                <ShieldCheck
                  className="mr-1.5 inline h-3.5 w-3.5"
                  style={{ color: "var(--public-accent)" }}
                />
                PRIVATE CALL SUMMARY · EXPIRES IN 24 HOURS
              </p>
            </div>
            <h1
              className={pt.title}
              style={{ fontSize: "clamp(38px, 5vw, 64px)", marginTop: 24 }}
            >
              {outcomeHeading(outcome)[0]} <br />
              <span>{outcomeHeading(outcome)[1]}</span>
            </h1>
            <p className={pt.lede} style={{ marginTop: 20, maxWidth: 620 }}>
              {outcome.status === "completed"
                ? `${outcome.agent_name} handled it end to end. Everything below really happened in business tools, not a mockup.`
                : outcome.status === "needs_attention"
                  ? "Here is what got collected and exactly where it stopped. Anything unconfirmed is labeled as such."
                  : `The call ended before ${outcome.agent_name} could save anything. Give the final details and try again.`}
            </p>

            <div
              className={`mt-8 rounded-2xl border p-5 ${copy.tone}`}
              style={{ position: "relative" }}
            >
              <div className="flex items-start gap-3">
                {outcome.status === "completed" ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
                ) : (
                  <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                )}
                <div>
                  <p className="font-semibold">{copy.title}</p>
                  <p className="mt-1 text-sm opacity-80">
                    {outcome.organization_name || "Demo business"}
                    {outcome.actions.length
                      ? ` · ${outcome.actions.length} result${outcome.actions.length === 1 ? "" : "s"} saved`
                      : ""}
                  </p>
                  {outcome.actions.length ? (
                    <a
                      href="#call-results"
                      className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium underline underline-offset-4 opacity-90 hover:opacity-100"
                    >
                      See what was saved
                      <ArrowDown className="h-3.5 w-3.5" />
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          </section>

          <aside
            className={pt.outcomeFeedbackColumn}
            aria-label="Feedback and setup request"
          >
            <div
              className={pt.outcomeFeedbackSticky}
              data-testid="outcome-feedback-sticky"
            >
              <div className={pt.panel} style={{ padding: 24 }}>
                <p className={pt.eyebrow}>YOUR TURN · 30 SECONDS</p>
                <div className="mt-4">
                  <DemoFeedback demoSlug={slug} receiptToken={receiptToken} />
                </div>
                <div
                  className="my-6 border-t"
                  style={{ borderColor: "var(--line)" }}
                />
                <OutcomeInterest demoSlug={slug} />
              </div>
            </div>
          </aside>

          <section
            className={pt.outcomeDetails}
            aria-label="Call details and results"
          >
            {outcome.actions.length === 0 && (
              <section className="w-full">
                <div className={pt.panel} style={{ padding: "48px 24px" }}>
                  <div className="flex flex-col items-center text-center">
                    <div
                      className="flex h-14 w-14 items-center justify-center rounded-2xl"
                      style={{
                        background: "var(--panel)",
                        border: "1px solid var(--line)",
                        color: "var(--public-accent)",
                      }}
                    >
                      <Wrench className="h-7 w-7" />
                    </div>
                    <h2
                      className={pt.title}
                      style={{ fontSize: 24, marginTop: 20 }}
                    >
                      Nothing got saved on this call
                    </h2>
                    <p
                      className="mt-2 max-w-md text-sm leading-6"
                      style={{ color: "var(--public-muted)" }}
                    >
                      Let the agent confirm the final details before hanging up.
                      This page only shows results that tools confirmed.
                    </p>
                    <Link
                      className={pt.primary}
                      style={{ marginTop: 24 }}
                      href={`/demo/${encodeURIComponent(slug)}`}
                    >
                      <RefreshCw size={16} />
                      Try the call again
                    </Link>
                  </div>
                </div>
              </section>
            )}

            {outcome.actions.length ? (
              <section
                id="call-results"
                className="w-full"
                style={{ scrollMarginTop: 90 }}
                aria-label="Call results"
              >
                <h2
                  className={pt.title}
                  style={{ fontSize: "clamp(26px, 3vw, 36px)" }}
                >
                  What {outcome.agent_name} <span>saved for you</span>
                </h2>
                <div className="mt-6 flex flex-col gap-5">
                  {outcome.actions.map((action) => (
                    <OutcomeActionCard key={action.id} action={action} />
                  ))}
                </div>
              </section>
            ) : null}

            <section className="w-full">
              <div className={pt.panel} style={{ padding: 28 }}>
                <p className={pt.eyebrow}>IF THIS RAN YOUR BUSINESS</p>
                <ul
                  style={{
                    marginTop: 20,
                    display: "flex",
                    flexDirection: "column",
                    gap: 14,
                    padding: 0,
                    listStyle: "none",
                    fontSize: 14,
                  }}
                >
                  <li className="flex items-center gap-3">
                    <CheckCircle2
                      size={17}
                      style={{ color: "var(--public-accent)", flexShrink: 0 }}
                    />
                    No missed calls, even after hours and weekends.
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2
                      size={17}
                      style={{ color: "var(--public-accent)", flexShrink: 0 }}
                    />
                    Bookings land straight in your calendar while you work.
                  </li>
                  <li className="flex items-center gap-3">
                    <CheckCircle2
                      size={17}
                      style={{ color: "var(--public-accent)", flexShrink: 0 }}
                    />
                    Every caller captured with details, ready for follow-up.
                  </li>
                </ul>
              </div>
            </section>

            <section className="w-full">
              <div>
                <Link className={pt.textLink} href="/request-demo">
                  Prefer the full demo form? Request a demo{" "}
                  <ArrowUpRight size={16} />
                </Link>
              </div>
            </section>

            <footer
              className="flex w-full flex-col gap-3 border-t pt-5 text-xs text-[var(--public-muted)] sm:flex-row sm:items-center sm:justify-between"
              style={{ borderColor: "var(--line)" }}
            >
              <span className="inline-flex items-center gap-1.5">
                <Clock3 className="h-3.5 w-3.5" /> Summary expires after 24 hours
              </span>
              <Link
                href={`/demo/${encodeURIComponent(slug)}`}
                className="inline-flex items-center gap-1.5 hover:opacity-80"
              >
                <ArrowLeft className="h-3.5 w-3.5" /> Back to demo
              </Link>
            </footer>
          </section>
        </main>

        <PublicFooter />
      </div>
    </PublicThemeRoot>
  );
}
