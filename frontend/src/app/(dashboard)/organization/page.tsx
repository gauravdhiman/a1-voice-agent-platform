"use client";

import React, { useState, useCallback, useEffect } from "react";
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
    business_details: string;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  // Agent management state
  const [selectedAgent, setSelectedAgent] = useState<VoiceAgent | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

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
        business_details: org.business_details || "",
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

  // Load data when component mounts or orgId changes
  useEffect(() => {
    if (orgId) {
      loadOrganizationData();
    }
  }, [orgId, loadOrganizationData]);

  // Sync tab state with URL
  useEffect(() => {
    const tabParam = searchParams.get("tab");
    if (tabParam === "overview" || tabParam === "ai-agent") {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = useCallback(
    (value: string) => {
      setActiveTab(value);
      router.push(`/organization?org_id=${orgId}&tab=${value}`, {
        scroll: false,
      });
    },
    [router, orgId],
  );

  // Validate organization access when orgId is provided
  const {
    isValid: isOrgValid,
    loading: validationLoading,
    organization: validatedOrg,
  } = useOrganizationById(orgId);

  // Set the current organization based on the validated orgId parameter if provided
  if (
    validatedOrg &&
    (!currentOrganization || currentOrganization.id !== validatedOrg.id)
  ) {
    setCurrentOrganization(validatedOrg);
  }

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
    if (!orgId || !editedOrg) return;

    setSaving(true);
    try {
      await organizationService.updateOrganization(orgId, {
        name: editedOrg.name,
        description: editedOrg.description,
        website: editedOrg.website,
        slug: editedOrg.slug,
        is_active: editedOrg.is_active,
        business_details: editedOrg.business_details,
      });

      toast.success("Organization updated successfully");
      setIsEditing(false);
      loadOrganizationData();
    } catch (error) {
      console.error("Failed to update organization:", error);
      toast.error("Failed to update organization");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    loadOrganizationData(); // Reload to reset changes
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
              {isEditing ? (
                <>
                  <Button
                    onClick={handleSave}
                    disabled={saving}
                    size="sm"
                    className="flex items-center space-x-2"
                  >
                    <Save className="h-4 w-4" />
                    <span>{saving ? "Saving..." : "Save Changes"}</span>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCancel}
                    className="flex items-center space-x-2"
                  >
                    <X className="h-4 w-4" />
                    <span>Cancel</span>
                  </Button>
                </>
              ) : (
                <div className="relative">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="sm" className="flex items-center space-x-2">
                        <Activity className="h-4 w-4" />
                        <span>Actions</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuItem
                        className="flex items-center space-x-2 cursor-pointer"
                        onClick={handleEdit}
                      >
                        <Edit3 className="h-4 w-4" />
                        <span>Edit Organization</span>
                      </DropdownMenuItem>
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
          )}
        </div>

        <div className="flex items-center space-x-4">
          <Badge variant={displayOrg.is_active ? "default" : "secondary"}>
            {displayOrg.is_active ? "Active" : "Inactive"}
          </Badge>
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
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <Card>
            <CardHeader className="p-5 pb-3">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Building2 className="h-5 w-5" />
                <span>Organization Information</span>
              </CardTitle>
              <CardDescription>
                {isEditing
                  ? "Edit your organization details"
                  : "Your organization details and settings"}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0 space-y-4">
              {isEditing ? (
                <>
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
                    <Label>Status</Label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="isActive"
                        checked={editedOrg?.is_active ?? true}
                        onChange={(e) =>
                          editedOrg &&
                          setEditedOrg({
                            ...editedOrg,
                            is_active: e.target.checked,
                          })
                        }
                        className="rounded"
                      />
                      <label htmlFor="isActive" className="text-sm">
                        Organization is active
                      </label>
                    </div>
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
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Website
                    </label>
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
                      <p className="text-muted-foreground">No website</p>
                    )}
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
                      Status
                    </label>
                    <div className="flex items-center space-x-2">
                      <Badge
                        variant={displayOrg.is_active ? "default" : "secondary"}
                      >
                        {displayOrg.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI Voice Agent Tab */}
        <TabsContent value="ai-agent">
          <div className="space-y-6">
            <Card>
              <CardHeader className="p-5 pb-3">
                <CardTitle className="flex items-center space-x-2 text-lg">
                  <Bot className="h-5 w-5" />
                  <span>AI Voice Agent Configuration</span>
                </CardTitle>
                <CardDescription>
                  Configure your AI voice agent with business information
                </CardDescription>
              </CardHeader>
              <CardContent className="p-5 pt-0 space-y-4">
                {isEditing ? (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="business_details">
                        Business Details for AI Agent
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
                        placeholder="Enter details about your business, products, services, hours, and other information for the AI agent to know..."
                        className="min-h-[200px]"
                      />
                      <p className="text-xs text-muted-foreground">
                        This information will be used by the AI voice agent to
                        answer customer questions
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <label className="text-sm font-medium text-muted-foreground">
                        Business Details
                      </label>
                      <p className="text-foreground whitespace-pre-wrap">
                        {organizationData?.organization.business_details ||
                          "No business details provided"}
                      </p>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

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
