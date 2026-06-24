"use client";

/**
 * Shared master-detail skill editor used by both the organization skills tab
 * (mode="organization") and the platform skills admin page (mode="platform").
 *
 * Layout: left panel = skill list with an expandable per-skill file tree; right
 * panel = skill/file view + inline edit. All data access is delegated to an
 * `adapter` so the same UI works against org-level or platform-level services.
 * Mode + feature flags hide org-only concepts (fork/refresh, Platform/Custom
 * badge, visibility toggle, "from platform library") on the platform page.
 *
 * @example
 * ```tsx
 * // Platform admin page
 * <SkillEditor mode="platform" adapter={platformAdapter} canCreate canEdit />
 *
 * // Organization skills tab
 * <SkillEditor
 *   mode="organization"
 *   adapter={orgAdapter}
 *   canCreate={isOrgAdmin || isPlatformAdmin}
 *   canEdit={isOrgAdmin || isPlatformAdmin}
 *   showSourceBadge
 *   showVisibilityToggle
 *   showRefresh
 *   showImportFromPlatformLibrary
 *   onForkPlatformSkill={...}
 * />
 * ```
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Archive,
  ChevronDown,
  ChevronRight,
  Edit3,
  Eye,
  EyeOff,
  FileText,
  FolderOpen,
  GitFork,
  Import,
  Library,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Search,
  RotateCcw,
  Trash2,
  Zap,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";

// ─── Unified types the editor works on ────────────────────────────────────

/** Skill shape normalized from OrganizationSkill or PlatformSkill. */
export interface EditableSkill {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  content: string;
  version: string | null;
  author?: string | null;
  /** Platform-skill lifecycle status (draft/active/deprecated/deleted). */
  status?: "draft" | "active" | "deprecated" | "deleted";
  is_visible?: boolean; // org only
  source_skill_id?: string | null; // org only (forked from platform)
  source_version?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EditableFileSummary {
  id: string;
  file_path: string;
  file_kind: string;
}

export interface SkillCreateInput {
  slug: string;
  name: string;
  description?: string | null;
  content: string;
}

export interface SkillUpdatePatch {
  name?: string;
  description?: string | null;
  content?: string;
  is_visible?: boolean;
}

export interface FileWriteInput {
  file_path: string;
  content: string;
  file_kind: string;
}

export interface CheckUpdateInfo {
  update_available: boolean;
  latest_version: string;
  current_version: string | null;
}

/**
 * Data-access adapter. The editor is agnostic to org vs platform; the page
 * supplies the concrete service calls.
 */
export interface SkillEditorAdapter {
  loadSkills(includeDeleted?: boolean): Promise<EditableSkill[]>;
  loadFiles(skillId: string): Promise<EditableFileSummary[]>;
  getFileContent(skill: EditableSkill, file: EditableFileSummary): Promise<string>;
  createSkill(input: SkillCreateInput): Promise<EditableSkill>;
  updateSkill(skillId: string, patch: SkillUpdatePatch): Promise<EditableSkill>;
  createFile(skillId: string, input: FileWriteInput): Promise<void>;
  updateFile(skillId: string, file: EditableFileSummary, input: FileWriteInput): Promise<void>;
  deleteFile(skillId: string, file: EditableFileSummary): Promise<void>;
  importFromUrl?(url: string): Promise<EditableSkill[]>;
  // org-only:
  checkUpdate?(skillId: string): Promise<CheckUpdateInfo>;
  refresh?(skillId: string): Promise<EditableSkill>;
  forkPlatformSkill?(platformSkillId: string): Promise<EditableSkill>;
  loadPlatformSkillsForFork?(): Promise<{ id: string; name: string; slug: string; description: string | null }[]>;
  /**
   * Hydrate a skill with its full content. Called lazily when a skill is
   * selected and its `content` is empty (e.g. list endpoints that return
   * summaries without content, like platform skills). Implementations that
   * already return content in loadSkills() can omit this.
   */
  hydrateSkill?(skill: EditableSkill): Promise<EditableSkill>;
  // delete + restore:
  deleteSkill?(skillId: string): Promise<void>;
  restoreSkill?(skillId: string): Promise<void>;
  // platform-only: status transitions (deprecate/reactivate)
  deprecateSkill?(skillId: string): Promise<void>;
  reactivateSkill?(skillId: string): Promise<void>;
  // org-only (hard delete pre-check):
  getAgentsUsingSkill?(skillId: string): Promise<{ id: string; name: string; is_active: boolean }[]>;
}

export interface SkillEditorProps {
  mode: "organization" | "platform";
  adapter: SkillEditorAdapter;
  canCreate: boolean;
  canEdit: boolean;
  /** Show the per-skill delete (trash) action. Org: hard delete + agents-using check. Platform: soft delete + restore. */
  canDelete?: boolean;
  /** Delete behavior: "hard" (org — permanent, with agents-using check) | "soft" (platform — hide + restorable). */
  deleteMode?: "hard" | "soft";
  /** Show a "Show deleted" toggle to reveal soft-deleted skills and restore them (platform). */
  showDeletedFilter?: boolean;
  /** org: show Platform/Custom badge + source version. */
  showSourceBadge?: boolean;
  /** org: show the library visibility (is_visible) eye toggle. */
  showVisibilityToggle?: boolean;
  /** org: show "Check Update" / "Refresh" for forked skills. */
  showRefresh?: boolean;
  /** org: show "Create from Platform Library" in the Add menu + its sheet. */
  showImportFromPlatformLibrary?: boolean;
  /** Optional URL sync callback (page owns the URL shape). */
  syncUrl?(state: { slug: string | null; filePath: string | null }): void;
  /** Initial selection restored from URL params. */
  initialSelection?: { slug?: string; filePath?: string | null };
  emptyHint?: string;
  /** Height fill; the editor fills its parent's height. */
  className?: string;
}

const FILE_KINDS = ["reference", "script", "asset", "other"] as const;

type SelectedFile = { skillId: string; filePath: string; content?: string } | null;

/**
 * Resolve the list of available row-level actions for a skill based on its
 * current ``status`` and the adapter's capabilities.
 *
 * The action set follows the same state machine as the backend
 * (``shared.voice_agents.skill_models.PlatformSkillStatus``):
 *
 *     active    → deprecate, delete
 *     deprecated→ reactivate, delete
 *     draft     → delete             (publish arrives later)
 *     deleted   → restore
 *
 * Returning an array instead of a single chained ternary means all valid
 * transitions render side-by-side. Previously a deprecated skill showed
 * only "reactivate" because the chained ternary hit the deprecated branch
 * first and never reached the delete fallback — that was the bug.
 */
function availableActions(
  skill: EditableSkill,
  deleteMode: "hard" | "soft",
  adapter: SkillEditorAdapter,
): Array<{
  id: "restore" | "deprecate" | "reactivate" | "delete";
  title: string;
  icon: typeof RotateCcw;
  iconClass: string;
}> {
  const actions: Array<{
    id: "restore" | "deprecate" | "reactivate" | "delete";
    title: string;
    icon: typeof RotateCcw;
    iconClass: string;
  }> = [];

  const status = skill.status ?? "active";

  if (status === "deleted") {
    // Trash bin: restore is the only meaningful action.
    if (deleteMode === "soft" && adapter.restoreSkill) {
      actions.push({
        id: "restore",
        title: "Restore skill",
        icon: RotateCcw,
        iconClass: "text-muted-foreground hover:text-foreground",
      });
    }
    return actions;
  }

  // Non-deleted states: each row gets the relevant status transitions +
  // delete (where the org adapter supports it). Draft has no transitions
  // today — when we add a publish endpoint we'll slot it in here.
  if (status === "active" && adapter.deprecateSkill) {
    actions.push({
      id: "deprecate",
      title: "Deprecate skill",
      icon: Archive,
      iconClass: "text-amber-400 hover:text-amber-600",
    });
  }
  if (status === "deprecated" && adapter.reactivateSkill) {
    actions.push({
      id: "reactivate",
      title: "Reactivate skill",
      icon: RotateCcw,
      iconClass: "text-emerald-400 hover:text-emerald-600",
    });
  }
  // Delete is available on every non-deleted state when the adapter
  // supports it. Soft-delete (platform) and hard-delete (org) both flow
  // through the same adapter.deleteSkill; the deleteMode prop on the
  // editor controls the confirm dialog copy + behavior.
  if (adapter.deleteSkill) {
    actions.push({
      id: "delete",
      title: "Delete skill",
      icon: Trash2,
      iconClass: "text-red-400 hover:text-red-600",
    });
  }

  return actions;
}

export function SkillEditor({
  mode,
  adapter,
  canCreate,
  canEdit,
  canDelete = false,
  deleteMode = "hard",
  showDeletedFilter = false,
  showSourceBadge = false,
  showVisibilityToggle = false,
  showRefresh = false,
  showImportFromPlatformLibrary = false,
  syncUrl,
  initialSelection,
  emptyHint = "Select a skill to view its content",
  className,
}: SkillEditorProps) {
  const [skills, setSkills] = useState<EditableSkill[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  const [selectedSkill, setSelectedSkill] = useState<EditableSkill | null>(null);
  const [selectedFile, setSelectedFile] = useState<SelectedFile>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [filesCache, setFilesCache] = useState<Record<string, EditableFileSummary[]>>({});
  const [loadingFileContent, setLoadingFileContent] = useState(false);

  // editing
  const [editingSkill, setEditingSkill] = useState(false);
  const [editSkillData, setEditSkillData] = useState({ name: "", description: "", content: "" });
  const [savingSkill, setSavingSkill] = useState(false);

  const [editingFile, setEditingFile] = useState(false);
  const [editFileData, setEditFileData] = useState({ filePath: "", content: "", fileId: "" });
  const [savingFile, setSavingFile] = useState(false);

  const [addingFile, setAddingFile] = useState(false);
  const [newFile, setNewFile] = useState<FileWriteInput>({ file_path: "", content: "", file_kind: "reference" });
  const [creatingFile, setCreatingFile] = useState(false);

  // delete / restore skill
  const [deleteTarget, setDeleteTarget] = useState<EditableSkill | null>(null);
  const [deleteAgents, setDeleteAgents] = useState<{ id: string; name: string; is_active: boolean }[]>([]);
  const [deletingSkill, setDeletingSkill] = useState(false);
  // platform soft-delete: "show deleted" filter + restore
  const [showDeleted, setShowDeleted] = useState(false);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  // create dialog
  const [createOpen, setCreateOpen] = useState(false);
  const [newSkill, setNewSkill] = useState<SkillCreateInput>({ slug: "", name: "", description: "", content: "" });
  const [creatingSkill, setCreatingSkill] = useState(false);

  // import sheet
  const [importOpen, setImportOpen] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const [importing, setImporting] = useState(false);

  // platform library (org only)
  const [browsePlatformOpen, setBrowsePlatformOpen] = useState(false);
  const [platformSkills, setPlatformSkills] = useState<{ id: string; name: string; slug: string; description: string | null }[]>([]);
  const [loadingPlatform, setLoadingPlatform] = useState(false);
  const [forkingSkillId, setForkingSkillId] = useState<string | null>(null);

  // refresh (org only)
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [refreshInfo, setRefreshInfo] = useState<CheckUpdateInfo | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const list = await adapter.loadSkills(showDeleted);
      setSkills(list);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }, [adapter, showDeleted]);

  useEffect(() => {
    reload();
  }, [reload]);

  const ensureFiles = useCallback(
    async (skillId: string) => {
      if (filesCache[skillId]) return filesCache[skillId];
      try {
        const files = await adapter.loadFiles(skillId);
        setFilesCache((prev) => ({ ...prev, [skillId]: files }));
        return files;
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to load files");
        return [];
      }
    },
    [adapter, filesCache],
  );

  /**
   * Lazily fetch a skill's full content when the list endpoint returns
   * summaries without content (platform skills). No-op when content is present.
   */
  const ensureContent = useCallback(
    async (skill: EditableSkill): Promise<EditableSkill> => {
      if (skill.content && skill.content.length > 0) return skill;
      if (!adapter.hydrateSkill) return skill;
      try {
        const full = await adapter.hydrateSkill(skill);
        setSkills((prev) => prev.map((s) => (s.id === full.id ? { ...s, content: full.content } : s)));
        return full;
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to load skill content");
        return skill;
      }
    },
    [adapter],
  );

  // Restore initial selection from URL ONCE, after skills first load. After
  // that the URL is write-only (selection -> URL via syncUrl); this effect must
  // not re-run on every URL/skills change or it clobbers the user's selection
  // (and races with lazy content hydration, causing the body to blank out).
  const restoredRef = useRef(false);
  useEffect(() => {
    if (restoredRef.current) return;
    if (skills.length === 0 || !initialSelection?.slug) return;
    restoredRef.current = true;
    const skill = skills.find((s) => s.slug === initialSelection.slug);
    if (skill) {
      setSelectedSkill(skill);
      setExpanded(new Set([skill.id]));
      ensureFiles(skill.id);
      // Lazily hydrate content for the restored selection too.
      ensureContent(skill).then((full) => setSelectedSkill(full));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skills, initialSelection]);

  const pushUrl = useCallback(
    (slug: string | null, filePath: string | null = null) => {
      syncUrl?.({ slug, filePath });
    },
    [syncUrl],
  );

  const selectSkill = useCallback(
    (skill: EditableSkill) => {
      setSelectedSkill(skill);
      setSelectedFile(null);
      setEditingSkill(false);
      setEditingFile(false);
      setExpanded((prev) => {
        const next = new Set(prev);
        if (next.has(skill.id)) next.delete(skill.id);
        else next.add(skill.id);
        return next;
      });
      ensureFiles(skill.id);
      pushUrl(skill.slug);
      // Lazily fetch full content if the list only returned a summary.
      ensureContent(skill).then((full) => setSelectedSkill(full));
    },
    [ensureContent, ensureFiles, pushUrl],
  );

  const selectEntry = useCallback(
    (skill: EditableSkill) => {
      setSelectedSkill(skill);
      setSelectedFile(null);
      setEditingSkill(false);
      setEditingFile(false);
      pushUrl(skill.slug);
      ensureContent(skill).then((full) => setSelectedSkill(full));
    },
    [ensureContent, pushUrl],
  );

  const selectFile = useCallback(
    async (skill: EditableSkill, file: EditableFileSummary) => {
      setSelectedSkill(skill);
      setSelectedFile({ skillId: skill.id, filePath: file.file_path });
      setEditingSkill(false);
      setEditingFile(false);
      pushUrl(skill.slug, file.file_path);
      setLoadingFileContent(true);
      try {
        const content = await adapter.getFileContent(skill, file);
        setSelectedFile({ skillId: skill.id, filePath: file.file_path, content });
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Failed to load file content");
      } finally {
        setLoadingFileContent(false);
      }
    },
    [adapter, pushUrl],
  );

  // ─── delete skill ───
  const requestDelete = async (skill: EditableSkill) => {
    setDeleteTarget(skill);
    setDeleteAgents([]);
    // Hard delete (org) pre-checks agents using the skill; soft delete (platform) does not.
    if (deleteMode === "hard" && adapter.getAgentsUsingSkill) {
      try {
        setDeleteAgents(await adapter.getAgentsUsingSkill(skill.id));
      } catch {
        setDeleteAgents([]);
      }
    }
  };

  const requestRestore = async (skill: EditableSkill) => {
    if (!adapter.restoreSkill) return;
    setRestoringId(skill.id);
    try {
      await adapter.restoreSkill(skill.id);
      toast.success(`Skill "${skill.name}" restored`);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to restore skill");
    } finally {
      setRestoringId(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget || !adapter.deleteSkill) return;
    setDeletingSkill(true);
    try {
      await adapter.deleteSkill(deleteTarget.id);
      toast.success(
        deleteMode === "soft"
          ? `Skill "${deleteTarget.name}" moved to deleted (restore via "Show deleted")`
          : `Skill "${deleteTarget.name}" deleted`,
      );
      setDeleteTarget(null);
      if (selectedSkill?.id === deleteTarget.id) {
        setSelectedSkill(null);
        setSelectedFile(null);
        pushUrl(null);
      }
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete skill");
    } finally {
      setDeletingSkill(false);
    }
  };
  const requestDeprecate = async (skill: EditableSkill) => {
    if (!adapter.deprecateSkill) return;
    try {
      await adapter.deprecateSkill(skill.id);
      toast.success(`Skill "${skill.name}" deprecated`);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to deprecate skill");
    }
  };

  const requestReactivate = async (skill: EditableSkill) => {
    if (!adapter.reactivateSkill) return;
    try {
      await adapter.reactivateSkill(skill.id);
      toast.success(`Skill "${skill.name}" reactivated`);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to reactivate skill");
    }
  };

  // ─── create ───
  const submitCreate = async () => {
    if (!newSkill.name.trim() || !newSkill.content.trim() || !newSkill.slug.trim()) {
      toast.error("Slug, name, and content are required");
      return;
    }
    setCreatingSkill(true);
    try {
      const created = await adapter.createSkill({
        slug: newSkill.slug.trim(),
        name: newSkill.name.trim(),
        description: newSkill.description?.trim() || null,
        content: newSkill.content,
      });
      toast.success("Skill created");
      setCreateOpen(false);
      setNewSkill({ slug: "", name: "", description: "", content: "" });
      await reload();
      setSelectedSkill(created);
      setExpanded(new Set([created.id]));
      ensureFiles(created.id);
      pushUrl(created.slug);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create skill");
    } finally {
      setCreatingSkill(false);
    }
  };

  // ─── import ───
  const submitImport = async () => {
    if (!importUrl.trim() || !adapter.importFromUrl) return;
    setImporting(true);
    try {
      const imported = await adapter.importFromUrl(importUrl.trim());
      const total = imported.length;
      toast.success(`Imported ${total} skill(s)`);
      setImportUrl("");
      setImportOpen(false);
      await reload();
      if (imported.length > 0) {
        setSelectedSkill(imported[0]);
        setExpanded(new Set([imported[0].id]));
        ensureFiles(imported[0].id);
        pushUrl(imported[0].slug);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  // ─── edit skill ───
  const startEditSkill = async () => {
    if (!selectedSkill) return;
    let skill = selectedSkill;
    if ((!skill.content || skill.content.length === 0) && adapter.hydrateSkill) {
      skill = await ensureContent(skill);
      setSelectedSkill(skill);
    }
    setEditSkillData({
      name: skill.name,
      description: skill.description ?? "",
      content: skill.content,
    });
    setEditingSkill(true);
    setEditingFile(false);
  };

  const submitEditSkill = async () => {
    if (!selectedSkill) return;
    setSavingSkill(true);
    try {
      const updated = await adapter.updateSkill(selectedSkill.id, {
        name: editSkillData.name,
        description: editSkillData.description || null,
        content: editSkillData.content,
      });
      toast.success("Skill updated");
      setSelectedSkill(updated);
      setEditingSkill(false);
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update skill");
    } finally {
      setSavingSkill(false);
    }
  };

  // ─── edit file ───
  const startEditFile = async () => {
    if (!selectedSkill || !selectedFile) return;
    const files = filesCache[selectedSkill.id] || [];
    const file = files.find((f) => f.file_path === selectedFile.filePath);
    if (!file) return;
    setEditFileData({ filePath: file.file_path, content: selectedFile.content ?? "", fileId: file.id });
    setEditingFile(true);
    setEditingSkill(false);
  };

  const submitEditFile = async () => {
    if (!selectedSkill || !editFileData.fileId) return;
    setSavingFile(true);
    try {
      const files = filesCache[selectedSkill.id] || [];
      const file = files.find((f) => f.id === editFileData.fileId);
      if (!file) return;
      await adapter.updateFile(selectedSkill.id, file, {
        file_path: editFileData.filePath,
        content: editFileData.content,
        file_kind: file.file_kind,
      });
      toast.success("File updated");
      setEditingFile(false);
      // refresh files + selection
      const refreshed = await adapter.loadFiles(selectedSkill.id);
      setFilesCache((prev) => ({ ...prev, [selectedSkill.id]: refreshed }));
      setSelectedFile({ skillId: selectedSkill.id, filePath: editFileData.filePath, content: editFileData.content });
      pushUrl(selectedSkill.slug, editFileData.filePath);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update file");
    } finally {
      setSavingFile(false);
    }
  };

  // ─── add file ───
  const submitAddFile = async () => {
    if (!selectedSkill) return;
    if (!newFile.file_path.trim() || !newFile.content.trim()) {
      toast.error("File path and content are required");
      return;
    }
    setCreatingFile(true);
    try {
      await adapter.createFile(selectedSkill.id, {
        file_path: newFile.file_path.trim(),
        content: newFile.content,
        file_kind: newFile.file_kind,
      });
      toast.success("File added");
      setAddingFile(false);
      setNewFile({ file_path: "", content: "", file_kind: "reference" });
      const refreshed = await adapter.loadFiles(selectedSkill.id);
      setFilesCache((prev) => ({ ...prev, [selectedSkill.id]: refreshed }));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add file");
    } finally {
      setCreatingFile(false);
    }
  };

  const filtered = useMemo(
    () =>
      skills.filter(
        (s) =>
          !filter ||
          s.name.toLowerCase().includes(filter.toLowerCase()) ||
          s.slug.toLowerCase().includes(filter.toLowerCase()) ||
          (s.description || "").toLowerCase().includes(filter.toLowerCase()),
      ),
    [skills, filter],
  );

  const isOrg = mode === "organization";

  return (
    <div className={`flex gap-4 h-full min-h-[60vh] ${className ?? ""}`}>
      {/* Left panel — skill list with expandable file tree */}
      <div className="w-80 shrink-0 flex flex-col border rounded-lg bg-card h-full overflow-hidden">
        <div className="p-3 border-b space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{skills.length} skills</span>
            {canCreate && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Plus className="h-4 w-4 mr-1" />
                    Add
                    <ChevronDown className="h-3 w-3 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {showImportFromPlatformLibrary && (
                    <DropdownMenuItem
                      onClick={async () => {
                        if (!adapter.loadPlatformSkillsForFork) return;
                        setLoadingPlatform(true);
                        setBrowsePlatformOpen(true);
                        try {
                          setPlatformSkills(await adapter.loadPlatformSkillsForFork());
                        } catch {
                          toast.error("Failed to load platform skills");
                        } finally {
                          setLoadingPlatform(false);
                        }
                      }}
                    >
                      <Library className="h-4 w-4 mr-2" />
                      Create from Platform Library
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem
                    onClick={() => {
                      setNewSkill({ slug: "", name: "", description: "", content: "" });
                      setCreateOpen(true);
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create {isOrg ? "Custom Skill" : "Skill"}
                  </DropdownMenuItem>
                  {adapter.importFromUrl && (
                    <DropdownMenuItem
                      onClick={() => {
                        setImportUrl("");
                        setImportOpen(true);
                      }}
                    >
                      <Import className="h-4 w-4 mr-2" />
                      Import from URL
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Filter skills..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="pl-8 h-8 text-sm"
            />
          </div>
          {showDeletedFilter && (
            <Button
              variant={showDeleted ? "default" : "outline"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setShowDeleted((v) => !v)}
            >
              {showDeleted ? "Hide deleted" : "Show deleted"}
            </Button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-sm text-muted-foreground">No skills found.</div>
          ) : (
            filtered.map((skill) => {
              const isExpanded = expanded.has(skill.id);
              const files = filesCache[skill.id] || [];
              return (
                <div key={skill.id}>
                  <div
                    className={`group px-3 py-2.5 cursor-pointer border-b transition-colors flex items-center gap-1.5 ${
                      selectedSkill?.id === skill.id && !selectedFile
                        ? "bg-primary/5 border-l-2 border-l-primary"
                        : "hover:bg-muted/50"
                    }`}
                    onClick={() => selectSkill(skill)}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium truncate">{skill.name}</div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        {showSourceBadge && (
                          <Badge
                            variant={skill.source_skill_id ? "secondary" : "outline"}
                            className="text-[11px] px-1.5 py-0"
                          >
                            {skill.source_skill_id ? "Platform" : "Custom"}
                          </Badge>
                        )}
                        {showSourceBadge && skill.source_version && (
                          <span className="text-[11px] text-muted-foreground">v{skill.source_version}</span>
                        )}
                        {showVisibilityToggle && !skill.is_visible && (
                          <Badge variant="outline" className="text-[11px] px-1.5 py-0 border-orange-200 text-orange-600 bg-orange-50">
                            <EyeOff className="h-3 w-3 mr-1" />Hidden
                          </Badge>
                        )}
                        {skill.status === "deleted" && (
                          <Badge variant="secondary" className="text-[11px] px-1.5 py-0">Deleted</Badge>
                        )}
                        {skill.status === "deprecated" && (
                          <Badge variant="outline" className="text-[11px] px-1.5 py-0 border-amber-200 text-amber-700 bg-amber-50">
                            Deprecated
                          </Badge>
                        )}
                        {skill.status === "draft" && (
                          <Badge variant="outline" className="text-[11px] px-1.5 py-0 border-slate-200 text-slate-600 bg-slate-50">
                            Draft
                          </Badge>
                        )}
                      </div>
                    </div>
                    {availableActions(skill, deleteMode, adapter).map((action) => (
                      <button
                        key={action.id}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded hover:bg-muted"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (action.id === "restore") requestRestore(skill);
                          else if (action.id === "deprecate") requestDeprecate(skill);
                          else if (action.id === "reactivate") requestReactivate(skill);
                          else if (action.id === "delete") requestDelete(skill);
                        }}
                        disabled={restoringId === skill.id}
                        title={action.title}
                      >
                        {restoringId === skill.id && action.id === "restore" ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                        ) : (
                          <action.icon className={`h-3.5 w-3.5 ${action.iconClass}`} />
                        )}
                      </button>
                    ))}
                  </div>
                  {isExpanded && (
                    <div className="border-b bg-muted/20">
                      <div
                        className={`pl-10 pr-3 py-1.5 cursor-pointer text-sm flex items-center gap-1.5 transition-colors ${
                          selectedSkill?.id === skill.id && !selectedFile
                            ? "bg-primary/10 text-primary font-medium"
                            : "hover:bg-muted/50 text-muted-foreground"
                        }`}
                        onClick={() => selectEntry(skill)}
                      >
                        <FileText className="h-3 w-3 shrink-0" />
                        <span className="truncate">SKILL.md</span>
                        <Badge variant="outline" className="text-[10px] px-1 py-0 ml-auto">ENTRY</Badge>
                      </div>
                      {files.length > 0 &&
                        (() => {
                          const folders: Record<string, EditableFileSummary[]> = {};
                          const rootFiles: EditableFileSummary[] = [];
                          files.forEach((f) => {
                            const parts = f.file_path.split("/");
                            if (parts.length > 1) {
                              const folder = parts[0];
                              (folders[folder] ||= []).push(f);
                            } else {
                              rootFiles.push(f);
                            }
                          });
                          const fileRow = (f: EditableFileSummary, indent: string) => (
                            <div
                              key={f.id}
                              className={`${indent} pr-3 py-1.5 cursor-pointer text-sm flex items-center gap-1.5 transition-colors ${
                                selectedFile?.filePath === f.file_path && selectedSkill?.id === skill.id
                                  ? "bg-primary/10 text-primary font-medium"
                                  : "hover:bg-muted/50 text-muted-foreground"
                              }`}
                              onClick={() => selectFile(skill, f)}
                            >
                              <FileText className="h-3 w-3 shrink-0" />
                              <span className="truncate">{f.file_path.split("/").pop()}</span>
                            </div>
                          );
                          return (
                            <>
                              {Object.entries(folders).map(([folder, folderFiles]) => (
                                <div key={folder}>
                                  <div className="pl-10 pr-3 py-1.5 text-sm text-muted-foreground font-medium flex items-center gap-1.5">
                                    <FolderOpen className="h-3 w-3" />
                                    {folder}
                                  </div>
                                  {folderFiles.map((f) => fileRow(f, "pl-14"))}
                                </div>
                              ))}
                              {rootFiles.map((f) => fileRow(f, "pl-10"))}
                            </>
                          );
                        })()}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right panel — skill content */}
      <div className="flex-1 border rounded-lg bg-card flex flex-col min-w-0 h-full overflow-hidden">
        {selectedSkill ? (
          <>
            <div className="p-4 border-b">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-lg">{selectedSkill.name}</h3>
                  {showSourceBadge && (
                    <Badge variant={selectedSkill.source_skill_id ? "secondary" : "outline"} className="text-xs">
                      {selectedSkill.source_skill_id ? "Platform" : "Custom"}
                    </Badge>
                  )}
                  {showVisibilityToggle && !selectedSkill.is_visible && (
                    <Badge variant="outline" className="text-xs border-orange-200 text-orange-600 bg-orange-50">
                      <EyeOff className="h-3 w-3 mr-1" /> Hidden
                    </Badge>
                  )}
                </div>
                {canEdit && !editingSkill && !editingFile && (
                  <div className="flex items-center gap-1.5">
                    {!selectedFile && (
                      <Button variant="outline" size="sm" onClick={startEditSkill}>
                        <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                      </Button>
                    )}
                    {selectedFile?.content !== undefined && selectedFile?.skillId === selectedSkill.id && (
                      <Button variant="outline" size="sm" onClick={startEditFile}>
                        <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                      </Button>
                    )}
                    {!selectedFile && (
                      <Button variant="outline" size="sm" onClick={() => { setNewFile({ file_path: "", content: "", file_kind: "reference" }); setAddingFile(true); }}>
                        <Plus className="h-3.5 w-3.5 mr-1" /> Add File
                      </Button>
                    )}
                    {showVisibilityToggle && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          try {
                            const updated = await adapter.updateSkill(selectedSkill.id, {
                              is_visible: !selectedSkill.is_visible,
                            });
                            toast.success(updated.is_visible ? "Skill visible in library" : "Skill hidden from library");
                            setSelectedSkill(updated);
                            await reload();
                          } catch (err) {
                            toast.error(err instanceof Error ? err.message : "Failed to update visibility");
                          }
                        }}
                        title={selectedSkill.is_visible ? "Hide from library" : "Show in library"}
                      >
                        {selectedSkill.is_visible ? (<><Eye className="h-3.5 w-3.5 mr-1" /> Hide</>) : (<><EyeOff className="h-3.5 w-3.5 mr-1" /> Show</>)}
                      </Button>
                    )}
                    {showRefresh && selectedSkill.source_skill_id && adapter.checkUpdate && adapter.refresh && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          if (!adapter.checkUpdate) return;
                          setCheckingUpdate(true);
                          try {
                            const info = await adapter.checkUpdate(selectedSkill.id);
                            setRefreshInfo(info);
                            if (!info.update_available) {
                              toast.success("Skill is up to date");
                            }
                          } catch (err) {
                            toast.error(err instanceof Error ? err.message : "Failed to check for updates");
                          } finally {
                            setCheckingUpdate(false);
                          }
                        }}
                        disabled={checkingUpdate}
                      >
                        {checkingUpdate ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <><RefreshCw className="h-3.5 w-3.5 mr-1" /> Check Update</>}
                      </Button>
                    )}
                  </div>
                )}
              </div>
              {selectedSkill.description && !editingSkill && (
                <p className="text-sm text-muted-foreground mt-1">{selectedSkill.description}</p>
              )}
              <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                {selectedSkill.author && <span><strong>Author:</strong> {selectedSkill.author}</span>}
                {selectedSkill.version && <span><strong>Version:</strong> {selectedSkill.version}</span>}
                {showSourceBadge && selectedSkill.source_version && <span><strong>Source:</strong> v{selectedSkill.source_version}</span>}
                <span><strong>Slug:</strong> <code className="text-xs bg-muted px-1 py-0.5 rounded">{selectedSkill.slug}</code></span>
              </div>
            </div>

            {editingSkill ? (
              <>
                <div className="px-4 py-2 border-b bg-muted/30 text-xs text-muted-foreground">Editing SKILL.md</div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="se-edit-name">Skill Name</Label>
                    <Input id="se-edit-name" value={editSkillData.name} onChange={(e) => setEditSkillData((d) => ({ ...d, name: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="se-edit-desc">Description</Label>
                    <Input id="se-edit-desc" value={editSkillData.description} onChange={(e) => setEditSkillData((d) => ({ ...d, description: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="se-edit-content">Skill Content (Markdown)</Label>
                    <Textarea id="se-edit-content" value={editSkillData.content} onChange={(e) => setEditSkillData((d) => ({ ...d, content: e.target.value }))} className="min-h-[300px] font-mono text-sm" />
                  </div>
                </div>
                <div className="p-4 border-t flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setEditingSkill(false)}>Cancel</Button>
                  <Button disabled={savingSkill || !editSkillData.name || !editSkillData.content} onClick={submitEditSkill}>
                    {savingSkill ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />} Save Changes
                  </Button>
                </div>
              </>
            ) : editingFile ? (
              <>
                <div className="px-4 py-2 border-b bg-muted/30 text-xs text-muted-foreground">Editing file</div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="se-edit-file-path">File Path</Label>
                    <Input id="se-edit-file-path" value={editFileData.filePath} onChange={(e) => setEditFileData((d) => ({ ...d, filePath: e.target.value }))} className="font-mono text-sm" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="se-edit-file-content">Content</Label>
                    <Textarea id="se-edit-file-content" value={editFileData.content} onChange={(e) => setEditFileData((d) => ({ ...d, content: e.target.value }))} className="min-h-[300px] font-mono text-sm" />
                  </div>
                </div>
                <div className="p-4 border-t flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setEditingFile(false)}>Cancel</Button>
                  <Button disabled={savingFile || !editFileData.filePath.trim() || !editFileData.content.trim()} onClick={submitEditFile}>
                    {savingFile ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />} Save Changes
                  </Button>
                </div>
              </>
            ) : addingFile ? (
              <>
                <div className="px-4 py-2 border-b bg-muted/30 text-xs text-muted-foreground">Adding reference file</div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="se-new-file-path">File Path</Label>
                      <Input id="se-new-file-path" value={newFile.file_path} onChange={(e) => setNewFile((f) => ({ ...f, file_path: e.target.value }))} placeholder="references/faqs.md" className="font-mono text-sm" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="se-new-file-kind">Kind</Label>
                      <select id="se-new-file-kind" value={newFile.file_kind} onChange={(e) => setNewFile((f) => ({ ...f, file_kind: e.target.value }))} className="w-full h-9 rounded-md border bg-transparent px-3 text-sm">
                        {FILE_KINDS.map((k) => (<option key={k} value={k}>{k}</option>))}
                      </select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="se-new-file-content">Content</Label>
                    <Textarea id="se-new-file-content" value={newFile.content} onChange={(e) => setNewFile((f) => ({ ...f, content: e.target.value }))} className="min-h-[280px] font-mono text-sm" />
                  </div>
                </div>
                <div className="p-4 border-t flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setAddingFile(false)}>Cancel</Button>
                  <Button disabled={creatingFile} onClick={submitAddFile}>
                    {creatingFile ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Plus className="h-4 w-4 mr-2" />} Add File
                  </Button>
                </div>
              </>
            ) : selectedFile?.content !== undefined && selectedFile?.skillId === selectedSkill.id ? (
              <>
                <div className="px-4 py-2 border-b bg-muted/30 flex items-center text-xs text-muted-foreground">
                  <FileText className="h-3.5 w-3.5 mr-2" /><code>{selectedFile.filePath}</code>
                </div>
                {selectedFile.filePath.endsWith(".json") ? (
                  <div className="flex-1 overflow-y-auto p-5">
                    <pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">{(() => { try { return JSON.stringify(JSON.parse(selectedFile.content), null, 2); } catch { return selectedFile.content; } })()}</pre>
                  </div>
                ) : selectedFile.filePath.match(/\.(py|js|ts|sh|bash|yaml|yml|toml)$/) ? (
                  <div className="flex-1 overflow-y-auto p-5"><pre className="text-xs font-mono bg-muted/50 rounded-lg p-4 overflow-x-auto whitespace-pre">{selectedFile.content}</pre></div>
                ) : (
                  <div className="flex-1 overflow-y-auto p-5 prose prose-sm prose-slate max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedFile.content}</ReactMarkdown></div>
                )}
              </>
            ) : loadingFileContent ? (
              <div className="flex-1 flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
            ) : (
              <div className="flex-1 overflow-y-auto p-5 prose prose-sm prose-slate max-w-none"><ReactMarkdown remarkPlugins={[remarkGfm]}>{selectedSkill.content}</ReactMarkdown></div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Zap className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="text-sm">{emptyHint}</p>
            </div>
          </div>
        )}
      </div>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{isOrg ? "Create Custom Skill" : "New Platform Skill"}</DialogTitle>
            <DialogDescription>
              {isOrg
                ? "Create a custom skill for this organization. Slug must be lowercase kebab-case and unique within the org."
                : "Create a new built-in platform skill template available to all organizations. Slug must be lowercase kebab-case and globally unique. The slug is fixed after creation (used for seeding)."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="se-new-slug">Slug</Label>
                <Input id="se-new-slug" value={newSkill.slug} onChange={(e) => setNewSkill((s) => ({ ...s, slug: e.target.value }))} placeholder="appointment-booking" className="font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="se-new-name">Name</Label>
                <Input id="se-new-name" value={newSkill.name} onChange={(e) => setNewSkill((s) => ({ ...s, name: e.target.value }))} placeholder="Appointment Booking" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="se-new-desc">Description</Label>
              <Input id="se-new-desc" value={newSkill.description ?? ""} onChange={(e) => setNewSkill((s) => ({ ...s, description: e.target.value }))} placeholder="Short description for skill selection UI" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="se-new-content">Content (SKILL.md, markdown)</Label>
              <Textarea id="se-new-content" value={newSkill.content} onChange={(e) => setNewSkill((s) => ({ ...s, content: e.target.value }))} placeholder="# Skill name&#10;&#10;## When to use&#10;..." className="min-h-[280px] font-mono text-xs" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button disabled={creatingSkill} onClick={submitCreate}>
              {creatingSkill && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Create skill
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import sheet — layout matches the org skills import drawer */}
      <Sheet open={importOpen} onOpenChange={setImportOpen}>
        <SheetContent className="flex flex-col w-full sm:max-w-xl">
          <SheetHeader className="px-6 pt-6 pb-4 border-b">
            <SheetTitle className="flex items-center gap-2">
              <Import className="h-5 w-5" />
              Import Skill from URL
            </SheetTitle>
            {/* Mode-specific description (org vs platform distinction stays). */}
            <SheetDescription>
              {isOrg
                ? "Paste a GitHub repository URL or a skills.sh shorthand to import a skill into this organization's library."
                : "Paste a GitHub repository URL or a skills.sh shorthand to import a skill as a platform skill template (available to all organizations via forking)."}
            </SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="se-import-url">GitHub URL or skills.sh shorthand</Label>
              <Input
                id="se-import-url"
                placeholder="https://github.com/user/repo or skills.sh/skill-name"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                disabled={importing}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && importUrl.trim() && !importing) {
                    submitImport();
                  }
                }}
              />
              <p className="text-xs text-muted-foreground">
                Supported formats: full GitHub repo URL, a sub-path like
                <code> /tree/main/skills/my-skill</code>, or skills.sh shorthand like
                <code> skills.sh/appointment-booking</code>.
              </p>
            </div>
          </div>
          <div className="px-6 py-4 border-t flex justify-between gap-3">
            <Button variant="outline" onClick={() => setImportOpen(false)} disabled={importing}>
              Cancel
            </Button>
            <Button onClick={submitImport} disabled={!importUrl.trim() || importing}>
              {importing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Import className="h-4 w-4 mr-2" />}
              Import Skill
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Delete skill confirmation */}
      {canDelete && deleteTarget && (
        <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{deleteMode === "soft" ? "Delete skill" : `Delete skill: ${deleteTarget.name}?`}</DialogTitle>
            </DialogHeader>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {deleteMode === "soft"
                  ? `"${deleteTarget.name}" will be hidden from forking and from the default list. Existing org forks keep working. You can restore it later via "Show deleted".`
                  : "This will permanently delete this skill and all its reference files."}
              </p>
              {deleteMode === "hard" && deleteAgents.length > 0 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm font-medium text-amber-800">
                    This skill is currently used by {deleteAgents.length} agent{deleteAgents.length > 1 ? "s" : ""}:
                  </p>
                  <ul className="mt-1.5 space-y-1">
                    {deleteAgents.map((agent) => (
                      <li key={agent.id} className="text-sm text-amber-700 flex items-center gap-1.5">
                        <span>{agent.name}</span>
                        {!agent.is_active && <span className="text-xs text-amber-500">(inactive)</span>}
                      </li>
                    ))}
                  </ul>
                  <p className="text-xs text-amber-600 mt-2">
                    Deleting will automatically unassign this skill from these agents.
                  </p>
                </div>
              )}
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deletingSkill}>
                Cancel
              </Button>
              <Button variant="destructive" disabled={deletingSkill} onClick={confirmDelete}>
                {deletingSkill ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Trash2 className="h-4 w-4 mr-2" />}
                Delete Skill
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Platform library browser (org only) */}
      {showImportFromPlatformLibrary && (
        <Sheet open={browsePlatformOpen} onOpenChange={setBrowsePlatformOpen}>
          <SheetContent className="w-full sm:max-w-xl">
            <SheetHeader className="px-6 pt-6 pb-4 border-b">
              <SheetTitle className="flex items-center gap-2"><Library className="h-5 w-5" /> Platform Skill Library</SheetTitle>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
              {loadingPlatform ? (
                <div className="flex items-center py-8 justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
              ) : platformSkills.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No platform skills available.</p>
              ) : (
                platformSkills.map((ps) => (
                  <div key={ps.id} className="border rounded-lg p-4 space-y-3">
                    <h4 className="font-medium text-sm">{ps.name}</h4>
                    {ps.description && <p className="text-xs text-muted-foreground">{ps.description}</p>}
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      disabled={forkingSkillId === ps.id}
                      onClick={async () => {
                        if (!adapter.forkPlatformSkill) return;
                        setForkingSkillId(ps.id);
                        try {
                          const forked = await adapter.forkPlatformSkill(ps.id);
                          toast.success(`Forked "${ps.name}" into your library`);
                          setBrowsePlatformOpen(false);
                          await reload();
                          setSelectedSkill(forked);
                          setExpanded(new Set([forked.id]));
                          ensureFiles(forked.id);
                          pushUrl(forked.slug);
                        } catch (err) {
                          toast.error(err instanceof Error ? err.message : "Fork failed");
                        } finally {
                          setForkingSkillId(null);
                        }
                      }}
                    >
                      {forkingSkillId === ps.id ? <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" /> : <GitFork className="h-3.5 w-3.5 mr-1" />} Fork into Library
                    </Button>
                  </div>
                ))
              )}
            </div>
          </SheetContent>
        </Sheet>
      )}

      {/* Refresh confirmation (org forked skills only) */}
      {showRefresh && refreshInfo?.update_available && selectedSkill && (
        <Dialog open={!!refreshInfo} onOpenChange={(o) => !o && setRefreshInfo(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Refresh skill</DialogTitle>
              <DialogDescription>
                Refresh &quot;{selectedSkill.name}&quot; from platform v{refreshInfo.latest_version}? All content and
                reference files will be replaced; your customizations will be lost. This cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setRefreshInfo(null)}>Cancel</Button>
              <Button
                variant="destructive"
                onClick={async () => {
                  if (!adapter.refresh) return;
                  try {
                    const refreshed = await adapter.refresh(selectedSkill.id);
                    toast.success("Skill refreshed");
                    setRefreshInfo(null);
                    setSelectedSkill(refreshed);
                    setFilesCache((prev) => { const n = { ...prev }; delete n[selectedSkill.id]; return n; });
                    await ensureFiles(selectedSkill.id);
                    await reload();
                  } catch (err) {
                    toast.error(err instanceof Error ? err.message : "Refresh failed");
                  }
                }}
              >
                <RefreshCw className="h-4 w-4 mr-2" /> Refresh & overwrite
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
