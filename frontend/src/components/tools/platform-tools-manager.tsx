import * as React from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
  ShieldCheck,
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
  useStartPlatformMcpOAuth,
  useSetPlatformToolPremium,
  useUpdatePlatformTool,
} from "@/hooks/use-agent-queries";
import { agentService } from "@/services/agent-service";
import { toast } from "sonner";
import { McpToolDeleteDialog } from "@/components/tools/mcp-tool-delete-dialog";
import { McpFunctionCatalogDrawer } from "@/components/tools/mcp-function-catalog-drawer";
import { ExpandableDescription } from "@/components/tools/expandable-description";

/**
 * PlatformToolsManager — platform-admin catalog surface for the global tool
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
 * org user's agent tool panel, where an org admin supplies an org-owned API
 * key or completes the server's OAuth flow when the integration requires it.
 * OAuth MCP rows also expose a separate platform-admin discovery action so
 * their public function catalog is visible without reusing that credential at
 * agent runtime.
 *
 * The manage catalog stays on the page, while create/edit authoring opens in
 * the shared right-side Sheet pattern used by the rest of the application:
 *  - **Configure MCP server** (internal state `view === "author"`): a
 *    structured form (auth mode, Name, URL, public Headers, optional `{{KEY}}`
 *    secret-header template + transient Test API key, or OAuth metadata) *or*
 *    a "Paste JSON config" textarea holding a common MCP host-config blob.
 *    "Test & discover tools" previews the exposed tools in-memory before
 *    saving, substituting the Test API key into the `{{KEY}}` template for
 *    one-shot discover. "Save draft" persists `is_published=false`;
 *    "Publish" persists `is_published=true` and is gated on a successful
 *    "Test & discover" for public servers so the discovered tool list is
 *    captured into `tool_functions_schema`. Credentialed servers may publish
 *    without a platform key because the org supplies the key or completes
 *    OAuth before runtime discovery. On success the form resets so
 *    the drawer closes, and the manage list refetches.
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
 *  - **Static API key**: the platform admin may author a secret-header
 *    template containing a `{{KEY}}` placeholder or an optional literal
 *    platform fallback. The Org Admin drawer always offers an organization
 *    key; it is stored in `agent_tools.sensitive_config["api_key"]` and
 *    overrides platform credentials at runtime. The transient platform Test
 *    API key is used only for in-memory discovery and is never persisted.
 *  - **OAuth**: the platform admin may provide endpoints, scopes, and a public
 *    client ID or leave those fields blank for standard MCP metadata discovery;
 *    **Discover with OAuth** uses a platform-admin authorization only to cache
 *    the public function catalog, while the org admin authorizes the specific
 *    agent connection and owns the runtime token.
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
 * no window.* dialogs, and a right-side drawer for create/edit.
 */
export interface PlatformToolsManagerProps {
  /** Initial view shown when the panel mounts. Defaults to "manage" — the
   * platform-tools page lands the admin on the tool list, not the author
   * form (the form is opt-in via the "Configure MCP server" toggle). */
  initialView?: "author" | "manage";
}

type AuthMode = "none" | "api_key" | "oauth2";
type View = "author" | "manage";

const isCredentialHeaderName = (name: string): boolean =>
  /^(authorization|proxy-authorization|api-key|x-api-key|x-auth-token|x-access-token)$/i.test(
    name,
  ) || /(?:-api-key|-auth-token|-access-token)$/i.test(name);

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
  const [oauthAuthUrl, setOauthAuthUrl] = React.useState("");
  const [oauthTokenUrl, setOauthTokenUrl] = React.useState("");
  const [oauthScopes, setOauthScopes] = React.useState("");
  const [oauthClientId, setOauthClientId] = React.useState("");
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
  // The catalog drawer is opened from the compact exposed-function summary in
  // the manage list. Keeping the selected row separate from the edit state
  // lets admins inspect functions without leaving the list.
  const [catalogTool, setCatalogTool] = React.useState<PlatformTool | null>(
    null,
  );
  // React Query exposes one mutation-level `isPending` flag. Track the row id
  // separately so only the OAuth action that was clicked enters its loading
  // state; Linear must not make Notion or Google Calendar look busy.
  const [platformOAuthToolId, setPlatformOAuthToolId] = React.useState<
    string | null
  >(null);

  const discoverMutation = useDiscoverMcpTools();
  const parseMutation = useParseMcpServersJson();
  const createMutation = useCreatePlatformTool();
  const publishMutation = usePublishPlatformTool();
  const platformOAuthMutation = useStartPlatformMcpOAuth();
  const premiumMutation = useSetPlatformToolPremium();
  const updateMutation = useUpdatePlatformTool();
  // Platform-admin-only surface: list drafts + published for the manage view.
  const { data: platformTools = [] } = usePlatformTools(false, {
    includeDrafts: true,
  });

  React.useEffect(() => {
    if (!editingTool) return;
    const refreshedTool = platformTools.find(
      (tool) => tool.id === editingTool.id,
    );
    const functions = refreshedTool?.tool_functions_schema?.functions;
    if (!functions?.length || discoveredTools.length > 0) return;
    setDiscoveredTools(
      functions.map((func) => ({
        name: func.name,
        description: func.description || null,
        input_schema: func.parameters || null,
      })),
    );
  }, [discoveredTools.length, editingTool, platformTools]);

  // Clear every author-form field when starting a fresh server or after a
  // successful save before returning to the catalog.
  const resetForm = React.useCallback(() => {
    setRawConfig("");
    setAuthMode("none");
    setName("");
    setUrl("");
    setPublicHeadersJson("");
    setSecretHeadersJson("");
    setTestApiKey("");
    setOauthAuthUrl("");
    setOauthTokenUrl("");
    setOauthScopes("");
    setOauthClientId("");
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
        const parsedAuthMode = first.auth_type as AuthMode | null | undefined;
        if (parsedAuthMode === "api_key" || parsedAuthMode === "oauth2") {
          setAuthMode(parsedAuthMode);
        } else if (first.requires_auth) {
          // Preserve an explicit credential requirement even when a host
          // config uses an auth type this UI does not name separately.
          setAuthMode("api_key");
        } else if (
          first.secret_headers &&
          Object.keys(first.secret_headers).length > 0
        ) {
          setAuthMode("api_key");
        } else {
          setAuthMode("none");
        }
        setSecretHeadersJson(
          first.secret_headers && Object.keys(first.secret_headers).length > 0
            ? JSON.stringify(first.secret_headers, null, 2)
            : "",
        );
        const parsedOauth = first.auth_config || {};
        setOauthAuthUrl(String(parsedOauth.auth_url || ""));
        setOauthTokenUrl(String(parsedOauth.token_url || ""));
        setOauthScopes(
          Array.isArray(parsedOauth.scopes)
            ? parsedOauth.scopes.join(" ")
            : String(parsedOauth.scopes || ""),
        );
        setOauthClientId(String(parsedOauth.client_id || ""));
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
    if (authMode === "oauth2") {
      await handleOAuthFormDiscovery();
      return;
    }
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
              ...(testApiKey.trim() ? { test_api_key: testApiKey.trim() } : {}),
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

  /**
   * Persist the current OAuth MCP configuration as a draft when necessary,
   * then start platform OAuth discovery from the authoring workflow.
   *
   * OAuth discovery requires a persisted platform-tool id because the OAuth
   * callback writes the public tools/list catalog back to that row. A new
   * server therefore becomes a draft automatically; editing an existing row
   * saves its metadata first. Neither path publishes or creates an agent
   * connection.
   */
  const handleOAuthFormDiscovery = async () => {
    if (!name.trim() || !url.trim()) {
      setInlineError("Name and URL are required before OAuth discovery.");
      return;
    }
    try {
      const payload = buildSavePayload(
        editingTool ? Boolean(editingTool.is_published) : false,
      );
      const persistedTool = editingTool
        ? await updateMutation.mutateAsync({
            toolId: editingTool.id,
            payload,
          })
        : await createMutation.mutateAsync(payload);
      if (!persistedTool?.id) {
        throw new Error("The MCP draft was saved without a tool id.");
      }
      if (!editingTool) setEditingTool(persistedTool);
      await handlePlatformOAuthDiscovery(persistedTool.id);
    } catch (e) {
      setInlineError(
        e instanceof Error
          ? e.message
          : "Failed to save the MCP draft and start OAuth discovery.",
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
    const oauthScopesValue = oauthScopes
      .split(/[\s,]+/)
      .map((scope) => scope.trim())
      .filter(Boolean);
    const oauthConfig =
      authMode === "oauth2"
        ? {
            provider: "mcp",
            ...(oauthAuthUrl.trim() ? { auth_url: oauthAuthUrl.trim() } : {}),
            ...(oauthTokenUrl.trim()
              ? { token_url: oauthTokenUrl.trim() }
              : {}),
            ...(oauthScopesValue.length > 0
              ? { scopes: oauthScopesValue }
              : {}),
            ...(oauthClientId.trim()
              ? { client_id: oauthClientId.trim() }
              : {}),
          }
        : null;
    const credentialHeaderValues = [
      ...Object.entries(publicHeaders || {})
        .filter(([key]) => isCredentialHeaderName(key))
        .map(([, value]) => value),
      ...Object.values(secretHeaders || {}),
    ];
    const hasOrgKeyTemplate = credentialHeaderValues.some((value) =>
      value.includes("{{KEY}}"),
    );
    const hasPlatformKeyFallback = credentialHeaderValues.some(
      (value) => !value.includes("{{KEY}}"),
    );
    const preservesExistingPlatformFallback =
      editingTool?.auth_type === "api_key" &&
      editingTool.requires_auth === false &&
      !secretHeadersJson.trim();
    const apiKeyRequiresOrgKey =
      authMode === "api_key" &&
      (hasOrgKeyTemplate ||
        (!hasPlatformKeyFallback && !preservesExistingPlatformFallback));
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
      ...(oauthConfig ? { auth_config: oauthConfig } : {}),
      is_active: true,
      requires_auth: authMode === "oauth2" || apiKeyRequiresOrgKey,
      auth_type: authMode === "none" ? null : authMode,
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
    // Publishing without a successful discovery leaves the agent tool-config
    // drawer empty (no tool_functions_schema). OAuth servers must be
    // discovered by the platform admin before publishing; API-key servers may
    // still be published without a platform key because the org supplies its
    // own credential at connection time.
    if (
      isPublished &&
      discoveredTools.length === 0 &&
      (authMode === "none" || authMode === "oauth2")
    ) {
      setInlineError(
        authMode === "oauth2"
          ? "Authorize & discover tools before publishing so the OAuth function catalog is captured."
          : "Run 'Test connection & discover tools' before publishing so the tool list is captured.",
      );
      return;
    }
    try {
      const payload = buildSavePayload(isPublished);
      await createMutation.mutateAsync(payload);
      // Close the authoring drawer after save. The create hook invalidates the
      // platform-tools list, so the manage view refetches with the new row.
      resetForm();
      setView("manage");
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
      tool.auth_type === "oauth2"
        ? "oauth2"
        : tool.auth_type === "api_key"
          ? "api_key"
          : "none",
    );
    const storedOauth = tool.auth_config || {};
    setOauthAuthUrl(String(storedOauth.auth_url || ""));
    setOauthTokenUrl(String(storedOauth.token_url || ""));
    setOauthScopes(
      Array.isArray(storedOauth.scopes)
        ? storedOauth.scopes.join(" ")
        : String(storedOauth.scopes || ""),
    );
    setOauthClientId(String(storedOauth.client_id || ""));
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

  /** Open a clean authoring drawer for a brand-new platform MCP tool. */
  const startCreate = React.useCallback(() => {
    setEditingTool(null);
    resetForm();
    setView("author");
  }, [resetForm]);

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

  const isAuthorBusy = isBusy || platformOAuthMutation.isPending;

  const handlePlatformOAuthDiscovery = async (toolId: string) => {
    setPlatformOAuthToolId(toolId);
    try {
      await platformOAuthMutation.mutateAsync(toolId);
    } finally {
      setPlatformOAuthToolId((activeToolId) =>
        activeToolId === toolId ? null : activeToolId,
      );
    }
  };

  // OAuth MCPs must have a platform-discovered catalog before publishing so
  // the integration cannot enter the org catalog with no exposed functions.
  // API-key servers remain publishable without a platform key because an Org
  // Admin may provide the credential later; no-auth servers must be tested.
  const canPublish = discoveredTools.length > 0 || authMode === "api_key";

  return (
    <div className="space-y-6">
      {view === "author" ? (
        <Sheet
          open
          onOpenChange={(open) => {
            if (!open) cancelEdit();
          }}
        >
          <SheetContent className="form-drawer flex w-full flex-col overflow-hidden sm:max-w-2xl">
            <SheetHeader className="shrink-0 border-b px-6 pb-5 pt-6">
              <SheetTitle>
                {editingTool ? "Edit MCP server" : "Configure MCP server"}
              </SheetTitle>
              <SheetDescription>
                {editingTool
                  ? "Update this platform integration without leaving the tool catalog."
                  : "Add a remote MCP integration to the platform catalog."}
              </SheetDescription>
            </SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
              <div className="form-surface space-y-5">
                {editingTool && (
                  <div className="flex items-start gap-2 p-3 rounded-lg border bg-muted/40">
                    <Wrench className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <div className="text-xs text-muted-foreground">
                      Editing{" "}
                      <span className="font-medium text-foreground">
                        {editingTool.name.replace(/_/g, " ")}
                      </span>
                      . Changes apply to the existing server. Secret headers
                      left blank are kept as stored (encrypted).
                    </div>
                  </div>
                )}

                {/* Paste JSON config — an advanced import path, intentionally tucked
              away so the common structured setup remains calm and scannable. */}
                <details className="form-section group">
                  <summary className="cursor-pointer list-none text-sm font-medium flex items-center justify-between">
                    <span>Import from an MCP host config</span>
                    <span className="text-xs text-muted-foreground group-open:hidden">
                      Optional JSON
                    </span>
                  </summary>
                  <div className="space-y-2 pt-4">
                    <Label
                      htmlFor="mcp-json-config"
                      className="text-xs uppercase text-muted-foreground"
                    >
                      Paste JSON config
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
                      className="form-control min-h-[120px] font-mono text-xs"
                    />
                    <p className="text-xs text-muted-foreground">
                      Imports Claude Desktop, VS Code, Cursor, Windsurf, and
                      other common host shapes. Local <code>stdio</code> entries
                      are reported because hosted agents use remote HTTP
                      servers.
                    </p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleParseConfig}
                      disabled={!rawConfig.trim() || isAuthorBusy}
                    >
                      {parseMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <Search className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      Parse config
                    </Button>
                  </div>
                </details>

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
                  <div className="form-section space-y-3">
                    <Label
                      htmlFor="mcp-auth-mode"
                      className="text-xs uppercase text-muted-foreground"
                    >
                      Authentication — how will this server connect?
                    </Label>
                    <select
                      id="mcp-auth-mode"
                      value={authMode}
                      onChange={(e) => setAuthMode(e.target.value as AuthMode)}
                      className="form-control flex h-10 w-full rounded-lg px-3 text-sm"
                    >
                      <option value="none">
                        Public server — no credential
                      </option>
                      <option value="api_key">
                        API key — each org supplies its own
                      </option>
                      <option value="oauth2">
                        OAuth — each org connects its account
                      </option>
                    </select>
                    <p className="text-xs text-muted-foreground">
                      {authMode === "api_key"
                        ? "The platform key is optional. Org Admins can provide an organization key that overrides it; if neither key is configured, the runtime call will fail."
                        : authMode === "oauth2"
                          ? "OAuth endpoints can be supplied now or discovered when an Org Admin connects the server. PKCE protects the account authorization flow."
                          : "The server is called with only the public headers."}
                    </p>
                  </div>

                  <div className="form-field space-y-1">
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
                      className="form-control h-9 text-sm"
                    />
                  </div>
                  <div className="form-field space-y-1">
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
                      className="form-control h-9 text-sm"
                    />
                  </div>
                  <div className="form-field space-y-1">
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
                      className="form-control min-h-[80px] font-mono text-xs"
                    />
                  </div>
                  {authMode === "oauth2" && (
                    <div className="form-section space-y-3 border-sky-200 bg-sky-50/70 dark:border-sky-900 dark:bg-sky-950/20">
                      <div>
                        <p className="text-sm font-medium">OAuth details</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Leave endpoints blank when the MCP server publishes
                          standard OAuth metadata. A client ID is optional when
                          Dynamic Client Registration is enabled.
                        </p>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="form-field space-y-1">
                          <Label htmlFor="mcp-oauth-auth-url">
                            Authorization endpoint
                          </Label>
                          <Input
                            id="mcp-oauth-auth-url"
                            value={oauthAuthUrl}
                            onChange={(e) => setOauthAuthUrl(e.target.value)}
                            placeholder="https://auth.example/authorize"
                            className="form-control h-9 text-sm"
                          />
                        </div>
                        <div className="form-field space-y-1">
                          <Label htmlFor="mcp-oauth-token-url">
                            Token endpoint
                          </Label>
                          <Input
                            id="mcp-oauth-token-url"
                            value={oauthTokenUrl}
                            onChange={(e) => setOauthTokenUrl(e.target.value)}
                            placeholder="https://auth.example/token"
                            className="form-control h-9 text-sm"
                          />
                        </div>
                      </div>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="form-field space-y-1">
                          <Label htmlFor="mcp-oauth-scopes">
                            Scopes (optional)
                          </Label>
                          <Input
                            id="mcp-oauth-scopes"
                            value={oauthScopes}
                            onChange={(e) => setOauthScopes(e.target.value)}
                            placeholder="files:read files:write"
                            className="form-control h-9 text-sm"
                          />
                        </div>
                        <div className="form-field space-y-1">
                          <Label htmlFor="mcp-oauth-client-id">
                            Public client ID (optional)
                          </Label>
                          <Input
                            id="mcp-oauth-client-id"
                            value={oauthClientId}
                            onChange={(e) => setOauthClientId(e.target.value)}
                            placeholder="Provided by the MCP OAuth server"
                            className="form-control h-9 text-sm"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                  {authMode === "api_key" && (
                    <>
                      <div className="form-field space-y-1">
                        <Label
                          htmlFor="mcp-secret-headers"
                          className="text-xs uppercase text-muted-foreground"
                        >
                          Secret header template / API key (JSON, encrypted at
                          rest)
                        </Label>
                        <Textarea
                          id="mcp-secret-headers"
                          value={secretHeadersJson}
                          onChange={(e) => setSecretHeadersJson(e.target.value)}
                          placeholder='{ "Authorization": "Bearer {{KEY}}" }'
                          className="form-control min-h-[80px] font-mono text-xs"
                        />
                        <p className="text-xs text-muted-foreground">
                          Optional. Use <code>{"{{KEY}}"}</code> where the
                          org&apos;s API key goes. A literal value can remain as
                          a platform fallback, while an Org Admin key always
                          takes precedence. Leaving this blank is valid, but the
                          Org Admin must provide a key if no platform fallback
                          is configured.
                        </p>
                        {editingTool?.mcp_secret_headers_configured && (
                          <p className="text-xs text-amber-700 dark:text-amber-300">
                            This server has stored secret headers. Leave the
                            field blank to keep them when saving, and to reuse
                            them when testing the connection. Pasting new JSON
                            replaces them on save. If the stored template uses{" "}
                            <code>{"{{KEY}}"}</code>, enter a Test API key below
                            for the probe only.
                          </p>
                        )}
                      </div>
                      <div className="form-field space-y-1">
                        <Label
                          htmlFor="mcp-test-key"
                          className="text-xs uppercase text-muted-foreground"
                        >
                          Test API key (transient — used only to test, never
                          saved)
                        </Label>
                        <Input
                          id="mcp-test-key"
                          value={testApiKey}
                          onChange={(e) => setTestApiKey(e.target.value)}
                          placeholder="paste a test key for discover"
                          className="form-control h-9 text-sm font-mono"
                        />
                      </div>
                    </>
                  )}
                  <div className="form-field space-y-1">
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
                      className="form-control h-9 text-sm"
                    />
                  </div>
                  {/* Premium flag: gates the tool behind the org plan's
                `premium_tools` feature (403 on attach otherwise). */}
                  <div className="flex items-start gap-2 pt-1">
                    <Checkbox
                      id="mcp-premium"
                      checked={isPremium}
                      onCheckedChange={(checked) =>
                        setIsPremium(checked === true)
                      }
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
                        <code>premium_tools</code> feature before orgs can
                        attach it; shown with a Premium badge in the catalog.
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
                    disabled={!url.trim() || isAuthorBusy}
                  >
                    {discoverMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                    ) : (
                      <Search className="h-3.5 w-3.5 mr-1.5" />
                    )}
                    {authMode === "oauth2"
                      ? "Authorize & discover tools"
                      : "Test connection & discover tools"}
                  </Button>
                  {authMode === "oauth2" && (
                    <p className="text-xs text-muted-foreground">
                      This saves the configuration as a draft, opens OAuth, and
                      stores the public function catalog after authorization.
                      You can publish it once discovery finishes.
                    </p>
                  )}

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
                            <ExpandableDescription
                              description={t.description}
                              descriptionId={`discovered-tool-description-${t.name}`}
                              textClassName="text-xs text-muted-foreground"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Drawer footer. Buttons are w-full on mobile, auto-width
              side-by-side at sm+ so they never overflow the panel. */}
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  {editingTool ? (
                    <>
                      <Button
                        onClick={cancelEdit}
                        disabled={isAuthorBusy}
                        variant="outline"
                        className="w-full sm:w-auto"
                      >
                        Cancel
                      </Button>
                      <Button
                        onClick={handleSaveEdit}
                        disabled={!name.trim() || !url.trim() || isAuthorBusy}
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
                        disabled={!name.trim() || !url.trim() || isAuthorBusy}
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
                          !name.trim() ||
                          !url.trim() ||
                          !canPublish ||
                          isAuthorBusy
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
                    {authMode === "oauth2" ? (
                      <>
                        Complete{" "}
                        <span className="font-medium">
                          Authorize &amp; discover tools
                        </span>{" "}
                        before publishing so the OAuth function catalog is
                        captured.
                      </>
                    ) : (
                      <>
                        Run{" "}
                        <span className="font-medium">
                          Test connection &amp; discover tools
                        </span>{" "}
                        before publishing so the tool list is captured.
                      </>
                    )}
                  </p>
                )}
              </div>
            </div>
          </SheetContent>
        </Sheet>
      ) : (
        // Manage view: drafts + published, with publish/unpublish/delete.
        <div className="space-y-3">
          <div className="flex flex-col gap-3 rounded-2xl border bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-sm font-semibold">Platform tool catalog</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Add a new MCP integration or manage the tools already available
                to Org Admins.
              </p>
            </div>
            <Button onClick={startCreate} className="w-full sm:w-auto">
              <Plus className="mr-2 h-4 w-4" />
              Create new platform tool
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border bg-slate-950 p-4 text-white shadow-sm dark:bg-slate-900">
              <p className="text-[10px] uppercase tracking-[0.18em] text-slate-400">
                Catalog
              </p>
              <p className="mt-2 text-2xl font-semibold">
                {platformTools.length}
              </p>
              <p className="text-xs text-slate-400">platform integrations</p>
            </div>
            <div className="rounded-2xl border bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950/20">
              <p className="text-[10px] uppercase tracking-[0.18em] text-emerald-700 dark:text-emerald-300">
                Published
              </p>
              <p className="mt-2 text-2xl font-semibold text-emerald-950 dark:text-emerald-100">
                {platformTools.filter((tool) => tool.is_published).length}
              </p>
              <p className="text-xs text-emerald-800/70 dark:text-emerald-200/70">
                ready for Org Admins
              </p>
            </div>
            <div className="rounded-2xl border bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20">
              <p className="text-[10px] uppercase tracking-[0.18em] text-amber-700 dark:text-amber-300">
                In progress
              </p>
              <p className="mt-2 text-2xl font-semibold text-amber-950 dark:text-amber-100">
                {platformTools.filter((tool) => !tool.is_published).length}
              </p>
              <p className="text-xs text-amber-800/70 dark:text-amber-200/70">
                drafts to review
              </p>
            </div>
          </div>
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
                  className="flex flex-col items-start justify-between gap-4 rounded-2xl border bg-background p-4 transition-colors hover:bg-muted/20 sm:flex-row sm:items-center"
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
                    <ExpandableDescription
                      description={tool.description}
                      descriptionId={`platform-tool-description-${tool.id}`}
                      textClassName="text-xs text-muted-foreground"
                    />
                    {tool.tool_source === "mcp" && (
                      <div className="mt-2 space-y-0.5 text-[11px]">
                        {tool.tool_functions_schema?.functions?.length ? (
                          <>
                            <Button
                              type="button"
                              variant="link"
                              size="sm"
                              className="h-auto p-0 text-[11px] text-emerald-700 dark:text-emerald-300"
                              onClick={() => setCatalogTool(tool)}
                              aria-label={`View exposed functions for ${tool.name}`}
                            >
                              {tool.tool_functions_schema.functions.length}{" "}
                              exposed function
                              {tool.tool_functions_schema.functions.length === 1
                                ? ""
                                : "s"}
                            </Button>
                          </>
                        ) : (
                          <p className="text-amber-700 dark:text-amber-300">
                            Catalog unavailable — authenticate to discover
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                    {tool.tool_source === "mcp" &&
                      tool.auth_type === "oauth2" && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            void handlePlatformOAuthDiscovery(tool.id)
                          }
                          disabled={
                            isBusy ||
                            (platformOAuthMutation.isPending &&
                              platformOAuthToolId === tool.id)
                          }
                          title="Authorize once to discover and persist this MCP server's public tool catalog"
                          aria-label={`Discover with OAuth for ${tool.name}`}
                        >
                          {platformOAuthMutation.isPending &&
                          platformOAuthToolId === tool.id ? (
                            <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                          ) : (
                            <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                          )}
                          {tool.tool_functions_schema?.functions?.length
                            ? "Refresh catalog"
                            : "Discover with OAuth"}
                        </Button>
                      )}
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
      <McpFunctionCatalogDrawer
        open={catalogTool !== null}
        onOpenChange={(open) => {
          if (!open) setCatalogTool(null);
        }}
        tool={catalogTool}
      />
    </div>
  );
}
