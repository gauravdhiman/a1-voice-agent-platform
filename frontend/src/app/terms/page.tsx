import type { Metadata } from "next";

import { LegalDocumentPage } from "@/components/legal/legal-document-page";
import { createMarketingMetadata } from "@/lib/marketing-seo";

export const metadata: Metadata = createMarketingMetadata({
  path: "/terms",
  title: "Terms & Conditions",
  description:
    "Read the Terms & Conditions governing use of the 24x7 AI voice agent platform and services at 247ai.live.",
  keywords: ["terms and conditions", "terms of service", "24x7 AI terms"],
});

/** Public Terms & Conditions page: latest published version. */
export default function TermsPage() {
  return (
    <LegalDocumentPage
      documentKey="terms"
      heading="Terms & Conditions"
      unavailableMessage="The Terms & Conditions are not available right now."
    />
  );
}
