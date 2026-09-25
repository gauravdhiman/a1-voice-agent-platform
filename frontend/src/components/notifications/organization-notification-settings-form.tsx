"use client";

/**
 * Organization admin settings for critical notification contacts.
 */

import React, { useEffect, useState } from "react";
import { Bell, Loader2, Mail, MessageCircle, Phone, Save, Trash2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  telegramChatId: string;
  telegramBotToken: string;
  clearTelegramBotToken: boolean;
};

const EMPTY_DRAFT: NotificationDraft = {
  alertEmail: "",
  smsPhone: "",
  telegramChatId: "",
  telegramBotToken: "",
  clearTelegramBotToken: false,
};

function toDraft(settings: OrganizationNotificationSettings): NotificationDraft {
  return {
    alertEmail: settings.alert_email ?? "",
    smsPhone: settings.sms_phone ?? "",
    telegramChatId: settings.telegram_chat_id ?? "",
    // A saved credential is never returned by the API.
    telegramBotToken: "",
    clearTelegramBotToken: false,
  };
}

/**
 * Loads and saves an organization's critical notification contacts. Admin
 * account emails remain recipients, while the optional email adds a shared
 * inbox. SMS and Telegram are enabled by their required saved details.
 */
export function OrganizationNotificationSettingsForm({
  organizationId,
}: OrganizationNotificationSettingsFormProps) {
  const [settings, setSettings] =
    useState<OrganizationNotificationSettings | null>(null);
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
      const result =
        await notificationSettingsService.getOrganizationSettings(organizationId);
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
    setSaving(true);
    const result = await notificationSettingsService.updateOrganizationSettings(
      organizationId,
      {
        alert_email: draft.alertEmail.trim() || null,
        sms_phone: draft.smsPhone.trim() || null,
        telegram_chat_id: draft.telegramChatId.trim() || null,
        ...(draft.clearTelegramBotToken
          ? { telegram_bot_token: null }
          : draft.telegramBotToken.trim()
            ? { telegram_bot_token: draft.telegramBotToken.trim() }
            : {}),
      },
    );
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error || "Failed to save notification settings.");
      return;
    }
    setSettings(result.data);
    setDraft(toDraft(result.data));
    setSuccess("Notification settings saved.");
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
          <AlertDescription>
            {error || "Notification settings are unavailable."}
          </AlertDescription>
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
          Critical notifications
        </CardTitle>
        <CardDescription>
          Add contact details for important updates about your organization.
          Organization admins also receive critical notifications at their
          account email addresses.
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
              <AlertDescription className="text-green-800">
                {success}
              </AlertDescription>
            </Alert>
          )}

          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-semibold">Email</h2>
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-alert-email">
                Additional email address
              </Label>
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
                Add a shared inbox alongside organization admins&apos; account email
                addresses.
              </p>
            </div>
          </section>

          <section className="space-y-3 border-t pt-6">
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-semibold">SMS</h2>
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-sms-phone">Phone number</Label>
              <Input
                id="organization-sms-phone"
                type="tel"
                autoComplete="tel"
                inputMode="tel"
                maxLength={16}
                placeholder="+15551234567"
                value={draft.smsPhone}
                onChange={(event) => updateDraft("smsPhone", event.target.value)}
                disabled={saving}
              />
              <p className="text-xs text-muted-foreground">
                Enter a phone number in international format to receive SMS
                notifications. Clear the number to turn SMS off.
              </p>
            </div>
          </section>

          <section className="space-y-3 border-t pt-6">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4 text-muted-foreground" />
              <h2 className="font-semibold">Telegram</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              Create a bot with{" "}
              <a
                href="https://t.me/BotFather"
                target="_blank"
                rel="noreferrer"
                className="font-medium text-primary underline underline-offset-4"
              >
                BotFather
              </a>
              , add it to the chat or group, and enter the bot token and chat ID
              below. Both are required. Remove the saved bot token or clear the
              chat ID to turn Telegram notifications off.
            </p>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Label htmlFor="organization-telegram-bot-token">
                  Telegram bot token
                </Label>
                {settings.telegram_bot_configured && !draft.clearTelegramBotToken && (
                  <Badge variant="secondary">Token saved</Badge>
                )}
              </div>
              <Input
                id="organization-telegram-bot-token"
                type="password"
                autoComplete="new-password"
                maxLength={256}
                placeholder={
                  settings.telegram_bot_configured
                    ? "Enter a new token to replace the saved one"
                    : "Enter your bot token"
                }
                value={draft.telegramBotToken}
                onChange={(event) => {
                  updateDraft("telegramBotToken", event.target.value);
                  if (event.target.value) {
                    updateDraft("clearTelegramBotToken", false);
                  }
                }}
                disabled={saving}
              />
              {settings.telegram_bot_configured && !draft.clearTelegramBotToken && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="px-0 text-destructive hover:text-destructive"
                  onClick={() => {
                    updateDraft("telegramBotToken", "");
                    updateDraft("clearTelegramBotToken", true);
                  }}
                  disabled={saving}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Remove saved token
                </Button>
              )}
              {draft.clearTelegramBotToken && (
                <p className="text-xs text-muted-foreground" role="status">
                  The saved token will be removed when you save.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-telegram-chat-id">
                Chat ID or channel username
              </Label>
              <Input
                id="organization-telegram-chat-id"
                maxLength={100}
                placeholder="-1001234567890 or @team_alerts"
                value={draft.telegramChatId}
                onChange={(event) => updateDraft("telegramChatId", event.target.value)}
                disabled={saving}
              />
            </div>
          </section>

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
