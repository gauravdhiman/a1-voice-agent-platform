"use client";

import * as React from "react";
import { ProviderCredentialRow } from "@/components/organizations/provider-credential-row";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  countPendingProviderCredentialChanges,
  PROVIDER_LABELS,
  ProviderCredsDraft,
  SimpleProviderKey,
  SIMPLE_PROVIDER_KEYS,
} from "@/lib/provider-credentials-input";
import { KeyRound, Save } from "lucide-react";

/**
 * Props for the organization third-party API credentials card.
 */
export interface ProviderCredentialsCardProps {
  /** Per-provider configured flags from the organization read model. */
  status?: Record<string, boolean>;
  draft: ProviderCredsDraft;
  onDraftChange: (draft: ProviderCredsDraft) => void;
  touched: Record<string, boolean>;
  onMarkTouched: (key: string) => void;
  onClearTouched: (key: string) => void;
  onSave: () => void | Promise<void>;
  onRemoveProvider: (key: SimpleProviderKey) => void | Promise<void>;
  saving?: boolean;
  removingProvider?: SimpleProviderKey | null;
  canUpdate?: boolean;
}

export const EMPTY_DRAFT: ProviderCredsDraft = {
  google: "",
  deepgram: "",
  openai: "",
  cartesia: "",
  cerebras: "",
  openrouter: "",
  fish: "",
};

/**
 * Card for managing per-provider API keys on the organization settings page.
 *
 * Each provider row exposes explicit **Add**, **Update**, and **Remove**
 * actions so admins are not required to infer that an empty password field
 * means "clear on save".
 */
export function ProviderCredentialsCard({
  status = {},
  draft,
  onDraftChange,
  touched,
  onMarkTouched,
  onClearTouched,
  onSave,
  onRemoveProvider,
  saving = false,
  removingProvider = null,
  canUpdate = false,
}: ProviderCredentialsCardProps) {
  const [editingKeys, setEditingKeys] = React.useState<
    Record<string, boolean>
  >({});

  const pendingCount = countPendingProviderCredentialChanges(touched);
  const busy = saving || removingProvider !== null;

  const startEdit = (key: string) => {
    setEditingKeys((prev) => ({ ...prev, [key]: true }));
  };

  const cancelEdit = (key: SimpleProviderKey) => {
    setEditingKeys((prev) => ({ ...prev, [key]: false }));
    onDraftChange({ ...draft, [key]: "" });
    onClearTouched(key);
  };

  const handleRemove = async (key: SimpleProviderKey) => {
    await onRemoveProvider(key);
    setEditingKeys((prev) => ({ ...prev, [key]: false }));
  };

  const updateSimpleField = (key: SimpleProviderKey, value: string) => {
    onDraftChange({ ...draft, [key]: value });
    onMarkTouched(key);
  };

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="flex items-center space-x-2 text-lg">
          <KeyRound className="h-5 w-5 text-muted-foreground" />
          <span>Third-party API Credentials</span>
        </CardTitle>
        <CardDescription>
          Per-provider API keys for the modular voice engine. Keys are encrypted
          at rest and never shown after saving. Use each row to add, update, or
          remove a specific provider without affecting the others.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-5 pt-0">
        {canUpdate ? (
          <>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {SIMPLE_PROVIDER_KEYS.map((key) => (
                <ProviderCredentialRow
                  key={key}
                  label={`${PROVIDER_LABELS[key]} API key`}
                  configured={Boolean(status[key])}
                  value={draft[key]}
                  editing={Boolean(editingKeys[key])}
                  pendingChange={Boolean(touched[key])}
                  disabled={busy}
                  removing={removingProvider === key}
                  onStartEdit={() => startEdit(key)}
                  onCancelEdit={() => cancelEdit(key)}
                  onChange={(value) => updateSimpleField(key, value)}
                  onRemove={() => handleRemove(key)}
                />
              ))}
            </div>

            {pendingCount > 0 ? (
              <p className="text-sm text-amber-700">
                {pendingCount} unsaved change{pendingCount === 1 ? "" : "s"} —
                click Save credentials to apply.
              </p>
            ) : null}
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            You do not have permission to update provider credentials.
          </p>
        )}
      </CardContent>
      {canUpdate ? (
        <CardFooter className="flex justify-end space-x-2 border-t bg-muted/20 p-5">
          <Button
            size="sm"
            onClick={() => void onSave()}
            disabled={busy || pendingCount === 0}
            className="flex items-center space-x-2"
          >
            <Save className="h-4 w-4" />
            <span>
              {saving
                ? "Saving..."
                : pendingCount > 0
                  ? `Save credentials (${pendingCount})`
                  : "Save credentials"}
            </span>
          </Button>
        </CardFooter>
      ) : null}
    </Card>
  );
}

export { EMPTY_DRAFT as emptyProviderCredsDraft };
