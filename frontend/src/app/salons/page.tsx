import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata = createMarketingMetadata({
  path: "/salon-appointment-booking",
  title: "AI Receptionist for Salon Appointment Booking",
  description:
    "AI receptionist for salons and spas that answers booking calls, handles service questions, captures new-client details, and keeps appointments moving while stylists work.",
  keywords: [
    "AI receptionist for salons",
    "salon appointment booking",
    "salon answering service",
    "spa appointment scheduling",
    "salon missed calls",
  ],
});

const content: IndustryPageContent = {
  slug: "salons",
  label: "SALONS AND SPAS",
  headline: "Fully booked chairs, zero phone tag",
  subhead:
    "24x7 AI answers when your stylists are with clients and the shop is closed. It books cuts, color, and treatments through your scheduling system, takes new-client details, and confirms so clients actually show up.",
  pains: [
    "Calls ring out while every stylist is with a client, and the caller books across the street.",
    "Your mornings disappear into rescheduling texts instead of welcoming walk-ins.",
    "No-shows leave paid-for chairs empty because reminders depend on someone remembering.",
  ],
  outcomes: [
    {
      title: "Cuts, color, and treatments, booked to your calendar",
      description:
        "Checks real availability, confirms the slot with the caller, and writes the booking to the calendar or scheduling system your team uses.",
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
  demoBlurb:
    "No public salon demo yet. Request the workflow and we will shape it around your services, stylists, chairs, and policies.",
  proof: {
    eyebrow: "THE SERVICE CALL, BY THE NUMBERS",
    title: "A full chair cannot answer the phone.",
    description:
      "Consumer-services benchmarks point to a simple opportunity: make it easy for a ready-to-book caller to get an answer and a next step while your team is with clients.",
    points: [
      {
        value: "60%",
        label: "of consumer-services callers speak with a person.",
      },
      {
        value: "34%",
        label: "of answered consumer-services calls are leads.",
      },
      {
        value: "40%",
        label: "of consumer-services leads convert on the call.",
      },
    ],
    sourceNote:
      "Directional consumer-services averages. The benchmark includes vet, legal, storage, tutoring, and other categories, not salons specifically.",
    sources: [
      {
        label: "Invoca consumer-services benchmarks",
        href: "https://www.invoca.com/reports/the-invoca-consumer-services-lead-conversion-benchmarks-report-2026",
      },
    ],
  },
  faqs: [
    {
      question: "Can it handle reschedules and cancellations fairly?",
      answer:
        "Yes. You define the rules during setup, such as how late a client can move a booking, and the agent follows them on every call while keeping your scheduling system accurate.",
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
