import type { Metadata } from "next";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Receptionist for Dental Practices",
  description:
    "Never miss another patient call. 24x7 AI answers after hours, books cleanings and exams to your calendar, and captures callback requests — live in 48 hours.",
  alternates: { canonical: `${SITE_URL}/dental` },
};

const content: IndustryPageContent = {
  slug: "dental",
  headline: "Your dental practice, always answering",
  subhead:
    "24x7 AI picks up every patient call — after hours, weekends, and busy Mondays — books cleanings and exams straight to your calendar, and confirms so fewer patients no-show.",
  pains: [
    "After-hours callers hear voicemail and book with the practice down the street.",
    "Your front desk spends mornings playing phone tag instead of caring for patients in chairs.",
    "No-shows eat 15% of your day because reminders depend on someone remembering to send them.",
  ],
  outcomes: [
    {
      title: "New-patient intake, handled",
      description:
        "Greets first-time callers, captures their details and reason for visit, and books them into the right chair time.",
    },
    {
      title: "Cleanings and exams, booked to your calendar",
      description:
        "Checks real availability, confirms the slot with the caller, and writes the event to Google Calendar.",
    },
    {
      title: "Questions answered instantly",
      description:
        "Hours, location, services, insurance basics — answered from your business info, day or night.",
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
    "Try the live demo: book a dental visit with Alex and watch the calendar update.",
  faqs: [
    {
      question: "Do patients know they are talking to an AI?",
      answer:
        "The agent introduces itself as your practice's AI receptionist. In testing, most callers simply get their booking done — the experience feels like a capable front desk, not a phone tree.",
    },
    {
      question: "What happens when a caller needs a real person?",
      answer:
        "The agent offers to have your team call back, captures the number and reason, and sends your team the full context. Nothing falls into voicemail.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, calendar, hours, and services with you on a setup call, run test bookings until you approve, and go live — usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** Dental vertical landing page (SEO: AI receptionist for dentists). */
export default function DentalPage() {
  return <IndustryPage content={content} />;
}
