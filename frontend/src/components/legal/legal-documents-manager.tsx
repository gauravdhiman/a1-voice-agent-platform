"use client";

import * as React from "react";
import { Eye, Loader2, Pencil, Plus, Save, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DeleteConfirmationDialog } from "@/components/ui/delete-confirmation-dialog";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingState } from "@/components/ui/loading-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { BasicMarkdownRenderer } from "@/components/markdown/basic-markdown-renderer";
import { LegalPublishDialog } from "@/components/legal/legal-publish-dialog";
import { legalDocService } from "@/services/legal-doc-service";
import type {
  LegalDocumentKey,
  LegalDocumentVersionDetail,
  LegalDocumentVersionSummary,
  LegalVersionStatus,
} from "@/types/legal-docs";

const DOCUMENTS: { key: LegalDocumentKey; label: string }[] = [
  { key: "terms", label: "Terms & Conditions" },
  { key: "privacy", label: "Privacy Policy" },
];

function isDocumentKey(value: string): value is LegalDocumentKey {
  return DOCUMENTS.some((doc) => doc.key === value);
}

function statusBadgeVariant(
  status: LegalVersionStatus,
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "published":
      return "default";
    case "draft":
      return "secondary";
    case "deprecated":
      return "outline";
    default:
      return "destructive";
  }
}

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Platform-admin manager for legal documents: browse version history per
 * document, edit drafts, delete drafts, and publish a draft (optionally
 * notifying signed-up users).
 */
export function LegalDocumentsManager() {
  const [documentKey, setDocumentKey] =
    React.useState<LegalDocumentKey>("terms");
  const [versions, setVersions] = React.useState<LegalDocumentVersionSummary[]>(
    [],
  );
  const [loading, setLoading] = React.useState(true);
  const [loadError, setLoadError] = React.useState<string | null>(null);

  // Draft editor state.
  const [editorDraft, setEditorDraft] =
    React.useState<LegalDocumentVersionDetail | null>(null);
  const [content, setContent] = React.useState("");
  const [summary, setSummary] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [creating, setCreating] = React.useState(false);

  // Dialog state.
  const [publishTarget, setPublishTarget] =
    React.useState<LegalDocumentVersionDetail | null>(null);
  const [publishOpen, setPublishOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] =
    React.useState<LegalDocumentVersionSummary | null>(null);

  // Version viewer drawer state.
  const [viewDetail, setViewDetail] =
    React.useState<LegalDocumentVersionDetail | null>(null);
  const [viewLoading, setViewLoading] = React.useState(false);
  // Draft preview drawer state (renders unsaved editor content).
  const [previewOpen, setPreviewOpen] = React.useState(false);

  const loadVersions = React.useCallback(async (key: LegalDocumentKey) => {
    setLoading(true);
    setLoadError(null);
    try {
      const result = await legalDocService.listVersions(key);
      setVersions(result);
    } catch (error) {
      console.error("Failed to load legal versions:", error);
      setLoadError("Failed to load version history.");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadVersions(documentKey);
  }, [documentKey, loadVersions]);

  const closeEditor = () => {
    setEditorDraft(null);
    setContent("");
    setSummary("");
    setPreviewOpen(false);
  };

  const handleCreateDraft = async () => {
    setCreating(true);
    try {
      const draft = await legalDocService.createDraft(documentKey, {});
      setEditorDraft(draft);
      setContent(draft.content_markdown);
      setSummary(draft.summary_of_changes ?? "");
    } catch (error) {
      console.error("Failed to create legal draft:", error);
      toast.error("Failed to create draft");
    } finally {
      setCreating(false);
    }
  };

  const handleEditDraft = async (version: LegalDocumentVersionSummary) => {
    try {
      const detail = await legalDocService.getVersion(version.id);
      setEditorDraft(detail);
      setContent(detail.content_markdown);
      setSummary(detail.summary_of_changes ?? "");
    } catch (error) {
      console.error("Failed to load legal draft:", error);
      toast.error("Failed to load draft");
    }
  };

  const handleViewVersion = async (version: LegalDocumentVersionSummary) => {
    setViewLoading(true);
    try {
      const detail = await legalDocService.getVersion(version.id);
      setViewDetail(detail);
    } catch (error) {
      console.error("Failed to load legal version:", error);
      toast.error("Failed to load version");
    } finally {
      setViewLoading(false);
    }
  };

  const handlePublishDraft = async (version: LegalDocumentVersionSummary) => {
    try {
      const detail = await legalDocService.getVersion(version.id);
      setPublishTarget(detail);
      setPublishOpen(true);
    } catch (error) {
      console.error("Failed to load legal draft:", error);
      toast.error("Failed to load draft");
    }
  };

  const handleSaveDraft = async () => {
    if (!editorDraft) return;
    setSaving(true);
    try {
      const updated = await legalDocService.updateDraft(editorDraft.id, {
        content_markdown: content,
        summary_of_changes: summary.trim() ? summary.trim() : null,
      });
      setEditorDraft(updated);
      toast.success("Draft saved");
      await loadVersions(documentKey);
    } catch (error) {
      console.error("Failed to save legal draft:", error);
      toast.error("Failed to save draft");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDraft = async () => {
    if (!deleteTarget) return;
    try {
      await legalDocService.deleteDraft(deleteTarget.id);
      if (editorDraft?.id === deleteTarget.id) closeEditor();
      toast.success("Draft deleted");
      await loadVersions(documentKey);
      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete legal draft:", error);
      toast.error("Failed to delete draft");
      throw error instanceof Error
        ? error
        : new Error("Failed to delete draft");
    }
  };

  const handleOpenEditorPublish = () => {
    if (!editorDraft) return;
    setPublishTarget(editorDraft);
    setPublishOpen(true);
  };

  const handlePublished = async () => {
    closeEditor();
    setPublishTarget(null);
    await loadVersions(documentKey);
  };

  return (
    <div className="space-y-6">
      <Tabs
        value={documentKey}
        onValueChange={(value) => {
          if (!isDocumentKey(value)) return;
          closeEditor();
          setDocumentKey(value);
        }}
        className="space-y-5"
      >
        <TabsList>
          {DOCUMENTS.map((doc) => (
            <TabsTrigger key={doc.key} value={doc.key}>
              {doc.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {DOCUMENTS.map((doc) => (
          <TabsContent key={doc.key} value={doc.key} className="mt-0 space-y-6">
            {doc.key === documentKey ? (
              <>
                <Card>
                  <CardHeader>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <CardTitle>Version history</CardTitle>
                        <CardDescription>
                          Drafts, published versions, and deprecated versions
                          for this document.
                        </CardDescription>
                      </div>
                      <Button
                        onClick={() => void handleCreateDraft()}
                        disabled={creating}
                      >
                        {creating ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Creating…
                          </>
                        ) : (
                          <>
                            <Plus className="mr-2 h-4 w-4" />
                            Edit new draft
                          </>
                        )}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {loading ? (
                      <LoadingState message="Loading version history…" />
                    ) : loadError ? (
                      <ErrorState
                        title="Could not load versions"
                        message={loadError}
                        onRetry={() => void loadVersions(documentKey)}
                      />
                    ) : (
                      <Table className="min-w-[68rem] table-auto">
                        <TableHeader>
                          <TableRow>
                            <TableHead>Version</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Current</TableHead>
                            <TableHead>Published</TableHead>
                            <TableHead>Summary of changes</TableHead>
                            <TableHead className="whitespace-nowrap text-right">
                              Actions
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {versions.map((version) => (
                            <TableRow key={version.id}>
                              <TableCell className="font-medium">
                                v{version.version_number}
                              </TableCell>
                              <TableCell>
                                <Badge
                                  variant={statusBadgeVariant(version.status)}
                                >
                                  {version.status}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                {version.is_current ? (
                                  <Badge variant="outline">Current</Badge>
                                ) : (
                                  "—"
                                )}
                              </TableCell>
                              <TableCell>
                                {formatDateTime(version.published_at)}
                              </TableCell>
                              <TableCell>
                                <div className="whitespace-normal">
                                  {version.summary_of_changes ?? "—"}
                                </div>
                              </TableCell>
                              <TableCell className="whitespace-nowrap text-right">
                                <div className="flex justify-end gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() =>
                                      void handleViewVersion(version)
                                    }
                                  >
                                    <Eye className="mr-2 h-4 w-4" />
                                    View
                                  </Button>
                                  {version.status === "draft" ? (
                                    <>
                                      <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() =>
                                          void handleEditDraft(version)
                                        }
                                      >
                                        <Pencil className="mr-2 h-4 w-4" />
                                        Continue draft
                                      </Button>
                                      <Button
                                        size="sm"
                                        onClick={() =>
                                          void handlePublishDraft(version)
                                        }
                                      >
                                        <Upload className="mr-2 h-4 w-4" />
                                        Publish
                                      </Button>
                                      <Button
                                        variant="destructive"
                                        size="sm"
                                        onClick={() => {
                                          setDeleteTarget(version);
                                        }}
                                      >
                                        <Trash2 className="mr-2 h-4 w-4" />
                                        Delete draft
                                      </Button>
                                    </>
                                  ) : null}
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    )}
                  </CardContent>
                </Card>

                {editorDraft ? (
                  <Card>
                    <CardHeader>
                      <CardTitle>
                        Edit draft — v{editorDraft.version_number}
                      </CardTitle>
                      <CardDescription>
                        Publish this draft to replace the currently published
                        text.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="legal-draft-summary">
                          Summary of changes
                        </Label>
                        <Input
                          id="legal-draft-summary"
                          value={summary}
                          onChange={(e) => setSummary(e.target.value)}
                          placeholder="What changed in this version?"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="legal-draft-content">
                          Content (Markdown)
                        </Label>
                        <Textarea
                          id="legal-draft-content"
                          value={content}
                          onChange={(e) => setContent(e.target.value)}
                          rows={18}
                          className="font-mono text-sm"
                        />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          onClick={() => void handleSaveDraft()}
                          disabled={saving}
                        >
                          {saving ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Saving…
                            </>
                          ) : (
                            <>
                              <Save className="mr-2 h-4 w-4" />
                              Save draft
                            </>
                          )}
                        </Button>
                        <Button onClick={handleOpenEditorPublish}>
                          Publish
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => setPreviewOpen(true)}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          Preview
                        </Button>
                        <Button variant="outline" onClick={closeEditor}>
                          Close
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ) : null}
              </>
            ) : null}
          </TabsContent>
        ))}
      </Tabs>

      {publishTarget ? (
        <LegalPublishDialog
          version={publishTarget}
          open={publishOpen}
          onOpenChange={setPublishOpen}
          onPublished={() => void handlePublished()}
        />
      ) : null}

      {/*
        Conditionally rendered so the shared DeleteConfirmationDialog mounts
        fresh each open — its internal type-to-confirm state resets between
        deletes (always-mounted would leak "Delete" into the next dialog).
      */}
      {deleteTarget ? (
        <DeleteConfirmationDialog
          open
          onOpenChange={(o) => {
            if (!o) setDeleteTarget(null);
          }}
          itemName={`v${deleteTarget.version_number}`}
          itemType="draft"
          warnings={["The draft content will be permanently removed."]}
          onDelete={() => handleDeleteDraft()}
        />
      ) : null}

      {/* Right drawer: renders a version's content (View) or the unsaved
          draft editor content (Preview) with the public page prose classes. */}
      <Sheet
        open={Boolean(viewDetail) || previewOpen}
        onOpenChange={(o) => {
          if (!o) {
            setViewDetail(null);
            setPreviewOpen(false);
          }
        }}
      >
        <SheetContent className="flex h-[100dvh] max-h-[100dvh] w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl">
          <SheetHeader className="shrink-0 px-4 pb-3 pr-12 pt-4 sm:px-6 sm:pb-4 sm:pr-14 sm:pt-6">
            <SheetTitle className="truncate text-base sm:text-lg">
              {previewOpen && editorDraft
                ? `Preview draft — v${editorDraft.version_number}`
                : viewDetail
                  ? `v${viewDetail.version_number}`
                  : "Version"}
            </SheetTitle>
            <SheetDescription className="sr-only">
              {previewOpen
                ? "Unsaved draft preview as it would render on the public page."
                : "Version content and metadata."}
            </SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto px-4 pb-6 sm:px-6">
            {previewOpen ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Unsaved preview of the editor content.
                </p>
                <BasicMarkdownRenderer
                  content={content}
                  className="prose prose-sm max-w-none dark:prose-invert"
                />
              </div>
            ) : viewLoading && !viewDetail ? (
              <p className="text-sm text-muted-foreground">Loading…</p>
            ) : viewDetail ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                  <Badge variant={statusBadgeVariant(viewDetail.status)}>
                    {viewDetail.status}
                  </Badge>
                  {viewDetail.is_current ? (
                    <Badge variant="outline">Current</Badge>
                  ) : null}
                  <span>
                    {viewDetail.published_at
                      ? `Published ${formatDateTime(viewDetail.published_at)}`
                      : "Not published"}
                  </span>
                </div>
                {viewDetail.summary_of_changes ? (
                  <p className="text-sm text-muted-foreground">
                    {viewDetail.summary_of_changes}
                  </p>
                ) : null}
                <BasicMarkdownRenderer
                  content={viewDetail.content_markdown}
                  className="prose prose-sm max-w-none dark:prose-invert"
                />
              </div>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
