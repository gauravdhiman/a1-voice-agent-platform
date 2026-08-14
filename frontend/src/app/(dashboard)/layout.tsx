"use client";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { OrganizationCheck } from "@/components/auth/organization-check";
import { InviteWelcomeToast } from "@/components/dashboard/invite-welcome-toast";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { ProductTourProvider } from "@/components/product-tour/product-tour-provider";

export default function DashboardLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <OrganizationCheck>
        <InviteWelcomeToast />
        <ProductTourProvider>
          <DashboardLayout>{children}</DashboardLayout>
        </ProductTourProvider>
      </OrganizationCheck>
    </ProtectedRoute>
  );
}
