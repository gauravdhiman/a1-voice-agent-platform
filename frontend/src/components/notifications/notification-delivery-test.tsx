"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { notificationSettingsService } from "@/services/notification-settings-service";

interface NotificationDeliveryTestProps {
  organizationId?: string;
  disabled?: boolean;
}

/** Probe saved destinations only, showing provider failure separately from acceptance. */
export function NotificationDeliveryTest({ organizationId, disabled }: NotificationDeliveryTestProps) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send(channel: "email" | "telegram") {
    setPending(true);
    setError(null);
    setMessage(null);
    const result = await notificationSettingsService.testDelivery(channel, organizationId);
    setPending(false);
    if (result.success && result.data) setMessage(result.data.message);
    else setError(result.error || "Notification test failed.");
  }

  return (
    <section aria-label="Test saved notification destinations" className="space-y-3 border-t pt-4">
      <p className="text-sm text-muted-foreground">Save your changes before testing. Tests use saved destinations.</p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" disabled={disabled || pending} onClick={() => void send("email")}>Send test email</Button>
        <Button type="button" variant="outline" disabled={disabled || pending} onClick={() => void send("telegram")}>Send test Telegram</Button>
      </div>
      {pending ? <p role="status">Sending test...</p> : null}
      {message ? <p role="status" className="text-sm">{message}</p> : null}
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
    </section>
  );
}
