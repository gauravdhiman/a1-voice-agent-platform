import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Crown,
  Loader2,
  Plus,
  Server,
  Search,
  AlertCircle,
  CheckCircle2,
  Wrench,
  Trash2,
  Upload,
} from "lucide-react";
import type {
  PlatformTool,
  DiscoveredMcpTool,
  ParsedMcpServerError,
} from "@/types/agent";
import {
  useDiscoverMcpTools,
  useParseMcpServersJson,
  useCreatePlatformTool,
  usePlatformTools,
  usePublishPlatformTool,
  useSetPlatformToolPremium,
  useUpdatePlatformTool,
} from "@/hooks/use-agent-queries";
import { agentService } from "@/services/agent-service";
import { toast } from "sonner";
import { McpToolDeleteDialog } from "@/components/tools/mcp-tool-delete-dialog";

/**
 * PlatformToolsManager — inline platform-admin surface for the global tool
 * catalog (publish lifecycle, RFC §6.6). Rendered on the dedicated
 * `/platform/tools` page (parallel to `/platform/skills`); NOT on the agent
 * Tools tab, where authoring/publishing is the wrong (global) scope.
 *
 * Despite the file name of its predecessor (`add-mcp-server-dialog`), this
 * manages EVERY platform tool (legacy code-backed tools + authored MCP
 * servers), not just MCP servers — the page heading reads "Platform tools".
 *
 * A platform admin configures a remote MCP server here, tests it against the
 * live server, then saves it as a **draft** or **publishes** it to the global
 * catalog. Once published, the server appears as a normal tool card in every
 * org user's agent tool panel, where an org admin attaches it and supplies
 * the org's own API key (the tool-config-drawer "Configure API Key" path).
 *
 * Two views share one panel (inline toggle — no Sheet/drawer):
 *  - **Configure MCP server** (internal state `view === "author"`): a
 *    structured form (auth mode, Name, URL, public Headers, `{{KEY}}`
 *    secret-header template + transient Test API key) *or* a "Paste JSON
 *    config" textarea holding a Claude Desktop / VS Code `mcpServers` blob.
 *    "Test & discover tools" previews the exposed tools in-memory before
 *    saving, substituting the Test API key into the `{{KEY}}` template for
 *    one-shot discover. "Save draft" persists `is_published=false`;
 *    "Publish" persists `is_published=true` and is GATED on a successful
 *    "Test & discover" so the discovered tool list is captured into
 *    `tool_functions_schema` — publishing without discover leaves the agent
 *    tool-config drawer empty (no tool list), so Publish stays disabled
 *    until `discoveredTools.length > 0`. On success the form resets so
 *    the admin can author another, and the manage list refetches.
 *  - **Manage existing tools** (internal state `view === "manage"`): lists
 *    the platform admin's drafts + published tools (native + MCP) with
 *    publish/unpublish, premium mark/unmark, and delete actions. MCP rows
 *    also get an **Edit** action that loads the server back into the author
 *    form (URL, public headers, description, auth mode, premium flag
 *    prefilled; secret headers stay encrypted at rest and are only replaced
 *    when the admin pastes new ones). "Save changes" PUTs the payload with
 *    the row's publish state preserved and `tool_functions_schema` untouched
 *    unless the admin re-runs "Test & discover".
 *
 * Auth/key model (RFC §6.6):
 *  - **No auth**: no secret headers; the server is called with only the public
 *    headers.
 *  - **Static API key**: the platform admin authors a secret-header *template*
 *    containing a `{{KEY}}` placeholder (e.g. `{"Authorization": "Bearer {{KEY}}"}`),
 *    encrypted at rest. At runtime the **org admin's** API key (stored in
 *    `agent_tools.sensitive_config["api_key"]` via the existing drawer) is
 *    substituted into `{{KEY}}` — never the platform admin's transient Test
 *    API key, which is used only for the in-memory discover step and is never
 *    persisted. A literal value (no `{{KEY}}`) passes through as a fixed
 *    shared header.
 *
 * Security notes:
 *  - URL + headers are validated server-side (SSRF guard + stdio rejection via
 *    POST /tools/mcp/parse and POST /tools/mcp/discover). The panel only
 *    renders the errors the backend returns; it does no client-side security.
 *  - Secret-header templates are sent as `mcp_secret_headers_input` and
 *    encrypted at rest. On edit they never round-trip to the UI; leave the
 *    field blank to keep stored secrets. "Test connection" on edit passes
 *    `tool_id` so the backend merges those stored secrets into the probe.
 *    encrypted at rest by the backend; decrypted values are never returned.
 *
 * The org-scoped custom tier is retired — every authored server is a global
 * catalog row (`organization_id = NULL`), so there is no org prop.
 *
 * Conventions match tool-config-drawer.tsx: plain useState, no react-hook-form,
 * no window.* dialogs.
 */
export interface PlatformToolsManagerProps {
  /** Initial view shown when the panel mounts. Defaults to "manage" — the
   * platform-tools page lands the admin on the tool list, not the author
   * form (the form is opt-in via the "Configure MCP server" toggle). */
  initialView?: "author" | "manage";
}

type AuthMode = "none" | "api_key";
type View = "author" | "manage";

export function PlatformToolsManager({
  initialView = "manage",
}: PlatformToolsManagerProps) {
  const [view, setView] = React.useState<View>(initialView);

  // Author form state. ``rawConfig`` holds the pasted ``mcpServers`` blob; it
  // is DISTINCT from the header fields. The two must not share state —
  // otherwise parsing overwrites the pasted blob with extracted headers.
  const [rawConfig, setRawConfig] = React.useState("");
  const [authMode, setAuthMode] = React.useState<AuthMode>("none");
  const [name, setName] = React.useState("");
  const [url, setUrl] = React.useState("");
  const [publicHeadersJson, setPublicHeadersJson] = React.useState("");
  const [secretHeadersJson, setSecretHeadersJson] = React.useState("");
  const [testApiKey, setTestApiKey] = React.useState("");
  const [description, setDescription] = React.useState("");
  // Premium flag: premium tools require the org plan to entitle the
  // ``premium_tools`` feature before an org can attach them.
  const [isPremium, setIsPremium] = React.useState(false);
  // Set while the admin is editing an EXISTING MCP tool (null = authoring new).
  const [editingTool, setEditingTool] = React.useState<PlatformTool | null>(
    null,
  );

  // Parse / discover results
  const [discoveredTools, setDiscoveredTools] = React.useState<
    DiscoveredMcpTool[]
  >([]);
  const [parseErrors, setParseErrors] = React.useState<ParsedMcpServerError[]>(
    [],
  );
  const [inlineError, setInlineError] = React.useState<string | null>(null);
  // The MCP tool pending a type-to-confirm delete (null while the delete dialog
  // is closed). Native/legacy tools never set this — they have no Delete button.
  const [deleteTarget, setDeleteTarget] = React.useState<PlatformTool | null>(
    null,
  );

  const discoverMutation = useDiscoverMcpTools();
  const parseMutation = useParseMcpServersJson();
  const createMutation = useCreatePlatformTool();
  const publishMutation = usePublishPlatformTool();
  const premiumMutation = useSetPlatformToolPremium();
  const updateMutation = useUpdatePlatformTool();
  // Platform-admin-only surface: list drafts + published for the manage view.
  const { data: platformTools = [] } = usePlatformTools(false, {
    includeDrafts: true,
  });

  // Clear every author-form field so the admin can author another server after
  // a successful save (the dialog predecessor closed itself on save; an inline
  // panel has no dialog to close, so it resets instead).
  const resetForm = React.useCallback(() => {
    setRawConfig("");
    setAuthMode("none");
    setName("");
    setUrl("");
    setPublicHeadersJson("");
    setSecretHeadersJson("");
    setTestApiKey("");
    setDescription("");
    setIsPremium(false);
    setDiscoveredTools([]);
    setParseErrors([]);
    setInlineError(null);
  }, []);

  const parseHeaders = (
    raw: string,
  ): { headers: Record<string, string> | null; error: string | null } => {
    const trimmed = raw.trim();
    if (!trimmed) return { headers: null, error: null };
    try {
      const parsed = JSON.parse(trimmed);
      if (
        parsed === null ||
        typeof parsed !== "object" ||
        Array.isArray(parsed)
      ) {
        return { headers: null, error: "Headers must be a JSON object." };
      }
      const headers: Record<string, string> = {};
      for (const [k, v] of Object.entries(parsed as Record<string, unknown>)) {
        headers[String(k)] = String(v);
      }
      return { headers, error: null };
    } catch {
      return { headers: null, error: "Headers JSON is malformed." };
    }
  };

  /**
   * Build the headers to send on the one-shot discover call: public headers
   * merged with the secret-header template, substituting the transient Test
   * API key into every `{{KEY}}` placeholder. The Test API key is NEVER
   * persisted — it is used only for this in-memory discovery step.
   */
  const buildDiscoverHeaders = (): {
    headers: Record<string, string>;
    error: string | null;
  } => {
    const { headers: publicHeaders, error: pubErr } =
      parseHeaders(publicHeadersJson);
    if (pubErr) return { headers: {}, error: pubErr };
    const headers: Record<string, string> = { ...(publicHeaders || {}) };
    if (authMode === "api_key") {
      const { headers: secretHeaders, error: secErr } =
        parseHeaders(secretHeadersJson);
      if (secErr) return { headers: {}, error: secErr };
      if (secretHeaders) {
        for (const [k, v] of Object.entries(secretHeaders)) {
          headers[k] = v.replace(/\{\{KEY\}\}/g, testApiKey);
        }
      }
    }
    return { headers, error: null };
  };

  const handleParseConfig = async () => {
    setInlineError(null);
    setParseErrors([]);
    const trimmed = rawConfig.trim();
    if (!trimmed) {
      setInlineError("Paste an mcpServers JSON config first.");
      return;
    }
    try {
      const result = await parseMutation.mutateAsync(trimmed);
      setParseErrors(result.errors || []);
      if (result.servers && result.servers.length > 0) {
        // Autofill the form from the first valid server. If the user pasted
        // multiple servers, only the first is used (v1) — surface a note via
        // the errors channel so it isn't silent.
        const first = result.servers[0];
        setName(first.name || name);
        setUrl(first.url);
        setPublicHeadersJson(
          first.headers && Object.keys(first.headers).length > 0
            ? JSON.stringify(first.headers, null, 2)
            : "",
        );
        if (result.servers.length > 1) {
          setParseErrors((prev) => [
            ...prev,
            {
              name: "",
              message: `Multiple servers found in config; using "${first.name}". Only one server per config is supported in v1.`,
            },
          ]);
        }
      } else if (!result.errors || result.errors.length === 0) {
        setInlineError("No valid HTTP servers found in the config.");
      }
    } catch (e) {
      setInlineError(
        e instanceof Error ? e.message : "Failed to parse MCP config.",
      );
    }
  };

  const handleDiscover = async () => {
    setInlineError(null);
    setDiscoveredTools([]);
    if (!url.trim()) {
      setInlineError("Enter a server URL first.");
      return;
    }
    if (
      authMode === "api_key" &&
      secretHeadersJson.includes("{{KEY}}") &&
      !testApiKey.trim()
    ) {
      setInlineError("Enter a Test API key to substitute into {{KEY}}.");
      return;
    }
    // Secret-header templates overwrite public headers with the same key. If the
    // admin already put Authorization in Public headers, api_key mode without a
    // test key would silently replace it with "Bearer " (empty).
    if (
      authMode === "api_key" &&
      secretHeadersJson.trim() &&
      publicHeadersJson.toLowerCase().includes('"authorization"') &&
      !testApiKey.trim()
    ) {
      setInlineError(
        "Static API key mode is enabled but Test API key is empty — it will overwrite Authorization from Public headers. Either enter a Test API key, switch Authentication to 'No auth', or clear the secret header template.",
      );
      return;
    }
    const { headers, error } = buildDiscoverHeaders();
    if (error) {
      setInlineError(error);
      return;
    }
    try {
      const tools = await discoverMutation.mutateAsync({
        url: url.trim(),
        headers: Object.keys(headers).length > 0 ? headers : undefined,
        // Re-test on edit: backend decrypts stored secrets so the admin does
        // not have to re-paste them. Typed secret JSON still overrides.
        ...(editingTool
          ? {
              tool_id: editingTool.id,
              ...(testApiKey.trim()
                ? { test_api_key: testApiKey.trim() }
                : {}),
            }
          : {}),
      });
      setDiscoveredTools(tools);
      if (tools.length === 0) {
        setInlineError("Server connected but exposes no tools.");
      }
    } catch (e) {
      setInlineError(
        e instanceof Error ? e.message : "Failed to discover MCP tools.",
      );
    }
  };

  const buildSavePayload = (isPublished: boolean): Record<string, unknown> => {
    const { headers: publicHeaders, error: pubErr } =
      parseHeaders(publicHeadersJson);
    if (pubErr) throw new Error(pubErr);
    let secretHeaders: Record<string, string> | null = null;
    if (authMode === "api_key") {
      const { headers, error } = parseHeaders(secretHeadersJson);
      if (error) throw new Error(error);
      secretHeaders = headers;
    }
    return {
      name: name.trim(),
      description: description.trim() ? description.trim() : null,
      tool_source: "mcp",
      mcp_server_url: url.trim(),
      mcp_server_name: name.trim(),
      // Non-secret static headers (plaintext JSONB). Empty form → {} so a
      // clear persists (null would be dropped by the backend exclude_none dump).
      mcp_server_headers: publicHeaders ?? {},
      // Secret-header template (may contain {{KEY}}); encrypted at rest by the
      // backend. Omit when blank on edit so stored secrets are preserved;
      // send null/absent when auth is off so the backend can clear them.
      ...(authMode === "api_key"
        ? secretHeaders
          ? { mcp_secret_headers_input: secretHeaders }
          : {}
        : {}),
      is_active: true,
      requires_auth: authMode === "api_key",
      auth_type: authMode === "api_key" ? "api_key" : null,
      is_premium: isPremium,
      is_published: isPublished,
      // Persist the discovered tool list so the agent tool-config drawer can
      // render each tool with an enable/disable toggle (parity with native tool
      // cards). The worker re-discovers tools LIVE at call time via tools/list
      // and filters by agent_tools.unselected_functions, so these stored
      // schemas are display-only — but they must be present for the drawer to
      // show anything. Omitted when no tools were discovered (the drawer then
      // shows no list, same as the pre-fix behaviour).
      ...(discoveredTools.length > 0
        ? {
            tool_functions_schema: {
              functions: discoveredTools.map((t) => ({
                name: t.name,
                description: t.description,
                // The MCP server's inputSchema becomes the function's parameter
                // schema — matches the shape tool-config-drawer.tsx renders
                // (func.parameters.properties / .required).
                parameters: t.input_schema ?? {},
              })),
            },
          }
        : {}),
    };
  };

  const handleSave = async (isPublished: boolean) => {
    setInlineError(null);
    if (!name.trim() || !url.trim()) {
      setInlineError("Name and URL are required.");
      return;
    }
    // Publishing without a successful "Test & discover" leaves the agent
    // tool-config drawer empty (no tool_functions_schema). The Publish button
    // is disabled until discover succeeds; this guard is defense-in-depth for
    // the case where the button is somehow bypassed.
    if (isPublished && discoveredTools.length === 0) {
      setInlineError(
        "Run 'Test connection & discover tools' before publishing so the tool list is captured.",
      );
      return;
    }
    try {
      const payload = buildSavePayload(isPublished);
      await createMutation.mutateAsync(payload);
      // Inline panel has no dialog to close — reset the form so the admin can
      // author another server. The create hook invalidates the platform-tools
      // list, so the manage view refetches with the new row.
      resetForm();
    } catch (e) {
      setInlineError(
        e instanceof Error ? e.message : "Failed to add MCP server.",
      );
    }
  };

  const handlePublishToggle = async (tool: PlatformTool) => {
    // Unpublishing hides the tool from new attaches but keeps it on every agent
    // already using it (the worker loads agent tools without an is_published
    // filter). Surface that usage informationally so the admin learns unpublish
    // != "remove from agents" — a non-blocking info toast before the mutation.
    if (tool.is_published) {
      try {
        const usage = await agentService.getPlatformToolUsage(tool.id);
        if (usage.count > 0) {
          toast.info(
            `${usage.count} agent${usage.count > 1 ? "s" : ""} currently use this tool — they keep it on their next call; new agents can no longer add it.`,
          );
        }
      } catch {
        // Non-fatal: usage is informational only; proceed to unpublish.
      }
    }
    publishMutation.mutate({ toolId: tool.id, published: !tool.is_published });
  };

  // MCP delete opens the type-to-confirm dialog (native/legacy tools never call
  // this — they have no Delete button). The dialog pre-fetches usage and sends
  // `force = count > 0` after explicit confirmation.
  const handleDelete = (tool: PlatformTool) => {
    setDeleteTarget(tool);
  };

  // Load an existing MCP tool into the author form. Secret headers are
  // encrypted at rest and never returned to the frontend — the field starts
  // empty; leaving it blank keeps the stored ones (the backend only replaces
  // them when a non-null value is sent).
  const startEdit = (tool: PlatformTool) => {
    setEditingTool(tool);
    setView("author");
    setName(tool.name ?? "");
    setUrl(tool.mcp_server_url ?? "");
    setPublicHeadersJson(
      tool.mcp_server_headers && Object.keys(tool.mcp_server_headers).length > 0
        ? JSON.stringify(tool.mcp_server_headers, null, 2)
        : "",
    );
    setSecretHeadersJson("");
    setTestApiKey("");
    setDescription(tool.description ?? "");
    setAuthMode(
      tool.requires_auth && tool.auth_type === "api_key" ? "api_key" : "none",
    );
    setIsPremium(Boolean(tool.is_premium));
    setDiscoveredTools([]);
    setParseErrors([]);
    setInlineError(null);
  };

  const cancelEdit = () => {
    setEditingTool(null);
    resetForm();
    setView("manage");
  };

  // Save edits to an EXISTING tool via the full PUT. Publish state is
  // preserved from the row (published tools keep `is_published=true`; drafts
  // stay drafts — the admin publishes later from the manage view). A stored
  // `tool_functions_schema` is untouched: the payload omits it unless the
  // admin re-runs "Test & discover" in this session.
  const handleSaveEdit = async () => {
    if (!editingTool) return;
    setInlineError(null);
    if (!name.trim() || !url.trim()) {
      setInlineError("Name and URL are required.");
      return;
    }
    try {
      const payload = buildSavePayload(Boolean(editingTool.is_published));
      await updateMutation.mutateAsync({ toolId: editingTool.id, payload });
      setEditingTool(null);
      resetForm();
      setView("manage");
    } catch (e) {
      setInlineError(
        e instanceof Error ? e.message : "Failed to update MCP server.",
      );
    }
  };

  const handlePremiumToggle = (tool: PlatformTool) => {
    premiumMutation.mutate({ toolId: tool.id, isPremium: !tool.is_premium });
  };

  const isBusy =
    discoverMutation.isPending ||
    parseMutation.isPending ||
    createMutation.isPending ||
    publishMutation.isPending ||
    premiumMutation.isPending ||
    updateMutation.isPending;

  // Publish requires a successful "Test & discover" so the discovered tool
  // list is captured into tool_functions_schema. Save draft is allowed without
  // discover (drafts aren't shown to org users, so an empty tool list is fine
  // for a work-in-progress draft).
  const canPublish = discoveredTools.length > 0;

  return (
    <div className="space-y-6">
      {/* View toggle (plain state — inline panel). Manage is first and the
          default — the page lands the admin on the tool list; authoring a new
          server is opt-in via the second toggle. */}
      <div className="inline-flex items-center rounded-lg border bg-muted/40 p-1">
        <button
          type="button"
          className={cn(
            "px-3 py-1.5 text-sm rounded-md transition-colors",
            view === "manage"
              ? "bg-background shadow-sm font-medium"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => {
            // Leaving the edit session via the tab cancels it (form state and
            // banner belong to the editing tool).
            if (editingTool) cancelEdit();
            else setView("manage");
          }}
        >
          Manage existing tools ({platformTools.length})
        </button>
        <button
          type="button"
          className={cn(
            "px-3 py-1.5 text-sm rounded-md transition-colors",
            view === "author"
              ? "bg-background shadow-sm font-medium"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setView("author")}
        >
          Configure MCP server
        </button>
      </div>

      {view === "author" ? (
        <div className="space-y-5">
          {editingTool && (
            <div className="flex items-start gap-2 p-3 rounded-lg border bg-muted/40">
              <Wrench className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
              <div className="text-xs text-muted-foreground">
                Editing{" "}
                <span className="font-medium text-foreground">
                  {editingTool.name.replace(/_/g, " ")}
                </span>
                . Changes apply to the existing server. Secret headers left
                blank are kept as stored (encrypted).
              </div>
            </div>
          )}

          {/* Paste JSON config */}
          <div className="space-y-2">
            <Label
              htmlFor="mcp-json-config"
              className="text-xs uppercase text-muted-foreground"
            >
              Paste JSON config (optional)
            </Label>
            <Textarea
              id="mcp-json-config"
              value={rawConfig}
              onChange={(e) => setRawConfig(e.target.value)}
              placeholder={`{
  "mcpServers": {
    "my-server": {
      "url": "https://example.com/mcp",
      "headers": { "Authorization": "Bearer ..." }
    }
  }
}`}
              className="min-h-[120px] font-mono text-xs"
            />
            <p className="text-xs text-muted-foreground">
              Claude Desktop / VS Code <code>mcpServers</code> format. stdio
              entries (<code>command</code>/<code>args</code>) are rejected.
              Parsing populates the fields below.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleParseConfig}
              disabled={!rawConfig.trim() || isBusy}
            >
              {parseMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Search className="h-3.5 w-3.5 mr-1.5" />
              )}
              Parse config
            </Button>
          </div>

          {/* Per-entry parse errors (e.g. stdio rejected) */}
          {parseErrors.length > 0 && (
            <div className="space-y-2">
              {parseErrors.map((err, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 p-3 rounded-lg border bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800"
                >
                  <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                  <div className="text-xs text-red-700 dark:text-red-300">
                    {err.name && (
                      <span className="font-medium">{err.name}: </span>
                    )}
                    {err.message}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Structured fields */}
          <div className="space-y-3">
            {/* Auth mode */}
            <div className="space-y-1">
              <Label
                htmlFor="mcp-auth-mode"
                className="text-xs uppercase text-muted-foreground"
              >
                Authentication
              </Label>
              <select
                id="mcp-auth-mode"
                value={authMode}
                onChange={(e) => setAuthMode(e.target.value as AuthMode)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="none">No auth</option>
                <option value="api_key">Static API key (per-org)</option>
              </select>
              <p className="text-xs text-muted-foreground">
                {authMode === "api_key"
                  ? "Each org supplies its own API key at attach time; it is substituted into the {{KEY}} placeholder at runtime."
                  : "No authentication headers. The server is called with only the public headers."}
              </p>
            </div>

            <div className="space-y-1">
              <Label
                htmlFor="mcp-name"
                className="text-xs uppercase text-muted-foreground"
              >
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="mcp-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-mcp-server"
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label
                htmlFor="mcp-url"
                className="text-xs uppercase text-muted-foreground"
              >
                Server URL <span className="text-destructive">*</span>
              </Label>
              <Input
                id="mcp-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/mcp"
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-1">
              <Label
                htmlFor="mcp-public-headers"
                className="text-xs uppercase text-muted-foreground"
              >
                Public headers (JSON, optional)
              </Label>
              <Textarea
                id="mcp-public-headers"
                value={publicHeadersJson}
                onChange={(e) => setPublicHeadersJson(e.target.value)}
                placeholder='{ "X-Client": "24x7-ai" }'
                className="min-h-[80px] font-mono text-xs"
              />
            </div>
            {authMode === "api_key" && (
              <>
                <div className="space-y-1">
                  <Label
                    htmlFor="mcp-secret-headers"
                    className="text-xs uppercase text-muted-foreground"
                  >
                    Secret header template (JSON, encrypted at rest)
                  </Label>
                  <Textarea
                    id="mcp-secret-headers"
                    value={secretHeadersJson}
                    onChange={(e) => setSecretHeadersJson(e.target.value)}
                    placeholder='{ "Authorization": "Bearer {{KEY}}" }'
                    className="min-h-[80px] font-mono text-xs"
                  />
                  <p className="text-xs text-muted-foreground">
                    Use <code>{"{{KEY}}"}</code> where the org&apos;s API key
                    goes. Literal values (no placeholder) pass through as fixed
                    shared headers.
                  </p>
                  {editingTool?.mcp_secret_headers_configured && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      This server has stored secret headers. Leave the field
                      blank to keep them when saving, and to reuse them when
                      testing the connection. Pasting new JSON replaces them on
                      save. If the stored template uses{" "}
                      <code>{"{{KEY}}"}</code>, enter a Test API key below for
                      the probe only.
                    </p>
                  )}
                </div>
                <div className="space-y-1">
                  <Label
                    htmlFor="mcp-test-key"
                    className="text-xs uppercase text-muted-foreground"
                  >
                    Test API key (transient — used only to test, never saved)
                  </Label>
                  <Input
                    id="mcp-test-key"
                    value={testApiKey}
                    onChange={(e) => setTestApiKey(e.target.value)}
                    placeholder="paste a test key for discover"
                    className="h-9 text-sm font-mono"
                  />
                </div>
              </>
            )}
            <div className="space-y-1">
              <Label
                htmlFor="mcp-description"
                className="text-xs uppercase text-muted-foreground"
              >
                Description (optional)
              </Label>
              <Input
                id="mcp-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What this server does"
                className="h-9 text-sm"
              />
            </div>
            {/* Premium flag: gates the tool behind the org plan's
                `premium_tools` feature (403 on attach otherwise). */}
            <div className="flex items-start gap-2 pt-1">
              <Checkbox
                id="mcp-premium"
                checked={isPremium}
                onCheckedChange={(checked) => setIsPremium(checked === true)}
                className="mt-0.5"
              />
              <div className="space-y-0.5">
                <Label
                  htmlFor="mcp-premium"
                  className="text-xs font-medium leading-tight"
                >
                  Premium tool
                </Label>
                <p className="text-xs text-muted-foreground">
                  Requires an org plan that entitles the{" "}
                  <code>premium_tools</code> feature before orgs can attach it;
                  shown with a Premium badge in the catalog.
                </p>
              </div>
            </div>
          </div>

          {/* Discover + preview */}
          <div className="space-y-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleDiscover}
              disabled={!url.trim() || isBusy}
            >
              {discoverMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Search className="h-3.5 w-3.5 mr-1.5" />
              )}
              Test connection &amp; discover tools
            </Button>

            {inlineError && (
              <div className="flex items-start gap-2 p-3 rounded-lg border bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800">
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                <div className="text-xs text-red-700 dark:text-red-300">
                  {inlineError}
                </div>
              </div>
            )}

            {discoveredTools.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-xs text-green-700 dark:text-green-300">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Discovered {discoveredTools.length} tool
                  {discoveredTools.length === 1 ? "" : "s"}:
                </div>
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {discoveredTools.map((t) => (
                    <div
                      key={t.name}
                      className="p-2.5 rounded-lg border bg-muted/30"
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <Wrench className="h-3 w-3 text-muted-foreground" />
                        <span className="text-xs font-medium font-mono">
                          {t.name}
                        </span>
                      </div>
                      {t.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {t.description}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Inline footer (was a Sheet footer; on the page it's just a row of
              buttons). Buttons are w-full on mobile, auto-width side-by-side
              at sm+ so they never overflow the panel. */}
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            {editingTool ? (
              <>
                <Button
                  onClick={cancelEdit}
                  disabled={isBusy}
                  variant="outline"
                  className="w-full sm:w-auto"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveEdit}
                  disabled={!name.trim() || !url.trim() || isBusy}
                  className="w-full sm:w-auto"
                >
                  {updateMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                  )}
                  Save changes
                </Button>
              </>
            ) : (
              <>
                <Button
                  onClick={() => handleSave(false)}
                  disabled={!name.trim() || !url.trim() || isBusy}
                  variant="outline"
                  className="w-full sm:w-auto"
                >
                  {createMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4 mr-2" />
                  )}
                  Save draft
                </Button>
                <Button
                  onClick={() => handleSave(true)}
                  disabled={
                    !name.trim() || !url.trim() || !canPublish || isBusy
                  }
                  className="w-full sm:w-auto"
                >
                  {createMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4 mr-2" />
                  )}
                  Publish
                </Button>
              </>
            )}
          </div>
          {!canPublish && (
            <p className="text-xs text-muted-foreground -mt-2 sm:text-right">
              Run{" "}
              <span className="font-medium">
                Test connection &amp; discover tools
              </span>{" "}
              before publishing so the tool list is captured.
            </p>
          )}
        </div>
      ) : (
        // Manage view: drafts + published, with publish/unpublish/delete.
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Drafts are visible only to platform admins. Publishing surfaces a
            tool in every org&apos;s tool catalog; unpublishing hides it from
            new attaches (existing attachments keep working). Marking a tool
            premium gates it behind the plan&apos;s <code>premium_tools</code>{" "}
            feature.
          </p>
          {platformTools.length === 0 ? (
            <div className="text-center py-8 bg-muted/20 rounded-lg border border-dashed">
              <Server className="h-8 w-8 text-muted-foreground mx-auto mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">
                No platform tools yet. Configure an MCP server to get started.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {platformTools.map((tool) => (
                <div
                  key={tool.id}
                  className="flex items-center justify-between gap-3 p-3 rounded-lg border bg-muted/20"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-sm font-medium">
                        {tool.name.replace(/_/g, " ")}
                      </span>
                      {tool.tool_source === "mcp" && (
                        <Badge variant="secondary" className="h-5 text-[10px]">
                          MCP
                        </Badge>
                      )}
                      <Badge
                        variant={tool.is_published ? "default" : "outline"}
                        className="h-5 text-[10px]"
                      >
                        {tool.is_published ? "Published" : "Draft"}
                      </Badge>
                      {tool.is_premium && (
                        <Badge
                          variant="outline"
                          className="h-5 text-[10px] border-amber-300 dark:border-amber-700 bg-amber-100/60 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200"
                        >
                          <Crown className="h-2.5 w-2.5 mr-0.5" />
                          Premium
                        </Badge>
                      )}
                    </div>
                    {tool.description && (
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {tool.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant={tool.is_premium ? "default" : "outline"}
                      onClick={() => handlePremiumToggle(tool)}
                      disabled={isBusy}
                      title={
                        tool.is_premium
                          ? "Remove the premium gate (any entitled plan can attach)"
                          : "Premium tools require the org plan to entitle the premium_tools feature"
                      }
                    >
                      <Crown className="h-3.5 w-3.5 mr-1" />
                      {tool.is_premium ? "Unmark premium" : "Mark premium"}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handlePublishToggle(tool)}
                      disabled={isBusy}
                    >
                      {tool.is_published ? (
                        "Unpublish"
                      ) : (
                        <>
                          <Upload className="h-3.5 w-3.5 mr-1" />
                          Publish
                        </>
                      )}
                    </Button>
                    {/* Native/legacy tools are code-backed and re-seeded by the
                        worker on startup — edits (like deletes) would be
                        clobbered, so only MCP tools get an Edit affordance. */}
                    {tool.tool_source !== "legacy" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => startEdit(tool)}
                        disabled={isBusy}
                        aria-label="Edit"
                      >
                        <Wrench className="h-3.5 w-3.5 mr-1" />
                        Edit
                      </Button>
                    )}
                    {/* Native/legacy tools are code-backed and re-seeded by the
                        worker on startup — they are not hard-deletable (the backend
                        refuses with 400). Only MCP tools get a Delete affordance. */}
                    {tool.tool_source !== "legacy" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(tool)}
                        disabled={isBusy}
                        aria-label="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Conditionally rendered so the shared DeleteConfirmationDialog mounts
          fresh each open — its internal type-to-confirm state resets between
          deletes (always-mounted would leak "Delete" into the next dialog). */}
      {deleteTarget && (
        <McpToolDeleteDialog
          open
          onOpenChange={(o) => {
            if (!o) setDeleteTarget(null);
          }}
          tool={deleteTarget}
          onDeleted={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
