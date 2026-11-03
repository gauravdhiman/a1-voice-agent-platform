"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import { AccessDenied } from "@/components/ui/access-denied";
import { OrganizationEditDialog } from "@/components/organizations/organization-edit-dialog";
import { WebsiteBusinessContextGenerator } from "@/components/organizations/website-business-context-generator";
import { ProviderCredentialsCard } from "@/components/organizations/provider-credentials-card";
import { PublicPageSettingsCard } from "@/components/organizations/public-page-settings-card";
import { OrganizationNotificationSettingsForm } from "@/components/notifications/organization-notification-settings-form";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  buildProviderCredentialDescriptionsInput,
  buildProviderCredentialsInput,
  PROVIDER_LABELS,
  ProviderCredentialDescriptions,
  ProviderCredentialKey,
} from "@/lib/provider-credentials-input";
import {
  ORGANIZATION_TIMEZONE_OPTIONS,
  ORGANIZATION_TIMEZONE_UNSET,
} from "@/lib/organization-timezones";
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
  OrganizationUpdate,
} from "@/types/organization";

import { organizationService } from "@/services/organization-service";
import { legacyTabRedirect } from "./legacy-tab-redirect";
import { toast } from "sonner";

const ORGANIZATION_TABS = [
  "general",
  "credentials",
  "public-page",
  "notifications",
] as const;

type OrganizationTab = (typeof ORGANIZATION_TABS)[number];

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
    timezone: string;
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
    resend: "",
  });
  const [providerCredsTouched, setProviderCredsTouched] = useState<
    Record<string, boolean>
  >({});
  const [providerCredDescriptions, setProviderCredDescriptions] = useState<
    ProviderCredentialDescriptions
  >({});
  const [providerCredDescriptionsTouched, setProviderCredDescriptionsTouched] =
    useState<Record<string, boolean>>({});
  const [providerCredsSaving, setProviderCredsSaving] = useState(false);
  const [removingProviderCred, setRemovingProviderCred] =
    useState<ProviderCredentialKey | null>(null);

  // All organization settings are peers in one horizontal tab row. Older
  // `tab=settings&section=...` links are canonicalized in the effect below.
  const searchParamsString = searchParams.toString();
  const requestedTab = searchParams.get("tab");
  const requestedSettingsSection = searchParams.get("section");
  const legacySettingsTab =
    requestedTab === "settings"
      ? requestedSettingsSection
      : requestedTab === "info"
        ? "general"
        : requestedTab === "public"
          ? "public-page"
          : null;
  const activeTabFromUrl: OrganizationTab = ORGANIZATION_TABS.includes(
    requestedTab as OrganizationTab,
  )
    ? (requestedTab as OrganizationTab)
    : legacySettingsTab &&
        ORGANIZATION_TABS.includes(legacySettingsTab as OrganizationTab)
      ? (legacySettingsTab as OrganizationTab)
      : "general";
  const [activeTab, setActiveTab] = useState<OrganizationTab>(activeTabFromUrl);
  const settingsTabsListRef = useRef<HTMLDivElement>(null);

  const loadOrganizationData = useCallback(async () => {
    if (!orgId) return;

    setLoading(true);
    try {
      const org = (await organizationService.getOrganizationById(
        orgId,
      )) as OrganizationEnhanced;
      setOrganizationData({ organization: org });
      setProviderCredDescriptions(org.provider_credentials_descriptions ?? {});
      setEditedOrg({
        name: org.name,
        description: org.description || "",
        website: org.website || "",
        slug: org.slug,
        is_active: org.is_active,
        industry: org.industry || "",
        location: org.location || "",
        timezone: org.timezone || ORGANIZATION_TIMEZONE_UNSET,
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

  // Sync legacy tabs with their current destinations. Phone Numbers, Skills,
  // and the AI Voice Agent remain separate routes; organization settings now
  // use one canonical `?tab=` value per horizontal tab.
  useEffect(() => {
    const target = legacyTabRedirect(
      requestedTab,
      orgId,
      new URLSearchParams(searchParamsString),
    );
    if (target) {
      router.replace(target);
    }
  }, [requestedTab, searchParamsString, orgId, router]);

  // Older organization URLs used `tab=settings&section=...`; keep those deep
  // links working while canonicalizing them to one top-level tab.
  useEffect(() => {
    let canonicalTab: OrganizationTab | null = null;
    if (requestedTab === "settings") {
      canonicalTab = ORGANIZATION_TABS.includes(
        requestedSettingsSection as OrganizationTab,
      )
        ? (requestedSettingsSection as OrganizationTab)
        : "general";
    } else if (requestedTab === "info") {
      canonicalTab = "general";
    } else if (requestedTab === "public") {
      canonicalTab = "public-page";
    }
    if (!canonicalTab) return;

    const params = new URLSearchParams(searchParamsString);
    params.set("tab", canonicalTab);
    params.delete("section");
    router.replace(`/organization?${params.toString()}`, { scroll: false });
  }, [requestedSettingsSection, requestedTab, router, searchParamsString]);

  useEffect(() => {
    setActiveTab(activeTabFromUrl);
  }, [activeTabFromUrl]);

  useEffect(() => {
    const keepActiveTabVisible = () => {
      const activeTrigger =
        settingsTabsListRef.current?.querySelector<HTMLElement>(
          '[role="tab"][aria-selected="true"]',
        );
      activeTrigger?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    };
    keepActiveTabVisible();
    window.addEventListener("resize", keepActiveTabVisible, { passive: true });
    return () => window.removeEventListener("resize", keepActiveTabVisible);
  }, [activeTab]);

  // Switch the top-level area and keep its deep link in the URL.
  const handleTabChange = useCallback(
    (value: string) => {
      const nextTab = ORGANIZATION_TABS.includes(value as OrganizationTab)
        ? (value as OrganizationTab)
        : "general";
      setActiveTab(nextTab);
      const params = new URLSearchParams(searchParamsString);
      params.set("tab", nextTab);
      params.delete("section");
      router.push(`/organization?${params.toString()}`, { scroll: false });
    },
    [router, searchParamsString],
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
        timezone:
          editedOrg.timezone === ORGANIZATION_TIMEZONE_UNSET
            ? ""
            : editedOrg.timezone,
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
        timezone: org.timezone || ORGANIZATION_TIMEZONE_UNSET,
        business_details: org.business_details || "",
      });
    }
  };

  /**
   * Save ONLY the touched voice-provider credentials.
   *
   * Builds `provider_credentials_input` with touched keys only: a non-empty
   * value SETS, an empty touched value CLEARS (`null`), and an untouched key is
   * OMITTED (the backend preserves it). Nothing is sent if no field was touched.
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
      resend: "",
    });
    setProviderCredsTouched({});
  };

  const resetProviderCredDescriptionDraft = () => {
    setProviderCredDescriptionsTouched({});
  };

  const handleSaveProviderCreds = async () => {
    if (!orgId) return;
    const credentialInput = buildProviderCredentialsInput(
      providerCreds,
      providerCredsTouched,
    );
    const descriptionInput = buildProviderCredentialDescriptionsInput(
      providerCredDescriptions,
      providerCredDescriptionsTouched,
    );
    if (
      Object.keys(credentialInput).length === 0 &&
      Object.keys(descriptionInput).length === 0
    ) {
      toast.info("No provider credential changes.");
      return;
    }
    setProviderCredsSaving(true);
    try {
      const update: OrganizationUpdate = {};
      if (Object.keys(credentialInput).length > 0) {
        update.provider_credentials_input = credentialInput;
      }
      if (Object.keys(descriptionInput).length > 0) {
        update.provider_credentials_descriptions_input = descriptionInput;
      }
      const response = await organizationService.updateOrganization(orgId, update);
      setOrganizationData({ organization: response as OrganizationEnhanced });
      setProviderCredDescriptions(
        (response as OrganizationEnhanced).provider_credentials_descriptions ??
          {},
      );
      resetProviderCredDraft();
      resetProviderCredDescriptionDraft();
      toast.success("Provider credential changes saved");
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

  const markProviderCredDescriptionTouched = (key: string) => {
    setProviderCredDescriptionsTouched((prev) =>
      prev[key] ? prev : { ...prev, [key]: true },
    );
  };

  const clearProviderCredDescriptionTouched = (key: string) => {
    setProviderCredDescriptionsTouched((prev) => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const resetProviderCredDescription = (key: ProviderCredentialKey) => {
    setProviderCredDescriptions((prev) => ({
      ...prev,
      [key]: organizationData?.organization.provider_credentials_descriptions?.[
        key
      ] ?? "",
    }));
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
      setProviderCreds((prev) => ({ ...prev, [key]: "" }));
      clearProviderCredTouched(key);
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
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3 sm:gap-4">
            <div className="shrink-0 rounded-lg bg-primary/10 p-2">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-foreground sm:text-2xl">
                {displayOrg.name}
              </h1>
              <p className="text-sm text-muted-foreground">
                Manage organization settings and API credentials
              </p>
            </div>
          </div>

          {canUpdateOrganization && (
            <div className="flex items-center gap-2">
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

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="flex items-center text-sm text-muted-foreground">
            <Calendar className="h-4 w-4 mr-1" />
            Created {new Date(validatedOrg.created_at).toLocaleDateString()}
          </span>
          {userRoles.length > 0 && (
            <span className="flex items-center text-sm text-muted-foreground">
              <Crown className="h-4 w-4 mr-1" />
              {userRoles.length === 1
                ? userRoles[0].name
                : `${userRoles.length} roles`}
            </span>
          )}
        </div>
      </div>

      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList
          ref={settingsTabsListRef}
          aria-label="Organization settings"
          className="grid w-full grid-cols-2 overflow-visible sm:flex sm:flex-nowrap sm:justify-start sm:overflow-x-auto"
        >
          <TabsTrigger
            className="min-w-0 justify-center px-2 sm:shrink-0 sm:px-6"
            value="general"
          >
            General
          </TabsTrigger>
          <TabsTrigger
            className="min-w-0 justify-center px-2 sm:shrink-0 sm:px-6"
            value="credentials"
          >
            API Credentials
          </TabsTrigger>
          <TabsTrigger
            className="min-w-0 justify-center px-2 sm:shrink-0 sm:px-6"
            value="public-page"
          >
            Public page
          </TabsTrigger>
          {(isOrgAdmin || isPlatformAdmin) && (
            <TabsTrigger
              className="min-w-0 justify-center px-2 sm:shrink-0 sm:px-6"
              value="notifications"
            >
              Notifications
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="general" className="min-w-0">
          <section aria-label="General organization settings">
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

                          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
                            <Label htmlFor="timezone">Business timezone</Label>
                            <Select
                              value={editedOrg?.timezone ?? ORGANIZATION_TIMEZONE_UNSET}
                              onValueChange={(value) =>
                                editedOrg &&
                                setEditedOrg({
                                  ...editedOrg,
                                  timezone: value,
                                })
                              }
                            >
                              <SelectTrigger id="timezone">
                                <SelectValue placeholder="Select timezone" />
                              </SelectTrigger>
                              <SelectContent>
                                {ORGANIZATION_TIMEZONE_OPTIONS.map((option) => (
                                  <SelectItem key={option.value} value={option.value}>
                                    {option.label}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                              Used by voice agents for &quot;today&quot;, business hours, and
                              calendar availability. Leave as platform default until you pick
                              your zone.
                            </p>
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
                            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                              <Label htmlFor="business_details">
                                Business Context
                              </Label>
                              {orgId && editedOrg && (
                                <WebsiteBusinessContextGenerator
                                  organizationId={orgId}
                                  website={editedOrg.website}
                                  businessContext={editedOrg.business_details}
                                  onBusinessContextChange={(business_details) =>
                                    setEditedOrg((current) =>
                                      current
                                        ? { ...current, business_details }
                                        : current,
                                    )
                                  }
                                  disabled={saving}
                                />
                              )}
                            </div>
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
                          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
                              Timezone
                            </label>
                            <p className="text-foreground">
                              {displayOrg.timezone
                                ? ORGANIZATION_TIMEZONE_OPTIONS.find(
                                    (option) => option.value === displayOrg.timezone,
                                  )?.label ?? displayOrg.timezone
                                : "Platform default"}
                            </p>
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
                    <CardFooter className="flex flex-col-reverse items-stretch gap-2 border-t bg-muted/20 p-5 sm:flex-row sm:items-center sm:justify-end">
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
          </section>
        </TabsContent>

        <TabsContent value="public-page" className="min-w-0">
          {organizationData?.organization ? (
            <PublicPageSettingsCard
              organization={organizationData.organization}
              canEdit={canUpdateOrganization}
              onUpdated={loadOrganizationData}
            />
          ) : null}
        </TabsContent>

        {(isOrgAdmin || isPlatformAdmin) && (
          <TabsContent value="notifications" className="min-w-0">
            {orgId ? (
              <OrganizationNotificationSettingsForm organizationId={orgId} />
            ) : null}
          </TabsContent>
        )}

        {/* Third-party API Credentials tab — per-provider API keys for the
            modular voice engine (Deepgram, OpenAI, Cartesia, Cerebras). A
            DEDICATED card with its own Save — separate from the main org form
            so the empty-string-clears-everything footgun can't wipe all keys at
            once. Feeds the encrypted provider_credentials blob the worker's
            per-org key resolver reads. */}
        <TabsContent value="credentials">
          <ProviderCredentialsCard
            status={
              organizationData?.organization?.provider_credentials_status
            }
            draft={providerCreds}
            onDraftChange={setProviderCreds}
            touched={providerCredsTouched}
            descriptions={providerCredDescriptions}
            descriptionTouched={providerCredDescriptionsTouched}
            onMarkTouched={markProviderCredTouched}
            onClearTouched={clearProviderCredTouched}
            onDescriptionChange={(key, value) =>
              setProviderCredDescriptions((prev) => ({
                ...prev,
                [key]: value,
              }))
            }
            onMarkDescriptionTouched={markProviderCredDescriptionTouched}
            onClearDescriptionTouched={clearProviderCredDescriptionTouched}
            onResetDescription={resetProviderCredDescription}
            onSave={handleSaveProviderCreds}
            onRemoveProvider={handleRemoveProviderCred}
            saving={providerCredsSaving}
            removingProvider={removingProviderCred}
            canUpdate={canUpdateOrganization}
          />
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
