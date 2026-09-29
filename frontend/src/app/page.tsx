import type { Metadata } from "next";

import { HomePage } from "@/components/home/home-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "",
  title: "Answer more calls. Capture more business.",
  description:
    "A 24x7 AI phone assistant answers calls on your business number and website, handles questions, bookings and orders, and records callback requests. No phone menus or hold music.",
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
