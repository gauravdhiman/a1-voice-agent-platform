"use client";

import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Search, Phone, MapPin } from "lucide-react";
import { toast } from "sonner";
import {
  AvailablePhoneNumber,
  PhoneNumberSearchMode,
  PhoneNumberType,
  formatPhoneNumber,
  getPhoneNumberTypeLabel,
} from "@/types/phone-number";
import { phoneNumberService } from "@/services/phone-number-service";
import { cn } from "@/lib/utils";

interface PhoneNumberSearchProps {
  /** Organization whose included-number allowance and permissions apply. */
  organizationId: string;
  /** Current credit balance used to gate paid number purchases. */
  creditBalance: number;
  /** Called when the user selects an available number. */
  onNumberSelected?: (number: AvailablePhoneNumber) => void;
  /** Optional layout classes, including the drawer's full-height mode. */
  className?: string;
}

const COUNTRIES = [{ code: "US", name: "United States" }];

const NUMBER_TYPES: { value: PhoneNumberType; label: string }[] = [
  { value: "local", label: "Local" },
  { value: "toll_free", label: "Toll-Free" },
];

const SEARCH_MODES: { value: PhoneNumberSearchMode; label: string }[] = [
  { value: "contains", label: "Contains" },
  { value: "begins_with", label: "Begins with" },
  { value: "ends_with", label: "Ends with" },
];

export function PhoneNumberSearch({
  organizationId,
  creditBalance,
  onNumberSelected,
  className,
}: PhoneNumberSearchProps) {
  const [countryCode, setCountryCode] = useState("US");
  const [numberType, setNumberType] = useState<PhoneNumberType>("local");
  const [areaCode, setAreaCode] = useState("");
  const [contains, setContains] = useState("");
  const [searchMode, setSearchMode] =
    useState<PhoneNumberSearchMode>("contains");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<AvailablePhoneNumber[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleSearch = async () => {
    setSearching(true);
    setHasSearched(true);
    setResults([]);
    setSearchError(null);

    try {
      const response = await phoneNumberService.searchAvailable({
        organization_id: organizationId,
        country_code: countryCode,
        phone_number_type: numberType,
        area_code: areaCode || null,
        contains: contains || null,
        search_mode: searchMode,
        page: 1,
        page_size: 50,
      });

      setResults(response.items);
    } catch (error) {
      console.error("Error searching phone numbers:", error);
      const message =
        error instanceof Error
          ? error.message
          : "Phone number search is temporarily unavailable. Please try again later.";
      setSearchError(message);
      toast.error(message);
    } finally {
      setSearching(false);
    }
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void handleSearch();
  };

  const canAfford = (cost: number) => creditBalance >= cost;

  return (
    <div className={cn("flex min-h-0 flex-col gap-6", className)}>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Search Available Numbers
          </CardTitle>
          <CardDescription>
            Find and select a phone number for your organization
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form
            aria-label="Available phone number search"
            onSubmit={handleSubmit}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label
                  htmlFor="phone-number-country"
                  className="text-sm font-medium"
                >
                  Country
                </label>
                <Select value={countryCode} onValueChange={setCountryCode}>
                  <SelectTrigger id="phone-number-country">
                    <SelectValue placeholder="Select country" />
                  </SelectTrigger>
                  <SelectContent>
                    {COUNTRIES.map((country) => (
                      <SelectItem key={country.code} value={country.code}>
                        {country.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="phone-number-type"
                  className="text-sm font-medium"
                >
                  Number Type
                </label>
                <Select
                  value={numberType}
                  onValueChange={(v) => setNumberType(v as PhoneNumberType)}
                >
                  <SelectTrigger id="phone-number-type">
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {NUMBER_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="phone-number-area-code"
                  className="text-sm font-medium"
                >
                  Area Code (Optional)
                </label>
                <Input
                  id="phone-number-area-code"
                  placeholder="e.g., 555"
                  value={areaCode}
                  onChange={(e) => setAreaCode(e.target.value)}
                  maxLength={3}
                />
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="phone-number-search-mode"
                  className="text-sm font-medium"
                >
                  Match
                </label>
                <Select
                  value={searchMode}
                  onValueChange={(value) =>
                    setSearchMode(value as PhoneNumberSearchMode)
                  }
                >
                  <SelectTrigger id="phone-number-search-mode">
                    <SelectValue placeholder="Select match" />
                  </SelectTrigger>
                  <SelectContent>
                    {SEARCH_MODES.map((mode) => (
                      <SelectItem key={mode.value} value={mode.value}>
                        {mode.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="phone-number-pattern"
                  className="text-sm font-medium"
                >
                  Phone number pattern (Optional)
                </label>
                <Input
                  id="phone-number-pattern"
                  placeholder={
                    searchMode === "begins_with"
                      ? "e.g., 480"
                      : searchMode === "ends_with"
                        ? "e.g., 2168"
                        : "e.g., 1234"
                  }
                  value={contains}
                  onChange={(e) => setContains(e.target.value)}
                  maxLength={16}
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={searching}
              className="w-full"
            >
              {searching ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4 mr-2" />
                  Search Numbers
                </>
              )}
            </Button>

            <div className="text-sm text-muted-foreground">
              Your balance:{" "}
              <span className="font-semibold">{creditBalance} credits</span>
            </div>
          </form>
        </CardContent>
      </Card>

      {hasSearched && (
        <Card className="flex min-h-0 flex-1 flex-col">
          <CardHeader>
            <CardTitle>Available Numbers</CardTitle>
            <CardDescription>
              {searchError
                ? "Search could not be completed"
                : `${results.length} numbers found`}
              {!searchError && results.length > 0 && (
                <span className="ml-2">(monthly pricing shown per number)</span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col">
            {searching ? (
              <div className="flex flex-1 items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : searchError ? (
              <div
                className="flex flex-1 flex-col items-center justify-center py-8 text-center text-muted-foreground"
                role="alert"
              >
                <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>{searchError}</p>
              </div>
            ) : results.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center py-8 text-center text-muted-foreground">
                <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No available numbers found</p>
                <p className="text-sm">Try a different search criteria</p>
              </div>
            ) : (
              <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                {results.map((number) => (
                  <div
                    key={number.phone_number}
                    className="flex flex-col gap-3 rounded-lg border p-3 transition-colors hover:bg-muted/50 lg:flex-row lg:items-center lg:justify-between lg:p-4"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex min-w-0 items-start gap-2">
                        <Phone className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" />
                        <div className="min-w-0">
                          <div className="break-all font-medium lg:break-normal">
                            {formatPhoneNumber(number.phone_number)}
                          </div>
                          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
                            <Badge className="shrink-0" variant="outline">
                              {getPhoneNumberTypeLabel(
                                number.phone_number_type,
                              )}
                            </Badge>
                            {number.locality && (
                              <span className="flex min-w-0 items-center gap-1 break-words">
                                <MapPin className="h-3 w-3 shrink-0" />
                                {number.locality}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex w-full flex-col gap-2 lg:w-auto lg:flex-row lg:items-center lg:justify-end">
                      <div className="min-w-0 text-left lg:text-right">
                        <div className="whitespace-nowrap font-semibold">
                          {number.is_included_in_plan
                            ? "Included with plan"
                            : `${number.monthly_cost_credits} credits/mo${number.phone_number_type === "local" && number.country_code === "US" ? ` · $${(number.monthly_cost_credits / 40).toFixed(2).replace(/\.00$/, "")}/mo value` : ""}`}
                        </div>
                        {!canAfford(number.monthly_cost_credits) && (
                          <Badge
                            variant="outline"
                            className="border-red-700 bg-red-50 text-xs text-red-900 dark:border-red-400 dark:bg-red-950/40 dark:text-red-100"
                          >
                            Insufficient credits
                          </Badge>
                        )}
                      </div>
                      <Button
                        size="sm"
                        className="w-full lg:w-auto"
                        disabled={!canAfford(number.monthly_cost_credits)}
                        onClick={() => onNumberSelected?.(number)}
                      >
                        Select
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
