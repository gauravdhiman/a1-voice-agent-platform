import type { Metadata } from "next";

import { HomePageLegacy } from "@/components/home/home-page-legacy";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "home-classic",
  title: "Classic homepage",
  description:
    "Previous 24x7 AI homepage experience, kept as a fallback while the new homepage rolls out.",
  keywords: ["24x7 AI", "classic homepage"],
});

/** Fallback route preserving the previous homepage storytelling experience. */
export default function HomeClassicPage() {
  return <HomePageLegacy />;
}
