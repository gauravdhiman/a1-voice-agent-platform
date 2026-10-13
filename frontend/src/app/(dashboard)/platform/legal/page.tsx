"use client";

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { LegalDocumentsManager } from "@/components/legal/legal-documents-manager";

/**
 * Platform admin manager for public legal documents: version history, draft
 * editing, and publishing for the Terms & Conditions and Privacy Policy.
 */
export default function PlatformLegalPage() {
  const { user } = useAuth();

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage legal documents."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Legal Documents
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage the published Terms &amp; Conditions and Privacy Policy: review
          version history, edit drafts, and publish updates. Publishing replaces
          the text shown to visitors on 247ai.live.
        </p>
      </div>
      <LegalDocumentsManager />
    </div>
  );
}
