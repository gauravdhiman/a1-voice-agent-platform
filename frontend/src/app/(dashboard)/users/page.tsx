'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, UserPlus, UserCheck, UserX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/auth-context';
import { AccessDenied } from '@/components/ui/access-denied';

export default function UsersPage() {
  const { user } = useAuth();

  // Check if user is a platform admin
  const isPlatformAdmin = user?.hasRole('platform_admin');

  // If user is not a platform admin, show access denied message
  if (!isPlatformAdmin) {
    return <AccessDenied
      title="Access Denied"
      description="You do not have permission to access this page. Only platform administrators can view this page."
      redirectPath="/dashboard"
    />;
  }

  return (
    <div className="p-6">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center space-x-4">
          <div className="bg-primary/10 p-3 rounded-lg">
            <Users className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-foreground">User Management</h1>
            <p className="text-muted-foreground">
              Platform-wide user management coming soon. For now, manage users through organization invitations.
            </p>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>User Management</CardTitle>
          <CardDescription>
            Platform-wide user management features are under development.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Currently, user management is handled through organization memberships. 
            Users can be invited and managed through the organization members section.
          </p>
          <div className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => window.location.href = '/organizations'}
            >
              Go to Organizations
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
