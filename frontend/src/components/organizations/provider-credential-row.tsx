"use client";

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
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import {
  CircleHelp,
  ExternalLink,
  KeyRound,
  Pencil,
  Trash2,
} from "lucide-react";

/**
 * Props for a single third-party API credential row on the organization page.
 */
export interface ProviderCredentialRowProps {
  /** Display name, e.g. "Deepgram". */
  label: string;
  /** Short provider-specific guidance shown in the help tooltip. */
  helpText?: string;
  /** Provider dashboard or docs page where a user can create a key. */
  setupUrl?: string;
  /** Whether a key is already stored for this provider. */
  configured: boolean;
  /** Draft value while editing (never populated from the server). */
  value: string;
  /** Called when the user types in the password field. */
  onChange: (value: string) => void;
  /** Called after the user confirms removal in the dialog. */
  onRemove: () => void | Promise<void>;
  /** True while a remove request is in flight. */
  removing?: boolean;
  /** Disable all actions (e.g. while another save runs). */
  disabled?: boolean;
  /** Whether the row is in add/update edit mode. */
  editing: boolean;
  /** Enter edit mode to set or replace a key. */
  onStartEdit: () => void;
  /** Leave edit mode and discard unsaved draft for this row. */
  onCancelEdit: () => void;
  /** True when this row has unsaved draft changes. */
  pendingChange?: boolean;
  /** Non-secret user-maintained reference note for this provider. */
  description?: string;
  /** Called when the reference note changes. */
  onDescriptionChange?: (value: string) => void;
  className?: string;
}

/**
 * One provider credential with clear configured state and explicit actions.
 *
 * When a key exists, users see a masked placeholder (not the real secret) and
 * can **Update key** or **Remove key**. When none exists, **Add API key**
 * opens the password field. Removal uses a confirmation dialog (no browser
 * alerts).
 */
export function ProviderCredentialRow({
  label,
  helpText,
  setupUrl,
  configured,
  value,
  onChange,
  onRemove,
  removing = false,
  disabled = false,
  editing,
  onStartEdit,
  onCancelEdit,
  pendingChange = false,
  description = "",
  onDescriptionChange,
  className,
}: ProviderCredentialRowProps) {
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
            <div className="flex items-center gap-2">
              <KeyRound className="h-4 w-4 text-muted-foreground" />
              <Label className="text-sm font-medium">{label}</Label>
              {helpText ? (
                <TooltipProvider delayDuration={300}>
                  <Tooltip disableHoverableContent>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className="inline-flex shrink-0 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1"
                        aria-label={`Help for ${label}`}
                      >
                        <CircleHelp className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent
                      side="top"
                      align="start"
                      className="max-w-xs text-xs leading-relaxed"
                    >
                      {helpText}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ) : null}
              <Badge
                variant={configured ? "default" : "secondary"}
                className={
                  configured
                    ? "bg-green-600 hover:bg-green-600/90"
                    : undefined
                }
              >
                {configured ? "Configured" : "Not configured"}
              </Badge>
              {pendingChange ? (
                <Badge variant="outline" className="border-amber-500 text-amber-700">
                  Unsaved
                </Badge>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground">
              {configured
                ? "A key is stored securely. Update to replace it or remove to delete it."
                : "No key stored yet. Add one to enable voice features that need this provider."}
            </p>
            {setupUrl ? (
              <a
                href={setupUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-primary underline-offset-4 hover:underline"
              >
                Get an API key
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </a>
            ) : null}
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
                {configured ? "Update key" : "Add API key"}
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
                  {removing ? "Removing..." : "Remove key"}
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
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor={`provider-cred-${label}`} className="text-xs">
                {configured ? "New API key" : "API key"}
              </Label>
              <Input
                id={`provider-cred-${label}`}
                type="password"
                autoComplete="off"
                value={value}
                disabled={disabled}
                placeholder={
                  configured
                    ? "Enter a new key to replace the stored one"
                    : "Paste your API key"
                }
                onChange={(event) => onChange(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`provider-desc-${label}`} className="text-xs">
                Description <span className="font-normal text-muted-foreground">(optional)</span>
              </Label>
              <Textarea
                id={`provider-desc-${label}`}
                value={description}
                disabled={disabled}
                maxLength={1000}
                placeholder="Add a private reference note, such as the project or environment this key belongs to."
                className="min-h-20 resize-y"
                onChange={(event) => onDescriptionChange?.(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                This note is for your team&apos;s reference and is not sent to the provider.
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              Click <span className="font-medium">Save changes</span> below when
              you are ready to apply this update.
            </p>
          </div>
        ) : configured ? (
          <>
            <div
              className="flex h-10 items-center rounded-md border bg-muted/40 px-3 font-mono text-sm tracking-widest text-muted-foreground"
              aria-label={`${label} key stored`}
            >
              ••••••••••••
            </div>
            {description.trim() ? (
              <div className="rounded-md border border-dashed bg-muted/20 px-3 py-2">
                <p className="text-xs font-medium text-muted-foreground">Description</p>
                <p className="mt-1 whitespace-pre-wrap text-sm">{description}</p>
              </div>
            ) : null}
          </>
        ) : description.trim() ? (
          <div className="rounded-md border border-dashed bg-muted/20 px-3 py-2">
            <p className="text-xs font-medium text-muted-foreground">Description</p>
            <p className="mt-1 whitespace-pre-wrap text-sm">{description}</p>
          </div>
        ) : null}
      </div>

      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove {label} API key?</DialogTitle>
            <DialogDescription>
              This deletes the stored key for {label}. Voice features that rely
              on this provider may stop working until you add a new key.
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
              {removing ? "Removing..." : "Remove key"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
