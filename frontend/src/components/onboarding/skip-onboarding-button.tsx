"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Widget-level control to abandon founder onboarding and open the dashboard.
 *
 * Shown on early wizard steps only (not the final test step). Completing
 * onboarding server-side is the caller's responsibility so OrganizationCheck
 * does not bounce the user back into the wizard.
 */
export interface SkipOnboardingButtonProps {
  /** Called when the user confirms they want to leave the wizard */
  onSkip: () => void | Promise<void>;
  /** Disables the control while skip is in progress */
  loading?: boolean;
  /** Optional className for layout tweaks */
  className?: string;
}

/**
 * Renders a low-emphasis skip action for the onboarding wizard card.
 *
 * @param onSkip Handler that marks onboarding complete and navigates away
 * @param loading When true, shows a spinner and disables the button
 * @param className Optional extra classes on the wrapper
 */
export function SkipOnboardingButton({
  onSkip,
  loading = false,
  className,
}: SkipOnboardingButtonProps) {
  return (
    <div className={className}>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="w-full text-muted-foreground hover:text-foreground"
        onClick={() => {
          void onSkip();
        }}
        disabled={loading}
        data-testid="skip-onboarding"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Skipping...
          </>
        ) : (
          "Skip setup and go to dashboard"
        )}
      </Button>
    </div>
  );
}
