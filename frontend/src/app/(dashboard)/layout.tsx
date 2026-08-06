"use client";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { OrganizationCheck } from "@/components/auth/organization-check";
import { InviteWelcomeToast } from "@/components/dashboard/invite-welcome-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";

export default function DashboardLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <OrganizationCheck>
        <InviteWelcomeToast />
        <DashboardLayout>{children}</DashboardLayout>
      </OrganizationCheck>
    </ProtectedRoute>
  );
}
