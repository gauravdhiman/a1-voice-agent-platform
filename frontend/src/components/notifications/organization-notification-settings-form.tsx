"use client";

/**
 * Organization admin settings for critical OAuth connection alerts.
 */

import React, { useEffect, useState } from "react";
import { Bell, Loader2, Mail, MessageCircle, Phone, Save } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  notificationSettingsService,
  type OrganizationNotificationSettings,
} from "@/services/notification-settings-service";

interface OrganizationNotificationSettingsFormProps {
  organizationId: string;
}

type NotificationDraft = {
  alertEmail: string;
  smsPhone: string;
  smsEnabled: boolean;
  telegramChatId: string;
  telegramEnabled: boolean;
};

const EMPTY_DRAFT: NotificationDraft = {
  alertEmail: "",
  smsPhone: "",
  smsEnabled: false,
  telegramChatId: "",
  telegramEnabled: false,
};

function toDraft(settings: OrganizationNotificationSettings): NotificationDraft {
  return {
    alertEmail: settings.alert_email ?? "",
    smsPhone: settings.sms_phone ?? "",
    smsEnabled: settings.sms_enabled,
    telegramChatId: settings.telegram_chat_id ?? "",
    telegramEnabled: settings.telegram_enabled,
  };
}

/**
 * Loads and saves tenant destinations for OAuth recovery messages.
 * Organization admin account emails remain included automatically; the shared
 * email field adds a team inbox as another recipient.
 */
export function OrganizationNotificationSettingsForm({
  organizationId,
}: OrganizationNotificationSettingsFormProps) {
  const [settings, setSettings] = useState<OrganizationNotificationSettings | null>(null);
  const [draft, setDraft] = useState<NotificationDraft>(EMPTY_DRAFT);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    async function load() {
      setLoading(true);
      setError(null);
      setSettings(null);
      setDraft(EMPTY_DRAFT);
      const result = await notificationSettingsService.getOrganizationSettings(organizationId);
      if (!current) return;
      if (!result.success || !result.data) {
        setError(result.error || "Failed to load notification settings.");
        setLoading(false);
        return;
      }
      setSettings(result.data);
      setDraft(toDraft(result.data));
      setLoading(false);
    }
    void load();
    return () => {
      current = false;
    };
  }, [organizationId, reloadKey]);

  const updateDraft = <K extends keyof NotificationDraft>(
    key: K,
    value: NotificationDraft[K],
  ) => setDraft((previous) => ({ ...previous, [key]: value }));

  const handleSave = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (draft.smsEnabled && !draft.smsPhone.trim()) {
      setError("Enter a phone number before enabling SMS alerts.");
      return;
    }
    if (draft.telegramEnabled && !draft.telegramChatId.trim()) {
      setError("Enter a Telegram chat ID before enabling Telegram alerts.");
      return;
    }

    setSaving(true);
    const result = await notificationSettingsService.updateOrganizationSettings(
      organizationId,
      {
        alert_email: draft.alertEmail.trim() || null,
        sms_phone: draft.smsPhone.trim() || null,
        sms_enabled: draft.smsEnabled,
        telegram_chat_id: draft.telegramChatId.trim() || null,
        telegram_enabled: draft.telegramEnabled,
      },
    );
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error || "Failed to save notification settings.");
      return;
    }
    setSettings(result.data);
    setDraft(toDraft(result.data));
    setSuccess("Organization notification settings saved.");
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading notification settings...
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="max-w-3xl space-y-3">
        <Alert variant="destructive" role="alert">
          <AlertDescription>{error || "Notification settings are unavailable."}</AlertDescription>
        </Alert>
        <Button
          type="button"
          variant="outline"
          onClick={() => setReloadKey((previous) => previous + 1)}
        >
          Try again
        </Button>
      </div>
    );
  }

  return (
    <Card className="max-w-3xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Bell className="h-5 w-5" />
          Critical access alerts
        </CardTitle>
        <CardDescription>
          Choose where your team receives OAuth connection recovery notices. Organization admins continue to receive email automatically.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSave} className="space-y-7">
          {error && (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="border-green-200 bg-green-50" role="status">
              <AlertDescription className="text-green-800">{success}</AlertDescription>
            </Alert>
          )}

          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-semibold">Shared email inbox</h2>
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-alert-email">Additional alert email</Label>
              <Input
                id="organization-alert-email"
                type="email"
                autoComplete="email"
                maxLength={320}
                placeholder="operations@example.com"
                value={draft.alertEmail}
                onChange={(event) => updateDraft("alertEmail", event.target.value)}
                disabled={saving}
              />
              <p className="text-xs text-muted-foreground">
                This address receives the same recovery email as organization admins.
              </p>
            </div>
          </section>

          <section className="space-y-4 border-t pt-6">
            <div className="flex flex-wrap items-center gap-2">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-semibold">SMS alerts</h2>
              {settings?.sms_sender_configured ? (
                <Badge className="bg-green-600 hover:bg-green-600/90">SMS provider ready</Badge>
              ) : (
                <Badge variant="secondary">SMS provider not configured</Badge>
              )}
            </div>
            <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
              <div className="space-y-1">
                <Label htmlFor="organization-sms-enabled">Enable SMS alerts</Label>
                <p className="text-sm text-muted-foreground">
                  Send urgent connection recovery notices to this number.
                </p>
              </div>
              <Switch
                id="organization-sms-enabled"
                checked={draft.smsEnabled}
                onCheckedChange={(checked) => updateDraft("smsEnabled", checked)}
                disabled={saving}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-sms-phone">Phone number</Label>
              <Input
                id="organization-sms-phone"
                type="tel"
                autoComplete="tel"
                maxLength={16}
                placeholder="+15551234567"
                value={draft.smsPhone}
                onChange={(event) => updateDraft("smsPhone", event.target.value)}
                disabled={saving}
              />
              <p className="text-xs text-muted-foreground">
                Use E.164 format with country code. The platform admin configures the Twilio sender.
              </p>
            </div>
          </section>

          <section className="space-y-4 border-t pt-6">
            <div className="flex flex-wrap items-center gap-2">
              <MessageCircle className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-semibold">Telegram alerts</h2>
              {settings?.telegram_bot_configured ? (
                <Badge className="bg-green-600 hover:bg-green-600/90">Telegram bot ready</Badge>
              ) : (
                <Badge variant="secondary">Telegram bot not configured</Badge>
              )}
            </div>
            <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
              <div className="space-y-1">
                <Label htmlFor="organization-telegram-enabled">Enable Telegram alerts</Label>
                <p className="text-sm text-muted-foreground">
                  Send urgent connection recovery notices to this chat or group.
                </p>
              </div>
              <Switch
                id="organization-telegram-enabled"
                checked={draft.telegramEnabled}
                onCheckedChange={(checked) => updateDraft("telegramEnabled", checked)}
                disabled={saving}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-telegram-chat-id">Chat ID or channel username</Label>
              <Input
                id="organization-telegram-chat-id"
                maxLength={100}
                placeholder="-1001234567890 or @team_alerts"
                value={draft.telegramChatId}
                onChange={(event) => updateDraft("telegramChatId", event.target.value)}
                disabled={saving}
              />
              <p className="text-xs text-muted-foreground">
                Add the platform configured bot to the chat first. The platform admin manages the bot in Platform → Notifications.
              </p>
            </div>
          </section>

          {!settings?.sms_sender_configured || !settings?.telegram_bot_configured ? (
            <Alert>
              <AlertDescription className="text-sm">
                SMS and Telegram delivery need provider credentials configured by a platform admin. Email notices remain available while a provider is being set up.
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="flex justify-end border-t pt-5">
            <Button type="submit" disabled={saving}>
              {saving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" />
                  Save notification settings
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}