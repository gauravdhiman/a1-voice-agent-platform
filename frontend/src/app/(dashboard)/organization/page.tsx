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
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  TabsContent,
  TabsList,
  TabsTrigger,
  AnimatedTabs,
} from "@/components/ui/tabs";
import {
  Plus,
  Building2,
  Users,
  Calendar,
  Activity,
  CreditCard,
  Save,
  X,
  Crown,
  Bot,
  Edit3,
  Phone,
  Info,
  Zap,
  Eye,
  Search,
  Loader2,
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
import { agentService } from "@/services/agent-service";
import { VoiceAgent } from "@/types/agent";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import { AgentCard } from "@/components/agents/agent-card";
import { PhoneNumberDashboard } from "@/components/phone-numbers/phone-number-dashboard";
import { phoneNumberService } from "@/services/phone-number-service";
import { billingService } from "@/services/billing-service";
import { PhoneNumberWithAgent } from "@/types/phone-number";
import { skillService } from "@/services/skill-service";
import type { OrganizationSkill } from "@/types/skill";
import { Switch } from "@/components/ui/switch";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import ReactMarkdown from "react-markdown";
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
  const orgId = searchParams.get("org_id");

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [organizationData, setOrganizationData] =
    useState<OrganizationCompleteData | null>(null);
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<VoiceAgent[]>([]);

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

  // Agent management state
  const [selectedAgent, setSelectedAgent] = useState<VoiceAgent | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  // Phone number state
  const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumberWithAgent[]>([]);
  const [creditBalance, setCreditBalance] = useState(0);
  const [phoneNumbersLoading, setPhoneNumbersLoading] = useState(false);

  // Skills state
  const [orgSkills, setOrgSkills] = useState<OrganizationSkill[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<OrganizationSkill | null>(null);
  const [skillFilter, setSkillFilter] = useState("");
  const [createSkillOpen, setCreateSkillOpen] = useState(false);
  const [newSkill, setNewSkill] = useState({ name: "", slug: "", description: "", content: "" });
  const [creatingSkill, setCreatingSkill] = useState(false);
  const [seedingSkills, setSeedingSkills] = useState(false);
  const [editingSkill, setEditingSkill] = useState(false);
  const [editSkillData, setEditSkillData] = useState({ name: "", description: "", content: "" });
  const [savingSkill, setSavingSkill] = useState(false);

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

      // Load agents
      const orgAgents = await agentService.getOrgAgents(orgId);
      setAgents(orgAgents);
    } catch (error) {
      console.error("Failed to load organization data:", error);
      toast.error("Failed to load organization data");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  const loadSkills = useCallback(async () => {
    if (!orgId) return;
    setSkillsLoading(true);
    try {
      const skills = await skillService.getOrganizationSkills(orgId);
      setOrgSkills(skills);
    } catch (error) {
      console.error("Failed to load skills:", error);
    } finally {
      setSkillsLoading(false);
    }
  }, [orgId]);

  const loadPhoneNumbers = useCallback(async () => {
    if (!orgId) return;
    setPhoneNumbersLoading(true);
    try {
      const [numbersRes, balanceRes] = await Promise.all([
        phoneNumberService.getOrganizationNumbers(orgId),
        billingService.getCreditBalance(orgId),
      ]);
      setPhoneNumbers(numbersRes.items);
      setCreditBalance(balanceRes.total_credits);
    } catch (error) {
      console.error("Failed to load phone numbers:", error);
      toast.error("Failed to load phone numbers");
    } finally {
      setPhoneNumbersLoading(false);
    }
  }, [orgId]);

  // Load data when component mounts or orgId changes
  useEffect(() => {
    if (orgId) {
      loadOrganizationData();
      // Also load skills eagerly so they're ready when tab is clicked
      loadSkills();
    }
  }, [orgId, loadOrganizationData, loadSkills]);

  // Sync tab state with URL
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "overview" || tabParam === "ai-agent" || tabParam === "phone-numbers" || tabParam === "skills") {
      setActiveTab(tabParam);
      if (tabParam === "phone-numbers" && orgId) {
        loadPhoneNumbers();
      }
      if (tabParam === "skills" && orgId) {
        loadSkills();
      }
    }
  }, [searchParams, orgId, loadPhoneNumbers, loadSkills]);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value);
      router.push(`/organization?org_id=${orgId}&tab=${value}`, {
        scroll: false,
      });
      if (value === "phone-numbers") {
        loadPhoneNumbers();
      }
      if (value === "skills") {
        loadSkills();
      }
    },
    [router, orgId, loadPhoneNumbers, loadSkills],
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

  const handleAddAgent = () => {
    router.push(orgId ? `/agents/create?org_id=${orgId}` : "/agents/create");
  };

  const handleDeleteAgent = useCallback((agent: VoiceAgent) => {
    setSelectedAgent(agent);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteSuccess = useCallback(
    async (agentId: string) => {
      try {
        await agentService.deleteAgent(agentId);
        toast.success("Agent deleted successfully");
        setDeleteDialogOpen(false);
        setSelectedAgent(null);
        loadOrganizationData();
      } catch (error) {
        console.error("Failed to delete agent:", error);
        toast.error("Failed to delete agent");
        throw error;
      }
    },
    [loadOrganizationData],
  );

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

      <AnimatedTabs
        value={activeTab}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList className="w-full">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="ai-agent">AI Voice Agent</TabsTrigger>
          <TabsTrigger value="skills" className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Skills
          </TabsTrigger>
          <TabsTrigger value="phone-numbers" className="flex items-center gap-2">
            Phone Numbers
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <Card>
            <CardHeader className="p-5 pb-3">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <CardTitle className="flex items-center space-x-2 text-lg">
                    <Building2 className="h-5 w-5" />
                    <span>Organization Information</span>
                  </CardTitle>
                  <CardDescription>
                    {isEditing
                      ? "Edit your organization details"
                      : "Your organization details and settings"}
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
        </TabsContent>

        {/* AI Voice Agent Tab */}
        <TabsContent value="ai-agent">
          <div className="space-y-6">
            <Card>
              <CardHeader className="p-5 pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-2 text-lg">
                      <Phone className="h-5 w-5" />
                      <span>Voice Agents</span>
                    </CardTitle>
                    <CardDescription>
                      Manage your AI voice agents and their phone numbers
                    </CardDescription>
                  </div>
                  <Button size="sm" onClick={handleAddAgent}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Agent
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                {agents.length === 0 ? (
                  <div className="text-center py-8 bg-muted/20 rounded-lg border-2 border-dashed">
                    <Bot className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                    <p className="text-muted-foreground">
                      No voice agents configured yet
                    </p>
                    <Button
                      variant="link"
                      onClick={handleAddAgent}
                      className="mt-2"
                    >
                      Create your first agent
                    </Button>
                  </div>
                ) : (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {agents.map((agent) => (
                      <AgentCard
                        key={agent.id}
                        agent={agent}
                        view="grid"
                        onDelete={handleDeleteAgent}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Skills Tab — Split View: list on left, content on right */}
        <TabsContent value="skills">
          {skillsLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-2 text-sm text-muted-foreground">Loading skills...</span>
            </div>
          ) : orgSkills.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Zap className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No skills yet.</p>
                <p className="text-sm mt-1 mb-4">Seed built-in skills to get started, or create custom ones.</p>
                <div className="flex justify-center gap-3">
                  {(isOrgAdmin || isPlatformAdmin) && (
                    <>
                      <Button
                        variant="outline"
                        disabled={seedingSkills}
                        onClick={async () => {
                          if (!orgId) return;
                          setSeedingSkills(true);
                          try {
                            const result = await skillService.seedSkills(orgId);
                            toast.success(`Seeded ${result.seeded} built-in skills`);
                            loadSkills();
                          } catch {
                            toast.error("Failed to seed skills");
                          } finally {
                            setSeedingSkills(false);
                          }
                        }}
                      >
                        {seedingSkills ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Zap className="h-4 w-4 mr-2" />}
                        Seed Built-in Skills
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setNewSkill({ name: "", slug: "", description: "", content: "" });
                          setCreateSkillOpen(true);
                        }}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Create Custom Skill
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="flex gap-4 min-h-[500px]">
              {/* Left panel — skill list */}
              <div className="w-80 shrink-0 flex flex-col border rounded-lg bg-card">
                <div className="p-3 border-b space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{orgSkills.length} skills</span>
                    {(isOrgAdmin || isPlatformAdmin) && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setNewSkill({ name: "", slug: "", description: "", content: "" });
                          setCreateSkillOpen(true);
                        }}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Filter skills..."
                      value={skillFilter}
                      onChange={(e) => setSkillFilter(e.target.value)}
                      className="pl-8 h-8 text-sm"
                    />
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {orgSkills
                    .filter((s) =>
                      !skillFilter ||
                      s.name.toLowerCase().includes(skillFilter.toLowerCase()) ||
                      s.slug.toLowerCase().includes(skillFilter.toLowerCase()) ||
                      (s.description || "").toLowerCase().includes(skillFilter.toLowerCase())
                    )
                    .map((skill) => (
                      <div
                        key={skill.id}
                        className={`px-3 py-2.5 cursor-pointer border-b last:border-b-0 transition-colors ${
                          selectedSkill?.id === skill.id
                            ? "bg-primary/5 border-l-2 border-l-primary"
                            : "hover:bg-muted/50 border-l-2 border-l-transparent"
                        }`}
                        onClick={() => {
                          setSelectedSkill(skill);
                          setEditingSkill(false);
                        }}
                      >
                        <div className="flex items-center gap-1.5">
                          <Zap className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                          <span className="font-medium text-sm truncate">{skill.name}</span>
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5 ml-5">
                          <Badge
                            variant={skill.category === "built_in" ? "secondary" : "outline"}
                            className="text-[10px] px-1.5 py-0"
                          >
                            {skill.category === "built_in" ? "Built-in" : "Custom"}
                          </Badge>
                          {skill.version && (
                            <span className="text-[10px] text-muted-foreground">v{skill.version}</span>
                          )}
                        </div>
                      </div>
                    ))}
                </div>
              </div>

              {/* Right panel — skill content */}
              <div className="flex-1 border rounded-lg bg-card flex flex-col min-w-0">
                {selectedSkill ? (
                  <>
                    {/* Header */}
                    <div className="p-4 border-b">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-lg">{selectedSkill.name}</h3>
                          <Badge
                            variant={selectedSkill.category === "built_in" ? "secondary" : "outline"}
                            className="text-xs"
                          >
                            {selectedSkill.category === "built_in" ? "Built-in" : "Custom"}
                          </Badge>
                        </div>
                        {selectedSkill.category === "custom" && (isOrgAdmin || isPlatformAdmin) && !editingSkill && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setEditSkillData({
                                name: selectedSkill.name || "",
                                description: selectedSkill.description || "",
                                content: selectedSkill.content || "",
                              });
                              setEditingSkill(true);
                            }}
                          >
                            <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                          </Button>
                        )}
                      </div>
                      {selectedSkill.description && !editingSkill && (
                        <p className="text-sm text-muted-foreground mt-1">{selectedSkill.description}</p>
                      )}
                      <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                        {selectedSkill.author && <span><strong>Author:</strong> {selectedSkill.author}</span>}
                        {selectedSkill.version && <span><strong>Version:</strong> {selectedSkill.version}</span>}
                        <span><strong>Mode:</strong> {selectedSkill.category === "built_in" ? "Read only" : "Editable"}</span>
                        <span><strong>Slug:</strong> <code className="text-xs bg-muted px-1 py-0.5 rounded">{selectedSkill.slug}</code></span>
                      </div>
                    </div>

                    {/* Content area */}
                    {editingSkill ? (
                      <>
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                          <div className="space-y-2">
                            <Label htmlFor="edit-skill-name">Name</Label>
                            <Input
                              id="edit-skill-name"
                              value={editSkillData.name}
                              onChange={(e) => setEditSkillData({ ...editSkillData, name: e.target.value })}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="edit-skill-desc">Description</Label>
                            <Input
                              id="edit-skill-desc"
                              value={editSkillData.description}
                              onChange={(e) => setEditSkillData({ ...editSkillData, description: e.target.value })}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="edit-skill-content">Content (Markdown)</Label>
                            <Textarea
                              id="edit-skill-content"
                              value={editSkillData.content}
                              onChange={(e) => setEditSkillData({ ...editSkillData, content: e.target.value })}
                              className="min-h-[300px] font-mono text-sm"
                            />
                          </div>
                        </div>
                        <div className="p-4 border-t flex justify-end gap-2">
                          <Button variant="outline" onClick={() => setEditingSkill(false)}>
                            Cancel
                          </Button>
                          <Button
                            disabled={savingSkill || !editSkillData.name || !editSkillData.content}
                            onClick={async () => {
                              if (!orgId || !selectedSkill) return;
                              setSavingSkill(true);
                              try {
                                const updated = await skillService.updateSkill(orgId, selectedSkill.id, {
                                  name: editSkillData.name,
                                  description: editSkillData.description || undefined,
                                  content: editSkillData.content,
                                });
                                toast.success("Skill updated");
                                setSelectedSkill(updated);
                                setEditingSkill(false);
                                loadSkills();
                              } catch {
                                toast.error("Failed to update skill");
                              } finally {
                                setSavingSkill(false);
                              }
                            }}
                          >
                            {savingSkill ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Save Changes
                          </Button>
                        </div>
                      </>
                    ) : (
                      <div className="flex-1 overflow-y-auto p-5 prose prose-sm prose-slate max-w-none">
                        <ReactMarkdown>{selectedSkill.content}</ReactMarkdown>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-muted-foreground">
                    <div className="text-center">
                      <Zap className="h-10 w-10 mx-auto mb-3 opacity-30" />
                      <p className="text-sm">Select a skill to view its content</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </TabsContent>

        {/* Create Skill Drawer */}
        <Sheet open={createSkillOpen} onOpenChange={setCreateSkillOpen}>
          <SheetContent className="flex flex-col w-full sm:max-w-xl">
            <SheetHeader className="px-6 pt-6 pb-4 border-b">
              <SheetTitle>Create Custom Skill</SheetTitle>
              <SheetDescription>
                Define a reusable skill with procedures and knowledge in markdown.
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="skill-name">Name</Label>
                <Input
                  id="skill-name"
                  value={newSkill.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
                    setNewSkill({ ...newSkill, name, slug });
                  }}
                  placeholder="e.g., Insurance Verification"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="skill-slug">Slug</Label>
                <Input
                  id="skill-slug"
                  value={newSkill.slug}
                  onChange={(e) => setNewSkill({ ...newSkill, slug: e.target.value })}
                  placeholder="e.g., insurance-verification"
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  URL-safe identifier. Auto-generated from name.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="skill-description">Description</Label>
                <Input
                  id="skill-description"
                  value={newSkill.description}
                  onChange={(e) => setNewSkill({ ...newSkill, description: e.target.value })}
                  placeholder="Short description for skill selection"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="skill-content">Skill Content (Markdown)</Label>
                <Textarea
                  id="skill-content"
                  value={newSkill.content}
                  onChange={(e) => setNewSkill({ ...newSkill, content: e.target.value })}
                  placeholder={`# Insurance Verification

## When to Use
- Caller asks about insurance coverage
- New patient needs insurance verified

## Procedure
1. Ask for insurance provider name
2. Request member ID and group number
3. Verify coverage using the system
4. Confirm copay and deductible amounts`}
                  className="min-h-[300px] font-mono text-sm"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-2">
              <Button variant="outline" onClick={() => setCreateSkillOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={creatingSkill || !newSkill.name || !newSkill.slug || !newSkill.content}
                onClick={async () => {
                  if (!orgId) return;
                  setCreatingSkill(true);
                  try {
                    await skillService.createSkill(orgId, {
                      organization_id: orgId,
                      slug: newSkill.slug,
                      name: newSkill.name,
                      description: newSkill.description || undefined,
                      content: newSkill.content,
                      category: "custom",
                    });
                    toast.success(`Skill "${newSkill.name}" created`);
                    setCreateSkillOpen(false);
                    loadSkills();
                  } catch (err) {
                    const msg = err instanceof Error ? err.message : "Failed to create skill";
                    toast.error(msg);
                  } finally {
                    setCreatingSkill(false);
                  }
                }}
              >
                {creatingSkill ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
                Create Skill
              </Button>
            </div>
          </SheetContent>
        </Sheet>

        {/* Phone Numbers Tab */}
        <TabsContent value="phone-numbers">
          <PhoneNumberDashboard
            organizationId={orgId!}
            phoneNumbers={phoneNumbers}
            creditBalance={creditBalance}
            isLoading={phoneNumbersLoading}
            onRefresh={loadPhoneNumbers}
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

      {/* Agent Delete Dialog */}
      {selectedAgent && (
        <AgentDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          agent={selectedAgent}
          onSuccess={handleDeleteSuccess}
        />
      )}
    </div>
  );
}
