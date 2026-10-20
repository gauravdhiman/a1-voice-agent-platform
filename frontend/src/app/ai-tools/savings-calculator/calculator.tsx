"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

const WEEKS_PER_MONTH = 4.33;

type BusinessSize = "solo" | "small" | "mid" | "large";

const SIZE_OPTIONS: { id: BusinessSize; label: string; closeRate: number; hourlyRate: number }[] = [
  { id: "solo", label: "Solo", closeRate: 0.25, hourlyRate: 30 },
  { id: "small", label: "2 to 10", closeRate: 0.2, hourlyRate: 30 },
  { id: "mid", label: "11 to 50", closeRate: 0.15, hourlyRate: 40 },
  { id: "large", label: "50+", closeRate: 0.1, hourlyRate: 40 },
];

function useAnimatedNumber(target: number, duration = 600): number {
  const [value, setValue] = useState(target);
  const currentRef = useRef(target);

  useEffect(() => {
    const from = currentRef.current;
    if (from === target) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const next = from + (target - from) * eased;
      currentRef.current = next;
      setValue(next);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        currentRef.current = target;
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}

function formatMoney(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

interface SliderFieldProps {
  id: string;
  label: string;
  hint: string;
  value: number;
  min: number;
  max: number;
  unit: string;
  onChange: (value: number) => void;
}

function SliderField({ id, label, hint, value, min, max, unit, onChange }: SliderFieldProps) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <label htmlFor={id} className="font-medium text-foreground">
          {label}
        </label>
        <span className="shrink-0 rounded-md bg-muted px-2 py-0.5 text-sm font-semibold text-foreground">
          {value} {unit}
        </span>
      </div>
      <p className="mt-0.5 text-sm text-muted-foreground">{hint}</p>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-3 w-full accent-primary"
      />
      <div className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

interface ToolPick {
  id: "receptionist" | "scheduling" | "chatbot" | "reviews";
  name: string;
  href: string;
  price: string;
  why: string;
  eligible: boolean;
  weight: number;
}

export function SavingsCalculator() {
  const [missedCalls, setMissedCalls] = useState(8);
  const [schedHours, setSchedHours] = useState(5);
  const [questionHours, setQuestionHours] = useState(4);
  const [reviewHours, setReviewHours] = useState(2);
  const [avgRevenue, setAvgRevenue] = useState(150);
  const [size, setSize] = useState<BusinessSize>("small");

  const sizeConfig = SIZE_OPTIONS.find((option) => option.id === size) ?? SIZE_OPTIONS[1];

  const math = useMemo(() => {
    const monthlyMissedCalls = missedCalls * WEEKS_PER_MONTH;
    const lostCustomers = monthlyMissedCalls * sizeConfig.closeRate;
    const monthlyLeak = lostCustomers * avgRevenue;

    const busyHoursWeekly = schedHours + questionHours + reviewHours;
    const busyHoursMonthly = busyHoursWeekly * WEEKS_PER_MONTH;
    const monthlyBusywork = busyHoursMonthly * sizeConfig.hourlyRate;

    const total = monthlyLeak + monthlyBusywork;
    return {
      monthlyMissedCalls,
      lostCustomers,
      monthlyLeak,
      busyHoursWeekly,
      busyHoursMonthly,
      monthlyBusywork,
      total,
      yearly: total * 12,
    };
  }, [missedCalls, schedHours, questionHours, reviewHours, avgRevenue, sizeConfig]);

  const animatedTotal = useAnimatedNumber(math.total);
  const animatedYearly = useAnimatedNumber(math.yearly);

  const stack = useMemo<ToolPick[]>(() => {
    const hourly = sizeConfig.hourlyRate;
    const candidates: ToolPick[] = [
      {
        id: "receptionist",
        name: "24x7 AI",
        href: "/ai-tools/ai-receptionists/24x7-ai",
        price: "From $49/mo, free plan available",
        why:
          missedCalls > 2
            ? `You miss about ${Math.round(math.monthlyMissedCalls)} calls a month. At your ${Math.round(sizeConfig.closeRate * 100)}% close rate that is roughly ${formatMoney(math.monthlyLeak)} in lost customers an AI receptionist could catch for you.`
            : "Missed calls are not your big leak right now, but an AI receptionist is the usual first win: every call answered, day and night.",
        eligible: missedCalls > 2,
        weight: math.monthlyLeak,
      },
      {
        id: "scheduling",
        name: "Cal.com",
        href: "/ai-tools/ai-scheduling/cal-com",
        price: "Free for 1 user",
        why:
          schedHours >= 2
            ? `Scheduling eats about ${Math.round(schedHours * WEEKS_PER_MONTH)} hours a month. A booking link gives most of that time back, and the free plan covers a solo calendar.`
            : "A booking link ends the back-and-forth of finding a time. It is free to start, so many owners set it up even before scheduling becomes a problem.",
        eligible: schedHours >= 2,
        weight: schedHours * WEEKS_PER_MONTH * hourly,
      },
      {
        id: "chatbot",
        name: "Chatbase",
        href: "/ai-tools/ai-chatbots/chatbase",
        price: "Free plan, paid from $40/mo",
        why:
          questionHours >= 2
            ? `You spend about ${Math.round(questionHours * WEEKS_PER_MONTH)} hours a month answering the same questions. A chatbot trained on your own pages answers them instantly, around the clock.`
            : "A website chatbot answers routine questions while you work on everything else. Worth it once the same questions start repeating.",
        eligible: questionHours >= 2,
        weight: questionHours * WEEKS_PER_MONTH * hourly,
      },
      {
        id: "reviews",
        name: "NiceJob",
        href: "/ai-tools/ai-review-management/nicejob",
        price: "From $75/mo, no contract",
        why:
          reviewHours >= 2
            ? `Chasing reviews takes about ${Math.round(reviewHours * WEEKS_PER_MONTH)} hours a month. NiceJob automates the asking and the follow-up, so reviews come in without the manual nagging.`
            : "Automated review requests keep new reviews coming in without anyone remembering to ask. A good third or fourth tool, once the bigger leaks are plugged.",
        eligible: reviewHours >= 2,
        weight: reviewHours * WEEKS_PER_MONTH * hourly,
      },
    ];

    const eligible = candidates
      .filter((candidate) => candidate.eligible)
      .sort((a, b) => b.weight - a.weight);
    const fallbackOrder = ["receptionist", "scheduling", "chatbot", "reviews"];
    const picked: ToolPick[] = [...eligible];
    for (const id of fallbackOrder) {
      if (picked.length >= 3) break;
      const candidate = candidates.find((c) => c.id === id);
      if (candidate && !picked.some((p) => p.id === id)) {
        picked.push(candidate);
      }
    }
    return picked.slice(0, 3);
  }, [missedCalls, schedHours, questionHours, reviewHours, math, sizeConfig]);

  return (
    <div>
      <div className="grid gap-6 lg:grid-cols-5">
        <section
          aria-label="Your numbers"
          className="rounded-xl border border-border bg-card p-6 shadow-sm lg:col-span-3"
        >
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            Tell us about your week
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Drag the sliders to roughly match your business. The results on the
            right update as you go. Rough numbers are fine.
          </p>

          <div className="mt-8 space-y-8">
            <SliderField
              id="missed-calls"
              label="Missed calls per week"
              hint="Calls that ring out, go to voicemail, or come in after hours."
              value={missedCalls}
              min={0}
              max={50}
              unit="/wk"
              onChange={setMissedCalls}
            />
            <SliderField
              id="sched-hours"
              label="Hours lost to scheduling each week"
              hint="The back-and-forth of finding a time, confirming, and rescheduling."
              value={schedHours}
              min={0}
              max={20}
              unit="hrs/wk"
              onChange={setSchedHours}
            />
            <SliderField
              id="question-hours"
              label="Hours answering the same questions each week"
              hint="Prices, hours, directions, policies: the questions you answer over and over."
              value={questionHours}
              min={0}
              max={20}
              unit="hrs/wk"
              onChange={setQuestionHours}
            />
            <SliderField
              id="review-hours"
              label="Hours chasing reviews each week"
              hint="Asking happy customers for a review and following up when they forget."
              value={reviewHours}
              min={0}
              max={20}
              unit="hrs/wk"
              onChange={setReviewHours}
            />
          </div>

          <div className="mt-8 grid gap-6 sm:grid-cols-2">
            <div>
              <label htmlFor="avg-revenue" className="font-medium text-foreground">
                Average revenue per customer
              </label>
              <p className="mt-0.5 text-sm text-muted-foreground">
                What one typical job or sale is worth to you.
              </p>
              <div className="relative mt-3">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  $
                </span>
                <input
                  id="avg-revenue"
                  type="number"
                  min={0}
                  step={10}
                  value={avgRevenue}
                  onChange={(event) =>
                    setAvgRevenue(Math.max(0, Number(event.target.value) || 0))
                  }
                  className="w-full rounded-md border border-border bg-background py-2 pl-7 pr-3 text-foreground"
                />
              </div>
            </div>

            <div>
              <span id="business-size-label" className="font-medium text-foreground">
                Business size
              </span>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Size changes the close rate and hourly cost we assume.
              </p>
              <div
                role="group"
                aria-labelledby="business-size-label"
                className="mt-3 grid grid-cols-4 overflow-hidden rounded-md border border-border"
              >
                {SIZE_OPTIONS.map((option) => {
                  const selected = size === option.id;
                  return (
                    <button
                      key={option.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setSize(option.id)}
                      className={
                        selected
                          ? "bg-primary px-2 py-2 text-sm font-semibold text-primary-foreground"
                          : "bg-background px-2 py-2 text-sm font-medium text-muted-foreground transition hover:bg-muted"
                      }
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <section
          aria-label="Your results"
          className="rounded-xl border border-border bg-card p-6 shadow-sm lg:col-span-2 lg:sticky lg:top-6 lg:self-start"
        >
          <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
            What this costs you
          </p>
          <p className="mt-2 text-4xl font-bold tracking-tight text-foreground">
            {formatMoney(animatedTotal)}
            <span className="text-lg font-medium text-muted-foreground"> /month</span>
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            About {formatMoney(animatedYearly)} a year.
          </p>

          <div className="mt-6 space-y-5 border-t border-border pt-6 text-sm">
            <div>
              <p className="font-semibold text-foreground">
                Missed calls: {formatMoney(math.monthlyLeak)}/month
              </p>
              <ul className="mt-2 space-y-1 text-muted-foreground">
                <li>
                  {missedCalls} missed calls a week x 4.33 weeks ={" "}
                  {Math.round(math.monthlyMissedCalls)} calls a month
                </li>
                <li>
                  x {Math.round(sizeConfig.closeRate * 100)}% close rate for a business
                  your size = {math.lostCustomers.toFixed(1)} lost customers
                </li>
                <li>
                  x {formatMoney(avgRevenue)} per customer = {formatMoney(math.monthlyLeak)}{" "}
                  lost
                </li>
              </ul>
            </div>

            <div>
              <p className="font-semibold text-foreground">
                Busywork: {formatMoney(math.monthlyBusywork)}/month
              </p>
              <ul className="mt-2 space-y-1 text-muted-foreground">
                <li>
                  {math.busyHoursWeekly} hours a week on scheduling, repeat questions,
                  and reviews
                </li>
                <li>
                  x 4.33 weeks = {Math.round(math.busyHoursMonthly)} hours a month
                </li>
                <li>
                  x {formatMoney(sizeConfig.hourlyRate)} an hour (your time, or staff
                  time) = {formatMoney(math.monthlyBusywork)}
                </li>
              </ul>
            </div>
          </div>

          <p className="mt-6 border-t border-border pt-4 text-xs text-muted-foreground">
            These are estimates to size the problem, not a promise. The full math
            is shown so you can sanity-check every line against your own
            experience.
          </p>
        </section>
      </div>

      <section aria-label="Your starter stack" className="mt-12">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">
          Your starter stack
        </h2>
        <p className="mt-2 max-w-2xl text-muted-foreground">
          Based on your numbers, these are the first three tools we would set up,
          in order. Each one targets your biggest leak first.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {stack.map((tool, index) => (
            <div
              key={tool.id}
              className="flex flex-col rounded-xl border border-border bg-card p-5 shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                  Step {index + 1}
                </span>
                <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-foreground">
                  {tool.price}
                </span>
              </div>
              <h3 className="mt-3 text-lg font-semibold text-foreground">{tool.name}</h3>
              {tool.id === "receptionist" ? (
                <p className="mt-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Full disclosure: we build this one
                </p>
              ) : null}
              <p className="mt-2 flex-1 text-sm text-muted-foreground">{tool.why}</p>
              <Link
                href={tool.href}
                className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                Read the honest review{" "}
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Not sure where to start? The tool in step 1 fixes your single biggest
          number above.
        </p>
      </section>
    </div>
  );
}
