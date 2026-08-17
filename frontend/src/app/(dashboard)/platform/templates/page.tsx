"use client";

/**
 * Platform use-case template management page.
 *
 * Platform admins author the reusable Markdown-backed templates that appear in
 * agent creation and editing. The backend repeats the role check on every CRUD
 * endpoint, so this page gate is a fast, user-friendly complement.
 */

import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformVoiceTemplatesManager } from "@/components/voice-templates/platform-voice-templates-manager";
import { useAuth } from "@/contexts/auth-context";

export default function PlatformTemplatesPage() {
  const { user } = useAuth();

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage use case templates."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Platform Admin</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground">Use Case Templates</h1>
        <p className="mt-1 max-w-3xl text-muted-foreground">
          Create reusable Markdown-backed starting points for agent setup. Active templates are available in both the create wizard and the agent editor.
        </p>
      </div>
      <PlatformVoiceTemplatesManager />
    </div>
  );
}
