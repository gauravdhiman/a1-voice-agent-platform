"use client";

import { useState, type FormEvent } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { OnboardingWizardState } from "@/lib/onboarding";
import { cn } from "@/lib/utils";
import { phoneNumberService } from "@/services/phone-number-service";
import type { AvailablePhoneNumber } from "@/types/phone-number";

export interface StepPhoneProps {
  state: OnboardingWizardState;
  orgId: string;
  onChange: (update: Partial<OnboardingWizardState>) => void;
  onNext: () => void;
  onBack: () => void;
}

/**
 * Step 3 — optional phone number purchase during onboarding.
 *
 * Phone numbers are optional; users can skip and add one later from Settings.
 */
export function StepPhone({
  state,
  orgId,
  onChange,
  onNext,
  onBack,
}: StepPhoneProps) {
  const [searching, setSearching] = useState(false);
  const [areaCode, setAreaCode] = useState("");
  const [results, setResults] = useState<AvailablePhoneNumber[]>([]);
  const [purchasing, setPurchasing] = useState(false);
  const [selectedNumber, setSelectedNumber] =
    useState<AvailablePhoneNumber | null>(null);

  const handleSearch = async () => {
    setSearching(true);
    try {
      const response = await phoneNumberService.searchAvailable({
        country_code: "US",
        phone_number_type: "local",
        area_code: areaCode || undefined,
        page_size: 5,
      });
      setResults(response.items);
    } catch {
      toast.error("Failed to search phone numbers");
    } finally {
      setSearching(false);
    }
  };

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void handleSearch();
  };

  const handlePurchase = async () => {
    if (!selectedNumber) return;
    setPurchasing(true);
    try {
      await phoneNumberService.purchaseNumber(orgId, {
        phone_number: selectedNumber.phone_number,
        country_code: selectedNumber.country_code,
        phone_number_type: selectedNumber.phone_number_type,
      });
      onChange({ purchasedPhoneNumber: selectedNumber.phone_number });
      toast.success(`Purchased ${selectedNumber.phone_number}`);
      onNext();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Purchase failed");
    } finally {
      setPurchasing(false);
    }
  };

  if (state.purchasedPhoneNumber) {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Phone number ready
          </h2>
        </div>
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-green-600" />
          <div>
            <p className="font-semibold text-green-800">
              {state.purchasedPhoneNumber}
            </p>
            <p className="text-sm text-green-600">Your phone number is ready</p>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onBack} className="w-32">
            <ChevronLeft className="w-4 h-4 mr-1" /> Back
          </Button>
          <Button onClick={onNext} className="flex-1" size="lg">
            Continue <ChevronRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Get a phone number</h2>
        <p className="text-gray-500 mt-1">
          Your AI agent needs a phone number to receive calls. Search for one
          below, or skip for now.
        </p>
      </div>

      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <Input
          placeholder="Area code (optional)"
          value={areaCode}
          onChange={(e) => setAreaCode(e.target.value)}
          className="w-40"
          maxLength={3}
        />
        <Button type="submit" disabled={searching} variant="outline">
          {searching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4 mr-1" />
          )}
          Search
        </Button>
      </form>

      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((num) => (
            <div
              key={num.phone_number}
              onClick={() => setSelectedNumber(num)}
              className={cn(
                "p-3 border-2 rounded-lg cursor-pointer flex items-center justify-between",
                selectedNumber?.phone_number === num.phone_number
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 hover:border-blue-200",
              )}
            >
              <div>
                <p className="font-medium">{num.phone_number}</p>
                <p className="text-xs text-gray-500">
                  {num.locality ?? num.area_code} · {num.phone_number_type}
                </p>
              </div>
              {selectedNumber?.phone_number === num.phone_number && (
                <CheckCircle2 className="w-5 h-5 text-blue-500" />
              )}
            </div>
          ))}

          {selectedNumber && (
            <Button
              onClick={handlePurchase}
              disabled={purchasing}
              className="w-full mt-2"
            >
              {purchasing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Purchasing...
                </>
              ) : (
                <>Purchase {selectedNumber.phone_number}</>
              )}
            </Button>
          )}
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <Button variant="outline" onClick={onBack} className="w-32">
          <ChevronLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <Button variant="outline" onClick={onNext} className="flex-1">
          <ChevronRight className="w-4 h-4 mr-2" /> Skip for now
        </Button>
      </div>
    </div>
  );
}
