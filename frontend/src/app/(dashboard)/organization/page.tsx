"use client";

import React, { useState, useCallback, useEffect, useRef } from "react";
import { useAuth } from "@/contexts/auth-context";
import { useOrganization } from "@/contexts/organization-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import { useOrganizationById } from "@/hooks/use-organization-by-id";
import { AccessDenied } from "@/components/ui/access-denied";
import { OrganizationEditDialog } from "@/components/organizations/organization-edit-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  KeyRound,
} from "lucide-react";
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
    google_api_key: string;
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
    livekit_api_key: "",
    livekit_api_secret: "",
  });
  const [providerCredsTouched, setProviderCredsTouched] = useState<
    Record<string, boolean>
  >({});
  const [providerCredsSaving, setProviderCredsSaving] = useState(false);

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
        google_api_key: org.google_api_key || "",
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

    // Store original data for rollback if needed
    const originalData = { ...organizationData };

    setSaving(true);
    try {
      const response = await organizationService.updateOrganization(orgId, {
        name: editedOrg.name,
        description: editedOrg.description,
        website: editedOrg.website,
        slug: editedOrg.slug,
        is_active: editedOrg.is_active,
        industry: editedOrg.industry,
        location: editedOrg.location,
        business_details: editedOrg.business_details,
        // Send empty string to clear, or the actual value. Don't default to null.
        google_api_key: editedOrg.google_api_key,
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
        google_api_key: org.google_api_key || "",
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
  const handleSaveProviderCreds = async () => {
    if (!orgId) return;
    const input: Record<
      string,
      string | { api_key: string; api_secret: string } | null
    > = {};
    const simpleKeys = [
      "google",
      "deepgram",
      "openai",
      "cartesia",
      "cerebras",
    ] as const;
    for (const key of simpleKeys) {
      if (providerCredsTouched[key]) {
        const val = providerCreds[key].trim();
        input[key] = val ? val : null;
      }
    }
    if (providerCredsTouched.livekit) {
      const apiKey = providerCreds.livekit_api_key.trim();
      const apiSecret = providerCreds.livekit_api_secret.trim();
      input.livekit = apiKey || apiSecret ? { api_key: apiKey, api_secret: apiSecret } : null;
    }
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
      // Reset the draft + touched flags (decrypted values never come back, so
      // inputs go blank again — the status pills reflect the new state).
      setProviderCreds({
        google: "",
        deepgram: "",
        openai: "",
        cartesia: "",
        cerebras: "",
        livekit_api_key: "",
        livekit_api_secret: "",
      });
      setProviderCredsTouched({});
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

      {/* N1 redesign: the org page is now settings-only. Phone Numbers,
          Skills, and AI Voice Agent moved to top-level routes. The
          redirect logic in `legacy-tab-redirect.ts` handles the legacy
          `?tab=...` URLs. The "Active" tab strip is gone, so this
          page renders directly as a single card. */}
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
                    <Label htmlFor="slug">Slug</Label>
                    <Input
                      id="slug"
                      value={editedOrg?.slug || ""}
                      onChange={(e) =>
                        editedOrg &&
                        setEditedOrg({ ...editedOrg, slug: e.target.value })
                      }
                      placeholder="organization-slug"
                    />
                    <p className="text-xs text-muted-foreground">
                      Used in URLs and API calls
                    </p>
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

                  <div className="space-y-2">
                    <Label htmlFor="google_api_key">
                      Google API Key
                    </Label>
                    <Input
                      id="google_api_key"
                      type="password"
                      value={editedOrg?.google_api_key || ""}
                      onChange={(e) =>
                        editedOrg &&
                        setEditedOrg({
                          ...editedOrg,
                          google_api_key: e.target.value,
                        })
                      }
                      placeholder="Enter your Google API key (leave empty to use platform key)"
                    />
                    <p className="text-xs text-muted-foreground">
                      If set, voice agents will use this API key instead of the platform key.
                      This allows billing to go directly to your Google Cloud project.
                    </p>
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
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Google API Key
                    </label>
                    <p className="text-foreground">
                      {displayOrg.google_api_key ? (
                        <span className="text-green-600 flex items-center gap-2">
                          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                          Configured
                        </span>
                      ) : (
                        <span className="text-muted-foreground">
                          Not configured (using platform key)
                        </span>
                      )}
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

      {/* Voice provider credentials (Phase 4). A DEDICATED card with its own
          Save — separate from the main org form so the empty-string-clears-
          everything footgun can't wipe all keys at once. Feeds the encrypted
          provider_credentials blob the worker's per-org key resolver reads. */}
      <Card>
        <CardHeader className="p-5 pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2 text-lg">
              <KeyRound className="h-5 w-5 text-muted-foreground" />
              <span>Voice Provider Credentials</span>
            </CardTitle>
          </div>
          <CardDescription>
            Per-provider API keys for the modular voice engine (Deepgram, OpenAI,
            Cartesia, Cerebras, LiveKit). Encrypted at rest; decrypted values are
            never shown. Enter a value to set it, clear the field to remove it.
            Untouched fields are left unchanged on save.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5 pt-0 space-y-5">
          {/* Status pills (read-only; derived from provider_credentials_status). */}
          <div className="flex flex-wrap gap-3">
            {(
              [
                "google",
                "deepgram",
                "openai",
                "cartesia",
                "cerebras",
                "livekit",
              ] as const
            ).map((key) => {
              const configured = Boolean(
                organizationData?.organization?.provider_credentials_status?.[
                  key
                ],
              );
              return (
                <div
                  key={key}
                  className="flex items-center gap-1.5 text-xs"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      configured ? "bg-green-500" : "bg-gray-400"
                    }`}
                  />
                  <span className="capitalize text-muted-foreground">
                    {key}
                  </span>
                  <span
                    className={
                      configured
                        ? "text-green-600 font-medium"
                        : "text-muted-foreground"
                    }
                  >
                    {configured ? "Configured" : "Not configured"}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Editable inputs (gated by canUpdateOrganization). */}
          {canUpdateOrganization ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <ProviderCredInput
                  label="Google API key"
                  value={providerCreds.google}
                  onChange={(v) => {
                    setProviderCreds({ ...providerCreds, google: v });
                    markProviderCredTouched("google");
                  }}
                  placeholder="Enter to set; clear to remove"
                />
                <ProviderCredInput
                  label="Deepgram API key"
                  value={providerCreds.deepgram}
                  onChange={(v) => {
                    setProviderCreds({ ...providerCreds, deepgram: v });
                    markProviderCredTouched("deepgram");
                  }}
                  placeholder="Enter to set; clear to remove"
                />
                <ProviderCredInput
                  label="OpenAI API key"
                  value={providerCreds.openai}
                  onChange={(v) => {
                    setProviderCreds({ ...providerCreds, openai: v });
                    markProviderCredTouched("openai");
                  }}
                  placeholder="Enter to set; clear to remove"
                />
                <ProviderCredInput
                  label="Cartesia API key"
                  value={providerCreds.cartesia}
                  onChange={(v) => {
                    setProviderCreds({ ...providerCreds, cartesia: v });
                    markProviderCredTouched("cartesia");
                  }}
                  placeholder="Enter to set; clear to remove"
                />
                <ProviderCredInput
                  label="Cerebras API key"
                  value={providerCreds.cerebras}
                  onChange={(v) => {
                    setProviderCreds({ ...providerCreds, cerebras: v });
                    markProviderCredTouched("cerebras");
                  }}
                  placeholder="Enter to set; clear to remove"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium">LiveKit</Label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <ProviderCredInput
                    label="LiveKit API key"
                    value={providerCreds.livekit_api_key}
                    onChange={(v) => {
                      setProviderCreds({
                        ...providerCreds,
                        livekit_api_key: v,
                      });
                      markProviderCredTouched("livekit");
                    }}
                    placeholder="API key"
                  />
                  <ProviderCredInput
                    label="LiveKit API secret"
                    value={providerCreds.livekit_api_secret}
                    onChange={(v) => {
                      setProviderCreds({
                        ...providerCreds,
                        livekit_api_secret: v,
                      });
                      markProviderCredTouched("livekit");
                    }}
                    placeholder="API secret"
                  />
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              You do not have permission to update provider credentials.
            </p>
          )}
        </CardContent>
        {canUpdateOrganization && (
          <CardFooter className="flex justify-end space-x-2 p-5 border-t bg-muted/20">
            <Button
              size="sm"
              onClick={handleSaveProviderCreds}
              disabled={providerCredsSaving}
              className="flex items-center space-x-2"
            >
              <Save className="h-4 w-4" />
              <span>
                {providerCredsSaving ? "Saving..." : "Save Credentials"}
              </span>
            </Button>
          </CardFooter>
        )}
      </Card>

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

/**
 * A single password-type provider-credential input with a label.
 *
 * Used by the "Voice Provider Credentials" card. `type="password"` so typed
 * keys are masked. The parent tracks touched state separately (see
 * `markProviderCredTouched`) so only edited fields are sent on save.
 */
function ProviderCredInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm font-medium">{label}</Label>
      <Input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}
