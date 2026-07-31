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
import { cn } from "@/lib/utils";
import { KeyRound, Pencil, Trash2 } from "lucide-react";

/**
 * Props for a single third-party API credential row on the organization page.
 */
export interface ProviderCredentialRowProps {
  /** Display name, e.g. "Deepgram". */
  label: string;
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
            <p className="text-xs text-muted-foreground">
              Click <span className="font-medium">Save credentials</span> below
              when you are ready to apply this change.
            </p>
          </div>
        ) : configured ? (
          <div
            className="flex h-10 items-center rounded-md border bg-muted/40 px-3 font-mono text-sm tracking-widest text-muted-foreground"
            aria-label={`${label} key stored`}
          >
            ••••••••••••
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
