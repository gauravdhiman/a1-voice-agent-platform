'use client';

import React, { useCallback, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useUserPermissions } from '@/hooks/use-user-permissions';
import { useAgent, usePlatformTools, useAgentTools, useUpdateAgent, useToggleFunction, useUpdateAgentTool, useStartOAuth, useLogoutAgentTool } from '@/hooks/use-agent-queries';
import { organizationService } from '@/services/organization-service';
import { agentService } from '@/services/agent-service';
import type { PlatformTool, AgentTool } from '@/types/agent';
import type { Organization } from '@/types/organization';
import { AuthStatus } from '@/types/agent';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { AnimatedTabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Bot,
  Trash2,
  Settings,
  ShieldCheck,
  RefreshCw,
  LogOut,
  Clock,
  Save,
  ArrowLeft,
  Loader2,
  Wrench,
} from 'lucide-react';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { formatToolName } from '@/lib/utils';

export default function AgentDetailPage() {
  const { user } = useAuth();
  const { isPlatformAdmin } = useUserPermissions();
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const agentId = params.agentId as string;

  const [organization, setOrganization] = React.useState<Organization | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [localAgentTools, setLocalAgentTools] = React.useState<AgentTool[]>([]);
  const [activeTab, setActiveTab] = React.useState('properties');

  // Agent form state
  const [agentForm, setAgentForm] = React.useState({
    name: '',
    phone_number: '',
    system_prompt: '',
    is_active: true
  });

  // Fetch data using React Query
  const { data: agent, isLoading: agentLoading, error: agentError } = useAgent(agentId);
  const { data: platformTools = [], isLoading: toolsLoading } = usePlatformTools();
  const { data: agentTools = [], refetch: refetchAgentTools } = useAgentTools(agentId);

  // Mutations
  const updateAgentMutation = useUpdateAgent();
  const toggleFunctionMutation = useToggleFunction();
  const updateAgentToolMutation = useUpdateAgentTool();
  const startOAuthMutation = useStartOAuth();
  const logoutAgentToolMutation = useLogoutAgentTool();

  // Load organization when agent data is available
  React.useEffect(() => {
    if (agent?.organization_id) {
      organizationService.getOrganizationById(agent.organization_id)
        .then(setOrganization)
        .catch(error => {
          console.error('Failed to load organization:', error);
        });
    }
  }, [agent?.organization_id]);

  // Update form when agent data changes
  React.useEffect(() => {
    if (agent) {
      setAgentForm({
        name: agent.name,
        phone_number: agent.phone_number || '',
        system_prompt: agent.system_prompt || '',
        is_active: agent.is_active
      });
    }
  }, [agent]);

  // Sync local agent tools state with query data
  React.useEffect(() => {
    if (agentTools.length > 0) {
      setLocalAgentTools(agentTools);
    }
  }, [agentTools]);

  // Sync tab state with URL
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'properties' || tabParam === 'tools') {
      setActiveTab(tabParam);
    }
  }, [searchParams]);

  const handleTabChange = useCallback((value: string) => {
    setActiveTab(value);
    router.push(`/agents/${agentId}?tab=${value}`, { scroll: false });
  }, [router, agentId]);

  const handleSaveAgent = useCallback(async () => {
    if (!agentId) return;

    setSaving(true);
    try {
      await updateAgentMutation.mutateAsync({
        agentId,
        data: agentForm
      });
    } catch (error) {
      console.error('Failed to save agent:', error);
    } finally {
      setSaving(false);
    }
  }, [agentId, agentForm, updateAgentMutation]);

  const handleDeleteAgent = async () => {
    if (!agent || !confirm(`Are you sure you want to delete "${agent.name}"? This action cannot be undone.`)) return;
    
    router.back();
  };

  const handleToggleTool = useCallback(async (toolId: string, isEnabled: boolean) => {
    try {
      const existingAgentTool = localAgentTools.find(at => at.tool_id === toolId);

      if (existingAgentTool) {
        await updateAgentToolMutation.mutateAsync({
          agentToolId: existingAgentTool.id,
          data: { is_enabled: isEnabled }
        });
      } else {
        await agentService.configureAgentTool({
          agent_id: agentId,
          tool_id: toolId,
          is_enabled: isEnabled,
          config: {},
          unselected_functions: []
        });
        await refetchAgentTools();
      }
    } catch (error) {
      console.error('Failed to toggle tool:', error);
    }
  }, [localAgentTools, agentId, updateAgentToolMutation, refetchAgentTools]);

  const handleToggleFunction = useCallback(async (toolId: string, functionName: string, isEnabled: boolean) => {
    try {
      const existingAgentTool = localAgentTools.find(at => at.tool_id === toolId);
      if (!existingAgentTool) return;

      await toggleFunctionMutation.mutateAsync({
        agentToolId: existingAgentTool.id,
        functionName,
        isEnabled
      });
    } catch (error) {
      console.error('Failed to toggle function:', error);
    }
  }, [localAgentTools, toggleFunctionMutation]);

  const handleSaveToolConfig = useCallback(async (agentToolId: string, config: Record<string, unknown>) => {
    try {
      await updateAgentToolMutation.mutateAsync({
        agentToolId,
        data: { config }
      });
    } catch (error) {
      console.error('Failed to save tool config:', error);
    }
  }, [updateAgentToolMutation]);

  const handleOAuth = useCallback(async (toolName: string) => {
    try {
      await startOAuthMutation.mutateAsync({ toolName, agentId });
    } catch (error) {
      console.error('OAuth failed:', error);
    }
  }, [agentId, startOAuthMutation]);

  const handleLogout = useCallback(async (agentToolId: string) => {
    try {
      await logoutAgentToolMutation.mutateAsync(agentToolId);
    } catch (error) {
      console.error('Failed to log out:', error);
    }
  }, [logoutAgentToolMutation]);

  const renderToolConfig = useCallback((tool: PlatformTool, agentTool?: AgentTool) => {
    if (!agentTool) return null;

    const schema = tool.config_schema as {
      requires_auth?: boolean;
      properties?: Record<string, {
        title?: string;
        description?: string;
        default?: unknown;
      }>;
    } | null;

    const config = (agentTool.config || {}) as Record<string, unknown>;
    const isOAuth = schema?.requires_auth || tool.name.includes('calendar');

    const functions = tool.tool_functions_schema?.functions || [];
    const toolUnselectedFunctions = agentTool.unselected_functions || [];
    const isToolEnabled = agentTool.is_enabled;

    const handleConfigChange = (key: string, value: string) => {
      const newConfig = { ...config, [key]: value };
      setLocalAgentTools(prev => prev.map(at =>
        at.id === agentTool.id ? { ...at, config: newConfig } : at
      ));
    };

    const getTimeUntilExpiry = (expiresAt: number | null) => {
      if (!expiresAt) return null;
      const secondsLeft = Math.floor((expiresAt * 1000 - Date.now()) / 1000);
      const minutesLeft = Math.floor(secondsLeft / 60);

      if (minutesLeft < 1) return '< 1 minute';
      if (minutesLeft < 60) return `${minutesLeft} minutes`;
      if (minutesLeft < 1440) return `${Math.floor(minutesLeft / 60)} hours`;
      return `${Math.floor(minutesLeft / 1440)} days`;
    };

    const getAuthStatusConfig = () => {
      switch (agentTool.auth_status) {
        case AuthStatus.AUTHENTICATED:
          const timeLeft = getTimeUntilExpiry(agentTool.token_expires_at);
          return {
            message: 'Authenticated',
            iconColor: 'text-green-500',
            showButton: true,
            buttonText: 'Refresh now',
            showExpiry: !!timeLeft,
            expiryText: timeLeft
          };
        case AuthStatus.EXPIRED:
          return {
            message: 'Authentication expired',
            iconColor: 'text-red-500',
            showButton: true,
            buttonText: 'Authenticate',
            showExpiry: false
          };
        case AuthStatus.NOT_AUTHENTICATED:
        default:
          return {
            message: 'Authentication required',
            iconColor: 'text-muted',
            showButton: true,
            buttonText: 'Authenticate',
            showExpiry: false
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
                  <span className="text-xs font-medium">{authConfig.message}</span>
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
                <Label htmlFor={`${tool.id}-${key}`} className="text-[10px] uppercase text-muted-foreground">
                  {prop.title || key}
                </Label>
                <Input
                  id={`${tool.id}-${key}`}
                  placeholder={prop.description || ''}
                  value={(config[key] as string) || (prop.default as string) || ''}
                  onChange={(e) => handleConfigChange(key, e.target.value)}
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
                ({functions.length} total, {functions.length - toolUnselectedFunctions.length} enabled)
              </span>
              {!isToolEnabled && (
                <Badge variant="secondary" className="ml-2 h-5 text-[10px]">
                  Enable tool to use functions
                </Badge>
              )}
            </div>
            <div className="space-y-2">
              {functions.map((func) => {
                const isUnselected = toolUnselectedFunctions.includes(func.name);
                const isEnabled = !isUnselected;

                return (
                  <div
                    key={func.name}
                    className={`flex items-start justify-between p-3 rounded-lg border transition-colors ${
                      isEnabled
                        ? 'border-primary/20 bg-primary/5'
                        : 'border-muted/60 bg-muted/20'
                    }`}
                  >
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <div className={`p-1.5 rounded ${isEnabled ? 'bg-primary' : 'bg-muted'}`}>
                          <span className={`${isEnabled ? 'text-white' : 'text-muted-foreground'} text-xs font-medium`}>{func.name}</span>
                        </div>
                        {!isEnabled && (
                          <Badge variant="secondary" className="h-5 text-[10px]">
                            Disabled
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{func.description}</p>
                      {func.parameters?.properties && (
                        <div className="mt-2 text-[10px] text-muted-foreground">
                          <span className="font-medium">Parameters:</span>{' '}
                          {Object.keys(func.parameters.properties).join(', ')}
                        </div>
                      )}
                    </div>
                    <Checkbox
                      id={`func-${func.name}`}
                      checked={isEnabled}
                      onCheckedChange={(checked) => handleToggleFunction(tool.id, func.name, checked === true)}
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
  }, [handleOAuth, handleLogout, handleSaveToolConfig, handleToggleFunction]);

  if (agentError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Failed to load agent</div>
      </div>
    );
  }

  if (agentLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 text-muted-foreground animate-spin" />
        <span className="ml-3 text-muted-foreground">Loading agent...</span>
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Agent not found</div>
      </div>
    );
  }

  const canEdit = isPlatformAdmin || (agent && user?.hasRole('org_admin', agent.organization_id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.back()}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="bg-primary/10 p-3 rounded-lg">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            <p className="text-sm text-muted-foreground">
              {organization?.name || 'Unknown Organization'}
            </p>
          </div>
        </div>
        {canEdit && (
          <Button
            variant="outline"
            className="text-destructive"
            onClick={handleDeleteAgent}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete Agent
          </Button>
        )}
      </div>

      <AnimatedTabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList className="w-full">
          <TabsTrigger value="properties">Properties</TabsTrigger>
          <TabsTrigger value="tools">Tools</TabsTrigger>
        </TabsList>

        {/* Properties Tab */}
        <TabsContent value="properties">
          <Card>
            <CardHeader className="p-5 pb-3">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Settings className="h-5 w-5" />
                <span>Agent Properties</span>
              </CardTitle>
              <CardDescription>
                Configure your AI voice agent settings
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={agentForm.name}
                  onChange={(e) => setAgentForm({ ...agentForm, name: e.target.value })}
                  disabled={!canEdit}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input
                  id="phone"
                  value={agentForm.phone_number}
                  onChange={(e) => setAgentForm({ ...agentForm, phone_number: e.target.value })}
                  placeholder="+1234567890"
                  disabled={!canEdit}
                />
                <p className="text-xs text-muted-foreground">Twilio phone number for this agent</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="prompt">System Prompt</Label>
                <Textarea
                  id="prompt"
                  value={agentForm.system_prompt}
                  onChange={(e) => setAgentForm({ ...agentForm, system_prompt: e.target.value })}
                  placeholder="You are a helpful customer support agent..."
                  className="min-h-[200px]"
                  disabled={!canEdit}
                />
                <p className="text-xs text-muted-foreground">Instructions for the AI on how to behave</p>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
                  id="active"
                  checked={agentForm.is_active}
                  onCheckedChange={(checked) => setAgentForm({ ...agentForm, is_active: checked === true })}
                  disabled={!canEdit}
                />
                <Label htmlFor="active" className="text-sm font-normal cursor-pointer">
                  Agent is active and ready to handle calls
                </Label>
              </div>

              {canEdit && (
                <div className="flex space-x-2 pt-4">
                  <Button onClick={handleSaveAgent} disabled={saving || updateAgentMutation.isPending}>
                    <Save className="h-4 w-4 mr-2" />
                    {saving || updateAgentMutation.isPending ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tools Tab */}
        <TabsContent value="tools">
          <Card>
            <CardHeader className="p-5 pb-3">
              <CardTitle className="flex items-center space-x-2 text-lg">
                <Wrench className="h-5 w-5" />
                <span>Tool Configuration</span>
              </CardTitle>
              <CardDescription>
                Enable and configure platform tools for {agent.name}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0">
              {toolsLoading ? (
                <div className="flex flex-col items-center justify-center py-12 space-y-4">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                  <p className="text-sm text-muted-foreground">Loading tools...</p>
                </div>
              ) : platformTools.length === 0 ? (
                <div className="text-center py-12 bg-muted/20 rounded-lg">
                  <Wrench className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
                  <p className="text-muted-foreground">No platform tools available</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {platformTools.map((tool) => {
                    const agentTool = localAgentTools.find(at => at.tool_id === tool.id);
                    const isEnabled = agentTool?.is_enabled || false;

                    return (
                      <Card key={tool.id} className={`overflow-hidden border-2 transition-colors ${isEnabled ? 'border-primary/20 bg-primary/5' : 'border-muted/50'}`}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center space-x-3">
                              <div className={`p-2 rounded-lg ${isEnabled ? 'bg-primary' : 'bg-muted'}`}>
                                <Wrench className="h-4 w-4" />
                              </div>
                              <div>
                                <h4 className="font-semibold text-sm">{formatToolName(tool.name)}</h4>
                                <p className="text-xs text-muted-foreground line-clamp-2">{tool.description}</p>
                              </div>
                            </div>
                            <Checkbox
                              id={`tool-${tool.id}`}
                              checked={isEnabled}
                              onCheckedChange={(checked) => handleToggleTool(tool.id, checked === true)}
                              disabled={!canEdit}
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
                                <span>This tool is active for {agent.name}</span>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </AnimatedTabs>
    </div>
  );
}
