import type { Metadata } from "next";

import { HomePage } from "@/components/home/home-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "",
  title: "Answer more calls. Capture more business.",
  description:
    "Our 24x7 AI phone assistant answers customer calls, handles common questions, books appointments, takes orders, and records callback requests, even when you’re busy or closed. More answered calls and bookings can mean more business.",
  keywords: [
    "AI voice agents for small business",
    "AI receptionist",
    "AI call answering",
    "business phone automation",
    "missed-call solution",
  ],
});

/** Public homepage: business-led particle storytelling and concierge demo entry. */
export default function LandingPage() {
  return <HomePage />;
}
