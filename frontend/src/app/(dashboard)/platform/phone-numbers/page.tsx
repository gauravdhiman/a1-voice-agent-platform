import { redirect } from "next/navigation";

/** Preserve the old URL while sending administrators to the settings hub. */
export default function PlatformPhoneNumbersPage(): never {
  redirect("/platform/settings?section=phone-numbers");
}
