"use client";

/** Manage platform API credentials with explicit environment fallback status. */

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ProviderCredentialRow } from "@/components/organizations/provider-credential-row";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  PROVIDER_DEFINITIONS,
  PROVIDER_LABELS,
  VOICE_PROVIDER_KEYS,
  type VoiceProviderKey,
} from "@/lib/provider-credentials-input";
import { platformVoiceCredentialsService } from "@/services/platform-voice-credentials-service";
import type { PlatformVoiceProviderCredentialsResponse } from "@/types/platform-voice-credentials";
import { KeyRound } from "lucide-react";

const platformVoiceCredentialsQueryKey = ["platform-api-credentials"] as const;

/** Manage the shared provider keys used by platform-managed voice presets. */
export function PlatformVoiceProviderCredentialsForm() {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<Partial<Record<VoiceProviderKey, string>>>(
    {},
  );
  const [editing, setEditing] = useState<Partial<Record<VoiceProviderKey, boolean>>>(
    {},
  );

  const credentialsQuery = useQuery({
    queryKey: platformVoiceCredentialsQueryKey,
    queryFn: async () => {
      const response = await platformVoiceCredentialsService.getCredentials();
      if (!response.success || !response.data) {
        throw new Error(response.error ?? "Failed to load platform API credentials.");
      }
      return response.data;
    },
  });

  const saveMutation = useMutation({
    mutationFn: async ({ provider, apiKey }: { provider: VoiceProviderKey; apiKey: string }) => {
      const response = await platformVoiceCredentialsService.saveCredential(
        provider,
        apiKey,
      );
      if (!response.success) {
        throw new Error(response.error ?? "Failed to save platform API credential.");
      }
      return provider;
    },
    onSuccess: async (provider) => {
      setDrafts((current) => ({ ...current, [provider]: "" }));
      setEditing((current) => ({ ...current, [provider]: false }));
      toast.success(`${PROVIDER_LABELS[provider]} API credential saved`);
      await queryClient.invalidateQueries({
        queryKey: platformVoiceCredentialsQueryKey,
      });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to save platform API credential.");
    },
  });

  const removeMutation = useMutation({
    mutationFn: async (provider: VoiceProviderKey) => {
      const response =
        await platformVoiceCredentialsService.removeCredential(provider);
      if (!response.success) {
        throw new Error(response.error ?? "Failed to remove platform API credential.");
      }
      return provider;
    },
    onSuccess: async (provider) => {
      setEditing((current) => ({ ...current, [provider]: false }));
      setDrafts((current) => ({ ...current, [provider]: "" }));
      toast.success(`${PROVIDER_LABELS[provider]} API credential removed`);
      await queryClient.invalidateQueries({
        queryKey: platformVoiceCredentialsQueryKey,
      });
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : "Failed to remove platform API credential.");
    },
  });

  const credentials: PlatformVoiceProviderCredentialsResponse | undefined =
    credentialsQuery.data;

  return (
    <Card>
      <CardHeader className="p-5 pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <KeyRound className="h-5 w-5 text-muted-foreground" />
          <span>Platform API Credentials</span>
        </CardTitle>
        <CardDescription>
          Credentials saved here are encrypted. Platform-managed voice presets
          use a saved key first, then the matching environment variable as a
          fallback. Organization-managed presets continue using their organization
          credentials.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 p-5 pt-0">
        {credentialsQuery.isPending ? (
          <p className="text-sm text-muted-foreground" role="status">
            Loading platform API credentials...
          </p>
        ) : credentialsQuery.isError ? (
          <div className="space-y-3" role="alert">
            <p className="text-sm text-destructive">
              {credentialsQuery.error instanceof Error
                ? credentialsQuery.error.message
                : "Failed to load platform API credentials."}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void credentialsQuery.refetch()}
            >
              Try again
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {VOICE_PROVIDER_KEYS.map((provider) => {
              const status = credentials?.providers[provider];
              const saving =
                saveMutation.isPending &&
                saveMutation.variables?.provider === provider;
              const removing =
                removeMutation.isPending && removeMutation.variables === provider;
              const busy = saveMutation.isPending || removeMutation.isPending;

              return (
                <ProviderCredentialRow
                  key={provider}
                  label={`${PROVIDER_LABELS[provider]} API key`}
                  helpText={PROVIDER_DEFINITIONS[provider].helpText}
                  setupUrl={PROVIDER_DEFINITIONS[provider].setupUrl}
                  configured={status?.configured ?? false}
                  credentialScope="platform"
                  environmentFallbackConfigured={
                    status?.environment_fallback_configured ?? false
                  }
                  value={drafts[provider] ?? ""}
                  editing={Boolean(editing[provider])}
                  disabled={busy && !saving && !removing}
                  saving={saving}
                  removing={removing}
                  onStartEdit={() =>
                    setEditing((current) => ({ ...current, [provider]: true }))
                  }
                  onCancelEdit={() => {
                    setEditing((current) => ({ ...current, [provider]: false }));
                    setDrafts((current) => ({ ...current, [provider]: "" }));
                  }}
                  onChange={(value) =>
                    setDrafts((current) => ({ ...current, [provider]: value }))
                  }
                  onSave={async () => {
                    try {
                      await saveMutation.mutateAsync({
                        provider,
                        apiKey: drafts[provider] ?? "",
                      });
                    } catch {
                      // The mutation toast reports the safe server error.
                    }
                  }}
                  onRemove={async () => {
                    await removeMutation.mutateAsync(provider);
                  }}
                />
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
