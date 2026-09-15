import type { Metadata } from "next";
import {
  IndustryPage,
  type IndustryPageContent,
} from "@/components/seo/industry-page";
import { SITE_URL } from "@/lib/site-config";

export const metadata: Metadata = {
  title: "AI Receptionist for Real Estate | Every Enquiry Answered",
  description:
    "Speed wins listings. 24x7 AI answers every buyer and seller call, books viewings straight to your calendar, and captures enquiry details for follow-up. Live in 48 hours.",
  alternates: { canonical: `${SITE_URL}/real-estate` },
};

const content: IndustryPageContent = {
  slug: "real-estate",
  headline: "Every enquiry answered, every viewing booked",
  subhead:
    "24x7 AI picks up when you are at a closing, on a viewing, or off for the day. It answers listing questions, books viewings to your calendar, and captures every buyer and seller detail for follow-up.",
  pains: [
    "A hot buyer calls during your viewing and reaches voicemail. By callback time they have another agent.",
    "Weekend enquiries pile up as texts you answer late on Sunday night.",
    "New listings generate calls faster than any one person can qualify them.",
  ],
  outcomes: [
    {
      title: "Viewings booked to your calendar",
      description:
        "Offers real windows, confirms the visit with the caller, and records the booking where your day is planned.",
    },
    {
      title: "Buyer and seller details, captured whole",
      description:
        "Name, number, timeline, area, and budget range collected on the call, ready for your follow-up.",
    },
    {
      title: "Listing questions answered instantly",
      description:
        "Price, beds and baths, location, open-home times, answered from your listing info, day or night.",
    },
    {
      title: "Callbacks, never dead ends",
      description:
        "When a caller needs a person, the AI offers a callback and alerts you with the full context.",
    },
  ],
  demoSlug: "copper-ridge-service-request",
  demoName: "Jordan",
  demoBlurb:
    "Try a live enquiry with Jordan and watch the details land cleanly. Your version is trained on your listings and patches.",
  faqs: [
    {
      question: "Can it tell a hot buyer from a casual browser?",
      answer:
        "Yes. You define what counts during setup, such as timeline and budget range, and the agent captures those details on every call so you can prioritize follow-up.",
    },
    {
      question: "How do new listings reach the agent?",
      answer:
        "Share the listing sheet or details any time. We update prices, open-home times, and availability with you, then run test calls until you approve how it sounds.",
    },
    {
      question: "How long does setup take?",
      answer:
        "We configure your number, calendar, qualification questions, and after-hours rules with you on a setup call, run test calls until you approve, and go live, usually within 48 hours.",
    },
    {
      question: "What does it cost?",
      answer:
        "Pilot plans start at $79/mo with concierge setup included. You only move to a monthly plan once the pilot proves itself on your real calls.",
    },
  ],
};

/** Real estate vertical landing page (SEO: AI receptionist for realtors). */
export default function RealEstatePage() {
  return <IndustryPage content={content} />;
}
