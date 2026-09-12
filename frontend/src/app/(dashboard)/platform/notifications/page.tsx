"use client";

/**
 * Platform notification settings page (platform admin only).
 */

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformNotificationSettingsForm } from "@/components/notifications/platform-notification-settings-form";

export default function PlatformNotificationsPage() {
  const { user } = useAuth();

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage notification settings."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Notification Settings
        </h1>
        <p className="text-muted-foreground">
          Configure the lead-alert recipient, verification email sender, and
          Telegram alerts for signups, invitation joins, and interest requests.
        </p>
      </div>
      <PlatformNotificationSettingsForm />
    </div>
  );
}
