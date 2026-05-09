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
  EyeOff,
  Library,
  RefreshCw,
  GitFork,
  Search,
  Loader2,
  ChevronRight,
  ChevronDown,
  FileText,
  FolderOpen,
  Import,
  Trash2,
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());
  const [skillFiles, setSkillFiles] = useState<Record<string, import("@/types/skill").SkillFileSummary[]>>({});
  const [selectedFile, setSelectedFile] = useState<{ skillId: string; filePath: string; content?: string } | null>(null);
  const [importSheetOpen, setImportSheetOpen] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [loadingFileContent, setLoadingFileContent] = useState(false);
  const [deleteSkillOpen, setDeleteSkillOpen] = useState(false);
  const [deleteSkillAgents, setDeleteSkillAgents] = useState<Array<{ id: string; name: string; is_active: boolean }>>([]);
  const [deletingSkill, setDeletingSkill] = useState(false);
  const [addFileOpen, setAddFileOpen] = useState(false);
  const [addFileSkillId, setAddFileSkillId] = useState<string | null>(null);
  const [newFile, setNewFile] = useState({ file_path: "", content: "", file_kind: "reference" });
  const [creatingFile, setCreatingFile] = useState(false);
  const [editingFile, setEditingFile] = useState(false);
  const [editFileData, setEditFileData] = useState({ filePath: "", content: "", fileId: "" });
  const [savingFile, setSavingFile] = useState(false);

  // Platform skills library
  const [browsePlatformOpen, setBrowsePlatformOpen] = useState(false);
  const [platformSkills, setPlatformSkills] = useState<import("@/types/skill").PlatformSkillSummary[]>([]);
  const [platformSkillFilter, setPlatformSkillFilter] = useState("");
  const [loadingPlatform, setLoadingPlatform] = useState(false);
  const [forkingSkillId, setForkingSkillId] = useState<string | null>(null);

  // Refresh
  const [refreshConfirmOpen, setRefreshConfirmOpen] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<{
    update_available: boolean;
    latest_version: string;
    current_version: string | null;
  } | null>(null);

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

  const handleImportSubmit = useCallback(async () => {
    if (!orgId || !importUrl.trim()) return;
    if (importing) return;
    setImporting(true);
    try {
      const results = await skillService.importSkill(orgId, importUrl.trim());
      const total = results.reduce((sum, r) => sum + r.files_imported, 0);
      toast.success(`Successfully imported ${results.length} skill(s) with ${total} files!`);
      setImportUrl("");
      setImportSheetOpen(false);
      loadSkills();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Import failed";
      toast.error(msg);
    } finally {
      setImporting(false);
    }
  }, [orgId, importUrl, importing, loadSkills]);

  const loadPlatformSkills = useCallback(async () => {
    setLoadingPlatform(true);
    try {
      const skills = await skillService.listPlatformSkills();
      setPlatformSkills(skills);
    } catch (error) {
      console.error("Failed to load platform skills:", error);
    } finally {
      setLoadingPlatform(false);
    }
  }, []);

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

  // Update URL when skill/file selection changes
  const updateSkillUrl = useCallback((skillSlug: string | null, filePath: string | null = null) => {
    const params = new URLSearchParams();
    if (orgId) params.set("org_id", orgId);
    params.set("tab", "skills");
    if (skillSlug) params.set("skill", skillSlug);
    if (filePath) params.set("file", filePath);
    router.replace(`/organization?${params.toString()}`, { scroll: false });
  }, [orgId, router]);

  // Restore selected skill/file from URL params after skills load
  useEffect(() => {
    if (orgSkills.length === 0) return;
    const skillSlug = searchParams.get("skill");
    const filePath = searchParams.get("file");
    if (skillSlug) {
      const skill = orgSkills.find((s) => s.slug === skillSlug);
      if (skill) {
        setSelectedSkill(skill);
        setExpandedSkills(new Set([skill.id]));
        // Fetch files for this skill
        if (orgId && !skillFiles[skill.id]) {
          skillService.getSkillFiles(orgId, skill.id).then((f) => {
            setSkillFiles((prev) => ({ ...prev, [skill.id]: f }));
          });
        }
        // Restore selected file
        if (filePath && orgId) {
          skillService.getSkillFileContent(orgId, skill.slug, filePath).then((content) => {
            setSelectedFile({ skillId: skill.id, filePath, content });
          }).catch(() => {});
        }
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgSkills]);

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
                <p className="text-sm mt-1 mb-4">Browse the platform skill library to add pre-built capabilities, or create a custom skill.</p>
                <div className="flex justify-center gap-3">
                  {(isOrgAdmin || isPlatformAdmin) && (
                    <>
                      <Button
                        variant="outline"
                        onClick={() => {
                          loadPlatformSkills();
                          setPlatformSkillFilter("");
                          setBrowsePlatformOpen(true);
                        }}
                      >
                        <Library className="h-4 w-4 mr-2" />
                        Browse Platform Library
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
            <div className="flex gap-4 h-[calc(100vh-180px)] overflow-hidden">
              {/* Left panel — skill list with expandable file tree */}
              <div className="w-80 shrink-0 flex flex-col border rounded-lg bg-card h-full overflow-hidden">
                <div className="p-3 border-b space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{orgSkills.length} skills</span>
                    {(isOrgAdmin || isPlatformAdmin) && (
                      <>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="outline" size="sm">
                              <Plus className="h-4 w-4 mr-1" />
                              Add
                              <ChevronDown className="h-3 w-3 ml-1" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => {
                                loadPlatformSkills();
                                setPlatformSkillFilter("");
                                setBrowsePlatformOpen(true);
                              }}
                            >
                              <Library className="h-4 w-4 mr-2" />
                              Create from Platform Library
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                setNewSkill({ name: "", slug: "", description: "", content: "" });
                                setCreateSkillOpen(true);
                              }}
                            >
                              <Plus className="h-4 w-4 mr-2" />
                              Create Custom Skill
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                setImportUrl("");
                                setImportSheetOpen(true);
                              }}
                            >
                              <Import className="h-4 w-4 mr-2" />
                              Import from URL
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </>
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
                    .map((skill) => {
                      const isExpanded = expandedSkills.has(skill.id);
                      const files = skillFiles[skill.id] || [];
                      return (
                        <div key={skill.id}>
                          {/* Skill row — single click opens accordion + selects */}
                          <div
                            className={`group px-3 py-2.5 cursor-pointer border-b transition-colors ${
                              selectedSkill?.id === skill.id && !selectedFile
                                ? "bg-primary/5 border-l-2 border-l-primary"
                                : "hover:bg-muted/50 border-l-2 border-l-transparent"
                            }`}
                            onClick={() => {
                              // Select this skill and show SKILL.md content
                              setSelectedSkill(skill);
                              setSelectedFile(null);
                              setEditingSkill(false);
                              setEditingFile(false);
                              updateSkillUrl(skill.slug);

                              // Toggle accordion — only one open at a time
                              if (isExpanded) {
                                setExpandedSkills(new Set());
                              } else {
                                setExpandedSkills(new Set([skill.id]));
                                // Fetch files if not loaded
                                if (!skillFiles[skill.id] && orgId) {
                                  skillService.getSkillFiles(orgId, skill.id).then((f) => {
                                    setSkillFiles((prev) => ({ ...prev, [skill.id]: f }));
                                  });
                                }
                              }
                            }}
                          >
                            <div className="flex items-center gap-1.5">
                              {isExpanded
                                ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                                : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                              }
                              <Zap className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                              <span className="font-medium text-sm truncate flex-1">{skill.name}</span>
                              {(isOrgAdmin || isPlatformAdmin) && (
                                <button
                                  className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-red-100"
                                  onClick={async (e) => {
                                    e.stopPropagation();
                                    if (!orgId) return;
                                    try {
                                      const agents = await skillService.getAgentsUsingSkill(orgId, skill.id);
                                      setDeleteSkillAgents(agents);
                                    } catch {
                                      setDeleteSkillAgents([]);
                                    }
                                    setSelectedSkill(skill);
                                    setDeleteSkillOpen(true);
                                  }}
                                >
                                  <Trash2 className="h-3.5 w-3.5 text-red-400 hover:text-red-600" />
                                </button>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 mt-0.5 ml-8">
                              <Badge
                                variant={skill.source_skill_id ? "secondary" : "outline"}
                                className="text-[11px] px-1.5 py-0"
                              >
                                {skill.source_skill_id ? "Platform" : "Custom"}
                              </Badge>
                              {skill.source_version && (
                                <span className="text-[11px] text-muted-foreground">v{skill.source_version}</span>
                              )}
                              {!skill.is_visible && (
                                <Badge variant="outline" className="text-[11px] px-1.5 py-0 border-orange-200 text-orange-600 bg-orange-50">
                                  <EyeOff className="h-3 w-3 mr-1" />
                                  Hidden
                                </Badge>
                              )}
                            </div>
                          </div>

                          {/* Expanded file tree */}
                          {isExpanded && (
                            <div className="border-b bg-muted/20">
                              {/* SKILL.md (entry file) */}
                              <div
                                className={`pl-10 pr-3 py-1.5 cursor-pointer text-sm flex items-center gap-1.5 transition-colors ${
                                  selectedSkill?.id === skill.id && !selectedFile
                                    ? "bg-primary/10 text-primary font-medium"
                                    : "hover:bg-muted/50 text-muted-foreground"
                                }`}
                                onClick={() => {
                                  setSelectedSkill(skill);
                                  setSelectedFile(null);
                                  setEditingSkill(false);
                                  setEditingFile(false);
                                  updateSkillUrl(skill.slug);
                                }}
                              >
                                <FileText className="h-3 w-3 shrink-0" />
                                <span className="truncate">SKILL.md</span>
                                <Badge variant="outline" className="text-[10px] px-1 py-0 ml-auto">ENTRY</Badge>
                              </div>

                              {/* Reference files grouped by folder */}
                              {files.length > 0 ? (
                                (() => {
                                  // Group files by first directory
                                  const folders: Record<string, typeof files> = {};
                                  const rootFiles: typeof files = [];
                                  files.forEach((f) => {
                                    const parts = f.file_path.split("/");
                                    if (parts.length > 1) {
                                      const folder = parts[0];
                                      if (!folders[folder]) folders[folder] = [];
                                      folders[folder].push(f);
                                    } else {
                                      rootFiles.push(f);
                                    }
                                  });

                                  return (
                                    <>
                                      {Object.entries(folders).map(([folder, folderFiles]) => (
                                        <div key={folder}>
                                          <div className="pl-10 pr-3 py-1.5 text-sm text-muted-foreground font-medium flex items-center gap-1.5">
                                            <FolderOpen className="h-3 w-3" />
                                            {folder}
                                          </div>
                                          {folderFiles.map((f) => (
                                            <div
                                              key={f.id}
                                              className={`pl-14 pr-3 py-1.5 cursor-pointer text-sm flex items-center gap-1.5 transition-colors ${
                                                selectedFile?.filePath === f.file_path && selectedSkill?.id === skill.id
                                                  ? "bg-primary/10 text-primary font-medium"
                                                  : "hover:bg-muted/50 text-muted-foreground"
                                              }`}
                                              onClick={async () => {
                                                setSelectedSkill(skill);
                                                setSelectedFile({ skillId: skill.id, filePath: f.file_path });
                                                setEditingSkill(false);
                                                updateSkillUrl(skill.slug, f.file_path);
                                                if (orgId) {
                                                  setLoadingFileContent(true);
                                                  try {
                                                    const content = await skillService.getSkillFileContent(
                                                      orgId, skill.slug, f.file_path
                                                    );
                                                    setSelectedFile({ skillId: skill.id, filePath: f.file_path, content });
                                                  } catch {
                                                    toast.error("Failed to load file content");
                                                  }
                                                  setLoadingFileContent(false);
                                                }
                                              }}
                                            >
                                              <FileText className="h-3 w-3 shrink-0" />
                                              <span className="truncate">{f.file_path.split("/").pop()}</span>
                                            </div>
                                          ))}
                                        </div>
                                      ))}
                                      {rootFiles.map((f) => (
                                        <div
                                          key={f.id}
                                          className={`pl-10 pr-3 py-1.5 cursor-pointer text-sm flex items-center gap-1.5 transition-colors ${
                                            selectedFile?.filePath === f.file_path && selectedSkill?.id === skill.id
                                              ? "bg-primary/10 text-primary font-medium"
                                              : "hover:bg-muted/50 text-muted-foreground"
                                          }`}
                                          onClick={async () => {
                                            setSelectedSkill(skill);
                                            setSelectedFile({ skillId: skill.id, filePath: f.file_path });
                                            setEditingSkill(false);
                                            updateSkillUrl(skill.slug, f.file_path);
                                            if (orgId) {
                                              setLoadingFileContent(true);
                                              try {
                                                const content = await skillService.getSkillFileContent(
                                                  orgId, skill.slug, f.file_path
                                                );
                                                setSelectedFile({ skillId: skill.id, filePath: f.file_path, content });
                                              } catch {
                                                toast.error("Failed to load file content");
                                              }
                                              setLoadingFileContent(false);
                                            }
                                          }}
                                        >
                                          <FileText className="h-3 w-3 shrink-0" />
                                          <span className="truncate">{f.file_path}</span>
                                        </div>
                                      ))}
                                    </>
                                  );
                                })()
                              ) : (
                                <div className="pl-10 pr-3 py-1.5 text-xs text-muted-foreground italic">
                                  No reference files
                                </div>
                              )}

                              {/* Add File button */}
                              {(isOrgAdmin || isPlatformAdmin) && (
                                <div
                                  className="pl-10 pr-3 py-1.5 cursor-pointer text-xs text-primary hover:bg-muted/50 flex items-center gap-1.5"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setAddFileSkillId(skill.id);
                                    setNewFile({ file_path: "", content: "", file_kind: "reference" });
                                    setAddFileOpen(true);
                                  }}
                                >
                                  <Plus className="h-3 w-3" />
                                  <span>Add file</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Right panel — skill content */}
              <div className="flex-1 border rounded-lg bg-card flex flex-col min-w-0 h-full overflow-hidden">
                {selectedSkill ? (
                  <>
                    {/* Header */}
                    <div className="p-4 border-b">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-lg">{selectedSkill.name}</h3>
                          <Badge
                            variant={selectedSkill.source_skill_id ? "secondary" : "outline"}
                            className="text-xs"
                          >
                            {selectedSkill.source_skill_id ? "Platform" : "Custom"}
                          </Badge>
                          {!selectedSkill.is_visible && (
                            <Badge variant="outline" className="text-xs border-orange-200 text-orange-600 bg-orange-50">
                              <EyeOff className="h-3 w-3 mr-1" /> Hidden
                            </Badge>
                          )}
                        </div>
                        {(isOrgAdmin || isPlatformAdmin) && !editingSkill && !editingFile && (
                          <>
                            <div className="flex items-center gap-1.5">
                            {/* Edit SKILL.md — when no file is selected */}
                            {!selectedFile && (
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
                            {/* Edit reference file — when a file is selected */}
                            {selectedFile?.content !== undefined && selectedFile?.skillId === selectedSkill.id && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  const files = skillFiles[selectedSkill.id] || [];
                                  const fileEntry = files.find((f) => f.file_path === selectedFile.filePath);
                                  setEditFileData({
                                    filePath: selectedFile.filePath,
                                    content: selectedFile.content || "",
                                    fileId: fileEntry?.id || "",
                                  });
                                  setEditingFile(true);
                                }}
                              >
                                <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                              </Button>
                            )}
                            {/* Visibility toggle */}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={async () => {
                                if (!orgId) return;
                                try {
                                  await skillService.updateSkill(orgId, selectedSkill.id, {
                                    is_visible: !selectedSkill.is_visible,
                                  });
                                  toast.success(selectedSkill.is_visible ? "Skill hidden from library" : "Skill visible in library");
                                  loadSkills();
                                } catch {
                                  toast.error("Failed to update visibility");
                                }
                              }}
                              title={selectedSkill.is_visible ? "Hide from library" : "Show in library"}
                            >
                              {selectedSkill.is_visible ? (
                                <><Eye className="h-3.5 w-3.5 mr-1" /> Hide</>
                              ) : (
                                <><EyeOff className="h-3.5 w-3.5 mr-1" /> Show</>
                              )}
                            </Button>
                            {/* Refresh (only for forked skills) */}
                            {selectedSkill.source_skill_id && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={async () => {
                                  if (!orgId) return;
                                  setCheckingUpdate(true);
                                  try {
                                    const info = await skillService.checkUpdateAvailable(orgId, selectedSkill.id);
                                    setUpdateInfo(info);
                                    if (info.update_available) {
                                      setRefreshConfirmOpen(true);
                                    } else {
                                      toast.success("Skill is up to date");
                                    }
                                  } catch {
                                    toast.error("Failed to check for updates");
                                  } finally {
                                    setCheckingUpdate(false);
                                  }
                                }}
                                disabled={checkingUpdate}
                              >
                                {checkingUpdate ? (
                                  <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                                ) : (
                                  <><RefreshCw className="h-3.5 w-3.5 mr-1" /> Check Update</>
                                )}
                              </Button>
                            )}
                            </div>
                          </>
                        )}
                      </div>
                      {selectedSkill.description && !editingSkill && (
                        <p className="text-sm text-muted-foreground mt-1">{selectedSkill.description}</p>
                      )}
                      <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                        {selectedSkill.author && <span><strong>Author:</strong> {selectedSkill.author}</span>}
                        {selectedSkill.version && <span><strong>Version:</strong> {selectedSkill.version}</span>}
                        {selectedSkill.source_version && <span><strong>Source:</strong> v{selectedSkill.source_version}</span>}
                        <span><strong>Mode:</strong> Editable</span>
                        <span><strong>Slug:</strong> <code className="text-xs bg-muted px-1 py-0.5 rounded">{selectedSkill.slug}</code></span>
                      </div>
                    </div>

                    {/* Content area */}
                    {editingSkill ? (
                      /* Editing SKILL.md — show skill name, skill description, skill content */
                      <>
                        <div className="px-4 py-2 border-b bg-muted/30 text-xs text-muted-foreground">
                          Editing SKILL.md
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                          <div className="space-y-2">
                            <Label htmlFor="edit-skill-name">Skill Name</Label>
                            <Input
                              id="edit-skill-name"
                              value={editSkillData.name}
                              onChange={(e) => setEditSkillData({ ...editSkillData, name: e.target.value })}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="edit-skill-desc">Skill Description</Label>
                            <Input
                              id="edit-skill-desc"
                              value={editSkillData.description}
                              onChange={(e) => setEditSkillData({ ...editSkillData, description: e.target.value })}
                            />
                            <p className="text-xs text-muted-foreground">
                              Short description shown in the agent&apos;s prompt metadata and skill selection UI.
                            </p>
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="edit-skill-content">Skill Content (Markdown)</Label>
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
                    ) : editingFile ? (
                      /* Editing a reference file — show file path and content only */
                      <>
                        <div className="px-4 py-2 border-b bg-muted/30 text-xs text-muted-foreground">
                          Editing file
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                          <div className="space-y-2">
                            <Label htmlFor="edit-file-path">File Path</Label>
                            <Input
                              id="edit-file-path"
                              value={editFileData.filePath}
                              onChange={(e) => setEditFileData({ ...editFileData, filePath: e.target.value })}
                              className="font-mono text-sm"
                            />
                            <p className="text-xs text-muted-foreground">
                              Full path including folders, e.g. &quot;references/cancellation-policy.md&quot;
                            </p>
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="edit-file-content">Content</Label>
                            <Textarea
                              id="edit-file-content"
                              value={editFileData.content}
                              onChange={(e) => setEditFileData({ ...editFileData, content: e.target.value })}
                              className="min-h-[300px] font-mono text-sm"
                            />
                          </div>
                        </div>
                        <div className="p-4 border-t flex justify-end gap-2">
                          <Button variant="outline" onClick={() => setEditingFile(false)}>
                            Cancel
                          </Button>
                          <Button
                            disabled={savingFile || !editFileData.filePath.trim() || !editFileData.content.trim()}
                            onClick={async () => {
                              if (!orgId || !selectedSkill || !editFileData.fileId) return;
                              setSavingFile(true);
                              try {
                                await skillService.updateSkillFile(
                                  orgId, selectedSkill.id, editFileData.fileId,
                                  { file_path: editFileData.filePath, content: editFileData.content }
                                );
                                toast.success("File updated");
                                setEditingFile(false);
                                // Refresh the file content in view with new path
                                setSelectedFile({
                                  skillId: selectedSkill.id,
                                  filePath: editFileData.filePath,
                                  content: editFileData.content,
                                });
                                // Update URL to reflect new file path
                                updateSkillUrl(selectedSkill.slug, editFileData.filePath);
                                // Refresh file list
                                const updatedFiles = await skillService.getSkillFiles(orgId, selectedSkill.id);
                                setSkillFiles((prev) => ({ ...prev, [selectedSkill!.id]: updatedFiles }));
                              } catch {
                                toast.error("Failed to update file");
                              } finally {
                                setSavingFile(false);
                              }
                            }}
                          >
                            {savingFile ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                            Save Changes
                          </Button>
                        </div>
                      </>
                    ) : selectedFile?.content !== undefined && selectedFile?.skillId === selectedSkill.id ? (
                      /* Show selected reference file content (read mode) */
                      <>
                        <div className="px-4 py-2 border-b bg-muted/30 flex items-center text-xs text-muted-foreground">
                          <div className="flex items-center gap-2">
                            <FileText className="h-3.5 w-3.5" />
                            <code>{selectedFile.filePath}</code>
                          </div>
                        </div>
                        {selectedFile.filePath.endsWith(".json") ? (
                          <div className="flex-1 overflow-y-auto p-5">
                            <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">
                              {(() => {
                                try {
                                  return JSON.stringify(JSON.parse(selectedFile.content), null, 2);
                                } catch {
                                  return selectedFile.content;
                                }
                              })()}
                            </pre>
                          </div>
                        ) : selectedFile.filePath.match(/\.(py|js|ts|sh|bash|yaml|yml|toml)$/) ? (
                          <div className="flex-1 overflow-y-auto p-5">
                            <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">
                              {selectedFile.content}
                            </pre>
                          </div>
                        ) : (
                          <div className="flex-1 overflow-y-auto p-5 prose prose-sm prose-slate max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedFile.content}</ReactMarkdown>
                          </div>
                        )}
                      </>
                    ) : loadingFileContent ? (
                      <div className="flex-1 flex items-center justify-center">
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      </div>
                    ) : (
                      /* Show main SKILL.md content */
                      <div className="flex-1 overflow-y-auto p-5 prose prose-sm prose-slate max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedSkill.content}</ReactMarkdown>
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

        {/* Delete Skill Confirmation */}
        <Dialog open={deleteSkillOpen} onOpenChange={setDeleteSkillOpen}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Delete skill: {selectedSkill?.name}?</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                This will permanently delete this skill and all its reference files.
              </p>
              {deleteSkillAgents.length > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm font-medium text-amber-800">
                    This skill is currently used by {deleteSkillAgents.length} agent{deleteSkillAgents.length > 1 ? "s" : ""}:
                  </p>
                  <ul className="mt-1.5 space-y-1">
                    {deleteSkillAgents.map((agent) => (
                      <li key={agent.id} className="text-sm text-amber-700 flex items-center gap-1.5">
                        <span>{agent.name}</span>
                        {!agent.is_active && (
                          <span className="text-xs text-amber-500">(inactive)</span>
                        )}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-amber-600 mt-2">
                    Deleting will automatically unassign this skill from these agents.
                  </p>
                </div>
              )}
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={() => setDeleteSkillOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                disabled={deletingSkill}
                onClick={async () => {
                  if (!orgId || !selectedSkill) return;
                  setDeletingSkill(true);
                  try {
                    await skillService.deleteSkill(orgId, selectedSkill.id);
                    toast.success(`Skill "${selectedSkill.name}" deleted`);
                    setSelectedSkill(null);
                    setSelectedFile(null);
                    setDeleteSkillOpen(false);
                    updateSkillUrl(null);
                    loadSkills();
                  } catch {
                    toast.error("Failed to delete skill");
                  } finally {
                    setDeletingSkill(false);
                  }
                }}
              >
                {deletingSkill ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
                Delete Skill
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Add File to Skill Drawer */}
        <Sheet open={addFileOpen} onOpenChange={setAddFileOpen}>
          <SheetContent className="flex flex-col w-full sm:max-w-xl">
            <SheetHeader className="px-6 pt-6 pb-4 border-b">
              <SheetTitle>Add File to Skill</SheetTitle>
              <SheetDescription>
                Add a reference file, script, or asset to this skill. Use folder paths like
                &quot;references/policies.md&quot; to organize files into folders.
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="new-file-path">File Path</Label>
                <Input
                  id="new-file-path"
                  value={newFile.file_path}
                  onChange={(e) => setNewFile({ ...newFile, file_path: e.target.value })}
                  placeholder="e.g., references/cancellation-policy.md"
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Use &quot;/&quot; to create folders. Example: &quot;references/my-doc.md&quot;, &quot;scripts/validate.py&quot;
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-file-kind">File Type</Label>
                <select
                  id="new-file-kind"
                  value={newFile.file_kind}
                  onChange={(e) => setNewFile({ ...newFile, file_kind: e.target.value })}
                  className="w-full px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  <option value="reference">Reference (documentation)</option>
                  <option value="script">Script (code)</option>
                  <option value="asset">Asset (data)</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-file-content">Content</Label>
                <Textarea
                  id="new-file-content"
                  value={newFile.content}
                  onChange={(e) => setNewFile({ ...newFile, content: e.target.value })}
                  placeholder="File content..."
                  className="min-h-[300px] font-mono text-sm"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-end gap-2">
              <Button variant="outline" onClick={() => setAddFileOpen(false)}>
                Cancel
              </Button>
              <Button
                disabled={creatingFile || !newFile.file_path.trim() || !newFile.content.trim()}
                onClick={async () => {
                  if (!orgId || !addFileSkillId) return;
                  setCreatingFile(true);
                  try {
                    await skillService.createSkillFile(orgId, addFileSkillId, {
                      file_path: newFile.file_path.trim(),
                      content: newFile.content,
                      file_kind: newFile.file_kind,
                    });
                    toast.success(`File "${newFile.file_path}" created`);
                    setAddFileOpen(false);
                    // Refresh file list for this skill
                    const updatedFiles = await skillService.getSkillFiles(orgId, addFileSkillId);
                    setSkillFiles((prev) => ({ ...prev, [addFileSkillId!]: updatedFiles }));
                  } catch (err) {
                    const msg = err instanceof Error ? err.message : "Failed to create file";
                    toast.error(msg);
                  } finally {
                    setCreatingFile(false);
                  }
                }}
              >
                {creatingFile ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />}
                Add File
              </Button>
            </div>
          </SheetContent>
        </Sheet>

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

        {/* Platform Skills Browser Sheet */}
        <Sheet open={browsePlatformOpen} onOpenChange={setBrowsePlatformOpen}>
          <SheetContent className="flex flex-col w-full sm:max-w-xl">
            <SheetHeader className="px-6 pt-6 pb-4 border-b">
              <SheetTitle className="flex items-center gap-2">
                <Library className="h-5 w-5" />
                Platform Skill Library
              </SheetTitle>
              <SheetDescription>
                Fork pre-built capabilities into your organization&apos;s library.
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {loadingPlatform ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span className="ml-2 text-sm text-muted-foreground">Loading platform skills...</span>
                </div>
              ) : platformSkills.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Library className="h-10 w-10 mx-auto mb-3 opacity-50" />
                  <p>No platform skills available yet.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <Input
                      placeholder="Filter platform skills..."
                      value={platformSkillFilter}
                      onChange={(e) => setPlatformSkillFilter(e.target.value)}
                      className="pl-8 h-9 text-sm"
                    />
                  </div>
                  <div className="space-y-4">
                    {platformSkills
                      .filter((s) =>
                        !platformSkillFilter ||
                        s.name.toLowerCase().includes(platformSkillFilter.toLowerCase()) ||
                        (s.description || "").toLowerCase().includes(platformSkillFilter.toLowerCase())
                      )
                      .map((skill) => (
                        <div key={skill.id} className="border rounded-lg p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-sm">{skill.name}</h4>
                            <Badge variant="secondary" className="text-[11px]">v{skill.version}</Badge>
                          </div>
                          {skill.description && (
                            <p className="text-xs text-muted-foreground leading-relaxed">{skill.description}</p>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full"
                            disabled={forkingSkillId === skill.id}
                            onClick={async () => {
                              if (!orgId) return;
                              setForkingSkillId(skill.id);
                              try {
                                const forked = await skillService.forkPlatformSkill(orgId, {
                                  platform_skill_id: skill.id,
                                });
                                toast.success(`Forked "${skill.name}" into your library`);
                                setOrgSkills((prev) => [forked, ...prev]);
                                setSelectedSkill(forked);
                                setExpandedSkills(new Set([forked.id]));
                                updateSkillUrl(forked.slug);
                                setBrowsePlatformOpen(false);
                                skillService.getSkillFiles(orgId, forked.id)
                                  .then((files) => setSkillFiles((prev) => ({ ...prev, [forked.id]: files })))
                                  .catch(() => {});
                              } catch (err) {
                                const rawMsg = err instanceof Error ? err.message : "Fork failed";
                                // Show friendly duplicate message
                                const msg = rawMsg.includes("already exists")
                                  ? `"${skill.name}" is already in your library. You can only have one copy of each platform skill.`
                                  : rawMsg;
                                toast.error(msg);
                              } finally {
                                setForkingSkillId(null);
                              }
                            }}
                          >
                            {forkingSkillId === skill.id ? (
                              <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                            ) : (
                              <GitFork className="h-3.5 w-3.5 mr-1" />
                            )}
                            Fork into Library
                          </Button>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t flex justify-end">
              <Button variant="outline" onClick={() => setBrowsePlatformOpen(false)}>
                Close
              </Button>
            </div>
          </SheetContent>
        </Sheet>

        {/* Refresh Confirmation Dialog */}
        {updateInfo && (
          <Dialog open={refreshConfirmOpen} onOpenChange={setRefreshConfirmOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Refresh Skill</DialogTitle>
                <DialogDescription>
                  This will replace all content and files with the latest platform version.
                  Any customizations you made will be lost.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-2 py-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Current version:</span>
                  <span>v{selectedSkill?.source_version || "unknown"}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Latest version:</span>
                  <span className="font-medium">v{updateInfo.latest_version}</span>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setRefreshConfirmOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="default"
                  onClick={async () => {
                    if (!orgId || !selectedSkill) return;
                    try {
                      await skillService.refreshSkill(orgId, selectedSkill.id, {
                        confirm_overwrite: true,
                      });
                      toast.success("Skill refreshed successfully");
                      loadSkills();
                      setRefreshConfirmOpen(false);
                    } catch (err) {
                      const msg = err instanceof Error ? err.message : "Refresh failed";
                      toast.error(msg);
                    }
                  }}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh Now
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}

        {/* Import from URL Sheet */}
        <Sheet open={importSheetOpen} onOpenChange={setImportSheetOpen}>
          <SheetContent className="flex flex-col w-full sm:max-w-xl">
            <SheetHeader className="px-6 pt-6 pb-4 border-b">
              <SheetTitle className="flex items-center gap-2">
                <Import className="h-5 w-5" />
                Import Skill from URL
              </SheetTitle>
              <SheetDescription>
                Paste a GitHub repository URL or a skills.sh shorthand to import a skill into your library.
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="import-url">GitHub URL or skills.sh shorthand</Label>
                <Input
                  id="import-url"
                  placeholder="https://github.com/user/repo or skills.sh/skill-name"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  disabled={importing}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && importUrl.trim() && !importing) {
                      handleImportSubmit();
                    }
                  }}
                />
                <p className="text-xs text-muted-foreground">
                  Supported formats: full GitHub repo URL, or skills.sh shorthand like <code>skills.sh/appointment-booking</code>.
                </p>
              </div>
            </div>
            <div className="px-6 py-4 border-t flex justify-between gap-3">
              <Button variant="outline" onClick={() => setImportSheetOpen(false)} disabled={importing}>
                Cancel
              </Button>
              <Button
                onClick={handleImportSubmit}
                disabled={!importUrl.trim() || importing}
              >
                {importing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Import className="h-4 w-4 mr-2" />}
                Import Skill
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
