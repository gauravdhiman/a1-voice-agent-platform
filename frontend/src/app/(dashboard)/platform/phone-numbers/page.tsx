"use client";

/**
 * Platform-admin settings page for phone-number lifecycle operations.
 */

import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformPhoneNumberSettingsForm } from "@/components/phone-numbers/platform-phone-number-settings-form";
import { useAuth } from "@/contexts/auth-context";

export default function PlatformPhoneNumbersPage() {
  const { user } = useAuth();

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage phone-number settings."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Phone Number Settings
        </h1>
        <p className="text-muted-foreground">
          Configure rental grace periods and provider release retry cadence.
        </p>
      </div>
      <PlatformPhoneNumberSettingsForm />
    </div>
  );
}
