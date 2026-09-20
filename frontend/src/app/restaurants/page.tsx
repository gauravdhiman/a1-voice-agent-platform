import type { Metadata } from "next";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Receptionist for Restaurants | Never Miss a Reservation",
  description:
    "Missed calls cost covers. 24x7 AI answers every restaurant call, takes reservations and party bookings, and answers hours and directions questions. Live in 48 hours.",
  alternates: { canonical: `${SITE_URL}/restaurants` },
};

const content: IndustryPageContent = {
  slug: "restaurants",
  headline: "Every call answered, every table filled",
  subhead:
    "24x7 AI picks up mid-rush, after close, and on your day off. It takes reservations, captures party and catering requests with full details, and answers the questions callers always ask.",
  pains: [
    "Saturday at 7pm your line is busy and the caller books the place down the street.",
    "Your host is glued to the phone instead of greeting the guests already in the room.",
    "Party bookings and catering inquiries die in voicemail because nobody calls back fast enough.",
  ],
  outcomes: [
    {
      title: "Reservations taken mid-rush",
      description:
        "Date, time, party size, and contact captured on the call and handed to your team exactly as spoken.",
    },
    {
      title: "Party and catering requests, captured whole",
      description:
        "Headcount, occasion, budget hints, and callback number collected so big tables stop slipping away.",
    },
    {
      title: "Repeat questions answered instantly",
      description:
        "Hours, location, parking, dress code, and daily specials, answered from your info, day or night.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts your team with the full context.",
    },
  ],
  demoSlug: "verdi-table-restaurant",
  demoName: "Sofia",
  demoBlurb:
    "Try a live order or ask Sofia a menu question. Your version is trained on your menu, hours, and tables.",
  faqs: [
    {
      question: "What happens during a Friday night rush?",
      answer:
        "The agent picks up every call at once, so nobody hears a busy signal. Routine reservations and questions are handled on the spot; anything needing a human becomes a callback with full context.",
    },
    {
      question: "How do menu or hours changes reach the agent?",
      answer:
        "Tell us during setup and any time after. We update your services, hours, and specials with you, then run test calls until you approve how it sounds.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, reservation flow, hours, and FAQs with you on a setup call, run test calls until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** Restaurant vertical landing page (SEO: AI receptionist for restaurants). */
export default function RestaurantsPage() {
  return <IndustryPage content={content} />;
}
