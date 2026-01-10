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
  Trash2,
  Settings,
  Phone,
  MessageSquare,
  Wrench,
  Building2,
  Users,
  Calendar,
  Edit3,
  Activity,
  CreditCard,
  Save,
  X,
  Crown,
  Bot,
  ShieldCheck,
  RefreshCw,
  LogOut,
  Clock,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { AuthStatus } from "@/types/agent";
import {
  OrganizationCompleteData,
  OrganizationEnhanced,
} from "@/types/organization";

import { organizationService } from "@/services/organization-service";
import { agentService } from "@/services/agent-service";
import { VoiceAgent, PlatformTool, AgentTool } from "@/types/agent";
import { AgentDeleteDialog } from "@/components/agents/agent-delete-dialog";
import { toast } from "sonner";
import { formatToolName } from "@/lib/utils";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";

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
  const [platformTools, setPlatformTools] = useState<PlatformTool[]>([]);

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
  const [agentDialogOpen, setAgentDialogOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<VoiceAgent | null>(null);
  const [agentForm, setAgentForm] = useState({
    name: "",
    phone_number: "",
    system_prompt: "",
    is_active: true,
  });
  const [agentSaving, setAgentSaving] = useState(false);

  // Tool management state
  const [toolDialogOpen, setToolDialogOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<VoiceAgent | null>(null);
  const [agentTools, setAgentTools] = useState<AgentTool[]>([]);
  const [loadingTools, setLoadingTools] = useState(false);
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

      // Load agents and tools
      const [orgAgents, tools] = await Promise.all([
        agentService.getOrgAgents(orgId),
        agentService.getPlatformTools(),
      ]);
      setAgents(orgAgents);
      setPlatformTools(tools);
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
    setEditingAgent(null);
    setAgentForm({
      name: "",
      phone_number: "",
      system_prompt: "",
      is_active: true,
    });
    setAgentDialogOpen(true);
  };

  const handleEditAgent = (agent: VoiceAgent) => {
    setEditingAgent(agent);
    setAgentForm({
      name: agent.name,
      phone_number: agent.phone_number || "",
      system_prompt: agent.system_prompt || "",
      is_active: agent.is_active,
    });
    setAgentDialogOpen(true);
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

  const handleSaveAgent = async () => {
    if (!orgId) return;

    setAgentSaving(true);
    try {
      if (editingAgent) {
        await agentService.updateAgent(editingAgent.id, agentForm);
        toast.success("Agent updated successfully");
      } else {
        await agentService.createAgent({
          ...agentForm,
          organization_id: orgId,
        });
        toast.success("Agent created successfully");
      }
      setAgentDialogOpen(false);
      loadOrganizationData();
    } catch (error) {
      console.error("Failed to save agent:", error);
      toast.error("Failed to save agent");
    } finally {
      setAgentSaving(false);
    }
  };

  const handleConfigureTools = async (agent: VoiceAgent) => {
    setSelectedAgent(agent);
    setToolDialogOpen(true);
    setLoadingTools(true);
    try {
      const tools = await agentService.getAgentTools(agent.id);
      setAgentTools(tools);
    } catch (error) {
      console.error("Failed to load agent tools:", error);
      toast.error("Failed to load tools for this agent");
    } finally {
      setLoadingTools(false);
    }
  };

  const handleToggleTool = async (toolId: string, isEnabled: boolean) => {
    if (!selectedAgent) return;

    try {
      const existingAgentTool = agentTools.find((at) => at.tool_id === toolId);

      if (existingAgentTool) {
        // Eager update: optimistically update UI
        setAgentTools((prev) =>
          prev.map((at) =>
            at.id === existingAgentTool.id
              ? { ...at, is_enabled: isEnabled }
              : at,
          ),
        );

        // Make API call
        await agentService.updateAgentTool(existingAgentTool.id, {
          is_enabled: isEnabled,
        });
      } else {
        // Create with unselected_functions
        await agentService.configureAgentTool({
          agent_id: selectedAgent.id,
          tool_id: toolId,
          is_enabled: isEnabled,
          config: {},
          unselected_functions: [], // Default: no functions unselected
        });
      }

      // Refresh tools from server to get actual state
      const updatedTools = await agentService.getAgentTools(selectedAgent.id);
      setAgentTools(updatedTools);

      toast.success(isEnabled ? "Toolset enabled" : "Toolset disabled");
    } catch (error) {
      console.error("Failed to toggle tool:", error);
      toast.error("Failed to update tool status");

      // Revert to server state on error
      if (selectedAgent) {
        const updatedTools = await agentService.getAgentTools(selectedAgent.id);
        setAgentTools(updatedTools);
      }
    }
  };

  const handleToggleFunction = async (
    toolId: string,
    functionName: string,
    isEnabled: boolean,
  ) => {
    if (!selectedAgent) return;

    try {
      const existingAgentTool = agentTools.find((at) => at.tool_id === toolId);
      if (!existingAgentTool) return;

      // Get current unselected functions
      const currentUnselected = existingAgentTool.unselected_functions || [];
      let newUnselected: string[];

      if (isEnabled) {
        // Function is being ENABLED (checked): remove from unselected list
        newUnselected = currentUnselected.filter((fn) => fn !== functionName);
      } else {
        // Function is being DISABLED (unchecked): add to unselected list
        if (!currentUnselected.includes(functionName)) {
          newUnselected = [...currentUnselected, functionName];
        } else {
          newUnselected = currentUnselected;
        }
      }

      // Eager update: optimistically update UI immediately
      setAgentTools((prev) =>
        prev.map((at) =>
          at.id === existingAgentTool.id
            ? { ...at, unselected_functions: newUnselected }
            : at,
        ),
      );

      // Make API call
      await agentService.updateAgentTool(existingAgentTool.id, {
        unselected_functions: newUnselected,
      });

      // Refresh tools from server to get actual state
      const updatedTools = await agentService.getAgentTools(selectedAgent.id);
      setAgentTools(updatedTools);

      toast.success(
        isEnabled ? "Tool / Function enabled" : "Tool / Function disabled",
      );
    } catch (error) {
      console.error("Failed to toggle function:", error);
      toast.error("Failed to update function status");

      // Revert to server state on error
      const updatedTools = await agentService.getAgentTools(selectedAgent.id);
      setAgentTools(updatedTools);
    }
  };

  const handleSaveToolConfig = async (
    agentToolId: string,
    config: Record<string, unknown>,
  ) => {
    try {
      await agentService.updateAgentTool(agentToolId, { config });
      toast.success("Tool configuration updated");

      if (selectedAgent) {
        const updatedTools = await agentService.getAgentTools(selectedAgent.id);
        setAgentTools(updatedTools);
      }
    } catch (error) {
      console.error("Failed to save tool config:", error);
      toast.error("Failed to update tool configuration");
    }
  };

  const handleOAuth = async (toolName: string) => {
    if (!selectedAgent) return;
    try {
      const response = await agentService.startOAuth(
        toolName,
        selectedAgent.id,
      );
      // In a real app, we'd redirect. For this demo, we'll open in a new tab
      window.open(response.auth_url, "_blank");
      toast.info("Opening authentication page...");

      // Auto-refresh tools after 3 seconds to show updated auth status
      setTimeout(async () => {
        if (selectedAgent) {
          const updatedTools = await agentService.getAgentTools(
            selectedAgent.id,
          );
          setAgentTools(updatedTools);
        }
      }, 3000); // 3 seconds
    } catch (error) {
      console.error("OAuth failed:", error);
      toast.error("Failed to start authentication");
    }
  };

  const handleLogout = async (agentToolId: string) => {
    if (!selectedAgent) return;
    try {
      await agentService.logoutAgentTool(agentToolId);
      toast.success("Logged out successfully");

      // Refresh tools to update auth status
      const updatedTools = await agentService.getAgentTools(selectedAgent.id);
      setAgentTools(updatedTools);
    } catch (error) {
      console.error("Failed to log out:", error);
      toast.error("Failed to log out");
    }
  };

  const renderToolConfig = (tool: PlatformTool, agentTool?: AgentTool) => {
    if (!agentTool) return null;

    const schema = tool.config_schema as {
      requires_auth?: boolean;
      properties?: Record<
        string,
        {
          title?: string;
          description?: string;
          default?: unknown;
        }
      >;
    } | null;

    const config = (agentTool.config || {}) as Record<string, unknown>;
    const isOAuth = schema?.requires_auth || tool.name.includes("calendar");

    // Get function schemas from tool_functions_schema
    const functions = tool.tool_functions_schema?.functions || [];
    const toolUnselectedFunctions = agentTool.unselected_functions || [];
    const isToolEnabled = agentTool.is_enabled;

    // Calculate time until expiry
    const getTimeUntilExpiry = (expiresAt: number | null) => {
      if (!expiresAt) return null;
      const secondsLeft = Math.floor((expiresAt * 1000 - Date.now()) / 1000);
      const minutesLeft = Math.floor(secondsLeft / 60);

      if (minutesLeft < 1) return "< 1 minute";
      if (minutesLeft < 60) return `${minutesLeft} minutes`;
      if (minutesLeft < 1440) return `${Math.floor(minutesLeft / 60)} hours`;
      return `${Math.floor(minutesLeft / 1440)} days`;
    };

    // Determine auth status message and icon color
    const getAuthStatusConfig = () => {
      switch (agentTool.auth_status) {
        case AuthStatus.AUTHENTICATED:
          const timeLeft = getTimeUntilExpiry(agentTool.token_expires_at);
          return {
            message: "Authenticated",
            iconColor: "text-green-500",
            showButton: true,
            buttonText: "Refresh now",
            showExpiry: !!timeLeft,
            expiryText: timeLeft,
          };
        case AuthStatus.EXPIRED:
          return {
            message: "Authentication expired",
            iconColor: "text-red-500",
            showButton: true,
            buttonText: "Authenticate",
            showExpiry: false,
          };
        case AuthStatus.NOT_AUTHENTICATED:
        default:
          return {
            message: "Authentication required",
            iconColor: "text-muted",
            showButton: true,
            buttonText: "Authenticate",
            showExpiry: false,
          };
      }
    };

    const authConfig = getAuthStatusConfig();

    return (
      <div className="space-y-4">
        {isOAuth && (
          <div className="flex items-center justify-between p-3 bg-primary/5 rounded-lg border border-primary/10">
            <div className="flex flex-col gap-1">
              <div className="flex items-center space-x-2">
                <ShieldCheck className={`h-4 w-4 ${authConfig.iconColor}`} />
                <div>
                  <span className="text-xs font-medium">
                    {authConfig.message}
                  </span>
                  {agentTool.auth_status === AuthStatus.AUTHENTICATED && (
                    <Badge variant="secondary" className="ml-2 h-5 text-[10px]">
                      Active
                    </Badge>
                  )}
                </div>
                {authConfig.showExpiry && authConfig.expiryText && (
                  <div className="text-xs text-muted-foreground flex items-center">
                    <Clock className="h-3 w-3 mr-1" />
                    {authConfig.expiryText}
                  </div>
                )}
              </div>
              <div className="flex items-center space-x-2">
                {authConfig.showButton && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs"
                    onClick={() => handleOAuth(tool.name)}
                  >
                    <RefreshCw className="h-3.5 w-3.5 mr-1" />
                    {authConfig.buttonText}
                  </Button>
                )}
                {agentTool.auth_status === AuthStatus.AUTHENTICATED && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 text-xs text-muted-foreground"
                    onClick={() => handleLogout(agentTool.id)}
                  >
                    <LogOut className="h-3.5 w-3.5 mr-1" />
                    Log out
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        {schema?.properties && (
          <div className="grid gap-3">
            {Object.entries(schema.properties).map(([key, prop]) => (
              <div key={key} className="space-y-1">
                <Label
                  htmlFor={`${tool.id}-${key}`}
                  className="text-[10px] uppercase text-muted-foreground"
                >
                  {prop.title || key}
                </Label>
                <Input
                  id={`${tool.id}-${key}`}
                  placeholder={prop.description || ""}
                  value={
                    (config[key] as string) || (prop.default as string) || ""
                  }
                  onChange={(e) => {
                    const newConfig = { ...config, [key]: e.target.value };
                    setAgentTools((prev) =>
                      prev.map((at) =>
                        at.id === agentTool.id
                          ? { ...at, config: newConfig }
                          : at,
                      ),
                    );
                  }}
                  className="h-8 text-xs"
                />
              </div>
            ))}
            <Button
              size="sm"
              className="w-full h-8 text-xs mt-2"
              onClick={() => handleSaveToolConfig(agentTool.id, config)}
            >
              Save Configuration
            </Button>
          </div>
        )}

        {functions.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <div className="flex items-center space-x-2 text-xs font-medium text-muted-foreground mb-3">
              <Settings className="h-3.5 w-3.5" />
              <span>Available Functions</span>
              <span className="text-[10px] text-muted-foreground">
                ({functions.length} total,{" "}
                {functions.length - toolUnselectedFunctions.length} enabled)
              </span>
              {!isToolEnabled && (
                <Badge variant="secondary" className="ml-2 h-5 text-[10px]">
                  Enable tool to use functions
                </Badge>
              )}
            </div>
            <div className="space-y-2">
              {functions.map((func) => {
                const isUnselected = toolUnselectedFunctions.includes(
                  func.name,
                );
                const isEnabled = !isUnselected;

                return (
                  <div
                    key={func.name}
                    className={`flex items-start justify-between p-3 rounded-lg border transition-colors ${
                      isEnabled
                        ? "border-primary/20 bg-primary/5"
                        : "border-muted/60 bg-muted/20"
                    }`}
                  >
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <div
                          className={`p-1.5 rounded ${
                            isEnabled ? "bg-primary" : "bg-muted"
                          }`}
                        >
                          <span
                            className={`${
                              isEnabled ? "text-white" : "text-muted-foreground"
                            } text-xs font-medium`}
                          >
                            {func.name}
                          </span>
                        </div>
                        {!isEnabled && (
                          <Badge
                            variant="secondary"
                            className="h-5 text-[10px]"
                          >
                            Disabled
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {func.description}
                      </p>
                      {func.parameters?.properties && (
                        <div className="mt-2 text-[10px] text-muted-foreground">
                          <span className="font-medium">Parameters:</span>{" "}
                          {Object.keys(func.parameters.properties).join(", ")}
                        </div>
                      )}
                    </div>
                    <Checkbox
                      id={`func-${func.name}`}
                      checked={isEnabled}
                      onCheckedChange={(checked) =>
                        handleToggleFunction(
                          tool.id,
                          func.name,
                          checked === true,
                        )
                      }
                      disabled={!isToolEnabled}
                      className="mt-1"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
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
                      <Card
                        key={agent.id}
                        className="overflow-hidden border-muted/60 hover:border-primary/50 transition-colors"
                      >
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start mb-3">
                            <div>
                              <h4 className="font-semibold text-base">
                                {agent.name}
                              </h4>
                              <div className="flex items-center text-xs text-muted-foreground mt-1">
                                <Badge
                                  variant={
                                    agent.is_active ? "default" : "secondary"
                                  }
                                  className="h-5 scale-90 origin-left"
                                >
                                  {agent.is_active ? "Active" : "Inactive"}
                                </Badge>
                              </div>
                            </div>
                            <div className="flex space-x-1">
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                onClick={() => handleEditAgent(agent)}
                              >
                                <Edit3 className="h-4 w-4" />
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8 text-destructive"
                                onClick={() => handleDeleteAgent(agent)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>

                          <div className="space-y-2 mt-4">
                            <div className="flex items-center text-sm">
                              <Phone className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                              <span className="truncate">
                                {agent.phone_number || "No phone assigned"}
                              </span>
                            </div>
                            <div className="flex items-center text-sm">
                              <MessageSquare className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                              <span className="truncate text-xs italic text-muted-foreground">
                                {agent.system_prompt
                                  ? "Custom prompt configured"
                                  : "Using default prompt"}
                              </span>
                            </div>
                          </div>

                          <Separator className="my-4" />

                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full text-xs h-8"
                            onClick={() => handleConfigureTools(agent)}
                          >
                            <Wrench className="h-3.5 w-3.5 mr-2" />
                            Configure Tools
                          </Button>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </AnimatedTabs>

      {/* Agent Create/Edit Dialog */}
      <Dialog open={agentDialogOpen} onOpenChange={setAgentDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {editingAgent ? "Edit Voice Agent" : "Create New Voice Agent"}
            </DialogTitle>
            <DialogDescription>
              {editingAgent
                ? "Update your voice agent configuration and settings."
                : "Create a new AI voice agent for your organization."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="agent-name">Name</Label>
              <Input
                id="agent-name"
                value={agentForm.name}
                onChange={(e) =>
                  setAgentForm({ ...agentForm, name: e.target.value })
                }
                placeholder="Support Agent, Sales Bot, etc."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-phone">Phone Number (Optional)</Label>
              <Input
                id="agent-phone"
                value={agentForm.phone_number}
                onChange={(e) =>
                  setAgentForm({ ...agentForm, phone_number: e.target.value })
                }
                placeholder="+1234567890"
              />
              <p className="text-xs text-muted-foreground">
                Twilio phone number for this agent
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="agent-prompt">System Prompt (Optional)</Label>
              <Textarea
                id="agent-prompt"
                value={agentForm.system_prompt}
                onChange={(e) =>
                  setAgentForm({ ...agentForm, system_prompt: e.target.value })
                }
                placeholder="You are a helpful customer support agent..."
                className="min-h-[150px]"
              />
              <p className="text-xs text-muted-foreground">
                Instructions for the AI on how to behave
              </p>
            </div>
            <div className="flex items-center space-x-2 pt-2">
              <Checkbox
                id="agent-active"
                checked={agentForm.is_active}
                onCheckedChange={(checked) =>
                  setAgentForm({ ...agentForm, is_active: checked === true })
                }
              />
              <Label
                htmlFor="agent-active"
                className="text-sm font-normal cursor-pointer"
              >
                Agent is active and ready to handle calls
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAgentDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveAgent}
              disabled={agentSaving || !agentForm.name}
            >
              {agentSaving
                ? "Saving..."
                : editingAgent
                  ? "Update Agent"
                  : "Create Agent"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Tool Configuration Dialog */}
      <Dialog open={toolDialogOpen} onOpenChange={setToolDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Configure Tools: {selectedAgent?.name}</DialogTitle>
            <DialogDescription>
              Enable and configure platform tools for this agent.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto py-4 space-y-4">
            {loadingTools ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                <p className="text-sm text-muted-foreground">
                  Loading tools...
                </p>
              </div>
            ) : platformTools.length === 0 ? (
              <div className="text-center py-12 bg-muted/20 rounded-lg">
                <Wrench className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                <p className="text-muted-foreground">
                  No platform tools available
                </p>
              </div>
            ) : (
              <div className="grid gap-4">
                {platformTools.map((tool) => {
                  const agentTool = agentTools.find(
                    (at) => at.tool_id === tool.id,
                  );
                  const isEnabled = agentTool?.is_enabled || false;

                  return (
                    <Card
                      key={tool.id}
                      className={`overflow-hidden border-2 transition-colors ${
                        isEnabled
                          ? "border-primary/20 bg-primary/5"
                          : "border-muted/50"
                      }`}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <div
                              className={`p-2 rounded-lg ${
                                isEnabled ? "bg-primary" : "bg-muted"
                              }`}
                            >
                              <Wrench className="h-4 w-4" />
                            </div>
                            <div>
                              <h4 className="font-semibold text-sm">
                                {formatToolName(tool.name)}
                              </h4>
                              <p className="text-xs text-muted-foreground line-clamp-2">
                                {tool.description}
                              </p>
                            </div>
                          </div>
                          <Checkbox
                            id={`tool-${tool.id}`}
                            checked={isEnabled}
                            onCheckedChange={(checked) =>
                              handleToggleTool(tool.id, checked === true)
                            }
                          />
                        </div>

                        {isEnabled && (
                          <div className="mt-4 pt-4 border-t border-primary/10 space-y-4">
                            <div className="flex items-center text-xs font-medium text-primary">
                              <Settings className="h-3.5 w-3.5 mr-1" />
                              Configuration
                            </div>

                            {renderToolConfig(tool, agentTool)}

                            <div className="flex items-center space-x-2 text-[10px] text-muted-foreground">
                              <ShieldCheck className="h-3 w-3 text-green-500" />
                              <span>
                                This tool is active for {selectedAgent?.name}
                              </span>
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>

          <DialogFooter className="pt-4 border-t">
            <Button variant="outline" onClick={() => setToolDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
