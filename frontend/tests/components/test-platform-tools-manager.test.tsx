/**
 * Tests for PlatformToolsManager — the inline platform-admin surface for the
 * global tool catalog (publish lifecycle, RFC §6.6). Lives on the dedicated
 * `/platform/tools` page (parallel to `/platform/skills`); was previously a
 * Sheet dialog opened from the agent Tools tab.
 *
 * Covers:
 *  - Configure MCP server: paste `mcpServers` JSON → parse autofills the
 *    structured fields; stdio entries surface an inline per-entry error;
 *    "Test & discover" calls discoverMcpTools and renders the tool list;
 *    "Save draft" / "Publish" call createPlatformTool with the right payload
 *    (is_published, secret-header template, requires_auth/auth_type for the
 *    api-key mode) — no organization_id (global row), no per-agent attach
 *    hand-off — then reset the form so the admin can author another.
 *  - Auth/key model: api-key mode shows the `{{KEY}}` secret-header template +
 *    transient Test API key; discover substitutes the test key into `{{KEY}}`;
 *    save persists the template + requires_auth=true + auth_type=api_key.
 *  - Manage existing tools: lists drafts + published with Draft/Published
 *    badges and publish/unpublish + delete actions.
 *  - Premium flag: gold Premium badge on premium rows; Mark/Unmark premium
 *    toggle posts to the dedicated `/platform/{id}/premium` endpoint.
 *  - Edit flow: the Edit action loads an MCP tool into the author form
 *    (public fields prefilled; secret headers stay blank + keep-existing
 *    note), "Save changes" PUTs with the row's publish state preserved, and
 *    Cancel exits without sending anything.
 *  - No catalog tab (retired) and no "From catalog" button.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  renderWithProviders as render,
  screen,
  waitFor,
  fireEvent,
} from "../utils/test-utils";
import { PlatformToolsManager } from "@/components/tools/platform-tools-manager";
import { server } from "../mocks/server";
import { http, HttpResponse } from "msw";
import { createMockPlatformTool } from "../utils/data-factories";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const baseProps = (
  overrides: Partial<Parameters<typeof PlatformToolsManager>[0]> = {},
) => ({
  ...overrides,
});

// The component defaults to the "manage" view (the platform-tools page lands
// the admin on the tool list, not the author form). Author-flow tests opt
// INTO the author view explicitly so they don't depend on the default.
const authorProps = (
  overrides: Partial<Parameters<typeof PlatformToolsManager>[0]> = {},
) => ({ initialView: "author" as const, ...overrides });

// Capture the body posted to POST /tools/platform so a test can assert the
// create payload (the dialog no longer hands the created tool to a parent
// callback — it just creates + closes).
const captureCreateBody = () => {
  let captured: Record<string, any> | null = null;
  server.use(
    http.post(`${API_BASE_URL}/api/v1/tools/platform`, async ({ request }) => {
      captured = (await request.json()) as Record<string, any>;
      return HttpResponse.json({
        id: "new-mcp-tool",
        name: captured?.name || "new_mcp_server",
        tool_source: "mcp",
        mcp_server_url: captured?.mcp_server_url || null,
        is_published: captured?.is_published ?? false,
        mcp_secret_headers_configured: !!captured?.mcp_secret_headers_input,
      });
    }),
  );
  return () => captured;
};

describe("PlatformToolsManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Author flow", () => {
    it("parses mcpServers JSON and autofills name + url + public headers", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      const jsonTextarea = screen.getByPlaceholderText(/mcpServers/i);
      fireEvent.change(jsonTextarea, {
        target: {
          value: JSON.stringify({
            mcpServers: {
              "my-server": {
                url: "https://example.com/mcp",
                headers: { "X-Key": "v" },
              },
            },
          }),
        },
      });
      await user.click(screen.getByRole("button", { name: /parse config/i }));

      await waitFor(() => {
        expect(
          (screen.getByLabelText(/^name/i) as HTMLInputElement).value,
        ).toBe("my-server");
      });
      expect(
        (screen.getByLabelText(/server url/i) as HTMLInputElement).value,
      ).toBe("https://example.com/mcp");
      // Public headers field receives the extracted headers object.
      const publicHeaders = screen.getByLabelText(
        /public headers/i,
      ) as HTMLTextAreaElement;
      expect(publicHeaders.value).toContain('"X-Key"');
    });

    it("keeps the pasted config box separate from the public headers field", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      const blob = JSON.stringify({
        mcpServers: {
          "my-server": {
            url: "https://example.com/mcp",
            headers: { "X-Key": "secret" },
          },
        },
      });
      const pasteBox = screen.getByPlaceholderText(
        /mcpServers/i,
      ) as HTMLTextAreaElement;
      fireEvent.change(pasteBox, { target: { value: blob } });

      await user.click(screen.getByRole("button", { name: /parse config/i }));

      await waitFor(() => {
        expect(
          (screen.getByLabelText(/^name/i) as HTMLInputElement).value,
        ).toBe("my-server");
      });

      // The public headers field holds ONLY the extracted headers object.
      const publicHeaders = screen.getByLabelText(
        /public headers/i,
      ) as HTMLTextAreaElement;
      expect(publicHeaders.value).toContain('"X-Key"');
      expect(publicHeaders.value).not.toContain("mcpServers");

      // The paste-config box retains the original blob (not overwritten).
      expect(pasteBox.value).toContain("mcpServers");
    });

    it("shows an inline error for a rejected stdio entry", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      const jsonTextarea = screen.getByPlaceholderText(/mcpServers/i);
      fireEvent.change(jsonTextarea, {
        target: {
          value: JSON.stringify({
            mcpServers: {
              "local-runner": {
                command: "npx",
                args: ["some-server"],
              },
            },
          }),
        },
      });
      await user.click(screen.getByRole("button", { name: /parse config/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/stdio servers are not supported/i),
        ).toBeInTheDocument();
      });
    });

    it("discovers tools and renders the discovered list", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      await user.click(
        screen.getByRole("button", {
          name: /test connection & discover tools/i,
        }),
      );

      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument();
      });
      expect(screen.getByText("add")).toBeInTheDocument();
      expect(screen.getByText("multiply")).toBeInTheDocument();
    });

    it("Save draft posts is_published=false and returns to the catalog", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const getBody = captureCreateBody();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.type(screen.getByLabelText(/^name/i), "my-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      await user.click(screen.getByRole("button", { name: /^save draft/i }));

      await waitFor(() => expect(getBody()).not.toBeNull());
      const body = getBody()!;
      expect(body).toMatchObject({
        name: "my-mcp",
        tool_source: "mcp",
        mcp_server_url: "https://example.com/mcp",
        is_published: false,
        is_active: true,
        requires_auth: false,
        auth_type: null,
      });
      // Global row — the org-scoped custom tier is retired (RFC §6.6).
      expect(body.organization_id).toBeUndefined();
      expect(
        screen.getByRole("button", { name: /Create new platform tool/i }),
      ).toBeInTheDocument();
      expect(screen.queryByLabelText(/^name/i)).not.toBeInTheDocument();
    });

    it("Publish posts is_published=true after a successful discover", async () => {
      // Publish is gated on a successful "Test & discover" so the tool list is
      // captured (publishing without discover leaves the agent drawer empty).
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const getBody = captureCreateBody();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.type(screen.getByLabelText(/^name/i), "my-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      await user.click(
        screen.getByRole("button", {
          name: /test connection & discover tools/i,
        }),
      );
      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /^publish$/i }));

      await waitFor(() => expect(getBody()).not.toBeNull());
      expect(getBody()!.is_published).toBe(true);
    });

    it("api-key mode: save persists the {{KEY}} template + requires_auth + auth_type=api_key", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const getBody = captureCreateBody();
      render(<PlatformToolsManager {...authorProps()} />);

      // Switch auth mode to Static API key.
      await user.selectOptions(
        screen.getByLabelText(/authentication/i),
        "api_key",
      );
      await user.type(screen.getByLabelText(/^name/i), "keyed-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      const secretBox = screen.getByLabelText(
        /secret header template/i,
      ) as HTMLTextAreaElement;
      fireEvent.change(secretBox, {
        target: { value: '{ "Authorization": "Bearer {{KEY}}" }' },
      });
      await user.click(screen.getByRole("button", { name: /^save draft/i }));

      await waitFor(() => expect(getBody()).not.toBeNull());
      const body = getBody()!;
      expect(body.mcp_secret_headers_input).toEqual({
        Authorization: "Bearer {{KEY}}",
      });
      expect(body.requires_auth).toBe(true);
      expect(body.auth_type).toBe("api_key");
      // The transient test key is NOT persisted — only the template is.
      expect(body.mcp_secret_headers_input.Authorization).toContain("{{KEY}}");
    });

    it("allows a platform API key fallback while still offering org override", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const getBody = captureCreateBody();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.selectOptions(
        screen.getByLabelText(/authentication/i),
        "api_key",
      );
      await user.type(screen.getByLabelText(/^name/i), "platform-key-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      fireEvent.change(screen.getByLabelText(/secret header template/i), {
        target: { value: '{ "X-API-Key": "platform-key" }' },
      });
      await user.click(screen.getByRole("button", { name: /^save draft/i }));

      await waitFor(() => expect(getBody()).not.toBeNull());
      expect(getBody()!.requires_auth).toBe(false);
      expect(getBody()!.auth_type).toBe("api_key");
    });

    it("api-key mode: discover substitutes the test key into {{KEY}}", async () => {
      // Capture the discover request body to confirm the test key is substituted
      // into the {{KEY}} placeholder for the one-shot discover call.
      let discoverBody: {
        url: string;
        headers?: Record<string, string>;
      } | null = null;
      server.use(
        http.post(
          `${API_BASE_URL}/api/v1/tools/mcp/discover`,
          async ({ request }) => {
            discoverBody = (await request.json()) as {
              url: string;
              headers?: Record<string, string>;
            };
            return HttpResponse.json({
              tools: [
                {
                  name: "add",
                  description: "Add two numbers",
                  input_schema: null,
                },
              ],
            });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.selectOptions(
        screen.getByLabelText(/authentication/i),
        "api_key",
      );
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      const secretBox = screen.getByLabelText(
        /secret header template/i,
      ) as HTMLTextAreaElement;
      fireEvent.change(secretBox, {
        target: { value: '{ "Authorization": "Bearer {{KEY}}" }' },
      });
      await user.type(
        screen.getByLabelText(/test api key/i),
        "test-secret-123",
      );
      await user.click(
        screen.getByRole("button", {
          name: /test connection & discover tools/i,
        }),
      );

      await waitFor(() => expect(discoverBody).not.toBeNull());
      expect(discoverBody!.headers).toEqual({
        Authorization: "Bearer test-secret-123",
      });
    });

    it("supports OAuth MCP configs without asking the platform admin for a key", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      let captured: Record<string, any> | null = null;
      server.use(
        http.post(
          `${API_BASE_URL}/api/v1/tools/platform`,
          async ({ request }) => {
            captured = (await request.json()) as Record<string, any>;
            return HttpResponse.json({
              id: "oauth-mcp-tool",
              name: captured.name,
              tool_source: "mcp",
              auth_type: "oauth2",
              requires_auth: true,
              is_published: false,
            });
          },
        ),
      );
      render(<PlatformToolsManager {...authorProps()} />);

      await user.selectOptions(
        screen.getByLabelText(/authentication/i),
        "oauth2",
      );
      await user.type(screen.getByLabelText(/^name/i), "oauth-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://oauth.example/mcp",
      );
      await user.click(screen.getByRole("button", { name: /^save draft/i }));

      await waitFor(() => expect(captured).not.toBeNull());
      expect(captured).toMatchObject({
        auth_type: "oauth2",
        requires_auth: true,
      });
      expect(captured).not.toHaveProperty("mcp_secret_headers_input");
      expect(screen.queryByLabelText(/test api key/i)).not.toBeInTheDocument();
    });

    it("keeps OAuth publish disabled until the function catalog is discovered", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.selectOptions(
        screen.getByLabelText(/authentication/i),
        "oauth2",
      );
      await user.type(screen.getByLabelText(/^name/i), "oauth-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://oauth.example/mcp",
      );

      expect(screen.getByRole("button", { name: /^publish$/i })).toBeDisabled();
      expect(
        screen.getByRole("button", { name: /authorize & discover tools/i }),
      ).toBeEnabled();
    });

    it("saves an OAuth draft and opens discovery from the author form", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      let createBody: Record<string, any> | null = null;
      server.use(
        http.post(
          `${API_BASE_URL}/api/v1/tools/platform`,
          async ({ request }) => {
            createBody = (await request.json()) as Record<string, any>;
            return HttpResponse.json(
              createMockPlatformTool({
                id: "oauth-draft-tool",
                name: createBody.name,
                tool_source: "mcp",
                auth_type: "oauth2",
                requires_auth: true,
                is_published: false,
              }),
            );
          },
        ),
        http.get(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId/oauth`,
          ({ params }) => {
            expect(params.toolId).toBe("oauth-draft-tool");
            return HttpResponse.json({
              auth_url: "https://auth.example/authorize",
            });
          },
        ),
      );
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

      render(<PlatformToolsManager {...authorProps()} />);
      await user.selectOptions(
        screen.getByLabelText(/authentication/i),
        "oauth2",
      );
      await user.type(screen.getByLabelText(/^name/i), "oauth-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://oauth.example/mcp",
      );
      await user.click(
        screen.getByRole("button", { name: /authorize & discover tools/i }),
      );

      await waitFor(() => expect(createBody).not.toBeNull());
      expect(createBody).toMatchObject({
        is_published: false,
        auth_type: "oauth2",
        requires_auth: true,
      });
      await waitFor(() => {
        expect(openSpy).toHaveBeenCalledWith(
          "https://auth.example/authorize",
          "_blank",
        );
      });
      openSpy.mockRestore();
    });

    it("maps parsed OAuth and secret-header metadata into the structured form", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      server.use(
        http.post(`${API_BASE_URL}/api/v1/tools/mcp/parse`, () =>
          HttpResponse.json({
            servers: [
              {
                name: "calendar",
                url: "https://calendar.example/mcp",
                headers: { "X-Client": "24x7-ai" },
                secret_headers: {},
                auth_type: "oauth2",
                requires_auth: true,
                auth_config: {
                  provider: "mcp",
                  auth_url: "https://auth.example/authorize",
                  token_url: "https://auth.example/token",
                  scopes: ["calendar.read"],
                },
              },
            ],
            errors: [],
          }),
        ),
      );
      render(<PlatformToolsManager {...authorProps()} />);

      fireEvent.change(screen.getByPlaceholderText(/mcpServers/i), {
        target: {
          value:
            '{"servers":{"calendar":{"url":"https://calendar.example/mcp"}}}',
        },
      });
      await user.click(screen.getByRole("button", { name: /parse config/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/authentication/i)).toHaveValue("oauth2");
      });
      expect(screen.getByLabelText(/authorization endpoint/i)).toHaveValue(
        "https://auth.example/authorize",
      );
      expect(screen.getByLabelText(/scopes/i)).toHaveValue("calendar.read");
    });

    it("requires name + url before saving (draft + publish disabled)", async () => {
      render(<PlatformToolsManager {...authorProps()} />);
      expect(
        screen.getByRole("button", { name: /^save draft/i }),
      ).toBeDisabled();
      expect(screen.getByRole("button", { name: /^publish$/i })).toBeDisabled();
    });

    it("marks Name and Server URL as required (optional fields unmarked)", () => {
      // The author form has no field-level validation hints; the admin can't
      // tell what's mandatory. Name + Server URL (the save guard) get a red
      // asterisk; optional fields (Description, Public headers) do not.
      render(<PlatformToolsManager {...authorProps()} />);
      const nameLabel = document.querySelector('label[for="mcp-name"]');
      const urlLabel = document.querySelector('label[for="mcp-url"]');
      expect(nameLabel?.textContent).toMatch(/\*/);
      expect(urlLabel?.textContent).toMatch(/\*/);
      const descLabel = document.querySelector('label[for="mcp-description"]');
      const pubHeadersLabel = document.querySelector(
        'label[for="mcp-public-headers"]',
      );
      expect(descLabel?.textContent).not.toMatch(/\*/);
      expect(pubHeadersLabel?.textContent).not.toMatch(/\*/);
    });

    it("Publish is disabled until Test & discover succeeds (Save draft still allowed)", async () => {
      // Publishing without discovering leaves the agent tool drawer empty (no
      // tool_functions_schema). Publish is gated on a successful discover; a
      // draft is still allowed without discover (drafts aren't shown to orgs).
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.type(screen.getByLabelText(/^name/i), "my-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );

      // Name + url filled, but no discover yet → Publish disabled, Save draft enabled.
      expect(screen.getByRole("button", { name: /^publish$/i })).toBeDisabled();
      expect(
        screen.getByRole("button", { name: /^save draft/i }),
      ).toBeEnabled();

      await user.click(
        screen.getByRole("button", {
          name: /test connection & discover tools/i,
        }),
      );
      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument();
      });

      // After a successful discover, Publish is enabled.
      expect(screen.getByRole("button", { name: /^publish$/i })).toBeEnabled();
    });

    it("persists discovered tools as tool_functions_schema so the agent panel shows them", async () => {
      // After publishing a custom MCP server, the agent tool-config drawer reads
      // `tool.tool_functions_schema.functions` to render the tool list with
      // enable/disable toggles (parity with native tool cards). If the authoring
      // dialog drops the discovered tools on save, the drawer is empty — the bug.
      // The save payload must carry the discovered tools mapped to
      // { name, description, parameters: input_schema }.
      server.use(
        http.post(`${API_BASE_URL}/api/v1/tools/mcp/discover`, () =>
          HttpResponse.json({
            tools: [
              {
                name: "read_wiki_contents",
                description: "View documentation about a GitHub repository.",
                input_schema: {
                  type: "object",
                  properties: {
                    repoName: { type: "string", description: "owner/repo" },
                  },
                  required: ["repoName"],
                },
              },
              {
                name: "ask_question",
                description: "Ask a question about a repository.",
                input_schema: {
                  type: "object",
                  properties: {
                    repoName: { type: "string" },
                    question: { type: "string" },
                  },
                  required: ["repoName", "question"],
                },
              },
            ],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const getBody = captureCreateBody();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.type(screen.getByLabelText(/^name/i), "deepwiki");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://mcp.deepwiki.com/mcp",
      );
      await user.click(
        screen.getByRole("button", {
          name: /test connection & discover tools/i,
        }),
      );
      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /^publish$/i }));

      await waitFor(() => expect(getBody()).not.toBeNull());
      const body = getBody()!;
      expect(body.tool_functions_schema).toEqual({
        functions: [
          {
            name: "read_wiki_contents",
            description: "View documentation about a GitHub repository.",
            parameters: {
              type: "object",
              properties: {
                repoName: { type: "string", description: "owner/repo" },
              },
              required: ["repoName"],
            },
          },
          {
            name: "ask_question",
            description: "Ask a question about a repository.",
            parameters: {
              type: "object",
              properties: {
                repoName: { type: "string" },
                question: { type: "string" },
              },
              required: ["repoName", "question"],
            },
          },
        ],
      });
    });

    it("omits tool_functions_schema when no tools were discovered", async () => {
      // Saving without discovering must not send an empty {functions:[]} — the
      // backend stores null and the drawer simply shows no list (same as today).
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      const getBody = captureCreateBody();
      render(<PlatformToolsManager {...authorProps()} />);

      await user.type(screen.getByLabelText(/^name/i), "my-mcp");
      await user.type(
        screen.getByLabelText(/server url/i),
        "https://example.com/mcp",
      );
      await user.click(screen.getByRole("button", { name: /^save draft/i }));

      await waitFor(() => expect(getBody()).not.toBeNull());
      const body = getBody()!;
      expect(body.tool_functions_schema).toBeUndefined();
    });
  });

  describe("Manage flow", () => {
    it("shows Manage existing tools as the default active tab (no click needed)", () => {
      // The platform-tools page lands the admin on the tool list, not the
      // author form. Manage content is rendered on mount; the author-only
      // paste-config box is not.
      render(<PlatformToolsManager {...baseProps()} />);
      expect(
        screen.getByText(/Drafts are visible only to platform admins/i),
      ).toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText(/mcpServers/i),
      ).not.toBeInTheDocument();
    });

    it("lists platform tools with a Draft badge + Publish + delete actions", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      // The mock platform tool 'test_tool' renders as 'test tool'. The default
      // mock has no is_published, so it shows as a Draft badge with a Publish button.
      await waitFor(() => {
        expect(screen.getByText("Draft")).toBeInTheDocument();
      });
      expect(
        screen.getByRole("button", { name: /publish/i }),
      ).toBeInTheDocument();
      // Delete is the ghost icon button.
      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
    });

    it("shows the MCP catalog state and starts platform OAuth discovery", async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                auth_type: "oauth2",
                requires_auth: true,
                tool_functions_schema: null,
                is_published: true,
              }),
            ],
          }),
        ),
        http.get(`${API_BASE_URL}/api/v1/tools/platform/:toolId/oauth`, () =>
          HttpResponse.json({ auth_url: "https://auth.example/authorize" }),
        ),
      );
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();

      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByText(/Catalog unavailable — authenticate to discover/i),
        ).toBeInTheDocument();
      });
      const discoverButton = screen.getByRole("button", {
        name: /discover with oauth/i,
      });
      expect(discoverButton).toBeInTheDocument();

      await user.click(discoverButton);

      await waitFor(() => {
        expect(openSpy).toHaveBeenCalledWith(
          "https://auth.example/authorize",
          "_blank",
        );
      });
      openSpy.mockRestore();
    });

    it("opens the exposed function catalog drawer with function details", async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                name: "Linear",
                auth_type: "oauth2",
                is_published: true,
                tool_functions_schema: {
                  functions: [
                    {
                      type: "function",
                      name: "list_issues",
                      description: "List issues for a team",
                      parameters: {
                        type: "object",
                        properties: {
                          team_id: {
                            type: "string",
                            description: "Linear team identifier",
                          },
                        },
                        required: ["team_id"],
                      },
                    },
                  ],
                },
              }),
            ],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      const exposedFunctions = await screen.findByRole("button", {
        name: /exposed functions/i,
      });
      await user.click(exposedFunctions);

      expect(
        await screen.findByRole("heading", { name: /linear functions/i }),
      ).toBeInTheDocument();
      expect(screen.getByText("List issues for a team")).toBeInTheDocument();
      expect(screen.queryByText("team_id")).not.toBeInTheDocument();
      const functionToggle = screen.getByRole("button", {
        name: /list_issues/i,
      });
      expect(functionToggle).toHaveAttribute("aria-expanded", "false");
      await user.click(functionToggle);
      expect(functionToggle).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByText("list_issues")).toBeInTheDocument();
      expect(screen.getByText("team_id")).toBeInTheDocument();
      expect(screen.getByText(/required/i)).toBeInTheDocument();
    });

    it("opens the same exposed function catalog drawer for native tools", async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "legacy",
                name: "Google Calendar",
                auth_type: "oauth2",
                is_published: true,
                tool_functions_schema: {
                  functions: [
                    {
                      type: "function",
                      name: "create_event",
                      description: "Create a calendar event",
                      parameters: {
                        type: "object",
                        properties: {
                          start_time: {
                            type: "string",
                            description: "Event start time",
                          },
                        },
                        required: ["start_time"],
                      },
                    },
                  ],
                },
              }),
            ],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await user.click(
        await screen.findByRole("button", {
          name: /view exposed functions for google calendar/i,
        }),
      );

      expect(
        await screen.findByRole("heading", {
          name: /google calendar functions/i,
        }),
      ).toBeInTheDocument();
      expect(screen.getByText("Create a calendar event")).toBeInTheDocument();
      expect(screen.getByText("create_event")).toBeInTheDocument();

      await user.click(
        screen.getByRole("button", { name: /create_event/i }),
      );
      expect(screen.getByText("start_time")).toBeInTheDocument();
      expect(screen.getByText("Event start time")).toBeInTheDocument();
    });

    it("filters the exposed function catalog from the drawer search", async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                name: "Linear",
                auth_type: "oauth2",
                is_published: true,
                tool_functions_schema: {
                  functions: [
                    {
                      type: "function",
                      name: "list_issues",
                      description: "List issues for a team",
                      parameters: {
                        type: "object",
                        properties: {
                          team_id: {
                            type: "string",
                            description: "Linear team identifier",
                          },
                        },
                      },
                    },
                    {
                      type: "function",
                      name: "create_comment",
                      description: "Add a comment to an issue",
                      parameters: {
                        type: "object",
                        properties: {
                          body: {
                            type: "string",
                            description: "Comment body",
                          },
                        },
                      },
                    },
                  ],
                },
              }),
            ],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await user.click(
        await screen.findByRole("button", { name: /exposed functions/i }),
      );

      const search = screen.getByRole("searchbox", {
        name: /search functions/i,
      });
      expect(screen.getByText("list_issues")).toBeInTheDocument();
      expect(screen.getByText("create_comment")).toBeInTheDocument();

      await user.type(search, "comment");

      expect(screen.queryByText("list_issues")).not.toBeInTheDocument();
      expect(screen.getByText("create_comment")).toBeInTheDocument();
      expect(screen.getByText(/1 of 2 functions/i)).toBeInTheDocument();

      await user.click(
        screen.getByRole("button", { name: /clear function search/i }),
      );
      expect(search).toHaveValue("");
      expect(screen.getByText("list_issues")).toBeInTheDocument();

      await user.type(search, "team identifier");
      expect(screen.getByText("No functions found")).toBeInTheDocument();
    });

    it("lets platform admins expand long tool descriptions in the catalog", async () => {
      const longDescription =
        "Connects the workspace to the remote MCP server and exposes the functions needed to search, inspect, and update records for this organization. ".repeat(
          2,
        );
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                name: "Linear",
                description: longDescription,
                auth_type: "oauth2",
                is_published: true,
                tool_functions_schema: { functions: [] },
              }),
            ],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      const showDescription = await screen.findByRole("button", {
        name: /show full description/i,
      });
      expect(showDescription).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByText(longDescription)).not.toBeInTheDocument();

      await user.click(showDescription);

      expect(showDescription).toHaveAttribute("aria-expanded", "true");
      const description = document.getElementById(
        showDescription.getAttribute("aria-controls") || "",
      );
      expect(description).toHaveTextContent(longDescription.trim());
    });

    it("lets platform admins expand long descriptions and separates parameter surfaces", async () => {
      const longDescription =
        "Searches the workspace for issues matching the supplied filters, then returns a paginated result set with the fields needed to triage, prioritize, and route work to the right team. ".repeat(
          2,
        );
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                name: "Linear",
                auth_type: "oauth2",
                is_published: true,
                tool_functions_schema: {
                  functions: [
                    {
                      type: "function",
                      name: "search_issues",
                      description: longDescription,
                      parameters: {
                        type: "object",
                        properties: {
                          query: {
                            type: "string",
                            description: "Search expression",
                          },
                        },
                        required: ["query"],
                      },
                    },
                  ],
                },
              }),
            ],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await user.click(
        await screen.findByRole("button", { name: /exposed functions/i }),
      );

      const showDescription = screen.getByRole("button", {
        name: /show full description/i,
      });
      expect(showDescription).toHaveAttribute("aria-expanded", "false");
      expect(screen.queryByText(longDescription)).not.toBeInTheDocument();

      await user.click(showDescription);

      expect(showDescription).toHaveAttribute("aria-expanded", "true");
      const description = document.getElementById(
        showDescription.getAttribute("aria-controls") || "",
      );
      expect(description).toHaveTextContent(longDescription.trim());

      const functionToggle = screen.getByRole("button", {
        name: /search_issues/i,
      });
      await user.click(functionToggle);
      expect(
        screen.getByText("Parameters").closest("div.border-t"),
      ).toHaveClass("bg-slate-100/70");
      expect(screen.getByText("query").closest("div.rounded-xl")).toHaveClass(
        "bg-white",
      );
    });

    it("only marks the MCP row being discovered as busy", async () => {
      let resolveOAuth: (() => void) | undefined;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                id: "linear-tool",
                name: "Linear",
                tool_source: "mcp",
                auth_type: "oauth2",
                is_published: true,
              }),
              createMockPlatformTool({
                id: "notion-tool",
                name: "Notion",
                tool_source: "mcp",
                auth_type: "oauth2",
                is_published: true,
              }),
            ],
          }),
        ),
        http.get(
          `${API_BASE_URL}/api/v1/tools/platform/linear-tool/oauth`,
          async () => {
            await new Promise<void>((resolve) => {
              resolveOAuth = resolve;
            });
            return HttpResponse.json({
              auth_url: "https://auth.example/linear",
            });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      const linearButton = await screen.findByRole("button", {
        name: /discover with oauth for linear/i,
      });
      const notionButton = screen.getByRole("button", {
        name: /discover with oauth for notion/i,
      });
      await user.click(linearButton);

      await waitFor(() => expect(linearButton).toBeDisabled());
      expect(notionButton).not.toBeDisabled();
      resolveOAuth?.();
    });

    it("publish button calls the publish endpoint", async () => {
      let publishedCalled = false;
      server.use(
        http.post(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId/publish`,
          () => {
            publishedCalled = true;
            return HttpResponse.json({ id: "tool-1", is_published: true });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /publish/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /publish/i }));

      await waitFor(() => expect(publishedCalled).toBe(true));
    });

    it("delete opens a type-to-confirm dialog and deletes with force when in use", async () => {
      // The default usage mock returns count=2 (in use), so the confirm must
      // send `?force=true` after the admin types "Delete".
      let deleteUrl: string | null = null;
      server.use(
        http.delete(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId`,
          ({ request }) => {
            deleteUrl = request.url;
            return HttpResponse.json({ deleted: true });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /delete/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /delete/i }));

      // The shared confirm dialog opens; the in-use warnings are visible.
      await waitFor(() => {
        expect(screen.getByText(/Used by 2 agents/i)).toBeInTheDocument();
      });
      await user.type(screen.getByPlaceholderText("Delete"), "Delete");
      await user.click(
        screen.getByRole("button", { name: /Delete MCP Server/i }),
      );

      await waitFor(() => expect(deleteUrl).not.toBeNull());
      expect(deleteUrl).toContain("tool-1");
      expect(deleteUrl).toContain("force=true");
    });

    it("does not render a Delete button for legacy (code-backed) tools", async () => {
      // Legacy tools are re-seeded by the worker on startup — hard-delete is the
      // wrong lever, so the Manage view hides the Delete affordance entirely.
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ tool_source: "legacy" })],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(screen.getByText("Draft")).toBeInTheDocument();
      });
      expect(
        screen.queryByRole("button", { name: /delete/i }),
      ).not.toBeInTheDocument();
    });

    it("unpublish surfaces an info toast with the usage count", async () => {
      const { toast } = await import("sonner");
      // Default mock tool has is_published undefined (renders as Draft) — flip
      // it to Published so the toggle button is "Unpublish".
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ is_published: true })],
          }),
        ),
        http.post(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId/unpublish`,
          () => HttpResponse.json({ id: "tool-1", is_published: false }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /unpublish/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /unpublish/i }));

      // The default usage mock returns count=2 (Alex + Sam).
      await waitFor(() => {
        expect(toast.info).toHaveBeenCalledWith(
          expect.stringMatching(/2 agents currently use this tool/i),
        );
      });
    });

    it("resets the type-to-confirm input between consecutive deletes", async () => {
      // Regression: the McpToolDeleteDialog wrapper must mount a FRESH
      // DeleteConfirmationDialog per delete (conditional render). An always-
      // mounted dialog would leak the typed "Delete" into the next dialog,
      // enabling the confirm button without re-typing — defeating the
      // type-to-confirm gate the user explicitly asked for.
      // Track deletions so the GET list reflects them (the real backend would).
      const deleted = new Set<string>();
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                id: "mcp-a",
                name: "alpha",
                tool_source: "mcp",
              }),
              createMockPlatformTool({
                id: "mcp-b",
                name: "beta",
                tool_source: "mcp",
              }),
            ].filter((t) => !deleted.has(t.id)),
          }),
        ),
        // Unused for both — no usage warnings.
        http.get(`${API_BASE_URL}/api/v1/tools/platform/:toolId/usage`, () =>
          HttpResponse.json({ count: 0, agents: [] }),
        ),
        http.delete(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId`,
          ({ params }) => {
            deleted.add(params.toolId as string);
            return HttpResponse.json({ deleted: true });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(screen.getAllByRole("button", { name: /delete/i })).toHaveLength(
          2,
        );
      });

      // Delete the first MCP tool: type "Delete" + confirm.
      await user.click(screen.getAllByRole("button", { name: /delete/i })[0]);
      await waitFor(() =>
        expect(screen.getByPlaceholderText("Delete")).toBeInTheDocument(),
      );
      await user.type(screen.getByPlaceholderText("Delete"), "Delete");
      await user.click(
        screen.getByRole("button", { name: /Delete MCP Server/i }),
      );

      // The dialog closes after the delete; only one delete button remains.
      await waitFor(() => {
        expect(screen.getAllByRole("button", { name: /delete/i })).toHaveLength(
          1,
        );
      });

      // Open the delete dialog for the SECOND tool.
      await user.click(screen.getAllByRole("button", { name: /delete/i })[0]);
      await waitFor(() =>
        expect(screen.getByPlaceholderText("Delete")).toBeInTheDocument(),
      );

      // The confirm input must be EMPTY (not pre-filled with the previous
      // "Delete"), and the confirm button must be disabled until re-typed.
      expect(
        (screen.getByPlaceholderText("Delete") as HTMLInputElement).value,
      ).toBe("");
      expect(
        screen.getByRole("button", { name: /Delete MCP Server/i }),
      ).toBeDisabled();

      // Clicking the empty confirm input's button does nothing — type "Delete" first.
      await user.type(screen.getByPlaceholderText("Delete"), "Delete");
      expect(
        screen.getByRole("button", { name: /Delete MCP Server/i }),
      ).toBeEnabled();
    });

    it("does not show a Premium badge for non-premium tools", async () => {
      // Default mock tool is NOT premium — no badge, and the toggle reads
      // "Mark premium".
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(screen.getByText("test tool")).toBeInTheDocument();
      });
      expect(screen.queryByText("Premium")).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /mark premium/i }),
      ).toBeInTheDocument();
    });

    it("shows a Premium badge + Unmark premium for a premium tool", async () => {
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ is_premium: true })],
          }),
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(screen.getByText("Premium")).toBeInTheDocument();
      });
      expect(
        screen.getByRole("button", { name: /unmark premium/i }),
      ).toBeInTheDocument();
    });

    it("mark/unmark premium calls the dedicated endpoint with the new flag", async () => {
      const premiumBodies: Array<{ is_premium: boolean }> = [];
      server.use(
        http.post(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId/premium`,
          async ({ params, request }) => {
            const body = (await request.json()) as { is_premium: boolean };
            premiumBodies.push(body);
            return HttpResponse.json({
              id: params.toolId as string,
              is_premium: body.is_premium,
            });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /mark premium/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /mark premium/i }));
      await waitFor(() => expect(premiumBodies).toHaveLength(1));
      expect(premiumBodies[0]).toEqual({ is_premium: true });
    });

    it("unmark premium sends is_premium=false for an already-premium tool", async () => {
      const premiumBodies: Array<{ is_premium: boolean }> = [];
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ is_premium: true })],
          }),
        ),
        http.post(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId/premium`,
          async ({ request }) => {
            const body = (await request.json()) as { is_premium: boolean };
            premiumBodies.push(body);
            return HttpResponse.json({
              id: "tool-1",
              is_premium: body.is_premium,
            });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /unmark premium/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /unmark premium/i }));

      await waitFor(() => expect(premiumBodies).toHaveLength(1));
      expect(premiumBodies[0]).toEqual({ is_premium: false });
    });

    it("Edit loads the MCP server into the author form; Save changes PUTs with publish state preserved", async () => {
      let putUrl: string | null = null;
      let putBody: Record<string, any> | null = null;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                mcp_server_url: "https://mcp.example.com",
                mcp_server_headers: { "X-Client": "24x7" },
                mcp_secret_headers_configured: true,
                description: "My MCP server",
                requires_auth: true,
                auth_type: "api_key",
                is_premium: true,
                is_published: true,
              }),
            ],
          }),
        ),
        http.put(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId`,
          async ({ params, request }) => {
            putUrl = params.toolId as string;
            putBody = (await request.json()) as Record<string, any>;
            return HttpResponse.json({ id: "tool-1", ...putBody });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /edit/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /edit/i }));

      // Author view opens with the editing banner + prefilled structured fields.
      // (The banner text is split across elements: "Editing" + the tool name.)
      expect(screen.getByText(/editing/i)).toBeInTheDocument();
      expect(screen.getByText("test tool")).toBeInTheDocument();
      expect((screen.getByLabelText(/^name/i) as HTMLInputElement).value).toBe(
        "test_tool",
      );
      expect(
        (screen.getByLabelText(/server url/i) as HTMLInputElement).value,
      ).toBe("https://mcp.example.com");
      expect(
        (screen.getByLabelText(/description/i) as HTMLInputElement).value,
      ).toBe("My MCP server");
      // Public headers come back from the row; secret headers never do (encrypted
      // at rest) — and the keep-existing note is shown because they are configured.
      expect(
        (screen.getByLabelText(/public headers/i) as HTMLTextAreaElement).value,
      ).toContain('"X-Client"');
      expect(
        (
          screen.getByLabelText(
            /secret header template/i,
          ) as HTMLTextAreaElement
        ).value,
      ).toBe("");
      expect(
        screen.getByText(/leave the field blank to keep them/i),
      ).toBeInTheDocument();
      expect(screen.getByLabelText(/premium tool/i)).toBeChecked();

      await user.click(screen.getByRole("button", { name: /save changes/i }));

      await waitFor(() => expect(putBody).not.toBeNull());
      expect(putUrl).toBe("tool-1");
      // Publish state preserved from the row; premium checkbox flows through.
      expect(putBody!.is_published).toBe(true);
      expect(putBody!.is_premium).toBe(true);
      expect(putBody!.mcp_server_url).toBe("https://mcp.example.com");
      // No discover in this session -> stored schema untouched (omitted).
      expect(putBody!.tool_functions_schema).toBeUndefined();
      // Blank secret field on edit: omit mcp_secret_headers_input so stored
      // secrets are preserved (backend only replaces when a non-empty value is sent).
      expect(putBody!.mcp_secret_headers_input).toBeUndefined();
      // Public headers still present when unchanged.
      expect(putBody!.mcp_server_headers).toEqual({ "X-Client": "24x7" });

      // After a successful save the panel returns to the manage view.
      await waitFor(() => {
        expect(
          screen.getByText(/drafts are visible only to platform admins/i),
        ).toBeInTheDocument();
      });
    });

    it("Edit discover sends tool_id so stored secrets are reused without re-paste", async () => {
      let discoverBody: {
        url?: string;
        tool_id?: string;
        headers?: Record<string, string>;
      } | null = null;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                mcp_server_url: "https://mcp.example.com",
                mcp_server_headers: { "X-Client": "24x7" },
                mcp_secret_headers_configured: true,
                requires_auth: true,
                auth_type: "api_key",
                is_published: true,
              }),
            ],
          }),
        ),
        http.post(
          `${API_BASE_URL}/api/v1/tools/mcp/discover`,
          async ({ request }) => {
            discoverBody = (await request.json()) as typeof discoverBody;
            return HttpResponse.json({
              tools: [
                {
                  name: "ping",
                  description: "Ping",
                  input_schema: null,
                },
              ],
            });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /edit/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /edit/i }));

      // Secret field stays blank (stored secrets); discover must still pass tool_id.
      expect(
        (
          screen.getByLabelText(
            /secret header template/i,
          ) as HTMLTextAreaElement
        ).value,
      ).toBe("");

      await user.click(
        screen.getByRole("button", {
          name: /test connection & discover tools/i,
        }),
      );

      await waitFor(() => expect(discoverBody).not.toBeNull());
      expect(discoverBody!.tool_id).toBe("tool-1");
      expect(discoverBody!.url).toBe("https://mcp.example.com");
      expect(discoverBody!.headers).toEqual({ "X-Client": "24x7" });
    });

    it("saves OAuth metadata before starting discovery from edit mode", async () => {
      let putBody: Record<string, any> | null = null;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                id: "linear-tool",
                name: "Linear",
                tool_source: "mcp",
                mcp_server_url: "https://mcp.linear.app/mcp",
                auth_type: "oauth2",
                requires_auth: true,
                is_published: true,
              }),
            ],
          }),
        ),
        http.put(
          `${API_BASE_URL}/api/v1/tools/platform/linear-tool`,
          async ({ request }) => {
            putBody = (await request.json()) as Record<string, any>;
            return HttpResponse.json(
              createMockPlatformTool({
                id: "linear-tool",
                name: "Linear",
                tool_source: "mcp",
                auth_type: "oauth2",
                requires_auth: true,
                is_published: true,
              }),
            );
          },
        ),
        http.get(
          `${API_BASE_URL}/api/v1/tools/platform/linear-tool/oauth`,
          () =>
            HttpResponse.json({
              auth_url: "https://auth.example/linear",
            }),
        ),
      );
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await user.click(await screen.findByRole("button", { name: /edit/i }));
      await user.click(
        screen.getByRole("button", { name: /authorize & discover tools/i }),
      );

      await waitFor(() => expect(putBody).not.toBeNull());
      expect(putBody).toMatchObject({
        auth_type: "oauth2",
        requires_auth: true,
        is_published: true,
      });
      await waitFor(() =>
        expect(openSpy).toHaveBeenCalledWith(
          "https://auth.example/linear",
          "_blank",
        ),
      );
      openSpy.mockRestore();
    });

    it("preserves a platform-owned API key without requiring an org key on edit", async () => {
      let putBody: Record<string, any> | null = null;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                mcp_server_url: "https://mcp.example.com",
                auth_type: "api_key",
                requires_auth: false,
                mcp_secret_headers_configured: true,
                is_published: true,
              }),
            ],
          }),
        ),
        http.put(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId`,
          async ({ request }) => {
            putBody = (await request.json()) as Record<string, any>;
            return HttpResponse.json({ id: "tool-1", ...putBody });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /edit/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /edit/i }));
      await user.click(screen.getByRole("button", { name: /save changes/i }));

      await waitFor(() => expect(putBody).not.toBeNull());
      expect(putBody!.auth_type).toBe("api_key");
      expect(putBody!.requires_auth).toBe(false);
    });

    it("Edit clearing public headers PUTs empty object so the clear persists", async () => {
      let putBody: Record<string, any> | null = null;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({
                tool_source: "mcp",
                mcp_server_url: "https://mcp.example.com",
                mcp_server_headers: { Authorization: "Bearer stale" },
                requires_auth: false,
                is_published: true,
              }),
            ],
          }),
        ),
        http.put(
          `${API_BASE_URL}/api/v1/tools/platform/:toolId`,
          async ({ request }) => {
            putBody = (await request.json()) as Record<string, any>;
            return HttpResponse.json({ id: "tool-1", ...putBody });
          },
        ),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /edit/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /edit/i }));

      const publicBox = screen.getByLabelText(
        /public headers/i,
      ) as HTMLTextAreaElement;
      expect(publicBox.value).toContain("Authorization");
      fireEvent.change(publicBox, { target: { value: "" } });

      await user.click(screen.getByRole("button", { name: /save changes/i }));

      await waitFor(() => expect(putBody).not.toBeNull());
      expect(putBody!.mcp_server_headers).toEqual({});
    });

    it("Cancel exits the edit session without PUTting", async () => {
      let putCalled = false;
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ tool_source: "mcp" })],
          }),
        ),
        http.put(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, () => {
          putCalled = true;
          return HttpResponse.json({ id: "tool-1" });
        }),
      );
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /edit/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /edit/i }));
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /cancel/i }),
        ).toBeInTheDocument();
      });
      await user.click(screen.getByRole("button", { name: /cancel/i }));

      // Back on the manage list; nothing was sent to the backend.
      expect(
        screen.getByText(/drafts are visible only to platform admins/i),
      ).toBeInTheDocument();
      expect(putCalled).toBe(false);
    });
  });

  it('has no catalog tab or "From catalog" button', () => {
    render(<PlatformToolsManager {...baseProps()} />);
    expect(
      screen.queryByRole("button", { name: /from catalog/i }),
    ).not.toBeInTheDocument();
  });

  describe("platform-admin messaging", () => {
    it("opens MCP configuration from a create button instead of a tab", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      expect(
        screen.getByRole("button", { name: /Create new platform tool/i }),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /Configure MCP server/i }),
      ).not.toBeInTheDocument();

      await user.click(
        screen.getByRole("button", { name: /Create new platform tool/i }),
      );

      expect(
        await screen.findByRole("heading", { name: /Configure MCP server/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("uses layered form surfaces to separate the MCP controls", async () => {
      const { userEvent } = await import("@testing-library/user-event");
      const user = userEvent.setup();
      render(<PlatformToolsManager {...baseProps()} />);

      await user.click(
        screen.getByRole("button", { name: /Create new platform tool/i }),
      );

      expect(screen.getByRole("dialog")).toHaveClass("form-drawer");
      expect(screen.getByLabelText(/authentication/i)).toHaveClass(
        "form-control",
      );
      expect(screen.getByLabelText(/^name/i)).toHaveClass("form-control");
      expect(
        screen
          .getByText(/Authentication — how will this server connect/i)
          .closest(".form-section"),
      ).not.toBeNull();
    });
  });

  it("closes the authoring drawer after a successful save", async () => {
    const { userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const getBody = captureCreateBody();
    render(<PlatformToolsManager {...authorProps()} />);
    const pasteBox = screen.getByPlaceholderText(
      /mcpServers/i,
    ) as HTMLTextAreaElement;
    fireEvent.change(pasteBox, { target: { value: '{ "x": 1 }' } });
    await user.type(screen.getByLabelText(/^name/i), "my-mcp");
    await user.type(
      screen.getByLabelText(/server url/i),
      "https://example.com/mcp",
    );
    await user.click(screen.getByRole("button", { name: /^save draft/i }));

    await waitFor(() => expect(getBody()).not.toBeNull());
    expect(
      screen.getByRole("button", { name: /Create new platform tool/i }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^name/i)).not.toBeInTheDocument();
  });
});
