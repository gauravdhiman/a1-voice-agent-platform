"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { PublicAgentCard } from "@/components/public-org/public-agent-card";
import { PublicOrgPassphraseGate } from "@/components/public-org/public-org-passphrase-gate";
import { Button } from "@/components/ui/button";
import {
  clearAccessToken,
  publicOrgPageService,
  readStoredAccessToken,
} from "@/services/public-org-page-service";
import type { PublicAgentSummary, PublicOrgSummary } from "@/types/public-org-page";

/**
 * Public organization showcase — lists explicitly published agents.
 */
export default function PublicOrgPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  const [summary, setSummary] = React.useState<PublicOrgSummary | null>(null);
  const [agents, setAgents] = React.useState<PublicAgentSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [needsPassphrase, setNeedsPassphrase] = React.useState(false);

  const loadAgents = React.useCallback(
    async (token: string | null) => {
      const { agents: list } = await publicOrgPageService.listAgents(slug, token);
      setAgents(list);
    },
    [slug],
  );

  React.useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setLoading(true);
      setError(null);
      try {
        const orgSummary = await publicOrgPageService.getOrgSummary(slug);
        if (cancelled) return;
        setSummary(orgSummary);

        const stored = readStoredAccessToken(slug);
        if (orgSummary.passphrase_required && !stored) {
          setNeedsPassphrase(true);
          setLoading(false);
          return;
        }

        await loadAgents(stored);
        setNeedsPassphrase(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Page not available");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [slug, loadAgents]);

  const handleUnlocked = async (token: string) => {
    setNeedsPassphrase(false);
    setLoading(true);
    setError(null);
    try {
      await loadAgents(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agents");
    } finally {
      setLoading(false);
    }
  };

  const handleLockedOut = () => {
    clearAccessToken(slug);
    setAgents([]);
    setNeedsPassphrase(true);
  };

  if (loading && !summary) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background px-4">
        <div className="max-w-md text-center">
          <h1 className="text-xl font-semibold">Page unavailable</h1>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  if (summary && needsPassphrase) {
    return (
      <div className="min-h-dvh bg-gradient-to-b from-muted/40 to-background px-4 py-10">
        <PublicOrgPassphraseGate
          slug={slug}
          orgName={summary.name}
          onUnlocked={(token) => void handleUnlocked(token)}
        />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-gradient-to-b from-muted/40 to-background">
      <header className="border-b bg-background/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-col gap-2 px-4 py-6">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {summary?.name}
          </h1>
          {summary?.description ? (
            <p className="text-sm text-muted-foreground sm:text-base">
              {summary.description}
            </p>
          ) : null}
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        {error ? (
          <div className="mb-6 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {error}
            {summary?.passphrase_required ? (
              <Button
                variant="link"
                className="mt-2 h-auto p-0"
                onClick={handleLockedOut}
              >
                Re-enter passphrase
              </Button>
            ) : null}
          </div>
        ) : null}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : agents.length === 0 ? (
          <div className="rounded-2xl border bg-card p-8 text-center">
            <p className="text-muted-foreground">
              No voice agents are published on this page yet.
            </p>
          </div>
        ) : (
          <>
            <p className="mb-4 text-sm text-muted-foreground">
              Choose an agent below to start a voice conversation.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              {agents.map((agent) => (
                <PublicAgentCard key={agent.id} slug={slug} agent={agent} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
