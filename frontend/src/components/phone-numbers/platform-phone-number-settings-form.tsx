"use client";

/**
 * Platform-admin form for phone-number billing and release retry settings.
 */

import React, { useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  platformPhoneNumberSettingsService,
  type PlatformPhoneNumberSettings,
} from "@/services/platform-phone-number-settings-service";

export function PlatformPhoneNumberSettingsForm() {
  const [settings, setSettings] = useState<PlatformPhoneNumberSettings | null>(
    null,
  );
  const [graceDays, setGraceDays] = useState("7");
  const [billingInterval, setBillingInterval] = useState("24");
  const [releaseInterval, setReleaseInterval] = useState("24");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const result = await platformPhoneNumberSettingsService.getSettings();
      if (!result.success || !result.data) {
        setError(result.error || "Failed to load settings.");
        setLoading(false);
        return;
      }
      setSettings(result.data);
      setGraceDays(String(result.data.billing_grace_period_days));
      setBillingInterval(String(result.data.billing_check_interval_hours));
      setReleaseInterval(String(result.data.release_retry_interval_hours));
      setLoading(false);
    }
    void load();
  }, []);

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    const result = await platformPhoneNumberSettingsService.updateSettings({
      billing_grace_period_days: Number(graceDays),
      billing_check_interval_hours: Number(billingInterval),
      release_retry_interval_hours: Number(releaseInterval),
    });
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error || "Failed to save settings.");
      return;
    }
    setSettings(result.data);
    setSuccess("Phone-number settings saved.");
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading settings...
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="max-w-2xl space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="border-green-200 bg-green-50">
          <AlertDescription className="text-green-800">
            {success}
          </AlertDescription>
        </Alert>
      )}
      <p className="text-sm text-muted-foreground">
        Incoming calls are disabled when a monthly rental debit fails. If the
        organization remains unpaid through the grace period, the provider
        number is released. Changes apply to the next scheduler iteration.
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="phone_grace_days">Grace period (days)</Label>
          <Input
            id="phone_grace_days"
            type="number"
            min={1}
            step={1}
            value={graceDays}
            onChange={(event) => setGraceDays(event.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="phone_billing_interval">
            Billing check (hours)
          </Label>
          <Input
            id="phone_billing_interval"
            type="number"
            min={0.1}
            step={0.1}
            value={billingInterval}
            onChange={(event) => setBillingInterval(event.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="phone_release_interval">
            Release retry (hours)
          </Label>
          <Input
            id="phone_release_interval"
            type="number"
            min={0.1}
            step={0.1}
            value={releaseInterval}
            onChange={(event) => setReleaseInterval(event.target.value)}
            required
          />
        </div>
      </div>
      <Button type="submit" disabled={saving}>
        {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
        Save settings
      </Button>
      {settings?.updated_at && (
        <p className="text-xs text-muted-foreground">
          Last updated {new Date(settings.updated_at).toLocaleString()}
        </p>
      )}
    </form>
  );
}
