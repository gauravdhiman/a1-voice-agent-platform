"use client";

/**
 * Platform-wide settings hub for notification delivery and phone-number policy.
 */

import { useSearchParams } from "next/navigation";
import { Bell, Phone } from "lucide-react";

import { PlatformNotificationSettingsForm } from "@/components/notifications/platform-notification-settings-form";
import { PlatformPhoneNumberSettingsForm } from "@/components/phone-numbers/platform-phone-number-settings-form";
import { SettingsSectionNavigation } from "@/components/settings/settings-section-navigation";
import type { SettingsNavigationSection } from "@/components/settings/settings-section-navigation";
import { AccessDenied } from "@/components/ui/access-denied";
import { useAuth } from "@/contexts/auth-context";

const PLATFORM_SETTINGS_SECTIONS: readonly SettingsNavigationSection[] = [
  {
    id: "notifications",
    label: "Notifications",
    description: "Alert destinations, email delivery, SMS, and Telegram.",
    icon: Bell,
  },
  {
    id: "phone-numbers",
    label: "Phone numbers",
    description: "Rental grace periods and release retry timing.",
    icon: Phone,
  },
];

/** Show all platform-wide settings behind a single platform-admin entry. */
export default function PlatformSettingsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const requestedSection = searchParams.get("section");
  const activeSection = PLATFORM_SETTINGS_SECTIONS.some(
    (section) => section.id === requestedSection,
  )
    ? requestedSection!
    : "notifications";

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage platform settings."
        redirectPath="/dashboard"
      />
    );
  }

  const hrefForSection = (sectionId: string) =>
    `/platform/settings?section=${encodeURIComponent(sectionId)}`;

  const activeTitle =
    PLATFORM_SETTINGS_SECTIONS.find((section) => section.id === activeSection)
      ?.label ?? "Platform settings";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Platform settings</h1>
        <p className="mt-1 text-muted-foreground">
          Manage platform-wide alerts and phone-number lifecycle policies.
        </p>
      </header>

      <div className="grid items-start gap-6 md:grid-cols-[14rem_minmax(0,1fr)]">
        <SettingsSectionNavigation
          ariaLabel="Platform settings"
          sections={PLATFORM_SETTINGS_SECTIONS}
          activeSection={activeSection}
          hrefForSection={hrefForSection}
        />
        <section
          aria-labelledby="platform-settings-section-title"
          className="min-w-0"
          data-testid={`platform-settings-${activeSection}`}
        >
          <h2 id="platform-settings-section-title" className="sr-only">
            {activeTitle}
          </h2>
          {activeSection === "notifications" ? (
            <PlatformNotificationSettingsForm />
          ) : (
            <PlatformPhoneNumberSettingsForm />
          )}
        </section>
      </div>
    </div>
  );
}
