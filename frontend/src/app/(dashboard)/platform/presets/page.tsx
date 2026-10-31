"use client";

/**
 * Platform Voice Presets management page (platform admin only).
 *
 * Dedicated home for the global voice-engine preset catalog — parallel to
 * `/platform/tools` and `/platform/skills`. Platform admins author a preset's
 * `SpeechConfig` (realtime or pipeline), save it as a draft or publish it to
 * the global catalog, and manage every preset (create / edit / publish /
 * unpublish / delete) via the catalog and right-side drawer in
 * `<PlatformPresetsManager>`.
 *
 * Published presets surface in every org admin's agent picker ("voice
 * profile") — the org user picks by name + description only and never sees
 * `engine_mode` / STT / LLM / TTS. An agent with no preset chosen falls back
 * to the current platform default voice profile (`preset_id = null`).
 *
 * Frontend authz gate. The backend independently enforces `platform_admin` on
 * every write endpoint (create/update/publish/delete) and on draft reads, so a
 * non-admin who reaches this route can read only published presets and write
 * nothing.
 *
 * @example
 * ```tsx
 * <PlatformPresetsPage />
 * ```
 */

import { useAuth } from "@/contexts/auth-context";
import { AccessDenied } from "@/components/ui/access-denied";
import { PlatformPresetsManager } from "@/components/presets/platform-presets-manager";

export default function PlatformPresetsPage() {
  const { user } = useAuth();

  // Frontend authz gate. Backend enforces the same independently. Placed
  // after all hooks (useAuth is the only hook here) so hook call order is
  // stable regardless of role.
  if (!user?.hasRole("platform_admin")) {
    return (
      <AccessDenied
        title="Access Denied"
        description="You do not have permission to access this page. Only platform administrators can manage voice presets."
        redirectPath="/dashboard"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Voice Presets
        </h1>
        <p className="text-muted-foreground mt-1">
          Author and publish voice-engine presets (realtime or modular
          pipeline). Published presets appear in every org&apos;s agent picker
          as selectable &quot;voice profiles&quot;.
        </p>
      </div>
      <PlatformPresetsManager />
    </div>
  );
}
