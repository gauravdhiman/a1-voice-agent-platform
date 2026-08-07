"use client";

/**
 * Telegram bot token field with configured-state UX matching org API credentials.
 */

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { Bot, Pencil, Trash2 } from "lucide-react";

export interface TelegramBotCredentialRowProps {
  /** Whether a bot token is stored (server-side encrypted). */
  configured: boolean;
  /** Public numeric bot id extracted from the token (not secret). */
  botId?: string | null;
  /** Draft token while editing (never populated from the server). */
  value: string;
  onChange: (value: string) => void;
  onRemove: () => void | Promise<void>;
  removing?: boolean;
  disabled?: boolean;
  editing: boolean;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  pendingChange?: boolean;
  className?: string;
}

/**
 * Bot token row with explicit configured / not configured state.
 */
export function TelegramBotCredentialRow({
  configured,
  botId,
  value,
  onChange,
  onRemove,
  removing = false,
  disabled = false,
  editing,
  onStartEdit,
  onCancelEdit,
  pendingChange = false,
  className,
}: TelegramBotCredentialRowProps) {
  const [removeDialogOpen, setRemoveDialogOpen] = React.useState(false);

  const handleConfirmRemove = async () => {
    await onRemove();
    setRemoveDialogOpen(false);
  };

  return (
    <>
      <div
        className={cn(
          "rounded-lg border bg-card p-4 space-y-3",
          pendingChange && "border-amber-500/50 bg-amber-500/5",
          className,
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Bot className="h-4 w-4 text-muted-foreground" />
              <Label className="text-sm font-medium">Bot token</Label>
              <Badge
                variant={configured ? "default" : "secondary"}
                className={
                  configured ? "bg-green-600 hover:bg-green-600/90" : undefined
                }
              >
                {configured ? "Configured" : "Not configured"}
              </Badge>
              {configured && botId ? (
                <Badge variant="outline" className="font-mono text-xs">
                  Bot ID {botId}
                </Badge>
              ) : null}
              {pendingChange ? (
                <Badge variant="outline" className="border-amber-500 text-amber-700">
                  Unsaved
                </Badge>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground">
              {configured
                ? "A token is stored securely. Update to replace it or remove to disconnect the bot."
                : "Paste the token from @BotFather to enable Telegram admin alerts."}
            </p>
          </div>

          {!editing ? (
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={disabled || removing}
                onClick={onStartEdit}
              >
                <Pencil className="mr-1.5 h-3.5 w-3.5" />
                {configured ? "Update token" : "Add bot token"}
              </Button>
              {configured ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  disabled={disabled || removing}
                  onClick={() => setRemoveDialogOpen(true)}
                >
                  <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                  {removing ? "Removing..." : "Remove token"}
                </Button>
              ) : null}
            </div>
          ) : (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={disabled}
              onClick={onCancelEdit}
            >
              Cancel
            </Button>
          )}
        </div>

        {editing ? (
          <div className="space-y-1.5">
            <Label htmlFor="telegram_bot_token" className="text-xs">
              {configured ? "New bot token" : "Bot token"}
            </Label>
            <Input
              id="telegram_bot_token"
              type="password"
              autoComplete="off"
              value={value}
              disabled={disabled}
              placeholder={
                configured
                  ? "Enter a new token to replace the stored one"
                  : "123456789:AAH..."
              }
              onChange={(event) => onChange(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Click <span className="font-medium">Save settings</span> below when
              you are ready to apply this change.
            </p>
          </div>
        ) : configured ? (
          <div
            className="flex h-10 items-center rounded-md border bg-muted/40 px-3 font-mono text-sm tracking-widest text-muted-foreground"
            aria-label="Telegram bot token stored"
          >
            ••••••••••••
          </div>
        ) : null}
      </div>

      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Telegram bot token?</DialogTitle>
            <DialogDescription>
              Admin signup alerts will stop until you add a valid bot token again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              disabled={removing}
              onClick={() => setRemoveDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={removing}
              onClick={() => void handleConfirmRemove()}
            >
              {removing ? "Removing..." : "Remove token"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
