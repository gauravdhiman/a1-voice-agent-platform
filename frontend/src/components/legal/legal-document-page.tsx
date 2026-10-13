"use client";

import { useEffect, useState } from "react";

import { BasicMarkdownRenderer } from "@/components/markdown/basic-markdown-renderer";
import { PublicFooter } from "@/components/public-theme/public-footer";
import { PublicHeader } from "@/components/public-theme/public-header";
import { PublicThemeRoot } from "@/components/public-theme/public-theme-root";
import pt from "@/components/public-theme/public-theme.module.css";
import { legalDocService } from "@/services/legal-doc-service";
import type { LegalDocumentKey, LegalDocumentPublic } from "@/types/legal-docs";

/** True when the error is a 404 from the legal documents API. */
function isNotFoundError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    error.status === 404
  );
}

function formatPublishedDate(publishedAt: string | null): string | null {
  if (!publishedAt) return null;
  return new Date(publishedAt).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

interface LegalDocumentPageProps {
  documentKey: LegalDocumentKey;
  /** Page heading shown above the fetched document title. */
  heading: string;
  /** Shown when no published version exists (404) or the load fails. */
  unavailableMessage: string;
}

/**
 * Public legal document page: fetches the latest published markdown version
 * for `documentKey` and renders it with title, version number, and published
 * date, plus loading and not-available states.
 */
export function LegalDocumentPage({
  documentKey,
  heading,
  unavailableMessage,
}: LegalDocumentPageProps) {
  const [document, setDocument] = useState<LegalDocumentPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    legalDocService
      .getPublishedDocument(documentKey)
      .then((doc) => {
        if (!cancelled) {
          setDocument(doc);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setDocument(null);
          setError(isNotFoundError(err) ? "not-found" : "load-failed");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [documentKey]);

  const publishedDate = formatPublishedDate(document?.published_at ?? null);

  return (
    <PublicThemeRoot>
      <PublicHeader />
      <main className={pt.page}>
        <div className={pt.legalLayout}>
          <section className={`${pt.panel} ${pt.legalBody}`}>
            <h1 className={`${pt.title} ${pt.legalTitle}`}>{heading}</h1>
            {loading ? (
              <p className={pt.lede}>Loading…</p>
            ) : error === "not-found" ? (
              <p className={pt.lede}>{unavailableMessage}</p>
            ) : error === "load-failed" ? (
              <p className={pt.lede}>
                {unavailableMessage} Please try again later.
              </p>
            ) : document ? (
              <>
                <div className={pt.lede}>
                  <p>
                    <strong>{document.title}</strong>
                    {" · "}Version {document.version_number}
                    {publishedDate ? ` · Published ${publishedDate}` : null}
                  </p>
                </div>
                <BasicMarkdownRenderer
                  content={document.content_markdown}
                  className="prose prose-sm max-w-none dark:prose-invert"
                />
              </>
            ) : null}
          </section>
        </div>
      </main>
      <PublicFooter />
    </PublicThemeRoot>
  );
}
