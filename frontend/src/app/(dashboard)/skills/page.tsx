"use client";

/**
 * Top-level /skills page (N1 redesign).
 *
 * Skills used to live as a tab inside the organization page. They are
 * now a first-class route, with their own permissions gate
 * (`skill:read` in the nav config) and a shareable URL.
 *
 * The page renders the existing `<OrganizationSkillsTab>` directly —
 * the tab is already self-contained (it owns its own data fetch via
 * the skill service), so the only thing this page adds is the URL
 * and the no-org-selected state.
 */

import React from "react";
import { useSearchParams } from "next/navigation";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { OrganizationSkillsTab } from "@/components/skills/organization-skills-tab";

export default function SkillsPage() {
  const searchParams = useSearchParams();
  const { currentOrganization } = useOrganization();
  const { isPlatformAdmin, isOrgAdmin } = useUserPermissions();

  // Prefer the URL's org_id, fall back to the current org from context.
  const orgId = searchParams.get("org_id") ?? currentOrganization?.id ?? null;

  if (!orgId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-muted-foreground">
          Select an organization to view its skills.
        </p>
      </div>
    );
  }

  // canCreate/canEdit require admin-level permissions. Regular members
  // can view skills but not create or edit them. The `<SkillEditor>`
  // enforces this with the same flags.
  const canManage = isPlatformAdmin || isOrgAdmin;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Skills</h1>
        <p className="text-sm text-muted-foreground">
          Browse, edit, and create skills available to your voice agents.
        </p>
      </div>
      <OrganizationSkillsTab
        orgId={orgId}
        canCreate={canManage}
        canEdit={canManage}
        basePath="/skills"
      />
    </div>
  );
}
