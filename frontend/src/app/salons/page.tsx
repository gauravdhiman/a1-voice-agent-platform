import type { Metadata } from "next";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Receptionist for Salons and Spas | Fill Every Chair",
  description:
    "Stop losing bookings to voicemail. 24x7 AI answers every salon call, books appointments straight to your calendar, and sends reminders that cut no-shows. Live in 48 hours.",
  alternates: { canonical: `${SITE_URL}/salons` },
};

const content: IndustryPageContent = {
  slug: "salons",
  headline: "Fully booked chairs, zero phone tag",
  subhead:
    "24x7 AI answers when your stylists are with clients and the shop is closed. It books cuts, color, and treatments straight to your calendar, takes new-client details, and confirms so clients actually show up.",
  pains: [
    "Calls ring out while every stylist is with a client, and the caller books across the street.",
    "Your mornings disappear into rescheduling texts instead of welcoming walk-ins.",
    "No-shows leave paid-for chairs empty because reminders depend on someone remembering.",
  ],
  outcomes: [
    {
      title: "Cuts, color, and treatments, booked to your calendar",
      description:
        "Checks real availability, confirms the slot with the caller, and writes the booking where your team sees it.",
    },
    {
      title: "New-client intake, handled warmly",
      description:
        "Greets first-timers, captures their details and what they want, and books them with the right stylist.",
    },
    {
      title: "Services and prices, answered instantly",
      description:
        "Treatments, durations, prices, parking, and policies, answered from your info, day or night.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts your team with the full context.",
    },
  ],
  demoSlug: "pleasant-pediatric-appointments",
  demoName: "Alex",
  demoBlurb:
    "Try booking a visit with Alex and watch the calendar update. Your version knows your services, stylists, and chairs.",
  faqs: [
    {
      question: "Can it handle reschedules and cancellations fairly?",
      answer:
        "Yes. You define the rules during setup, such as how late a client can move a booking, and the agent follows them on every call while keeping your calendar accurate.",
    },
    {
      question: "How do service or price changes reach the agent?",
      answer:
        "Tell us any time. We update your treatments, durations, and prices with you, then run test calls until you approve how it sounds.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, calendar, services, and reminder flow with you on a setup call, run test bookings until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** Salon and spa vertical landing page (SEO: AI receptionist for salons). */
export default function SalonsPage() {
  return <IndustryPage content={content} />;
}
