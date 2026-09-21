import type { Metadata } from "next";

import { HomePage } from "@/components/home/home-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "",
  title: "AI Voice Agents for Small Business Calls",
  description:
    "24x7 AI voice agents answer small-business calls, handle routine questions, book work, and capture leads in the tools your team already uses.",
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
