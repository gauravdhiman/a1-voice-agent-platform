"use client";

/**
 * Platform Tools management page (platform admin only).
 *
 * Dedicated home for the global tool catalog — parallel to `/platform/skills`.
 * Platform admins configure custom MCP servers (create/edit drawer → test →
 * save draft / publish) and manage every published platform tool (legacy +
 * MCP) via the catalog in `<PlatformToolsManager>`.
 *
 * This surface was previously crammed onto every agent's Tools tab as a
 * "Manage MCP servers" button. That conflated a global, platform-admin
 * concern (catalog authoring/publishing) with a per-agent, org-admin
 * concern (attach a published tool, supply the org's key). It now lives
 * here; org/regular admins still see published tools as normal `ToolCard`s
 * on the agent Tools tab for attachment — unchanged.
 *
 * Frontend authz gate. The backend independently enforces `platform_admin`
 * on every write endpoint (discover/parse/create/publish/delete), so a
 * non-admin who reaches this route can read nothing and write nothing.
 *
 * @example
 * ```tsx
 * <PlatformToolsPage />
 * ```
 */

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformToolsManager } from "@/components/tools/platform-tools-manager";

export default function PlatformToolsPage() {
  const { user } = useAuth();

  // Frontend authz gate. Backend enforces the same independently. Placed
  // after all hooks (useAuth is the only hook here) so hook call order is
  // stable regardless of role.
  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this page. Only platform administrators can manage platform tools."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Platform Tools
        </h1>
        <p className="text-muted-foreground mt-1">
          Configure custom MCP servers for the global catalog, and manage
          every published platform tool (native + MCP). Published tools appear
          on every org&apos;s agent Tools tab for attachment.
        </p>
      </div>
      <PlatformToolsManager />
    </div>
  );
}
