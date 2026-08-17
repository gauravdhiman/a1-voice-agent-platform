"use client";

/**
 * Platform-admin master-detail editor for reusable agent use case templates.
 *
 * The editor keeps the existing structured template fields because agent
 * creation and editing already map them into the canonical instruction
 * Markdown document. The right panel and authoring sheet show that generated
 * document through the shared Markdown renderer, so admins can verify headings,
 * lists, placeholders, and other Markdown before publishing a template to the
 * agent picker.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import {
  Check,
  Edit3,
  FileText,
  Loader2,
  Plus,
  Search,
  Trash2,
} from "lucide-react";

import { MarkdownRenderer } from "@/components/markdown";
import { DeleteConfirmationDialog } from "@/components/ui/delete-confirmation-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { buildMarkdownFromTemplate } from "@/lib/agent-instructions";
import { voiceTemplateService } from "@/services/voice-template-service";
import type {
  VoiceTemplate,
  VoiceTemplateInput,
} from "@/types/voice-template";

interface VoiceTemplateFormState {
  name: string;
  industry: string;
  description: string;
  persona: string;
  tone: string;
  mission: string;
  greeting: string;
  custom_instructions: string;
  is_active: boolean;
}

const EMPTY_FORM: VoiceTemplateFormState = {
  name: "",
  industry: "",
  description: "",
  persona: "",
  tone: "",
  mission: "",
  greeting: "",
  custom_instructions: "",
  is_active: true,
};

/** Convert a persisted template into editable, non-null form values. */
function toForm(template: VoiceTemplate): VoiceTemplateFormState {
  return {
    name: template.name,
    industry: template.industry,
    description: template.description ?? "",
    persona: template.persona ?? "",
    tone: template.tone ?? "",
    mission: template.mission ?? "",
    greeting: template.greeting ?? "",
    custom_instructions: template.custom_instructions ?? "",
    is_active: template.is_active,
  };
}

/** Build the canonical Markdown document used by agent instructions. */
function toMarkdown(
  template: Pick<VoiceTemplate, "mission" | "greeting" | "custom_instructions">,
): string {
  return buildMarkdownFromTemplate(template);
}

/** Normalize form values into the API payload shape. */
function toPayload(form: VoiceTemplateFormState): VoiceTemplateInput {
  return {
    name: form.name.trim(),
    industry: form.industry.trim(),
    description: form.description.trim() || null,
    persona: form.persona.trim() || null,
    tone: form.tone.trim() || null,
    mission: form.mission.trim() || null,
    greeting: form.greeting.trim() || null,
    custom_instructions: form.custom_instructions.trim() || null,
    is_active: form.is_active,
  };
}

/**
 * Platform-admin use-case template catalog.
 *
 * @returns A searchable template list, Markdown preview, CRUD authoring sheet,
 * and type-to-confirm deletion flow.
 */
export function PlatformVoiceTemplatesManager() {
  const [templates, setTemplates] = useState<VoiceTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<VoiceTemplate | null>(null);
  const [editorTemplate, setEditorTemplate] = useState<VoiceTemplate | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [form, setForm] = useState<VoiceTemplateFormState>(EMPTY_FORM);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<VoiceTemplate | null>(null);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const result = await voiceTemplateService.listAdminTemplates();
      setTemplates(result);
      setSelectedTemplate((current) =>
        current ? result.find((template) => template.id === current.id) ?? null : result[0] ?? null,
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTemplates();
  }, [loadTemplates]);

  const filteredTemplates = useMemo(() => {
    const normalizedFilter = filter.trim().toLowerCase();
    if (!normalizedFilter) return templates;
    return templates.filter((template) =>
      [template.name, template.industry, template.description ?? ""].some((value) =>
        value.toLowerCase().includes(normalizedFilter),
      ),
    );
  }, [filter, templates]);

  const openCreate = () => {
    setEditorTemplate(null);
    setForm(EMPTY_FORM);
    setEditorOpen(true);
  };

  const openEdit = (template: VoiceTemplate) => {
    setEditorTemplate(template);
    setForm(toForm(template));
    setEditorOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.industry.trim()) {
      toast.error("Name and industry are required");
      return;
    }

    setSaving(true);
    try {
      const payload = toPayload(form);
      const saved = editorTemplate
        ? await voiceTemplateService.updateTemplate(editorTemplate.id, payload)
        : await voiceTemplateService.createTemplate(payload);
      setTemplates((current) =>
        editorTemplate
          ? current.map((template) => (template.id === saved.id ? saved : template))
          : [...current, saved].sort((a, b) => a.name.localeCompare(b.name)),
      );
      setSelectedTemplate(saved);
      setEditorTemplate(null);
      setEditorOpen(false);
      toast.success(editorTemplate ? "Template updated" : "Template created");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to save template");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await voiceTemplateService.deleteTemplate(deleteTarget.id);
    setTemplates((current) => current.filter((template) => template.id !== deleteTarget.id));
    if (selectedTemplate?.id === deleteTarget.id) setSelectedTemplate(null);
    setDeleteTarget(null);
    toast.success(`"${deleteTarget.name}" deleted`);
  };

  const markdown = selectedTemplate ? toMarkdown(selectedTemplate) : "";
  const isEditing = Boolean(editorTemplate);

  return (
    <div className="grid min-h-[min(720px,calc(100vh-12rem))] gap-4 lg:grid-cols-[minmax(280px,0.85fr)_minmax(0,1.5fr)]">
      <section className="flex min-h-[520px] flex-col overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="border-b bg-muted/20 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Catalog</p>
              <h2 className="mt-1 text-lg font-semibold">Use case templates</h2>
              <p className="mt-1 text-xs text-muted-foreground">{templates.length} reusable starting points</p>
            </div>
            <Button onClick={openCreate} size="sm">
              <Plus className="mr-1.5 h-4 w-4" />
              New template
            </Button>
          </div>
          <div className="relative mt-4">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              aria-label="Filter templates"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder="Filter by name or industry"
              className="h-9 pl-8"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-primary" /></div>
          ) : filteredTemplates.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-muted-foreground">No templates found.</div>
          ) : (
            filteredTemplates.map((template) => (
              <div
                key={template.id}
                className={cn(
                  "group border-b px-4 py-3.5 transition-colors hover:bg-muted/30",
                  selectedTemplate?.id === template.id && "border-l-2 border-l-primary bg-primary/[0.04] pl-[14px]",
                )}
              >
                <button
                  type="button"
                  className="w-full text-left"
                  onClick={() => setSelectedTemplate(template)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-foreground">{template.name}</p>
                      <div className="mt-1 flex items-center gap-1.5">
                        <Badge variant="secondary" className="text-[10px] capitalize">{template.industry.replace(/_/g, " ")}</Badge>
                        {!template.is_active && <Badge variant="outline" className="text-[10px]">Inactive</Badge>}
                      </div>
                    </div>
                    {template.is_active && <span className="mt-1 h-2 w-2 rounded-full bg-emerald-500" title="Available in agent pickers" />}
                  </div>
                  {template.description && <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{template.description}</p>}
                </button>
                <div className="mt-3 flex items-center gap-1.5 opacity-70 transition-opacity group-hover:opacity-100">
                  <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => openEdit(template)}>
                    <Edit3 className="mr-1 h-3.5 w-3.5" /> Edit
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="ml-auto h-7 px-2 text-xs text-destructive hover:text-destructive"
                    aria-label={`Delete ${template.name}`}
                    onClick={() => setDeleteTarget(template)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="flex min-h-[520px] flex-col overflow-hidden rounded-xl border bg-card shadow-sm">
        {selectedTemplate ? (
          <>
            <div className="border-b p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    <h2 className="text-xl font-semibold">{selectedTemplate.name}</h2>
                    <Badge variant={selectedTemplate.is_active ? "default" : "outline"}>
                      {selectedTemplate.is_active ? "Picker-ready" : "Inactive"}
                    </Badge>
                  </div>
                  <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{selectedTemplate.description || "No description yet."}</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => openEdit(selectedTemplate)}>
                  <Edit3 className="mr-1.5 h-3.5 w-3.5" /> Edit template
                </Button>
              </div>
              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
                <span><strong className="font-medium text-foreground">Industry:</strong> {selectedTemplate.industry}</span>
                <span><strong className="font-medium text-foreground">Updated:</strong> {new Date(selectedTemplate.updated_at).toLocaleDateString()}</span>
                <span className="inline-flex items-center gap-1"><Check className="h-3 w-3 text-emerald-600" /> Used by agent create/edit insertion</span>
              </div>
            </div>
            <Tabs defaultValue="rendered" className="flex min-h-0 flex-1 flex-col">
              <TabsList className="shrink-0 px-4">
                <TabsTrigger value="rendered">Rendered Markdown</TabsTrigger>
                <TabsTrigger value="source">Markdown source</TabsTrigger>
              </TabsList>
              <TabsContent value="rendered" className="min-h-0 flex-1 overflow-y-auto p-6">
                <MarkdownRenderer content={markdown} className="prose prose-sm max-w-none dark:prose-invert" />
              </TabsContent>
              <TabsContent value="source" className="min-h-0 flex-1 overflow-y-auto p-6">
                <pre className="whitespace-pre-wrap rounded-lg border bg-muted/30 p-4 font-mono text-xs leading-relaxed">{markdown}</pre>
              </TabsContent>
            </Tabs>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center p-8 text-center text-muted-foreground">
            <div>
              <FileText className="mx-auto h-10 w-10 opacity-25" />
              <p className="mt-3 text-sm">Select a template to inspect its Markdown.</p>
              <p className="mt-1 text-xs">Create or edit one to make it available in agent setup.</p>
            </div>
          </div>
        )}
      </section>

      <Sheet open={editorOpen} onOpenChange={(open) => {
        setEditorOpen(open);
        if (!open) setEditorTemplate(null);
      }}>
        <SheetContent className="flex w-full flex-col overflow-hidden sm:max-w-2xl">
          <SheetHeader className="border-b px-6 pb-4 pt-6">
            <SheetTitle>{isEditing ? "Edit use case template" : "New use case template"}</SheetTitle>
            <SheetDescription>
              Write reusable agent behavior in Markdown-capable fields. Active templates appear in agent creation and editing.
            </SheetDescription>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
            <div
              className="mb-5 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-950 dark:border-yellow-900/40 dark:bg-yellow-950/20 dark:text-yellow-100"
              role="note"
              aria-label="Template usage guidance"
            >
              <p className="font-medium text-foreground">How this template is used</p>
              <p className="mt-1 text-xs leading-relaxed text-yellow-800 dark:text-yellow-200">
                Mission, greeting, and instructions become the generated Markdown. Persona and tone populate the agent settings. Business context comes from your organization details, not from this template. Edit the fields to change the Markdown; the preview is read-only.
              </p>
            </div>
            <Tabs defaultValue="fields">
              <TabsList>
                <TabsTrigger value="fields">Template fields</TabsTrigger>
                <TabsTrigger value="preview">Markdown preview</TabsTrigger>
              </TabsList>
              <TabsContent value="fields" className="space-y-4 pt-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5"><Label htmlFor="template-name">Name</Label><Input id="template-name" aria-label="Name" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} placeholder="Dental Receptionist" /></div>
                  <div className="space-y-1.5"><Label htmlFor="template-industry">Industry</Label><Input id="template-industry" aria-label="Industry" value={form.industry} onChange={(event) => setForm((current) => ({ ...current, industry: event.target.value }))} placeholder="dental" /></div>
                </div>
                <div className="space-y-1.5"><Label htmlFor="template-description">Description</Label><Input id="template-description" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="Short description for the template picker" /></div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-1.5"><Label htmlFor="template-persona">Persona</Label><Textarea id="template-persona" value={form.persona} onChange={(event) => setForm((current) => ({ ...current, persona: event.target.value }))} placeholder="You are a helpful receptionist..." className="min-h-28" /></div>
                  <div className="space-y-1.5"><Label htmlFor="template-tone">Tone</Label><Textarea id="template-tone" value={form.tone} onChange={(event) => setForm((current) => ({ ...current, tone: event.target.value }))} placeholder="warm, professional" className="min-h-28" /></div>
                </div>
                <div className="space-y-1.5"><Label htmlFor="template-mission">Mission</Label><Textarea id="template-mission" value={form.mission} onChange={(event) => setForm((current) => ({ ...current, mission: event.target.value }))} placeholder="What should this agent help callers accomplish?" className="min-h-24" /></div>
                <div className="space-y-1.5"><Label htmlFor="template-greeting">Greeting</Label><Textarea id="template-greeting" value={form.greeting} onChange={(event) => setForm((current) => ({ ...current, greeting: event.target.value }))} placeholder="Thank you for calling [Business Name]!" className="min-h-20" /></div>
                <div className="space-y-1.5"><Label htmlFor="template-instructions">Instructions</Label><Textarea id="template-instructions" aria-label="Instructions" value={form.custom_instructions} onChange={(event) => setForm((current) => ({ ...current, custom_instructions: event.target.value }))} placeholder="Use Markdown for instructions, lists, and escalation rules." className="min-h-40 font-mono text-sm" /></div>
                <label className="flex items-start gap-3 rounded-lg border bg-muted/20 p-3 text-sm">
                  <input type="checkbox" checked={form.is_active} onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))} className="mt-0.5 h-4 w-4 accent-primary" />
                  <span><span className="font-medium">Available in agent pickers</span><span className="mt-0.5 block text-xs text-muted-foreground">Turn this off to keep the template in the admin catalog without showing it during agent setup.</span></span>
                </label>
              </TabsContent>
              <TabsContent value="preview" className="space-y-4 pt-5">
                <div className="rounded-lg border bg-muted/20 p-4"><MarkdownRenderer content={toMarkdown(form)} className="prose prose-sm max-w-none dark:prose-invert" /></div>
                <details className="rounded-lg border bg-muted/20 p-4"><summary className="cursor-pointer text-sm font-medium">View Markdown source</summary><pre className="mt-3 whitespace-pre-wrap font-mono text-xs leading-relaxed">{toMarkdown(form)}</pre></details>
              </TabsContent>
            </Tabs>
          </div>
          <SheetFooter className="shrink-0 gap-2 border-t px-6 py-4">
            <Button variant="outline" onClick={() => { setEditorOpen(false); setEditorTemplate(null); }} disabled={saving}>Cancel</Button>
            <Button onClick={() => void handleSave()} disabled={saving || !form.name.trim() || !form.industry.trim()}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Check className="mr-2 h-4 w-4" />}
              {isEditing ? "Save changes" : "Create template"}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <DeleteConfirmationDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        itemName={deleteTarget?.name ?? ""}
        itemType="Use Case Template"
        warnings={["This removes the template from the platform catalog.", "Agents already using inserted instructions are not changed."]}
        onDelete={handleDelete}
      />
    </div>
  );
}
