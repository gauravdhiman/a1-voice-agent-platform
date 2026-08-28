import * as React from "react";
import { cn } from "@/lib/utils";
import { useLiveTime, formatTimeUntilExpiry } from "@/hooks/use-live-time";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  ShieldCheck,
  Lock,
  RefreshCw,
  LogOut,
  Clock,
  Settings,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Loader2,
  EyeOff,
} from "lucide-react";
import {
  AuthStatus,
  PlatformTool,
  AgentTool,
  OAuthRefreshMode,
} from "@/types/agent";
import { DeleteButton } from "@/components/ui/delete-button";
import {
  filterMcpFunctions,
  McpFunctionSearch,
} from "@/components/tools/mcp-function-search";
import { ExpandableDescription } from "@/components/tools/expandable-description";
import {
  getResendEmailConfigError,
  parseResendEmailRoutes,
  RESEND_EMAIL_TOOL_NAME,
  ResendEmailConfigEditor,
  ResendEmailRouteConfig,
} from "@/components/tools/resend-email-config";

export interface ToolConfigDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tool: PlatformTool;
  agentTool: AgentTool | null;
  organizationId?: string;
  resendCredentialConfigured?: boolean;
  onSaveConfig: (
    agentToolId: string,
    config: Record<string, unknown>,
  ) => Promise<void>;
  onToggleFunction: (
    toolId: string,
    functionName: string,
    isEnabled: boolean,
  ) => Promise<void>;
  onOAuth: (toolName: string) => Promise<void>;
  onLogout: (agentToolId: string) => Promise<void>;
  onSetApiKey: (agentToolId: string, apiKey: string) => Promise<void>;
  onDisconnect: () => void;
  canEdit: boolean;
  isSaving?: boolean;
}

export function ToolConfigDrawer({
  open,
  onOpenChange,
  tool,
  agentTool,
  organizationId,
  resendCredentialConfigured,
  onSaveConfig,
  onToggleFunction,
  onOAuth,
  onLogout,
  onSetApiKey,
  onDisconnect,
  canEdit,
  isSaving = false,
}: ToolConfigDrawerProps) {
  const [localConfig, setLocalConfig] = React.useState<Record<string, unknown>>(
    {},
  );
  const [hasUnsavedChanges, setHasUnsavedChanges] = React.useState(false);
  const [isConnecting, setIsConnecting] = React.useState(false);
  const [showApiKeyInput, setShowApiKeyInput] = React.useState(false);
  const [apiKey, setApiKey] = React.useState("");
  const [isSavingApiKey, setIsSavingApiKey] = React.useState(false);
  const [expandedFunctionName, setExpandedFunctionName] = React.useState<
    string | null
  >(null);
  const [expandedDescriptionName, setExpandedDescriptionName] = React.useState<
    string | null
  >(null);
  const [functionSearch, setFunctionSearch] = React.useState("");
  const currentTime = useLiveTime();

  React.useEffect(() => {
    setLocalConfig(agentTool?.config ?? {});
    setHasUnsavedChanges(false);
  }, [agentTool?.config, open]);

  React.useEffect(() => {
    setExpandedFunctionName(null);
    setExpandedDescriptionName(null);
    setFunctionSearch("");
  }, [open, tool.id]);

  React.useEffect(() => {
    setExpandedFunctionName(null);
    setExpandedDescriptionName(null);
  }, [functionSearch]);

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

  const functions = tool.tool_functions_schema?.functions || [];
  const filteredFunctions = filterMcpFunctions(functions, functionSearch);
  const toolUnselectedFunctions = agentTool?.unselected_functions || [];
  const isToolEnabled = agentTool?.is_enabled ?? false;
  const hasFunctions = functions.length > 0;
  const isResendEmailTool = tool.name === RESEND_EMAIL_TOOL_NAME;
  const resendRoutes = React.useMemo(
    () => parseResendEmailRoutes(localConfig.routes),
    [localConfig.routes],
  );
  const resendFromEmail =
    typeof localConfig.from_email === "string" ? localConfig.from_email : "";
  const resendFromName =
    typeof localConfig.from_name === "string" ? localConfig.from_name : "";
  const resendConfigError = isResendEmailTool
    ? getResendEmailConfigError(resendFromEmail, resendFromName, resendRoutes)
    : null;

  const isOAuth = tool.auth_type === "oauth2";
  const isApiKey = tool.auth_type === "api_key";
  const platformApiKeyFallbackAvailable =
    isApiKey && tool.requires_auth === false;

  const handleConfigChange = (key: string, value: string) => {
    const newConfig = { ...localConfig, [key]: value };
    setLocalConfig(newConfig);
    setHasUnsavedChanges(true);
  };

  const handleSaveConfig = async () => {
    if (!agentTool) return;
    if (isResendEmailTool && resendConfigError) return;
    await onSaveConfig(agentTool.id, localConfig);
    setHasUnsavedChanges(false);
  };

  const handleResendSenderChange = (
    field: "from_email" | "from_name",
    value: string,
  ) => {
    setLocalConfig((current) => ({ ...current, [field]: value }));
    setHasUnsavedChanges(true);
  };

  const handleResendRoutesChange = (routes: ResendEmailRouteConfig[]) => {
    setLocalConfig((current) => ({ ...current, routes }));
    setHasUnsavedChanges(true);
  };

  const handleOAuth = async () => {
    setIsConnecting(true);
    try {
      await onOAuth(tool.name);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleLogout = async () => {
    if (!agentTool) return;
    await onLogout(agentTool.id);
  };

  const handleSaveApiKey = async () => {
    if (!agentTool || !apiKey.trim()) return;
    setIsSavingApiKey(true);
    try {
      await onSetApiKey(agentTool.id, apiKey.trim());
      setApiKey("");
      setShowApiKeyInput(false);
    } finally {
      setIsSavingApiKey(false);
    }
  };

  const handleClearApiKey = async () => {
    if (!agentTool) return;
    await onLogout(agentTool.id);
  };

  // Check if token is locally expired (client-side detection)
  const isTokenExpired = !!(
    agentTool?.token_expires_at &&
    agentTool.token_expires_at * 1000 < currentTime
  );
  const authenticated =
    agentTool?.auth_status === AuthStatus.AUTHENTICATED && !isTokenExpired;
  const oauthRefreshMode: OAuthRefreshMode =
    agentTool?.oauth_refresh_mode ?? tool.oauth_refresh_mode ?? "unknown";
  const oauthRefreshMessage =
    agentTool?.oauth_refresh_message ??
    tool.oauth_refresh_message ??
    "Refresh support is not declared by this provider.";
  const oauthRefreshModeLabel =
    oauthRefreshMode === "automatic"
      ? "Automatic refresh"
      : oauthRefreshMode === "manual"
        ? "Manual reauthorization"
        : "Refresh support unknown";

  const getAuthStatusConfig = () => {
    if (!agentTool) {
      return {
        message: "Not configured",
        icon: AlertCircle,
        iconColor: "text-muted-foreground",
        showButton: true,
        buttonText: "Authenticate",
        showExpiry: false,
        bgColor:
          "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800",
      };
    }

    switch (agentTool.auth_status) {
      case AuthStatus.AUTHENTICATED:
        // If token is locally expired, treat as expired regardless of backend status
        if (isTokenExpired) {
          return {
            message: "Authentication expired",
            icon: AlertCircle,
            iconColor: "text-red-600 dark:text-red-400",
            showButton: true,
            buttonText: "Authenticate",
            showExpiry: false,
            bgColor:
              "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800",
          };
        }

        const timeLeft = formatTimeUntilExpiry(
          agentTool.token_expires_at,
          currentTime,
        );
        return {
          message: "Connected",
          icon: CheckCircle2,
          iconColor: "text-green-600 dark:text-green-400",
          showButton: true,
          buttonText: "Refresh",
          showExpiry: !!timeLeft && timeLeft !== "Expired",
          expiryText: timeLeft,
          bgColor:
            "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800",
        };
      case AuthStatus.EXPIRED:
        return {
          message: "Authentication expired",
          icon: AlertCircle,
          iconColor: "text-red-600 dark:text-red-400",
          showButton: true,
          buttonText: "Authenticate",
          showExpiry: false,
          bgColor:
            "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800",
        };
      case AuthStatus.NOT_AUTHENTICATED:
      default:
        return {
          message: "Authentication required",
          icon: AlertCircle,
          iconColor: "text-red-600 dark:text-red-400",
          showButton: true,
          buttonText: "Authenticate",
          showExpiry: false,
          bgColor:
            "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800",
        };
    }
  };

  const authConfig = getAuthStatusConfig();

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex flex-col w-full sm:max-w-2xl">
        <SheetHeader className="px-6 pt-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Settings className="h-5 w-5 text-primary" />
            </div>
            <div>
              <SheetTitle className="text-lg">
                {tool.name.replace(/_/g, " ")}
              </SheetTitle>
              <SheetDescription asChild>
                <ExpandableDescription
                  description={tool.description}
                  descriptionId={`tool-drawer-description-${tool.id}`}
                  textClassName="text-xs text-muted-foreground"
                />
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {tool.is_published === false && (
            <div className="flex items-start gap-2 p-3 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/20">
              <EyeOff className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
              <div className="text-xs text-amber-800 dark:text-amber-200 space-y-1">
                <p className="font-medium">
                  Unpublished — still mapped to this agent
                </p>
                <p>
                  This tool was unpublished from the platform catalog, so new
                  agents can no longer add it. This agent keeps using it until
                  you disconnect it here.
                </p>
              </div>
            </div>
          )}

          {isOAuth && (
            <div
              className={cn(
                "flex items-center justify-between gap-4 p-4 rounded-lg border",
                authConfig.bgColor,
              )}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className={`h-4 w-4 ${authConfig.iconColor}`} />
                  <span className="text-sm font-medium">
                    {authConfig.message}
                  </span>
                  {authenticated && (
                    <Badge variant="secondary" className="h-5 text-[10px]">
                      Active
                    </Badge>
                  )}
                </div>
                {authConfig.showExpiry && authConfig.expiryText && (
                  <div className="text-xs text-muted-foreground flex items-center">
                    <Clock className="h-3 w-3 mr-1" />
                    Expires in {authConfig.expiryText}
                  </div>
                )}
                <div
                  className={cn(
                    "mt-1 rounded-md border px-2.5 py-2 text-xs",
                    oauthRefreshMode === "automatic"
                      ? "border-emerald-200 bg-emerald-50/70 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-200"
                      : "border-amber-200 bg-amber-50/70 text-amber-800 dark:border-amber-800 dark:bg-amber-950/20 dark:text-amber-200",
                  )}
                >
                  <div className="flex items-center gap-1.5 font-medium">
                    <RefreshCw className="h-3 w-3" />
                    {oauthRefreshModeLabel}
                  </div>
                  <p className="mt-1 leading-relaxed">
                    {oauthRefreshMessage}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2 shrink-0">
                {authConfig.showButton && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs"
                    onClick={handleOAuth}
                    disabled={isConnecting || !canEdit}
                  >
                    {isConnecting ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    ) : authConfig.buttonText === "Refresh" ? (
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                    ) : (
                      <Lock className="h-3.5 w-3.5 mr-1" />
                    )}
                    {isConnecting ? "Authenticating..." : authConfig.buttonText}
                  </Button>
                )}
                {authenticated && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 text-xs text-muted-foreground"
                    onClick={handleLogout}
                    disabled={!canEdit}
                  >
                    <LogOut className="h-3.5 w-3.5 mr-1" />
                    Log out
                  </Button>
                )}
              </div>
            </div>
          )}

          {isApiKey && (
            <div
              className={cn(
                "space-y-3 p-4 rounded-lg border",
                authenticated
                  ? "bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800"
                  : platformApiKeyFallbackAvailable
                    ? "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800"
                    : "bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800",
              )}
            >
              {!authenticated && !showApiKeyInput && (
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck
                      className={cn(
                        "h-4 w-4",
                        platformApiKeyFallbackAvailable
                          ? "text-amber-600 dark:text-amber-400"
                          : "text-red-600 dark:text-red-400",
                      )}
                    />
                    <span className="text-sm font-medium">
                      {platformApiKeyFallbackAvailable
                        ? "Organization API Key (optional)"
                        : "Organization API Key Required"}
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs"
                    onClick={() => setShowApiKeyInput(true)}
                    disabled={!canEdit}
                  >
                    <Lock className="h-3.5 w-3.5 mr-1" />
                    Configure API Key
                  </Button>
                </div>
              )}

              {!authenticated &&
                platformApiKeyFallbackAvailable &&
                !showApiKeyInput && (
                  <p className="text-xs text-amber-800 dark:text-amber-200">
                    Your organization key overrides the platform fallback. Leave
                    it blank to use the platform key when one is configured.
                  </p>
                )}

              {authenticated && (
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center space-x-2">
                    <ShieldCheck className="h-4 w-4 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-medium">
                      API Key Configured
                    </span>
                    <Badge variant="secondary" className="h-5 text-[10px]">
                      Active
                    </Badge>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-8 text-xs text-muted-foreground"
                    onClick={handleClearApiKey}
                    disabled={!canEdit}
                  >
                    <LogOut className="h-3.5 w-3.5 mr-1" />
                    Clear
                  </Button>
                </div>
              )}

              {showApiKeyInput && (
                <div className="space-y-2 bg-background rounded-lg border p-4">
                  <Label htmlFor={`api-key-${tool.id}`}>API Key</Label>
                  <Input
                    id={`api-key-${tool.id}`}
                    type="password"
                    placeholder="Enter your API key"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    disabled={!canEdit}
                    className="h-9 text-sm"
                  />
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={handleSaveApiKey}
                      disabled={!apiKey.trim() || isSavingApiKey || !canEdit}
                    >
                      {isSavingApiKey ? (
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                      ) : null}
                      Save API Key
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setShowApiKeyInput(false);
                        setApiKey("");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {tool.tool_source === "mcp" && !hasFunctions && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950/20">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
              <div className="space-y-1 text-xs text-amber-800 dark:text-amber-200">
                <p className="font-medium">Tool catalog unavailable</p>
                <p>
                  The MCP server&apos;s functions have not been discovered yet.
                  Ask a platform administrator to{" "}
                  {isOAuth
                    ? "complete OAuth discovery"
                    : "run Test connection & discover tools"}{" "}
                  before configuring individual functions.
                </p>
              </div>
            </div>
          )}

          {schema?.properties && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-sm font-medium">
                  <Settings className="h-4 w-4" />
                  <span>Configuration</span>
                </div>
                {hasUnsavedChanges && canEdit && (
                  <Button
                    size="sm"
                    onClick={handleSaveConfig}
                    disabled={isSaving || Boolean(resendConfigError)}
                  >
                    {isSaving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : null}
                    Save
                  </Button>
                )}
              </div>
              {isResendEmailTool && resendCredentialConfigured === false && (
                <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950/20">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                  <p className="text-xs text-amber-800 dark:text-amber-200">
                    This organization has not configured a Resend API key. Add
                    it under{" "}
                    <a
                      className="font-medium underline underline-offset-2"
                      href={
                        organizationId
                          ? `/organization?org_id=${organizationId}&tab=credentials`
                          : "/organization?tab=credentials"
                      }
                    >
                      Organization → Credentials
                    </a>{" "}
                    before testing delivery.
                  </p>
                </div>
              )}
              {isResendEmailTool ? (
                <ResendEmailConfigEditor
                  routes={resendRoutes}
                  fromEmail={resendFromEmail}
                  fromName={resendFromName}
                  onFromEmailChange={(value) =>
                    handleResendSenderChange("from_email", value)
                  }
                  onFromNameChange={(value) =>
                    handleResendSenderChange("from_name", value)
                  }
                  onChange={handleResendRoutesChange}
                  canEdit={canEdit}
                />
              ) : (
                <div className="grid gap-3">
                  {Object.entries(schema.properties).map(([key, prop]) => (
                    <div key={key} className="space-y-1">
                      <Label
                        htmlFor={`drawer-${tool.id}-${key}`}
                        className="text-[10px] uppercase text-muted-foreground"
                      >
                        {prop.title || key}
                      </Label>
                      <Input
                        id={`drawer-${tool.id}-${key}`}
                        placeholder={prop.description || ""}
                        value={
                          (localConfig[key] as string) ||
                          (prop.default as string) ||
                          ""
                        }
                        onChange={(e) => handleConfigChange(key, e.target.value)}
                        className="h-9 text-sm"
                        disabled={!canEdit}
                      />
                    </div>
                  ))}
                </div>
              )}
              {hasUnsavedChanges && (
                <div className="flex items-center gap-1.5 text-xs text-orange-600 dark:text-orange-400">
                  <AlertCircle className="h-3.5 w-3.5" />
                  Unsaved configuration changes
                </div>
              )}
            </div>
          )}

          {hasFunctions && (
            <div className="space-y-3">
              {/* Function Selection Guidance */}
              <div className="bg-amber-50 border border-amber-200 rounded-md p-3 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-amber-800 space-y-1">
                  <p className="font-medium">Select Only Required Functions</p>
                  <p>
                    Enabling all functions can confuse the agent. Disable
                    functions that are not needed for the specific role of this
                    agent. For example, a scheduling agent only needs calendar
                    functions, not email management.
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-sm font-medium">
                  <Settings className="h-4 w-4" />
                  <span>Available Functions</span>
                </div>
                <Badge variant="secondary" className="h-5 text-[10px]">
                  {functions.length - toolUnselectedFunctions.length} /{" "}
                  {functions.length}
                </Badge>
              </div>
              <McpFunctionSearch
                value={functionSearch}
                onChange={setFunctionSearch}
                matchCount={filteredFunctions.length}
                totalCount={functions.length}
              />
              <div className="space-y-2">
                {filteredFunctions.map((func) => {
                  const isUnselected = toolUnselectedFunctions.includes(
                    func.name,
                  );
                  const isEnabled = !isUnselected;
                  const isExpanded = expandedFunctionName === func.name;
                  const properties = func.parameters?.properties || {};
                  const propertyEntries = Object.entries(properties);
                  const required = new Set(func.parameters?.required || []);
                  const description =
                    func.description || "No description provided.";
                  const hasLongDescription = description.length > 180;
                  const descriptionExpanded =
                    expandedDescriptionName === func.name;
                  const descriptionPreview = hasLongDescription
                    ? `${description.slice(0, 180).trimEnd()}…`
                    : description;
                  const detailsId = `agent-tool-function-details-${func.name.replace(
                    /[^a-zA-Z0-9_-]/g,
                    "-",
                  )}`;
                  const descriptionId = `${detailsId}-description`;

                  return (
                    <div
                      key={func.name}
                      className={cn(
                        "rounded-lg border transition-colors",
                        isEnabled
                          ? "border-primary/20 bg-primary/5"
                          : "border-muted/60 bg-muted/20",
                      )}
                    >
                      <div className="flex items-start justify-between gap-3 p-3">
                        <button
                          type="button"
                          className="min-w-0 flex-1 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                          aria-expanded={isExpanded}
                          aria-controls={detailsId}
                          onClick={() =>
                            setExpandedFunctionName((current) =>
                              current === func.name ? null : func.name,
                            )
                          }
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className={cn(
                                "rounded p-1",
                                isEnabled ? "bg-primary" : "bg-muted",
                              )}
                            >
                              <span
                                className={cn(
                                  "text-[10px] font-medium",
                                  isEnabled
                                    ? "text-white"
                                    : "text-muted-foreground",
                                )}
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
                          <p
                            id={descriptionId}
                            className={cn(
                              "mt-1 text-xs text-muted-foreground",
                              !descriptionExpanded && "line-clamp-2",
                            )}
                          >
                            {descriptionExpanded
                              ? description
                              : descriptionPreview}
                          </p>
                          <p className="mt-2 text-[10px] text-muted-foreground">
                            {propertyEntries.length > 0
                              ? `${propertyEntries.length} parameter${propertyEntries.length === 1 ? "" : "s"}`
                              : "No input parameters"}
                            <span className="mx-1.5 text-border">·</span>
                            {isExpanded ? "Hide details" : "View details"}
                          </p>
                        </button>
                        <div className="flex shrink-0 items-center gap-2">
                          <Switch
                            id={`drawer-func-${func.name}`}
                            checked={isEnabled}
                            onCheckedChange={(checked) =>
                              onToggleFunction(tool.id, func.name, checked)
                            }
                            disabled={!isToolEnabled || !canEdit}
                            className="mt-1"
                          />
                          <ChevronDown
                            className={cn(
                              "mt-1 h-4 w-4 text-muted-foreground transition-transform",
                              isExpanded && "rotate-180 text-primary",
                            )}
                          />
                        </div>
                      </div>
                      {hasLongDescription && (
                        <div className="px-3 pb-3 -mt-1">
                          <button
                            type="button"
                            className="text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                            aria-controls={descriptionId}
                            aria-expanded={descriptionExpanded}
                            onClick={() =>
                              setExpandedDescriptionName((current) =>
                                current === func.name ? null : func.name,
                              )
                            }
                          >
                            {descriptionExpanded
                              ? "Hide full description"
                              : "Show full description"}
                          </button>
                        </div>
                      )}
                      {isExpanded && (
                        <div
                          id={detailsId}
                          className="border-t px-3 pb-3 pt-2.5"
                        >
                          {propertyEntries.length > 0 ? (
                            <div className="space-y-2">
                              {propertyEntries.map(([name, property]) => (
                                <div
                                  key={name}
                                  className="rounded-md border bg-background/70 px-2.5 py-2"
                                >
                                  <div className="flex flex-wrap items-center gap-2">
                                    <span className="font-mono text-[11px] font-medium">
                                      {name}
                                    </span>
                                    <Badge
                                      variant="secondary"
                                      className="h-5 text-[10px]"
                                    >
                                      {property.type || "any"}
                                    </Badge>
                                    {required.has(name) && (
                                      <Badge
                                        variant="outline"
                                        className="h-5 border-amber-300 bg-amber-50 text-[10px] text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
                                      >
                                        required
                                      </Badge>
                                    )}
                                  </div>
                                  {property.description && (
                                    <p className="mt-1 text-[11px] leading-5 text-muted-foreground">
                                      {property.description}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-[11px] text-muted-foreground">
                              This function does not declare input parameters.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                {filteredFunctions.length === 0 && (
                  <div className="rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 px-4 py-6 text-center">
                    <p className="text-sm font-medium">No functions found</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Try a different name, description, or parameter.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {!isToolEnabled && (
            <div className="flex items-center justify-center p-4 bg-muted/20 rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Enable this tool to use its features
              </p>
            </div>
          )}
        </div>

        <SheetFooter className="px-6 pb-6 space-y-3">
          {agentTool && (
            <DeleteButton
              onClick={onDisconnect}
              disabled={!canEdit}
              className="w-full"
            >
              Disconnect Tool
            </DeleteButton>
          )}
          {!isToolEnabled && (
            <div className="w-full text-center py-2 bg-muted/20 rounded-lg border border-dashed">
              <p className="text-sm text-muted-foreground">
                Enable this tool to use its features
              </p>
            </div>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
