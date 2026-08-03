"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import { AccessDenied } from "@/components/ui/access-denied";
import { OrganizationEditDialog } from "@/components/organizations/organization-edit-dialog";
import { ProviderCredentialsCard } from "@/components/organizations/provider-credentials-card";
import { PublicPageSettingsCard } from "@/components/organizations/public-page-settings-card";
import {
  normalizeOrganizationSlug,
  publicOrgPagePath,
  suggestOrganizationSlugFromName,
  validateOrganizationSlug,
} from "@/lib/organization-slug";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AnimatedTabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Building2,
  Users,
  Calendar,
  Activity,
  CreditCard,
  Save,
  X,
  Crown,
  Edit3,
  Info,
} from "lucide-react";
import {
  buildProviderCredentialsInput,
  PROVIDER_LABELS,
  ProviderCredentialKey,
} from "@/lib/provider-credentials-input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  OrganizationCompleteData,
  OrganizationEnhanced,
} from "@/types/organization";

import { organizationService } from "@/services/organization-service";
import { legacyTabRedirect } from "./legacy-tab-redirect";
import { toast } from "sonner";

// Use real services

export default function OrganizationPage() {
  const { user } = useAuth();
  const {
    currentOrganization,
    loading: orgLoading,
    setCurrentOrganization,
  } = useOrganization();
  const { canUpdateOrganization, canViewMembers, isPlatformAdmin, isOrgAdmin } =
    useUserPermissions();
  const searchParams = useSearchParams();
  const router = useRouter();
  // N1 follow-up #2 bug fix: the sidebar nav links to bare
  // `/organization` (no `?org_id=`), so we fall back to the user's
  // currentOrganization from context. The URL still wins when
  // present (e.g. for org switching from the orgs listing).
  const orgId =
    searchParams.get("org_id") ?? currentOrganization?.id ?? null;

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [organizationData, setOrganizationData] =
    useState<OrganizationCompleteData | null>(null);
  const [loading, setLoading] = useState(true);

  const [editedOrg, setEditedOrg] = useState<{
    name: string;
    description: string;
    website: string;
    slug: string;
    is_active: boolean;
    industry: string;
    location: string;
    business_details: string;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  // Voice provider credentials (Phase 4) — a SEPARATE form from the main org
  // card, with its own Save. Decrypted values are never returned by the API, so
  // the inputs are always blank on load; the user types a value to SET or
  // clears a field to CLEAR. `providerCredsTouched` records which fields the
  // user actually edited so the save sends ONLY touched keys (the backend
  // preserves omitted keys and drops `None`) — this avoids the
  // empty-string-clears-everything footgun the main org form has.
  const [providerCreds, setProviderCreds] = useState({
    google: "",
    deepgram: "",
    openai: "",
    cartesia: "",
    cerebras: "",
    openrouter: "",
    fish: "",
    livekit_api_key: "",
    livekit_api_secret: "",
  });
  const [providerCredsTouched, setProviderCredsTouched] = useState<
    Record<string, boolean>
  >({});
  const [providerCredsSaving, setProviderCredsSaving] = useState(false);
  const [removingProviderCred, setRemovingProviderCred] =
    useState<ProviderCredentialKey | null>(null);

  // Org page tab state ("info" | "credentials"). Synced to `?tab=` so the two
  // cards are deep-linkable. Legacy `?tab=` values (phone-numbers/skills/
  // ai-agent) are redirected to their top-level routes by `legacyTabRedirect`
  // above; `info`/`credentials` fall through (no redirect) and set the tab.
  const [activeTab, setActiveTab] = useState<"info" | "credentials" | "public">("info");

  const loadOrganizationData = useCallback(async () => {
    if (!orgId) return;

    setLoading(true);
    try {
      const org = (await organizationService.getOrganizationById(
        orgId,
      )) as OrganizationEnhanced;
      setOrganizationData({ organization: org });
      setEditedOrg({
        name: org.name,
        description: org.description || "",
        website: org.website || "",
        slug: org.slug,
        is_active: org.is_active,
        industry: org.industry || "",
        location: org.location || "",
        business_details: org.business_details || "",
      });
    } catch (error) {
      console.error("Failed to load organization data:", error);
      toast.error("Failed to load organization data");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  // Load data when component mounts or orgId changes
  useEffect(() => {
    if (orgId) {
      loadOrganizationData();
    }
  }, [orgId, loadOrganizationData]);

  // Sync tab state with URL. The Phone Numbers, Skills, and AI Voice
  // Agent tabs are now top-level routes (N1 redesign): when the URL
  // carries one of those tabs, we redirect to the canonical route
  // instead of rendering a tab body. `overview` (and an absent `tab`)
  // are the only values that render this page. The decision is in
  // `legacy-tab-redirect.ts` so the redirect contract is unit-tested
  // independently of the page.
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    const target = legacyTabRedirect(tabParam, orgId, searchParams);
    if (target) {
      router.replace(target);
    }
  }, [searchParams, orgId, router]);

  // Sync the org-page tab ("info" | "credentials") from `?tab=`. Legacy values
  // are redirected above; only an explicit `info`/`credentials` flips the tab —
  // an absent or unknown `tab` leaves the current tab alone (the useState
  // default is "info", and tab switches drive `handleTabChange`). Mirrors the
  // agent-detail `?tab=` idiom.
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "info" || tabParam === "credentials" || tabParam === "public") {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  // Switch tab and persist it to `?tab=`, preserving `org_id` (and any other
  // active params) so the deep link stays valid.
  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value as "info" | "credentials" | "public");
      const params = new URLSearchParams(searchParams.toString());
      params.set("tab", value);
      router.push(`/organization?${params.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  // Validate organization access when orgId is provided
  const {
    isValid: isOrgValid,
    loading: validationLoading,
    organization: validatedOrg,
  } = useOrganizationById(orgId);

  // Set the current organization based on the validated orgId parameter if provided
  // Use useEffect to avoid setting state during render
  const hasSetOrgRef = useRef(false);
  useEffect(() => {
    if (
      validatedOrg &&
      (!currentOrganization || currentOrganization.id !== validatedOrg.id) &&
      !hasSetOrgRef.current
    ) {
      setCurrentOrganization(validatedOrg);
      hasSetOrgRef.current = true;
    }
  }, [validatedOrg, currentOrganization, setCurrentOrganization]);

  const handleEdit = () => {
    if (organizationData) {
      setIsEditing(true);
    }
  };

  const handleEditSuccess = () => {
    setEditDialogOpen(false);
    loadOrganizationData();
  };

  const handleSave = async () => {
    if (!orgId || !editedOrg || !organizationData) return;

    const normalizedSlug = normalizeOrganizationSlug(editedOrg.slug);
    const slugError = validateOrganizationSlug(normalizedSlug);
    if (slugError) {
      toast.error(slugError);
      return;
    }

    // Store original data for rollback if needed
    const originalData = { ...organizationData };

    setSaving(true);
    try {
      const response = await organizationService.updateOrganization(orgId, {
        name: editedOrg.name,
        description: editedOrg.description,
        website: editedOrg.website,
        slug: normalizedSlug,
        is_active: editedOrg.is_active,
        industry: editedOrg.industry,
        location: editedOrg.location,
        business_details: editedOrg.business_details,
      });

      // Only update UI after successful save
      setOrganizationData({ organization: response as OrganizationEnhanced });
      setIsEditing(false);
      toast.success("Organization updated successfully");
    } catch (error: unknown) {
      console.error("Failed to update organization:", error);
      // Extract error message from API response
      const errorMessage = error instanceof Error 
        ? error.message 
        : typeof error === 'object' && error !== null && 'detail' in error
          ? (error as { detail: string }).detail
          : "Failed to update organization";
      toast.error(errorMessage);
      // Don't update UI on error - keep original data showing
      setOrganizationData(originalData);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    // 1. Simply revert UI state
    setIsEditing(false);

    // 2. Reset draft state from existing data (No refetch!)
    if (organizationData) {
      const org = organizationData.organization;
      setEditedOrg({
        name: org.name,
        description: org.description || "",
        website: org.website || "",
        slug: org.slug,
        is_active: org.is_active,
        industry: org.industry || "",
        location: org.location || "",
        business_details: org.business_details || "",
      });
    }
  };

  /**
   * Save ONLY the touched voice-provider credentials.
   *
   * Builds `provider_credentials_input` with touched keys only: a non-empty
   * value SETS, an empty touched value CLEARS (`null`), and an untouched key is
   * OMITTED (the backend preserves it). LiveKit is sent as
   * `{api_key, api_secret}` when either field was touched — both empty clears
   * it (`null`). Nothing is sent if no field was touched.
   */
  const resetProviderCredDraft = () => {
    setProviderCreds({
      google: "",
      deepgram: "",
      openai: "",
      cartesia: "",
      cerebras: "",
      openrouter: "",
      fish: "",
      livekit_api_key: "",
      livekit_api_secret: "",
    });
    setProviderCredsTouched({});
  };

  const handleSaveProviderCreds = async () => {
    if (!orgId) return;
    const input = buildProviderCredentialsInput(
      providerCreds,
      providerCredsTouched,
    );
    if (Object.keys(input).length === 0) {
      toast.info("No provider credentials changed.");
      return;
    }
    setProviderCredsSaving(true);
    try {
      const response = await organizationService.updateOrganization(orgId, {
        provider_credentials_input: input,
      });
      setOrganizationData({ organization: response as OrganizationEnhanced });
      resetProviderCredDraft();
      toast.success("Voice provider credentials saved");
    } catch (error: unknown) {
      console.error("Failed to save provider credentials:", error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === "object" &&
              error !== null &&
              "detail" in error
            ? (error as { detail: string }).detail
            : "Failed to save provider credentials";
      toast.error(errorMessage);
    } finally {
      setProviderCredsSaving(false);
    }
  };

  /** Mark a provider-creds field touched on edit (drives the "send only touched" rule). */
  const markProviderCredTouched = (key: string) => {
    setProviderCredsTouched((prev) =>
      prev[key] ? prev : { ...prev, [key]: true },
    );
  };

  const clearProviderCredTouched = (key: string) => {
    setProviderCredsTouched((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  /**
   * Remove a single provider credential immediately (sends `null` for that key).
   */
  const handleRemoveProviderCred = async (key: ProviderCredentialKey) => {
    if (!orgId) return;
    setRemovingProviderCred(key);
    try {
      const response = await organizationService.updateOrganization(orgId, {
        provider_credentials_input: { [key]: null },
      });
      setOrganizationData({ organization: response as OrganizationEnhanced });
      if (key === "livekit") {
        setProviderCreds((prev) => ({
          ...prev,
          livekit_api_key: "",
          livekit_api_secret: "",
        }));
        clearProviderCredTouched("livekit");
      } else {
        setProviderCreds((prev) => ({ ...prev, [key]: "" }));
        clearProviderCredTouched(key);
      }
      toast.success(`${PROVIDER_LABELS[key]} credentials removed`);
    } catch (error: unknown) {
      console.error("Failed to remove provider credentials:", error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === "object" &&
              error !== null &&
              "detail" in error
            ? (error as { detail: string }).detail
            : "Failed to remove provider credentials";
      toast.error(errorMessage);
    } finally {
      setRemovingProviderCred(null);
    }
  };

  // Make orgId mandatory - if not provided, redirect to organizations page
  if (!orgId) {
    return (
      <AccessDenied
        title="Organization ID Required"
        description="Organization ID is required to access this page. Please select an organization from the organizations page."
        redirectPath="/organizations"
      />
    );
  }

  if (orgLoading || validationLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading organization...</div>
      </div>
    );
  }

  // Check if orgId is invalid (provided but validation failed)
  if (!isOrgValid) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this organization. Please contact your organization administrator or platform admin for access."
        redirectPath="/organizations"
      />
    );
  }

  if (!isPlatformAdmin && !isOrgAdmin) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to view organization pages. Please contact your organization administrator or platform admin for access."
        redirectPath="/dashboard"
      />
    );
  }

  if (!validatedOrg) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Organization not found</div>
      </div>
    );
  }

  const userRoles =
    user?.roles
      ?.filter(
        (userRole) =>
          !userRole.organization_id ||
          userRole.organization_id === validatedOrg.id,
      )
      .map((userRole) => userRole.role) || [];

  const displayOrg =
    isEditing && editedOrg ? editedOrg : organizationData?.organization;

  if (!displayOrg) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Organization data not available</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Organization Header */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <div className="bg-primary/10 p-2 rounded-lg">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">
                {displayOrg.name}
              </h1>
              <p className="text-sm text-muted-foreground">
                Organization Configuration
              </p>
            </div>
          </div>

          {canUpdateOrganization && (
            <div className="flex items-center space-x-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="sm" className="flex items-center space-x-2">
                    <Activity className="h-4 w-4" />
                    <span>Actions</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  {canViewMembers && (
                    <Link
                      href={`/organization/members?org_id=${validatedOrg.id}`}
                    >
                      <DropdownMenuItem className="flex items-center space-x-2 cursor-pointer">
                        <Users className="h-4 w-4" />
                        <span>Manage Members</span>
                      </DropdownMenuItem>
                    </Link>
                  )}
                  <Link
                    href={`/organization/billing?org_id=${validatedOrg.id}`}
                  >
                    <DropdownMenuItem className="flex items-center space-x-2 cursor-pointer">
                      <CreditCard className="h-4 w-4" />
                      <span>Billing & Subscriptions</span>
                    </DropdownMenuItem>
                  </Link>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-4">
          <span className="text-sm text-muted-foreground flex items-center">
            <Calendar className="h-4 w-4 mr-1" />
            Created {new Date(validatedOrg.created_at).toLocaleDateString()}
          </span>
          {userRoles.length > 0 && (
            <span className="text-sm text-muted-foreground flex items-center">
              <Crown className="h-4 w-4 mr-1" />
              {userRoles.length === 1
                ? userRoles[0].name
                : `${userRoles.length} roles`}
            </span>
          )}
        </div>
      </div>

      {/* N1 redesign: the org page is settings-only. Phone Numbers, Skills,
          and AI Voice Agent moved to top-level routes; `legacy-tab-redirect.ts`
          handles the legacy `?tab=...` URLs. The two remaining settings cards
          (Organization Info + Third-party API Credentials) are organized into
          a tabbed layout synced to `?tab=info|credentials`. */}
      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList className="w-full">
          <TabsTrigger value="info">Organization Info</TabsTrigger>
          <TabsTrigger value="credentials">API Credentials</TabsTrigger>
          <TabsTrigger value="public">Public Page</TabsTrigger>
        </TabsList>

        {/* Organization Info tab */}
        <TabsContent value="info">
      <Card>
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center justify-between">
            <div className="flex flex-col gap-1">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Building2 className="h-5 w-5" />
                <span>Organization Information</span>
              </CardTitle>
              <CardDescription>
                Your organization details and settings
              </CardDescription>
            </div>
            {canUpdateOrganization && !isEditing && (
              <Button variant="outline" size="sm" onClick={handleEdit}>
                <Edit3 className="h-4 w-4 mr-2" />
                Edit
              </Button>
            )}
          </div>
        </CardHeader>
            <CardContent className="p-5 pt-0 space-y-4">
              {isEditing ? (
                <>
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-3 flex items-start gap-2">
                    <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-blue-800">
                      The information you provide here helps AI agents represent your business accurately when speaking with callers.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={editedOrg?.name || ""}
                      onChange={(e) =>
                        editedOrg &&
                        setEditedOrg({ ...editedOrg, name: e.target.value })
                      }
                      placeholder="Enter organization name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={editedOrg?.description || ""}
                      onChange={(e) =>
                        editedOrg &&
                        setEditedOrg({
                          ...editedOrg,
                          description: e.target.value,
                        })
                      }
                      placeholder="Tell us about your organization, like little background, about team etc. This will be used by AI agent for context."
                      className="min-h-[100px]"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="industry">Industry</Label>
                      <Input
                        id="industry"
                        value={editedOrg?.industry || ""}
                        onChange={(e) =>
                          editedOrg &&
                          setEditedOrg({
                            ...editedOrg,
                            industry: e.target.value,
                          })
                        }
                        placeholder="e.g., Real Estate, Healthcare"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="location">Location / Address</Label>
                      <Input
                        id="location"
                        value={editedOrg?.location || ""}
                        onChange={(e) =>
                          editedOrg &&
                          setEditedOrg({
                            ...editedOrg,
                            location: e.target.value,
                          })
                        }
                        placeholder="123 Business St, City, State"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website">Website</Label>
                    <Input
                      id="website"
                      type="url"
                      value={editedOrg?.website || ""}
                      onChange={(e) =>
                        editedOrg &&
                        setEditedOrg({ ...editedOrg, website: e.target.value })
                      }
                      placeholder="https://www.example.com"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="slug">Organization slug</Label>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                      <div className="flex min-w-0 flex-1 items-center gap-1 rounded-md border bg-muted/30 px-3 py-2">
                        <span className="shrink-0 text-sm text-muted-foreground">
                          /o/
                        </span>
                        <Input
                          id="slug"
                          value={editedOrg?.slug || ""}
                          onChange={(e) =>
                            editedOrg &&
                            setEditedOrg({ ...editedOrg, slug: e.target.value })
                          }
                          placeholder="acme-support"
                          className="border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
                          spellCheck={false}
                          autoComplete="off"
                        />
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          if (!editedOrg) return;
                          const suggested = suggestOrganizationSlugFromName(
                            editedOrg.name,
                          );
                          if (suggested) {
                            setEditedOrg({ ...editedOrg, slug: suggested });
                          }
                        }}
                      >
                        Suggest from name
                      </Button>
                    </div>
                    {editedOrg?.slug ? (
                      validateOrganizationSlug(
                        normalizeOrganizationSlug(editedOrg.slug),
                      ) ? (
                        <p className="text-xs text-destructive">
                          {validateOrganizationSlug(
                            normalizeOrganizationSlug(editedOrg.slug),
                          )}
                        </p>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          Public page URL:{" "}
                          <span className="font-mono">
                            {publicOrgPagePath(
                              normalizeOrganizationSlug(editedOrg.slug),
                            )}
                          </span>
                          . Must be unique across all organizations.
                        </p>
                      )
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Used for your public page and API identifiers.
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="business_details">
                      Business Context
                    </Label>
                    <Textarea
                      id="business_details"
                      value={editedOrg?.business_details || ""}
                      onChange={(e) =>
                        editedOrg &&
                        setEditedOrg({
                          ...editedOrg,
                          business_details: e.target.value,
                        })
                      }
                      placeholder={`Describe your business context that you want your AI agents to be aware of. Include the most common things like:

• Short description of products and services you offer
• Business hours (weekdays, weekends, holidays, seasonal variations)
• Location and service areas
• Short decription of company policies and procedures
• Unique selling points and differentiators
• Common customer questions and how to handle them
• Emergency or after-hours protocols
• Any other relevant common information

Example:
We are a family-owned plumbing business serving the greater Phoenix area. Our regular hours are Monday-Friday 8am-6pm and Saturday 9am-2pm. 
We offer 24/7 emergency services with premium rates after hours. We specialize in residential repairs, water heater installations, and drain cleaning. 
All our technicians are licensed and background-checked. We offer a 90-day warranty on all repairs and free estimates for new installations. 
During monsoon season (July-September), we have extended hours for flood-related emergencies..."`}
                      className="min-h-[200px]"
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Name
                    </label>
                    <p className="text-foreground">{displayOrg.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Description
                    </label>
                    <p className="text-foreground">
                      {displayOrg.description || "No description"}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Industry
                      </label>
                      <p className="text-foreground">
                        {displayOrg.industry || "Not set"}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Location
                      </label>
                      <p className="text-foreground">
                        {displayOrg.location || "Not set"}
                      </p>
                    </div>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Website
                    </label>
                    <p className="text-foreground">
                      {displayOrg.website ? (
                        <a
                          href={displayOrg.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary/80 underline"
                        >
                          {displayOrg.website}
                        </a>
                      ) : (
                        <span className="text-muted-foreground">No website</span>
                      )}
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Slug
                    </label>
                    <p className="text-foreground font-mono">
                      {displayOrg.slug}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Public page:{" "}
                      <span className="font-mono">
                        {publicOrgPagePath(displayOrg.slug)}
                      </span>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Business Context
                    </label>
                    <p className="text-foreground whitespace-pre-wrap">
                      {displayOrg.business_details ||
                        "No business context provided"}
                    </p>
                  </div>
                </>
              )}
            </CardContent>
            {isEditing && (
              <CardFooter className="flex justify-end space-x-2 p-5 border-t bg-muted/20">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  disabled={saving}
                  className="flex items-center space-x-2"
                >
                  <X className="h-4 w-4" />
                  <span>Cancel</span>
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center space-x-2"
                >
                  <Save className="h-4 w-4" />
                  <span>{saving ? "Saving..." : "Save Changes"}</span>
                </Button>
              </CardFooter>
            )}
      </Card>
        </TabsContent>

        {/* Third-party API Credentials tab — per-provider API keys for the
            modular voice engine (Deepgram, OpenAI, Cartesia, Cerebras,
            LiveKit). A DEDICATED card with its own Save — separate from the
            main org form so the empty-string-clears-everything footgun can't
            wipe all keys at once. Feeds the encrypted provider_credentials
            blob the worker's per-org key resolver reads. */}
        <TabsContent value="credentials">
          <ProviderCredentialsCard
            status={
              organizationData?.organization?.provider_credentials_status
            }
            draft={providerCreds}
            onDraftChange={setProviderCreds}
            touched={providerCredsTouched}
            onMarkTouched={markProviderCredTouched}
            onClearTouched={clearProviderCredTouched}
            onSave={handleSaveProviderCreds}
            onRemoveProvider={handleRemoveProviderCred}
            saving={providerCredsSaving}
            removingProvider={removingProviderCred}
            canUpdate={canUpdateOrganization}
          />
        </TabsContent>

        <TabsContent value="public">
          {organizationData?.organization ? (
            <PublicPageSettingsCard
              organization={organizationData.organization}
              canEdit={canUpdateOrganization}
              onUpdated={loadOrganizationData}
            />
          ) : null}
        </TabsContent>
      </AnimatedTabs>

      {/* Edit Dialog (for fallback) */}
      {validatedOrg && (
        <OrganizationEditDialog
          open={editDialogOpen}
          onOpenChange={setEditDialogOpen}
          organization={validatedOrg}
          onSuccess={handleEditSuccess}
        />
      )}
    </div>
  );
}
