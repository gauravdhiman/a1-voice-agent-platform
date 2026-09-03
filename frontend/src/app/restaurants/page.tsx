import type { Metadata } from "next";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Phone Answering for Restaurants",
  description:
    "Stop missing reservations during the dinner rush. 24x7 AI takes bookings, party requests, and hours questions — live in 48 hours.",
  alternates: { canonical: `${SITE_URL}/restaurants` },
};

const content: IndustryPageContent = {
  slug: "restaurants",
  headline: "Full house on the floor, full book on the phone",
  subhead:
    "24x7 AI answers reservation calls during the rush, after close, and on days off — party size, time, and special requests captured without pulling staff off the floor.",
  pains: [
    "Friday-night reservation calls ring out while your host is seating a full house.",
    "Large-party and catering inquiries need details your voicemail can never collect.",
    "Hours, location, and menu questions interrupt service for answers anyone could give.",
  ],
  outcomes: [
    {
      title: "Reservations without the phone tag",
      description:
        "Captures party size, date, time, and contact details — then confirms back so the book stays accurate.",
    },
    {
      title: "Parties and special requests, detailed",
      description:
        "Birthdays, anniversaries, dietary needs, high chairs — collected up front so the night goes smoothly.",
    },
    {
      title: "Repeat questions, answered instantly",
      description:
        "Hours, location, parking, menu highlights — answered from your business info, even at midnight.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person — catering quotes, complaints — the AI offers a callback and alerts your team with context.",
    },
  ],
  demoSlug: "pleasant-pediatric-appointments",
  demoName: "Alex",
  demoBlurb:
    "Try a live demo agent to hear how natural booking sounds, then request your restaurant setup.",
  faqs: [
    {
      question: "Does it integrate with my reservation book?",
      answer:
        "Today the agent confirms bookings by call and text and records them in your Sheets or calendar. Deeper reservation-platform integrations are configured per pilot during setup.",
    },
    {
      question: "What happens during the dinner rush?",
      answer:
        "The AI answers every simultaneous call — no busy signal, no hold music. Your hosts stay on the floor while the book fills itself.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, hours, party rules, and FAQs with you on a setup call, run test calls until you approve, and go live — usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** Restaurant vertical landing page (SEO: AI phone answering). */
export default function RestaurantsPage() {
  return <IndustryPage content={content} />;
}
