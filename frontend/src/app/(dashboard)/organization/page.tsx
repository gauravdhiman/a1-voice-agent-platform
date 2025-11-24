'use client';

import React, { useState, useCallback } from 'react';
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
} from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import type { UserRoleWithPermissions } from '@/types/user';

export default function OrganizationPage() {
  const { user } = useAuth();
  const { currentOrganization, loading: orgLoading, setCurrentOrganization } = useOrganization();
  const { canUpdateOrganization, canViewMembers, isPlatformAdmin, isOrgAdmin } = useUserPermissions();
  const searchParams = useSearchParams();
  const orgId = searchParams.get('org_id');

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedOrg, setEditedOrg] = useState<{
    name: string;
    description: string;
    website: string;
    slug: string;
    is_active: boolean;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  const loadOrganizationData = useCallback(async () => {
    // This function is now primarily for re-fetching data after an update.
    // The initial data loading is handled by the hooks.
  }, []);

  // Validate organization access when orgId is provided
  const { isValid: isOrgValid, loading: validationLoading, organization: validatedOrg } = useOrganizationById(orgId);

  // Set the current organization based on the validated orgId parameter if provided
  if (validatedOrg && (!currentOrganization || currentOrganization.id !== validatedOrg.id)) {
    setCurrentOrganization(validatedOrg);
  }

  const handleEdit = () => {
    if (validatedOrg) {
      setEditedOrg({
        name: validatedOrg.name,
        description: validatedOrg.description || '',
        website: validatedOrg.website || '',
        slug: validatedOrg.slug,
        is_active: validatedOrg.is_active
      });
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
    setEditedOrg(null);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedOrg(null);
  };

  // Make orgId mandatory - if not provided, redirect to organizations page
 if (!orgId) {
   return <AccessDenied 
     title="Organization ID Required"
     description="Organization ID is required to access this page. Please select an organization from the organizations page."
     redirectPath="/organizations"
   />;
 }

 if (orgLoading || validationLoading) {
   return (
     <div className="p-6">
       <div className="flex items-center justify-center h-64">
         <div className="text-gray-50">Loading organization...</div>
       </div>
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
     <div className="p-6">
       <div className="flex items-center justify-center h-64">
         <div className="text-red-50">Organization not found</div>
       </div>
     </div>
   );
 }

 const userRoles = user?.roles
   ?.filter(userRole => !userRole.organization_id || userRole.organization_id === validatedOrg.id)
   .map(userRole => userRole.role) || [];

 const displayOrg = (isEditing && editedOrg) ? editedOrg : validatedOrg;

 if (!displayOrg) {
   return (
     <div className="p-6">
       <div className="flex items-center justify-center h-64">
         <div className="text-red-50">Organization data not available</div>
       </div>
     </div>
   );
 }

 return (
   <div className="p-6">
     {/* Organization Header */}
     <div className="mb-6">
       <div className="flex items-center justify-between mb-4">
         <div className="flex items-center space-x-4">
           <div className="bg-primary/10 p-3 rounded-lg">
             <Building2 className="h-8 w-8 text-primary" />
           </div>
           <div>
             <h1 className="text-3xl font-bold text-foreground">{displayOrg.name}</h1>
             <p className="text-muted-foreground">Organization Details</p>
           </div>
         </div>

         {canUpdateOrganization && (
           <div className="flex items-center space-x-2">
             {isEditing ? (
               <>
                 <Button onClick={handleSave} disabled={saving} className="flex items-center space-x-2">
                   <Save className="h-4 w-4" />
                   <span>{saving ? 'Saving...' : 'Save Changes'}</span>
                 </Button>
                 <Button variant="outline" onClick={handleCancel} className="flex items-center space-x-2">
                   <X className="h-4 w-4" />
                   <span>Cancel</span>
                 </Button>
               </>
             ) : (
               <div className="relative">
                 <DropdownMenu>
                   <DropdownMenuTrigger asChild>
                     <Button className="flex items-center space-x-2">
                       <Activity className="h-4 w-4" />
                       <span>Actions</span>
                     </Button>
                   </DropdownMenuTrigger>
                   <DropdownMenuContent align="end" className="w-56">
                     <DropdownMenuItem className="flex items-center space-x-2" onClick={handleEdit}>
                       <Edit3 className="h-4 w-4" />
                       <span>Edit Organization</span>
                     </DropdownMenuItem>
                     {canViewMembers && (
                       <Link href={`/organization/members?org_id=${validatedOrg.id}`}>
                         <DropdownMenuItem className="flex items-center space-x-2">
                           <Users className="h-4 w-4" />
                           <span>Manage Members</span>
                         </DropdownMenuItem>
                       </Link>
                     )}
                     <Link href={`/organization/billing?org_id=${validatedOrg.id}`}>
                       <DropdownMenuItem className="flex items-center space-x-2">
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
         <span className="text-muted-foreground flex items-center">
           <Calendar className="h-4 w-4 mr-1" />
           Created {new Date(validatedOrg.created_at).toLocaleDateString()}
         </span>
         {userRoles.length > 0 && (
           <span className="text-muted-foreground flex items-center">
             <Crown className="h-4 w-4 mr-1" />
             {userRoles.length === 1 
               ? userRoles[0].name 
               : `${userRoles.length} roles`
             }
           </span>
         )}
       </div>
     </div>

     <div className="space-y-6">
       {/* Organization Info */}
       <Card>
         <CardHeader>
           <CardTitle className="flex items-center space-x-2">
             <Building2 className="h-5 w-5" />
             <span>Organization Information</span>
           </CardTitle>
           <CardDescription>
             {isEditing ? 'Edit your organization details' : 'Your organization details and settings'}
           </CardDescription>
         </CardHeader>
         <CardContent className="space-y-4">
           {isEditing ? (
             <>
               <div className="space-y-2">
                 <Label htmlFor="name">Name</Label>
                 <Input
                   id="name"
                   value={editedOrg?.name || ''}
                   onChange={(e) => editedOrg && setEditedOrg({...editedOrg, name: e.target.value})}
                   placeholder="Enter organization name"
                 />
               </div>
               
               <div className="space-y-2">
                 <Label htmlFor="description">Description</Label>
                 <Textarea 
                   id="description" 
                   value={editedOrg?.description || ''}
                   onChange={(e) => editedOrg && setEditedOrg({...editedOrg, description: e.target.value})}
                   placeholder="Tell us about your organization"
                   className="min-h-[100px]"
                 />
               </div>
               
               <div className="space-y-2">
                 <Label htmlFor="website">Website</Label>
                 <Input 
                   id="website" 
                   type="url"
                   value={editedOrg?.website || ''}
                   onChange={(e) => editedOrg && setEditedOrg({...editedOrg, website: e.target.value})}
                   placeholder="https://www.example.com"
                 />
               </div>
               
               <div className="space-y-2">
                 <Label htmlFor="slug">Slug</Label>
                 <Input
                   id="slug"
                   value={editedOrg?.slug || ''}
                   onChange={(e) => editedOrg && setEditedOrg({...editedOrg, slug: e.target.value})}
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
                     onChange={(e) => editedOrg && setEditedOrg({...editedOrg, is_active: e.target.checked})}
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
     </div>

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
