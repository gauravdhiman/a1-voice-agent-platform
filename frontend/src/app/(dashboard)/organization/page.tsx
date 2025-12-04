'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useOrganization } from '@/contexts/organization-context';
import { useUserPermissions } from '@/hooks/use-user-permissions';
import { useOrganizationById } from '@/hooks/use-organization-by-id';
import { AccessDenied } from '@/components/ui/access-denied';
import { OrganizationEditDialog } from '@/components/organizations/organization-edit-dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { TabsContent, TabsList, TabsTrigger, AnimatedTabs } from '@/components/ui/tabs';
import {
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
} from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { OrganizationCompleteData } from '@/types/organization';

// Mock API service - in real implementation, this would be actual API calls
const apiService = {
 async getOrganizationData(orgId: string): Promise<OrganizationCompleteData> {
    // Mock data - replace with actual API call
    return {
      organization: {
        id: orgId,
        name: 'Acme Corp',
        description: 'A leading technology company',
        slug: 'acme-corp',
        website: 'https://acme.com',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
        business_details: 'We offer premium software solutions and professional consulting services to help businesses grow. Our products include advanced software tools and comprehensive consulting packages.',
      },
    };
 },
};

export default function OrganizationPage() {
  const { user } = useAuth();
  const { currentOrganization, loading: orgLoading, setCurrentOrganization } = useOrganization();
  const { canUpdateOrganization, canViewMembers, isPlatformAdmin, isOrgAdmin } = useUserPermissions();
  const searchParams = useSearchParams();
  const orgId = searchParams.get('org_id');

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [organizationData, setOrganizationData] = useState<OrganizationCompleteData | null>(null);
  const [loading, setLoading] = useState(true);
  const [editedOrg, setEditedOrg] = useState<{
    name: string;
    description: string;
    website: string;
    slug: string;
    is_active: boolean;
    business_details: string;
  } | null>(null);
  const [saving, setSaving] = useState(false);


  const loadOrganizationData = useCallback(async () => {
    if (!orgId) return;
    
    setLoading(true);
    try {
      const data = await apiService.getOrganizationData(orgId);
      setOrganizationData(data);
      setEditedOrg({
        name: data.organization.name,
        description: data.organization.description || '',
        website: data.organization.website || '',
        slug: data.organization.slug,
        is_active: data.organization.is_active,
        business_details: data.organization.business_details || '',
      });
    } catch (error) {
      console.error('Failed to load organization data:', error);
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

  // Validate organization access when orgId is provided
  const { isValid: isOrgValid, loading: validationLoading, organization: validatedOrg } = useOrganizationById(orgId);

  // Set the current organization based on the validated orgId parameter if provided
  if (validatedOrg && (!currentOrganization || currentOrganization.id !== validatedOrg.id)) {
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
    setSaving(true);
    // Simulate save operation
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSaving(false);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    loadOrganizationData(); // Reload to reset changes
  };


  // Make orgId mandatory - if not provided, redirect to organizations page
  if (!orgId) {
    return <AccessDenied
      title="Organization ID Required"
      description="Organization ID is required to access this page. Please select an organization from the organizations page."
      redirectPath="/organizations"
    />;
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
    return <AccessDenied
      title="Access Denied"
      description="You do not have permission to access this organization. Please contact your organization administrator or platform admin for access."
      redirectPath="/organizations"
    />;
  }

  if (!isPlatformAdmin && !isOrgAdmin) {
    return <AccessDenied
      title="Access Denied"
      description="You do not have permission to view organization pages. Please contact your organization administrator or platform admin for access."
      redirectPath="/dashboard"
    />;
  }

  if (!validatedOrg) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Organization not found</div>
      </div>
    );
  }

  const userRoles = user?.roles
    ?.filter(userRole => !userRole.organization_id || userRole.organization_id === validatedOrg.id)
    .map(userRole => userRole.role) || [];

  const displayOrg = (isEditing && editedOrg) ? editedOrg : organizationData?.organization;

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
              <h1 className="text-2xl font-bold text-foreground">{displayOrg.name}</h1>
              <p className="text-sm text-muted-foreground">Organization Configuration</p>
            </div>
          </div>

          {canUpdateOrganization && (
            <div className="flex items-center space-x-2">
              {isEditing ? (
                <>
                  <Button onClick={handleSave} disabled={saving} size="sm" className="flex items-center space-x-2">
                    <Save className="h-4 w-4" />
                    <span>{saving ? 'Saving...' : 'Save Changes'}</span>
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleCancel} className="flex items-center space-x-2">
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
                      <DropdownMenuItem className="flex items-center space-x-2 cursor-pointer" onClick={handleEdit}>
                        <Edit3 className="h-4 w-4" />
                        <span>Edit Organization</span>
                      </DropdownMenuItem>
                      {canViewMembers && (
                        <Link href={`/organization/members?org_id=${validatedOrg.id}`}>
                          <DropdownMenuItem className="flex items-center space-x-2 cursor-pointer">
                            <Users className="h-4 w-4" />
                            <span>Manage Members</span>
                          </DropdownMenuItem>
                        </Link>
                      )}
                      <Link href={`/organization/billing?org_id=${validatedOrg.id}`}>
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
            {displayOrg.is_active ? 'Active' : 'Inactive'}
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
                : `${userRoles.length} roles`
              }
            </span>
          )}
        </div>
      </div>

      <AnimatedTabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
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
                {isEditing ? 'Edit your organization details' : 'Your organization details and settings'}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-5 pt-0 space-y-4">
              {isEditing ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      value={editedOrg?.name || ''}
                      onChange={(e) => editedOrg && setEditedOrg({ ...editedOrg, name: e.target.value })}
                      placeholder="Enter organization name"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      value={editedOrg?.description || ''}
                      onChange={(e) => editedOrg && setEditedOrg({ ...editedOrg, description: e.target.value })}
                      placeholder="Tell us about your organization, like little background, about team etc. This will be used by AI agent for context."
                      className="min-h-[100px]"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website">Website</Label>
                    <Input
                      id="website"
                      type="url"
                      value={editedOrg?.website || ''}
                      onChange={(e) => editedOrg && setEditedOrg({ ...editedOrg, website: e.target.value })}
                      placeholder="https://www.example.com"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="slug">Slug</Label>
                    <Input
                      id="slug"
                      value={editedOrg?.slug || ''}
                      onChange={(e) => editedOrg && setEditedOrg({ ...editedOrg, slug: e.target.value })}
                      placeholder="organization-slug"
                    />
                    <p className="text-xs text-muted-foreground">Used in URLs and API calls</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Status</Label>
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="isActive"
                        checked={editedOrg?.is_active ?? true}
                        onChange={(e) => editedOrg && setEditedOrg({ ...editedOrg, is_active: e.target.checked })}
                        className="rounded"
                      />
                      <label htmlFor="isActive" className="text-sm">Organization is active</label>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Name</label>
                    <p className="text-foreground">{displayOrg.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Description</label>
                    <p className="text-foreground">{displayOrg.description || 'No description'}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Website</label>
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
                    <label className="text-sm font-medium text-muted-foreground">Slug</label>
                    <p className="text-foreground font-mono">{displayOrg.slug}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Status</label>
                    <div className="flex items-center space-x-2">
                      <Badge variant={displayOrg.is_active ? "default" : "secondary"}>
                        {displayOrg.is_active ? 'Active' : 'Inactive'}
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
                    <Label htmlFor="business_details">Business Details for AI Agent</Label>
                    <Textarea
                      id="business_details"
                      value={editedOrg?.business_details || ''}
                      onChange={(e) => editedOrg && setEditedOrg({ ...editedOrg, business_details: e.target.value })}
                      placeholder="Enter details about your business, products, services, hours, and other information for the AI agent to know..."
                      className="min-h-[200px]"
                    />
                    <p className="text-xs text-muted-foreground">This information will be used by the AI voice agent to answer customer questions</p>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">Business Details</label>
                    <p className="text-foreground">
                      {organizationData?.organization.business_details || 'No business details provided'}
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
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
