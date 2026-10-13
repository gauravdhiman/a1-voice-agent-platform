import type { Metadata } from "next";

import { LegalDocumentPage } from "@/components/legal/legal-document-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "/privacy",
  title: "Privacy Policy",
  description:
    "Read the Privacy Policy for the 24x7 AI voice agent platform: what data we collect, how we use it, and the choices you have at 247ai.live.",
  keywords: ["privacy policy", "data privacy", "24x7 AI privacy"],
});

/** Public Privacy Policy page: latest published version. */
export default function PrivacyPage() {
  return (
    <LegalDocumentPage
      documentKey="privacy"
      heading="Privacy Policy"
      unavailableMessage="The Privacy Policy is not available right now."
    />
  );
}
