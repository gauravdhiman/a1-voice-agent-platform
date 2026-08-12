import { redirect } from "next/navigation";

/**
 * Platform admin page for entitlement definition catalog metadata.
 */
export default function PlatformEntitlementsPage() {
  redirect("/platform/plans");
}
