"use client";

/**
 * Platform admin form for email, Telegram, SMS, and WhatsApp settings.
 */

import React, { useEffect, useState } from "react";
import { Loader2, Mail, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { TelegramBotCredentialRow } from "@/components/notifications/telegram-bot-credential-row";
import {
  notificationSettingsService,
  type PlatformNotificationSettings,
} from "@/services/notification-settings-service";

export function PlatformNotificationSettingsForm() {
  const [settings, setSettings] = useState<PlatformNotificationSettings | null>(
    null,
  );
  const [platformAdminEmail, setPlatformAdminEmail] = useState("");
  const [platformAdminSmsPhone, setPlatformAdminSmsPhone] = useState("");
  const [platformAdminWhatsappPhone, setPlatformAdminWhatsappPhone] = useState("");
  const [verificationFromEmail, setVerificationFromEmail] = useState("");
  const [verificationFromName, setVerificationFromName] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [telegramBotToken, setTelegramBotToken] = useState("");
  const [telegramBotEditing, setTelegramBotEditing] = useState(false);
  const [telegramEnabled, setTelegramEnabled] = useState(false);
  const [platformAdminSmsEnabled, setPlatformAdminSmsEnabled] = useState(false);
  const [platformAdminWhatsappEnabled, setPlatformAdminWhatsappEnabled] = useState(false);
  const [resendConfigured, setResendConfigured] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const botTokenPendingChange =
    telegramBotEditing && telegramBotToken.trim().length > 0;

  useEffect(() => {
    async function load() {
      setLoading(true);
      const [settingsResult, healthResult] = await Promise.all([
        notificationSettingsService.getSettings(),
        notificationSettingsService.getHealth(),
      ]);

      if (!settingsResult.success || !settingsResult.data) {
        setError(settingsResult.error || "Failed to load settings.");
        setLoading(false);
        return;
      }

      setSettings(settingsResult.data);
      setPlatformAdminEmail(settingsResult.data.platform_admin_email || "");
      setPlatformAdminSmsPhone(
        settingsResult.data.platform_admin_sms_phone || "",
      );
      setPlatformAdminWhatsappPhone(
        settingsResult.data.platform_admin_whatsapp_phone || "",
      );
      setPlatformAdminSmsEnabled(
        settingsResult.data.platform_admin_sms_notifications_enabled,
      );
      setPlatformAdminWhatsappEnabled(
        settingsResult.data.platform_admin_whatsapp_notifications_enabled,
      );
      setVerificationFromEmail(settingsResult.data.verification_from_email || "");
      setVerificationFromName(settingsResult.data.verification_from_name || "");
      setTelegramChatId(settingsResult.data.telegram_chat_id || "");
      setTelegramEnabled(settingsResult.data.telegram_notifications_enabled);
      setResendConfigured(healthResult.data?.resend_configured ?? null);
      setLoading(false);
    }
    void load();
  }, []);

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);

    const payload = {
      platform_admin_email: platformAdminEmail || null,
      platform_admin_sms_phone: platformAdminSmsPhone || null,
      platform_admin_sms_notifications_enabled: platformAdminSmsEnabled,
      platform_admin_whatsapp_phone: platformAdminWhatsappPhone || null,
      platform_admin_whatsapp_notifications_enabled: platformAdminWhatsappEnabled,
      verification_from_email: verificationFromEmail || null,
      verification_from_name: verificationFromName || null,
      telegram_chat_id: telegramChatId || null,
      telegram_notifications_enabled: telegramEnabled,
      ...(telegramBotToken.trim()
        ? { telegram_bot_token: telegramBotToken.trim() }
        : {}),
    };

    const result = await notificationSettingsService.updateSettings(payload);
    setSaving(false);

    if (!result.success || !result.data) {
      setError(result.error || "Failed to save settings.");
      return;
    }

    setSettings(result.data);
    setTelegramBotToken("");
    setTelegramBotEditing(false);
    setSuccess("Notification settings saved.");
  };

  const handleRemoveBotToken = async () => {
    setSaving(true);
    setError(null);
    const result = await notificationSettingsService.updateSettings({
      telegram_bot_token: "",
    });
    setSaving(false);
    if (!result.success || !result.data) {
      setError(result.error || "Failed to remove bot token.");
      return;
    }
    setSettings(result.data);
    setTelegramBotToken("");
    setTelegramBotEditing(false);
    setSuccess("Telegram bot token removed.");
  };

  const verificationActive =
    verificationFromEmail.trim().length > 0 &&
    verificationFromName.trim().length > 0;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading settings...
      </div>
    );
  }

  return (
    <form onSubmit={handleSave} className="space-y-8 max-w-2xl">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {success && (
        <Alert className="bg-green-50 border-green-200">
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Mail className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Email verification (Resend)</h2>
          {resendConfigured === true ? (
            <Badge className="bg-green-600 hover:bg-green-600/90">Resend configured</Badge>
          ) : resendConfigured === false ? (
            <Badge variant="secondary">Resend API key missing</Badge>
          ) : null}
          {verificationActive ? (
            <Badge className="bg-blue-600 hover:bg-blue-600/90">
              Verification active
            </Badge>
          ) : (
            <Badge variant="secondary">Verification off (set sender)</Badge>
          )}
          {resendConfigured === true && platformAdminEmail.trim() ? (
            <Badge className="bg-green-600 hover:bg-green-600/90">
              Lead alerts active
            </Badge>
          ) : (
            <Badge variant="secondary">Lead alerts off (set admin email)</Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          Signup email verification is enabled automatically when both From email
          and From name are set. Clear either field to disable verification. The
          Resend API key is set via environment variables (
          <code className="text-xs">RESEND_API_KEY</code>).
        </p>
        <Alert>
          <AlertDescription className="text-sm">
            If emails show as sent in logs but do not arrive, check spam and the{" "}
            <a
              href="https://resend.com/emails"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium"
            >
              Resend dashboard
            </a>
            . Test API keys only deliver to your Resend account email unless you
            verify a custom domain (e.g. 247ai.live).
          </AlertDescription>
        </Alert>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="platform_admin_email">Platform admin email</Label>
            <Input
              id="platform_admin_email"
              type="email"
              placeholder="admin@yourdomain.com"
              value={platformAdminEmail}
              onChange={(e) => setPlatformAdminEmail(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Receives platform alerts when a connected tool needs OAuth
              reauthorization. Lead notifications still require Resend.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="verification_from_email">From email</Label>
            <Input
              id="verification_from_email"
              type="email"
              placeholder="noreply@yourdomain.com"
              value={verificationFromEmail}
              onChange={(e) => setVerificationFromEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="verification_from_name">From name</Label>
            <Input
              id="verification_from_name"
              placeholder="24x7 AI"
              value={verificationFromName}
              onChange={(e) => setVerificationFromName(e.target.value)}
            />
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">WhatsApp lead alerts</h2>
          <p className="text-sm text-muted-foreground">
            Send the full contact-form submission to the platform admin. Twilio
            must have an approved WhatsApp Content template configured on the
            backend before delivery can be enabled.
          </p>
          <div className="mt-2">
            {settings?.whatsapp_sender_configured ? (
              <Badge className="bg-green-600 hover:bg-green-600/90">
                Twilio WhatsApp template configured
              </Badge>
            ) : (
              <Badge variant="secondary">Twilio WhatsApp template not configured</Badge>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label htmlFor="whatsapp_lead_enabled">Enable WhatsApp lead alerts</Label>
            <p className="text-sm text-muted-foreground">
              Delivery requires the setting below and a configured template.
            </p>
          </div>
          <Switch
            id="whatsapp_lead_enabled"
            checked={platformAdminWhatsappEnabled}
            onCheckedChange={setPlatformAdminWhatsappEnabled}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="platform_admin_whatsapp_phone">
            Platform admin WhatsApp number
          </Label>
          <Input
            id="platform_admin_whatsapp_phone"
            type="tel"
            autoComplete="tel"
            placeholder="+15551234567"
            value={platformAdminWhatsappPhone}
            onChange={(event) => setPlatformAdminWhatsappPhone(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Use E.164 format. The approved template must include placeholders
            1–10 for name, business, email, phone, business type, message,
            source, demo, submission time, and lead link.
          </p>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Telegram admin alerts</h2>
          <p className="text-sm text-muted-foreground">
            Receive Telegram notifications for new users, invitation joins, and
            demo or interest submissions. Create a bot with @BotFather and use
            your chat or group ID.
          </p>
        </div>

        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label htmlFor="telegram_enabled">Enable Telegram notifications</Label>
            <p className="text-sm text-muted-foreground">
              Send alerts to the configured chat when users join the platform or
              submit a demo or interest request.
            </p>
          </div>
          <Switch
            id="telegram_enabled"
            checked={telegramEnabled}
            onCheckedChange={setTelegramEnabled}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="telegram_chat_id">Chat ID</Label>
          <Input
            id="telegram_chat_id"
            placeholder="-1001234567890"
            value={telegramChatId}
            onChange={(e) => setTelegramChatId(e.target.value)}
          />
        </div>

        <TelegramBotCredentialRow
          configured={Boolean(settings?.telegram_bot_token_configured)}
          botId={settings?.telegram_bot_id}
          value={telegramBotToken}
          onChange={setTelegramBotToken}
          onRemove={handleRemoveBotToken}
          removing={saving}
          disabled={saving}
          editing={telegramBotEditing}
          onStartEdit={() => setTelegramBotEditing(true)}
          onCancelEdit={() => {
            setTelegramBotEditing(false);
            setTelegramBotToken("");
          }}
          pendingChange={botTokenPendingChange}
        />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold">SMS OAuth alerts</h2>
          <p className="text-sm text-muted-foreground">
            Send platform-admin alerts when a connected tool can no longer be
            renewed automatically. Configure Twilio credentials and
            <code className="mx-1 text-xs">TWILIO_SMS_FROM_NUMBER</code>
            on the backend to enable delivery.
          </p>
          <div className="mt-2">
            {settings?.sms_sender_configured ? (
              <Badge className="bg-green-600 hover:bg-green-600/90">
                Twilio sender configured
              </Badge>
            ) : (
              <Badge variant="secondary">Twilio sender not configured</Badge>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between rounded-lg border p-4">
          <div>
            <Label htmlFor="oauth_sms_enabled">Enable SMS OAuth alerts</Label>
            <p className="text-sm text-muted-foreground">
              SMS alerts go to the platform administrator destination below.
            </p>
          </div>
          <Switch
            id="oauth_sms_enabled"
            checked={platformAdminSmsEnabled}
            onCheckedChange={setPlatformAdminSmsEnabled}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="platform_admin_sms_phone">
            Platform admin phone
          </Label>
          <Input
            id="platform_admin_sms_phone"
            type="tel"
            autoComplete="tel"
            placeholder="+15551234567"
            value={platformAdminSmsPhone}
            onChange={(event) => setPlatformAdminSmsPhone(event.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            Enter an E.164 number, including the country code. SMS is sent only
            when enabled and Twilio is configured.
          </p>
        </div>
      </section>

      <Button type="submit" disabled={saving}>
        {saving ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Saving...
          </>
        ) : (
          <>
            <Save className="mr-2 h-4 w-4" />
            Save settings
          </>
        )}
      </Button>
    </form>
  );
}
