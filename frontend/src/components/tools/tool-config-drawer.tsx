import * as React from "react";
import { cn } from "@/lib/utils";
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
import { Checkbox } from "@/components/ui/checkbox";
import {
  ShieldCheck,
  RefreshCw,
  LogOut,
  Clock,
  Settings,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { AuthStatus, PlatformTool, AgentTool } from "@/types/agent";

export interface ToolConfigDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tool: PlatformTool;
  agentTool: AgentTool | null;
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
  canEdit: boolean;
  isSaving?: boolean;
}

export function ToolConfigDrawer({
  open,
  onOpenChange,
  tool,
  agentTool,
  onSaveConfig,
  onToggleFunction,
  onOAuth,
  onLogout,
  canEdit,
  isSaving = false,
}: ToolConfigDrawerProps) {
  const [localConfig, setLocalConfig] = React.useState<Record<string, unknown>>(
    {},
  );
  const [hasUnsavedChanges, setHasUnsavedChanges] = React.useState(false);
  const [isConnecting, setIsConnecting] = React.useState(false);

  React.useEffect(() => {
    if (agentTool?.config) {
      setLocalConfig(agentTool.config);
      setHasUnsavedChanges(false);
    }
  }, [agentTool?.config, open]);

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
  const toolUnselectedFunctions = agentTool?.unselected_functions || [];
  const isToolEnabled = agentTool?.is_enabled ?? false;

  const isOAuth = schema?.requires_auth || tool.name.includes("calendar");
  const hasFunctions = functions.length > 0;

  const getTimeUntilExpiry = (expiresAt: number | null) => {
    if (!expiresAt) return null;
    const secondsLeft = Math.floor((expiresAt * 1000 - Date.now()) / 1000);
    const minutesLeft = Math.floor(secondsLeft / 60);

    if (minutesLeft < 1) return "< 1 minute";
    if (minutesLeft < 60) return `${minutesLeft} minutes`;
    if (minutesLeft < 1440) return `${Math.floor(minutesLeft / 60)} hours`;
    return `${Math.floor(minutesLeft / 1440)} days`;
  };

  const handleConfigChange = (key: string, value: string) => {
    const newConfig = { ...localConfig, [key]: value };
    setLocalConfig(newConfig);
    setHasUnsavedChanges(true);
  };

  const handleSaveConfig = async () => {
    if (!agentTool) return;
    await onSaveConfig(agentTool.id, localConfig);
    setHasUnsavedChanges(false);
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

  const getAuthStatusConfig = () => {
    if (!agentTool) {
      return {
        message: "Not configured",
        icon: AlertCircle,
        iconColor: "text-muted-foreground",
        showButton: true,
        buttonText: "Connect",
        showExpiry: false,
      };
    }

    switch (agentTool.auth_status) {
      case AuthStatus.AUTHENTICATED:
        const timeLeft = getTimeUntilExpiry(agentTool.token_expires_at);
        return {
          message: "Connected",
          icon: CheckCircle2,
          iconColor: "text-green-500",
          showButton: true,
          buttonText: "Refresh",
          showExpiry: !!timeLeft,
          expiryText: timeLeft,
        };
      case AuthStatus.EXPIRED:
        return {
          message: "Authentication expired",
          icon: AlertCircle,
          iconColor: "text-orange-500",
          showButton: true,
          buttonText: "Connect",
          showExpiry: false,
        };
      case AuthStatus.NOT_AUTHENTICATED:
      default:
        return {
          message: "Authentication required",
          icon: AlertCircle,
          iconColor: "text-muted-foreground",
          showButton: true,
          buttonText: "Connect",
          showExpiry: false,
        };
    }
  };

  const authConfig = getAuthStatusConfig();
  const authenticated = agentTool?.auth_status === AuthStatus.AUTHENTICATED;

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
              <SheetDescription className="text-xs">
                {tool.description}
              </SheetDescription>
            </div>
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {isOAuth && (
            <div className="flex items-center justify-between gap-4 p-4 bg-primary/5 rounded-lg border border-primary/10">
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
                    {authConfig.expiryText}
                  </div>
                )}
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
                    ) : (
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                    )}
                    {isConnecting ? "Connecting..." : authConfig.buttonText}
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
                    disabled={isSaving}
                  >
                    {isSaving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : null}
                    Save
                  </Button>
                )}
              </div>
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
              <div className="space-y-2">
                {functions.map((func) => {
                  const isUnselected = toolUnselectedFunctions.includes(
                    func.name,
                  );
                  const isEnabled = !isUnselected;

                  return (
                    <div
                      key={func.name}
                      className={cn(
                        "flex items-start justify-between p-3 rounded-lg border transition-colors",
                        isEnabled
                          ? "border-primary/20 bg-primary/5"
                          : "border-muted/60 bg-muted/20",
                      )}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <div
                            className={cn(
                              "p-1 rounded",
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
                        id={`drawer-func-${func.name}`}
                        checked={isEnabled}
                        onCheckedChange={(checked) =>
                          checked !== "indeterminate" &&
                          onToggleFunction(tool.id, func.name, checked)
                        }
                        disabled={!isToolEnabled || !canEdit}
                        className="mt-1"
                      />
                    </div>
                  );
                })}
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

        <SheetFooter className="px-6 pb-6">
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
