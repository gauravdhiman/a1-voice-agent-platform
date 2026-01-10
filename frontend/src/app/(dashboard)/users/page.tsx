"use client";

import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Users, UserPlus, UserCheck, UserX, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { useRouter } from "next/navigation";

export default function UsersPage() {
  const { user } = useAuth();
  const router = useRouter();

  // Check if user is a platform admin
  const isPlatformAdmin = user?.hasRole("platform_admin");

  // If user is not a platform admin, show access denied message
  if (!isPlatformAdmin) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this page. Only platform administrators can view this page."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            User Management
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage platform users and permissions.
          </p>
        </div>
        <Button>
          <UserPlus className="mr-2 h-4 w-4" />
          Add User
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12,345</div>
            <p className="text-xs text-muted-foreground">
              +180 from last month
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <UserCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">10,234</div>
            <p className="text-xs text-muted-foreground">
              +12% from last month
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Suspended Users
            </CardTitle>
            <UserX className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">-2 from last month</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-dashed border-2 bg-muted/10">
        <CardHeader className="text-center">
          <div className="mx-auto bg-primary/10 p-4 rounded-full mb-4 w-16 h-16 flex items-center justify-center">
            <ShieldAlert className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-xl">
            Platform Management Under Construction
          </CardTitle>
          <CardDescription className="max-w-md mx-auto mt-2">
            We are currently building advanced user management features. For
            now, please manage users through their respective organizations.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center pb-8">
          <Button
            variant="outline"
            onClick={() => router.push("/organizations")}
            className="mt-4"
          >
            Go to Organizations
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
