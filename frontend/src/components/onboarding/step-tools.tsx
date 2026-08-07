"use client";

import { ChevronLeft, ChevronRight, Plug } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export interface StepToolsProps {
  onNext: () => void;
  onBack: () => void;
}

/**
 * Step 4 — informational tools overview (no selection during onboarding).
 *
 * Tools are configured later from Settings so this step only explains what is
 * possible after setup.
 */
export function StepTools({ onNext, onBack }: StepToolsProps) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">
          Tools &amp; integrations
        </h2>
        <p className="text-gray-500 mt-1">
          After setup, you can connect tools so your agent can take real actions
          during calls — like booking appointments or looking up customer
          information.
        </p>
      </div>

      <div className="p-5 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
            <Plug className="w-5 h-5 text-blue-700" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Connect when you&apos;re ready</p>
            <p className="text-sm text-gray-500">
              No tools to configure in this step.
            </p>
          </div>
        </div>
        <ul className="text-sm text-gray-600 list-disc pl-5 space-y-1">
          <li>Google Calendar and other booking tools</li>
          <li>CRM and messaging integrations</li>
          <li>Custom MCP tools your team connects later</li>
        </ul>
      </div>

      <Alert>
        <AlertDescription className="text-sm">
          You can connect tools anytime from{" "}
          <strong>Settings → Tools</strong> after finishing setup.
        </AlertDescription>
      </Alert>

      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack} className="w-32">
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button
          onClick={onNext}
          className="flex-1"
          size="lg"
          data-testid="onboarding-tools-continue"
        >
          Continue <ChevronRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}
