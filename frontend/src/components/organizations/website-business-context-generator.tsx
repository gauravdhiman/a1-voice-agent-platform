"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { organizationService } from "@/services/organization-service";

export interface WebsiteBusinessContextGeneratorProps {
  organizationId: string;
  website: string;
  businessContext: string;
  onBusinessContextChange: (businessContext: string) => void;
  disabled?: boolean;
}

/**
 * Check whether a website field contains a public HTTP(S) URL.
 *
 * @param value - URL currently entered in the organization form
 * @returns True when a public-looking website URL is ready to analyze
 */
export function isValidWebsiteUrl(value: string): boolean {
  const trimmedValue = value.trim();
  if (!/^https?:\/\//i.test(trimmedValue) || /\s/.test(trimmedValue)) {
    return false;
  }

  const authority = trimmedValue
    .slice(trimmedValue.indexOf("//") + 2)
    .split(/[/?#]/, 1)[0];
  if (!authority || authority.startsWith("/") || authority.endsWith(":")) {
    return false;
  }

  try {
    const url = new URL(trimmedValue);
    const hostname = url.hostname.toLowerCase().replace(/\.$/, "");
    const portAllowed =
      !url.port ||
      (url.protocol === "https:" && url.port === "443") ||
      (url.protocol === "http:" && url.port === "80");
    const invalidSuffixes = [
      ".localhost",
      ".local",
      ".internal",
      ".test",
      ".invalid",
    ];
    const privateIpv4 = isPrivateIpv4(hostname);

    return (
      (url.protocol === "http:" || url.protocol === "https:") &&
      !url.username &&
      !url.password &&
      isValidPublicHostname(hostname) &&
      hostname !== "localhost" &&
      !invalidSuffixes.some((suffix) => hostname.endsWith(suffix)) &&
      !privateIpv4 &&
      portAllowed
    );
  } catch {
    return false;
  }
}

function isValidPublicHostname(hostname: string): boolean {
  if (hostname.length > 253 || !hostname.includes(".")) return false;

  const labels = hostname.split(".");
  const validLabel = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i;
  if (labels.some((label) => label.length > 63 || !validLabel.test(label))) {
    return false;
  }

  const numericLabels = labels.every((label) => /^\d+$/.test(label));
  if (numericLabels) {
    return (
      labels.length === 4 &&
      labels.every((label) => Number(label) >= 0 && Number(label) <= 255)
    );
  }

  const topLevelDomain = labels[labels.length - 1] ?? "";
  return (
    /^[a-z]{2,63}$/i.test(topLevelDomain) ||
    (topLevelDomain.startsWith("xn--") && topLevelDomain.length > 4)
  );
}

function isPrivateIpv4(hostname: string): boolean {
  const octets = hostname.split(".").map(Number);
  if (
    octets.length !== 4 ||
    octets.some((octet) => !Number.isInteger(octet) || octet < 0 || octet > 255)
  ) {
    return false;
  }

  return (
    octets[0] === 0 ||
    octets[0] === 10 ||
    octets[0] === 127 ||
    octets[0] >= 224 ||
    (octets[0] === 169 && octets[1] === 254) ||
    (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
    (octets[0] === 100 && octets[1] >= 64 && octets[1] <= 127) ||
    (octets[0] === 192 && octets[1] === 0 && octets[2] === 0) ||
    (octets[0] === 192 && octets[1] === 0 && octets[2] === 2) ||
    (octets[0] === 192 && octets[1] === 88 && octets[2] === 99) ||
    (octets[0] === 192 && octets[1] === 168) ||
    (octets[0] === 198 && (octets[1] === 18 || octets[1] === 19)) ||
    (octets[0] === 198 && octets[1] === 51 && octets[2] === 100) ||
    (octets[0] === 203 && octets[1] === 0 && octets[2] === 113)
  );
}

/**
 * Let an organization administrator create an editable business-context draft
 * from the organization's public website.
 *
 * Existing context is only replaced in the form after explicit confirmation;
 * the organization is saved through its normal Save or Continue action.
 */
export function WebsiteBusinessContextGenerator({
  organizationId,
  website,
  businessContext,
  onBusinessContextChange,
  disabled = false,
}: WebsiteBusinessContextGeneratorProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const latestWebsite = useRef(website);
  const latestBusinessContext = useRef(businessContext);
  useEffect(() => {
    latestWebsite.current = website;
    latestBusinessContext.current = businessContext;
  }, [website, businessContext]);

  if (!isValidWebsiteUrl(website)) return null;

  const generateDraft = async () => {
    const websiteAtStart = latestWebsite.current.trim();
    const contextAtStart = latestBusinessContext.current;
    setError(null);
    setSummary(null);
    setLoading(true);

    try {
      const result = await organizationService.generateWebsiteBusinessContext(
        organizationId,
        websiteAtStart,
      );
      if (latestWebsite.current.trim() !== websiteAtStart) {
        setError("The website changed during analysis. Please generate a new draft.");
        return;
      }
      if (latestBusinessContext.current !== contextAtStart) {
        setError(
          "The business context changed during analysis, so your text was left untouched. Try again.",
        );
        return;
      }

      onBusinessContextChange(result.business_details);
      setSummary(
        result.page_limit_reached
          ? `Drafted from ${result.pages_analyzed} public pages. This site has more pages than the 50-page scan limit. Review the text before saving.`
          : `Drafted from ${result.pages_analyzed} public pages. Review the text before saving.`,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "We could not generate business context. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateClick = () => {
    if (businessContext.trim()) {
      setError(null);
      setSummary(null);
      setConfirmOpen(true);
      return;
    }
    void generateDraft();
  };

  return (
    <div className="flex max-w-full flex-col items-start gap-2 sm:items-end">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleGenerateClick}
        disabled={disabled || loading}
        aria-label="Generate business context from website"
        data-testid="generate-business-context"
      >
        {loading ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
        )}
        {loading ? "Reading website…" : "Generate business context"}
      </Button>
      <p className="max-w-md text-left text-xs text-muted-foreground sm:text-right">
        We’ll review up to 50 public pages and prepare an editable draft. It won’t be saved until you save these organization changes.
      </p>
      {summary && (
        <p className="text-sm text-muted-foreground" role="status">
          {summary}
        </p>
      )}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Replace the current business context?</DialogTitle>
            <DialogDescription>
              Generating a new draft will replace the business context in this form.
              You can review and edit it, and it will not be saved until you save
              these organization changes.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => {
                setConfirmOpen(false);
                void generateDraft();
              }}
            >
              Generate new draft
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
