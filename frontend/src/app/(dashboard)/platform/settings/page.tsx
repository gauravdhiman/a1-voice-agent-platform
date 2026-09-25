"use client";

/**
 * Platform-wide settings hub for notification delivery and phone-number policy.
 */

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PlatformNotificationSettingsForm } from "@/components/notifications/platform-notification-settings-form";
import { PlatformPhoneNumberSettingsForm } from "@/components/phone-numbers/platform-phone-number-settings-form";
import {
  AnimatedTabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { AccessDenied } from "@/components/ui/access-denied";
import { useAuth } from "@/contexts/auth-context";

const PLATFORM_SETTINGS_TABS = ["notifications", "phone-numbers"] as const;

type PlatformSettingsTab = (typeof PLATFORM_SETTINGS_TABS)[number];

/** Show all platform-wide settings behind a single platform-admin entry. */
export default function PlatformSettingsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const requestedSection = searchParams.get("section");
  const activeSectionFromUrl: PlatformSettingsTab = PLATFORM_SETTINGS_TABS.includes(
    requestedSection as PlatformSettingsTab,
  )
    ? (requestedSection as PlatformSettingsTab)
    : "notifications";
  const [activeSection, setActiveSection] =
    useState<PlatformSettingsTab>(activeSectionFromUrl);

  useEffect(() => {
    setActiveSection(activeSectionFromUrl);
  }, [activeSectionFromUrl]);

  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="Only platform administrators can manage platform settings."
        redirectPath="/dashboard"
      />
    );
  }

  const handleTabChange = (value: string) => {
    const nextSection = PLATFORM_SETTINGS_TABS.includes(
      value as PlatformSettingsTab,
    )
      ? (value as PlatformSettingsTab)
      : "notifications";
    setActiveSection(nextSection);
    const params = new URLSearchParams(searchParams.toString());
    params.set("section", nextSection);
    router.push(`/platform/settings?${params.toString()}`, { scroll: false });
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Platform settings</h1>
        <p className="mt-1 text-muted-foreground">
          Manage platform-wide alerts and phone-number lifecycle policies.
        </p>
      </header>

      <AnimatedTabs
        value={activeSection}
        onValueChange={handleTabChange}
        className="space-y-6"
      >
        <TabsList
          aria-label="Platform settings"
          className="w-full justify-start overflow-x-auto"
        >
          <TabsTrigger
            className="shrink-0 px-3 sm:px-6"
            value="notifications"
          >
            Notifications
          </TabsTrigger>
          <TabsTrigger
            className="shrink-0 px-3 sm:px-6"
            value="phone-numbers"
          >
            Phone numbers
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="notifications"
          className="min-w-0"
          data-testid="platform-settings-notifications"
        >
          <PlatformNotificationSettingsForm />
        </TabsContent>
        <TabsContent
          value="phone-numbers"
          className="min-w-0"
          data-testid="platform-settings-phone-numbers"
        >
          <PlatformPhoneNumberSettingsForm />
        </TabsContent>
      </AnimatedTabs>
    </div>
  );
}
