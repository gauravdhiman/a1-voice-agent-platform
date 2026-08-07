"use client";

import React from "react";
import { Building2, Check, Mic, Phone, Plug, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const STEPS = [
  { id: 1, label: "Organization", icon: Building2 },
  { id: 2, label: "Agent", icon: Mic },
  { id: 3, label: "Phone", icon: Phone },
  { id: 4, label: "Tools", icon: Plug },
  { id: 5, label: "Test", icon: Zap },
] as const;

/**
 * Horizontal step indicator for the founder onboarding wizard.
 *
 * @param currentStep Active 1-based step index
 */
export function StepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center justify-center mb-8">
      {STEPS.map((step, index) => {
        const Icon = step.icon;
        const isCompleted = currentStep > step.id;
        const isCurrent = currentStep === step.id;
        return (
          <React.Fragment key={step.id}>
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium transition-all",
                  isCompleted
                    ? "bg-blue-600 text-white"
                    : isCurrent
                      ? "bg-blue-600 text-white ring-4 ring-blue-100"
                      : "bg-gray-100 text-gray-400",
                )}
              >
                {isCompleted ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <span
                className={cn(
                  "text-xs mt-1 font-medium",
                  isCurrent
                    ? "text-blue-600"
                    : isCompleted
                      ? "text-gray-600"
                      : "text-gray-400",
                )}
              >
                {step.label}
              </span>
            </div>
            {index < STEPS.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-2 mb-5 transition-all",
                  currentStep > step.id ? "bg-blue-600" : "bg-gray-200",
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
