"use client";

import Link from "next/link";
import { AlertCircle, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Generic setup guidance when a voice profile is not yet ready for the org.
 *
 * Deliberately avoids naming underlying model providers (white-label). Copy
 * branches on `credentialsSelfService`: org admins who can configure keys
 * themselves get a link to Organization Settings; managed orgs are told to
 * contact the platform administrator.
 */
export interface PresetSetupCalloutProps {
  /** When true, link to the org credentials tab; else contact-admin copy only. */
  credentialsSelfService: boolean;
  /** Organization id for the credentials deep link. */
  organizationId: string;
  className?: string;
}

export function PresetSetupCallout({
  credentialsSelfService,
  organizationId,
  className,
}: PresetSetupCalloutProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30 p-3",
        className,
      )}
      role="status"
    >
      <div className="flex gap-2">
        <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-2 text-sm text-amber-900 dark:text-amber-100">
          <p>
            This voice profile is not set up for your organization yet. Calls
            may not work until setup is complete.
          </p>
          {credentialsSelfService ? (
            <p className="text-xs text-amber-800 dark:text-amber-200">
              You can configure API credentials in Organization Settings, or
              ask your platform administrator for assistance.
            </p>
          ) : (
            <p className="text-xs text-amber-800 dark:text-amber-200">
              Please contact your platform administrator to complete setup.
            </p>
          )}
          {credentialsSelfService && (
            <Link
              href={`/organization?org_id=${organizationId}&tab=credentials`}
              className="inline-flex items-center text-xs font-medium text-amber-700 hover:text-amber-900 dark:text-amber-300 dark:hover:text-amber-100"
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              Open API Credentials
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
