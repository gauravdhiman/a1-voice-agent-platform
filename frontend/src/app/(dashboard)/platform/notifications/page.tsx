import { redirect } from "next/navigation";

/** Preserve the old URL while sending administrators to the settings hub. */
export default function PlatformNotificationsPage(): never {
  redirect("/platform/settings?section=notifications");
}
