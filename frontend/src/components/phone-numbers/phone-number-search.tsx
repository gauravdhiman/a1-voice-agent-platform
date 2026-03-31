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
  PhoneNumberType,
  formatPhoneNumber,
  getPhoneNumberTypeLabel,
  getCreditsForType,
} from "@/types/phone-number";
import { phoneNumberService } from "@/services/phone-number-service";

interface PhoneNumberSearchProps {
  organizationId: string;
  creditBalance: number;
  onNumberSelected?: (number: AvailablePhoneNumber) => void;
}

const COUNTRIES = [
  { code: "US", name: "United States" },
];

const NUMBER_TYPES: { value: PhoneNumberType; label: string; cost: number }[] = [
  { value: "local", label: "Local", cost: 200 },
  { value: "toll_free", label: "Toll-Free", cost: 500 },
  { value: "mobile", label: "Mobile", cost: 200 },
];

export function PhoneNumberSearch({
  organizationId,
  creditBalance,
  onNumberSelected,
}: PhoneNumberSearchProps) {
  const [countryCode, setCountryCode] = useState("US");
  const [numberType, setNumberType] = useState<PhoneNumberType>("local");
  const [areaCode, setAreaCode] = useState("");
  const [contains, setContains] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState<AvailablePhoneNumber[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    setSearching(true);
    setHasSearched(true);
    setResults([]);

    try {
      const response = await phoneNumberService.searchAvailable({
        country_code: countryCode,
        phone_number_type: numberType,
        area_code: areaCode || null,
        contains: contains || null,
        page: 1,
        page_size: 50,
      });

      setResults(response.items);
    } catch (error) {
      console.error("Error searching phone numbers:", error);
      toast.error("Failed to search phone numbers");
    } finally {
      setSearching(false);
    }
  };

  const getCostForType = (type: PhoneNumberType) => {
    const typeConfig = NUMBER_TYPES.find((t) => t.value === type);
    return typeConfig?.cost || getCreditsForType(type);
  };

  const canAfford = (cost: number) => creditBalance >= cost;

  return (
    <div className="space-y-6">
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Country</label>
              <Select value={countryCode} onValueChange={setCountryCode}>
                <SelectTrigger>
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
              <label className="text-sm font-medium">Number Type</label>
              <Select
                value={numberType}
                onValueChange={(v) => setNumberType(v as PhoneNumberType)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {NUMBER_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label} ({type.cost} credits/mo)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Area Code (Optional)</label>
              <Input
                placeholder="e.g., 555"
                value={areaCode}
                onChange={(e) => setAreaCode(e.target.value)}
                maxLength={3}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Contains (Optional)</label>
              <Input
                placeholder="e.g., 1234"
                value={contains}
                onChange={(e) => setContains(e.target.value)}
                maxLength={10}
              />
            </div>
          </div>

          <Button onClick={handleSearch} disabled={searching} className="w-full">
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
            Your balance: <span className="font-semibold">{creditBalance} credits</span>
          </div>
        </CardContent>
      </Card>

      {hasSearched && (
        <Card>
          <CardHeader>
            <CardTitle>Available Numbers</CardTitle>
            <CardDescription>
              {results.length} numbers found
              {results.length > 0 && (
                <span className="ml-2">
                  (Showing {getCostForType(numberType)} credits/month)
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {searching ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin" />
              </div>
            ) : results.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No available numbers found</p>
                <p className="text-sm">Try a different search criteria</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {results.map((number) => (
                  <div
                    key={number.phone_number}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <Phone className="w-5 h-5 text-muted-foreground" />
                        <div>
                          <div className="font-medium">
                            {formatPhoneNumber(number.phone_number)}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Badge variant="outline">
                              {getPhoneNumberTypeLabel(number.phone_number_type)}
                            </Badge>
                            {number.locality && (
                              <span className="flex items-center gap-1">
                                <MapPin className="w-3 h-3" />
                                {number.locality}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="font-semibold">
                          {number.monthly_cost_credits} credits/mo
                        </div>
                        {!canAfford(number.monthly_cost_credits) && (
                          <Badge variant="destructive" className="text-xs">
                            Insufficient credits
                          </Badge>
                        )}
                      </div>
                      <Button
                        size="sm"
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
