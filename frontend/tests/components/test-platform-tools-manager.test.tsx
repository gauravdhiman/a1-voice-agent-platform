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
 *  - No catalog tab (retired) and no "From catalog" button.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  renderWithProviders as render,
  screen,
  waitFor,
  fireEvent,
} from '../utils/test-utils'
import { PlatformToolsManager } from '@/components/tools/platform-tools-manager'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockPlatformTool } from '../utils/data-factories'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const baseProps = (overrides: Partial<Parameters<typeof PlatformToolsManager>[0]> = {}) => ({
  ...overrides,
})

// The component defaults to the "manage" view (the platform-tools page lands
// the admin on the tool list, not the author form). Author-flow tests opt
// INTO the author view explicitly so they don't depend on the default.
const authorProps = (
  overrides: Partial<Parameters<typeof PlatformToolsManager>[0]> = {},
) => ({ initialView: 'author' as const, ...overrides })

// Capture the body posted to POST /tools/platform so a test can assert the
// create payload (the dialog no longer hands the created tool to a parent
// callback — it just creates + closes).
const captureCreateBody = () => {
  let captured: Record<string, any> | null = null
  server.use(
    http.post(`${API_BASE_URL}/api/v1/tools/platform`, async ({ request }) => {
      captured = (await request.json()) as Record<string, any>
      return HttpResponse.json({
        id: 'new-mcp-tool',
        name: captured?.name || 'new_mcp_server',
        tool_source: 'mcp',
        mcp_server_url: captured?.mcp_server_url || null,
        is_published: captured?.is_published ?? false,
        mcp_secret_headers_configured: !!captured?.mcp_secret_headers_input,
      })
    }),
  )
  return () => captured
}

describe('PlatformToolsManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Author flow', () => {
    it('parses mcpServers JSON and autofills name + url + public headers', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...authorProps()} />)

      const jsonTextarea = screen.getByPlaceholderText(/mcpServers/i)
      fireEvent.change(jsonTextarea, {
        target: {
          value: JSON.stringify({
            mcpServers: {
              'my-server': {
                url: 'https://example.com/mcp',
                headers: { 'X-Key': 'v' },
              },
            },
          }),
        },
      })
      await user.click(screen.getByRole('button', { name: /parse config/i }))

      await waitFor(() => {
        expect((screen.getByLabelText(/^name/i) as HTMLInputElement).value).toBe('my-server')
      })
      expect((screen.getByLabelText(/server url/i) as HTMLInputElement).value).toBe(
        'https://example.com/mcp',
      )
      // Public headers field receives the extracted headers object.
      const publicHeaders = screen.getByLabelText(/public headers/i) as HTMLTextAreaElement
      expect(publicHeaders.value).toContain('"X-Key"')
    })

    it('keeps the pasted config box separate from the public headers field', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...authorProps()} />)

      const blob = JSON.stringify({
        mcpServers: {
          'my-server': {
            url: 'https://example.com/mcp',
            headers: { 'X-Key': 'secret' },
          },
        },
      })
      const pasteBox = screen.getByPlaceholderText(/mcpServers/i) as HTMLTextAreaElement
      fireEvent.change(pasteBox, { target: { value: blob } })

      await user.click(screen.getByRole('button', { name: /parse config/i }))

      await waitFor(() => {
        expect((screen.getByLabelText(/^name/i) as HTMLInputElement).value).toBe('my-server')
      })

      // The public headers field holds ONLY the extracted headers object.
      const publicHeaders = screen.getByLabelText(/public headers/i) as HTMLTextAreaElement
      expect(publicHeaders.value).toContain('"X-Key"')
      expect(publicHeaders.value).not.toContain('mcpServers')

      // The paste-config box retains the original blob (not overwritten).
      expect(pasteBox.value).toContain('mcpServers')
    })

    it('shows an inline error for a rejected stdio entry', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...authorProps()} />)

      const jsonTextarea = screen.getByPlaceholderText(/mcpServers/i)
      fireEvent.change(jsonTextarea, {
        target: {
          value: JSON.stringify({
            mcpServers: {
              'local-runner': {
                command: 'npx',
                args: ['some-server'],
              },
            },
          }),
        },
      })
      await user.click(screen.getByRole('button', { name: /parse config/i }))

      await waitFor(() => {
        expect(screen.getByText(/stdio servers are not supported/i)).toBeInTheDocument()
      })
    })

    it('discovers tools and renders the discovered list', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      await user.click(
        screen.getByRole('button', { name: /test connection & discover tools/i }),
      )

      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument()
      })
      expect(screen.getByText('add')).toBeInTheDocument()
      expect(screen.getByText('multiply')).toBeInTheDocument()
    })

    it('Save draft posts is_published=false with no organization_id, then resets the form', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.type(screen.getByLabelText(/^name/i), 'my-mcp')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      await user.click(screen.getByRole('button', { name: /^save draft/i }))

      await waitFor(() => expect(getBody()).not.toBeNull())
      const body = getBody()!
      expect(body).toMatchObject({
        name: 'my-mcp',
        tool_source: 'mcp',
        mcp_server_url: 'https://example.com/mcp',
        is_published: false,
        is_active: true,
        requires_auth: false,
        auth_type: null,
      })
      // Global row — the org-scoped custom tier is retired (RFC §6.6).
      expect(body.organization_id).toBeUndefined()
      // Inline panel (no dialog to close) resets the form so the admin can
      // author another server.
      expect((screen.getByLabelText(/^name/i) as HTMLInputElement).value).toBe('')
      expect((screen.getByLabelText(/server url/i) as HTMLInputElement).value).toBe('')
    })

    it('Publish posts is_published=true after a successful discover', async () => {
      // Publish is gated on a successful "Test & discover" so the tool list is
      // captured (publishing without discover leaves the agent drawer empty).
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.type(screen.getByLabelText(/^name/i), 'my-mcp')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      await user.click(
        screen.getByRole('button', { name: /test connection & discover tools/i }),
      )
      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /^publish$/i }))

      await waitFor(() => expect(getBody()).not.toBeNull())
      expect(getBody()!.is_published).toBe(true)
    })

    it('api-key mode: save persists the {{KEY}} template + requires_auth + auth_type=api_key', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<PlatformToolsManager {...authorProps()} />)

      // Switch auth mode to Static API key.
      await user.selectOptions(screen.getByLabelText(/authentication/i), 'api_key')
      await user.type(screen.getByLabelText(/^name/i), 'keyed-mcp')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      const secretBox = screen.getByLabelText(/secret header template/i) as HTMLTextAreaElement
      fireEvent.change(secretBox, {
        target: { value: '{ "Authorization": "Bearer {{KEY}}" }' },
      })
      await user.click(screen.getByRole('button', { name: /^save draft/i }))

      await waitFor(() => expect(getBody()).not.toBeNull())
      const body = getBody()!
      expect(body.mcp_secret_headers_input).toEqual({
        Authorization: 'Bearer {{KEY}}',
      })
      expect(body.requires_auth).toBe(true)
      expect(body.auth_type).toBe('api_key')
      // The transient test key is NOT persisted — only the template is.
      expect(body.mcp_secret_headers_input.Authorization).toContain('{{KEY}}')
    })

    it('api-key mode: discover substitutes the test key into {{KEY}}', async () => {
      // Capture the discover request body to confirm the test key is substituted
      // into the {{KEY}} placeholder for the one-shot discover call.
      let discoverBody: { url: string; headers?: Record<string, string> } | null = null
      server.use(
        http.post(`${API_BASE_URL}/api/v1/tools/mcp/discover`, async ({ request }) => {
          discoverBody = (await request.json()) as { url: string; headers?: Record<string, string> }
          return HttpResponse.json({
            tools: [{ name: 'add', description: 'Add two numbers', input_schema: null }],
          })
        }),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.selectOptions(screen.getByLabelText(/authentication/i), 'api_key')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      const secretBox = screen.getByLabelText(/secret header template/i) as HTMLTextAreaElement
      fireEvent.change(secretBox, {
        target: { value: '{ "Authorization": "Bearer {{KEY}}" }' },
      })
      await user.type(screen.getByLabelText(/test api key/i), 'test-secret-123')
      await user.click(
        screen.getByRole('button', { name: /test connection & discover tools/i }),
      )

      await waitFor(() => expect(discoverBody).not.toBeNull())
      expect(discoverBody!.headers).toEqual({
        Authorization: 'Bearer test-secret-123',
      })
    })

    it('requires name + url before saving (draft + publish disabled)', async () => {
      render(<PlatformToolsManager {...authorProps()} />)
      expect(screen.getByRole('button', { name: /^save draft/i })).toBeDisabled()
      expect(screen.getByRole('button', { name: /^publish$/i })).toBeDisabled()
    })

    it('marks Name and Server URL as required (optional fields unmarked)', () => {
      // The author form has no field-level validation hints; the admin can't
      // tell what's mandatory. Name + Server URL (the save guard) get a red
      // asterisk; optional fields (Description, Public headers) do not.
      render(<PlatformToolsManager {...authorProps()} />)
      const nameLabel = document.querySelector('label[for="mcp-name"]')
      const urlLabel = document.querySelector('label[for="mcp-url"]')
      expect(nameLabel?.textContent).toMatch(/\*/)
      expect(urlLabel?.textContent).toMatch(/\*/)
      const descLabel = document.querySelector('label[for="mcp-description"]')
      const pubHeadersLabel = document.querySelector(
        'label[for="mcp-public-headers"]',
      )
      expect(descLabel?.textContent).not.toMatch(/\*/)
      expect(pubHeadersLabel?.textContent).not.toMatch(/\*/)
    })

    it('Publish is disabled until Test & discover succeeds (Save draft still allowed)', async () => {
      // Publishing without discovering leaves the agent tool drawer empty (no
      // tool_functions_schema). Publish is gated on a successful discover; a
      // draft is still allowed without discover (drafts aren't shown to orgs).
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.type(screen.getByLabelText(/^name/i), 'my-mcp')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')

      // Name + url filled, but no discover yet → Publish disabled, Save draft enabled.
      expect(screen.getByRole('button', { name: /^publish$/i })).toBeDisabled()
      expect(screen.getByRole('button', { name: /^save draft/i })).toBeEnabled()

      await user.click(
        screen.getByRole('button', { name: /test connection & discover tools/i }),
      )
      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument()
      })

      // After a successful discover, Publish is enabled.
      expect(screen.getByRole('button', { name: /^publish$/i })).toBeEnabled()
    })

    it('persists discovered tools as tool_functions_schema so the agent panel shows them', async () => {
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
                name: 'read_wiki_contents',
                description: 'View documentation about a GitHub repository.',
                input_schema: {
                  type: 'object',
                  properties: { repoName: { type: 'string', description: 'owner/repo' } },
                  required: ['repoName'],
                },
              },
              {
                name: 'ask_question',
                description: 'Ask a question about a repository.',
                input_schema: {
                  type: 'object',
                  properties: {
                    repoName: { type: 'string' },
                    question: { type: 'string' },
                  },
                  required: ['repoName', 'question'],
                },
              },
            ],
          }),
        ),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.type(screen.getByLabelText(/^name/i), 'deepwiki')
      await user.type(screen.getByLabelText(/server url/i), 'https://mcp.deepwiki.com/mcp')
      await user.click(
        screen.getByRole('button', { name: /test connection & discover tools/i }),
      )
      await waitFor(() => {
        expect(screen.getByText(/discovered 2 tools/i)).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /^publish$/i }))

      await waitFor(() => expect(getBody()).not.toBeNull())
      const body = getBody()!
      expect(body.tool_functions_schema).toEqual({
        functions: [
          {
            name: 'read_wiki_contents',
            description: 'View documentation about a GitHub repository.',
            parameters: {
              type: 'object',
              properties: { repoName: { type: 'string', description: 'owner/repo' } },
              required: ['repoName'],
            },
          },
          {
            name: 'ask_question',
            description: 'Ask a question about a repository.',
            parameters: {
              type: 'object',
              properties: {
                repoName: { type: 'string' },
                question: { type: 'string' },
              },
              required: ['repoName', 'question'],
            },
          },
        ],
      })
    })

    it('omits tool_functions_schema when no tools were discovered', async () => {
      // Saving without discovering must not send an empty {functions:[]} — the
      // backend stores null and the drawer simply shows no list (same as today).
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<PlatformToolsManager {...authorProps()} />)

      await user.type(screen.getByLabelText(/^name/i), 'my-mcp')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      await user.click(screen.getByRole('button', { name: /^save draft/i }))

      await waitFor(() => expect(getBody()).not.toBeNull())
      const body = getBody()!
      expect(body.tool_functions_schema).toBeUndefined()
    })
  })

  describe('Manage flow', () => {
    it('shows Manage existing tools as the default active tab (no click needed)', () => {
      // The platform-tools page lands the admin on the tool list, not the
      // author form. Manage content is rendered on mount; the author-only
      // paste-config box is not.
      render(<PlatformToolsManager {...baseProps()} />)
      expect(
        screen.getByText(/Drafts are visible only to platform admins/i),
      ).toBeInTheDocument()
      expect(screen.queryByPlaceholderText(/mcpServers/i)).not.toBeInTheDocument()
    })

    it('lists platform tools with a Draft badge + Publish + delete actions', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))

      // The mock platform tool 'test_tool' renders as 'test tool'. The default
      // mock has no is_published, so it shows as a Draft badge with a Publish button.
      await waitFor(() => {
        expect(screen.getByText('Draft')).toBeInTheDocument()
      })
      expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument()
      // Delete is the ghost icon button.
      expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
    })

    it('publish button calls the publish endpoint', async () => {
      let publishedCalled = false
      server.use(
        http.post(`${API_BASE_URL}/api/v1/tools/platform/:toolId/publish`, () => {
          publishedCalled = true
          return HttpResponse.json({ id: 'tool-1', is_published: true })
        }),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /publish/i }))

      await waitFor(() => expect(publishedCalled).toBe(true))
    })

    it('delete opens a type-to-confirm dialog and deletes with force when in use', async () => {
      // The default usage mock returns count=2 (in use), so the confirm must
      // send `?force=true` after the admin types "Delete".
      let deleteUrl: string | null = null
      server.use(
        http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, ({ request }) => {
          deleteUrl = request.url
          return HttpResponse.json({ deleted: true })
        }),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /delete/i }))

      // The shared confirm dialog opens; the in-use warnings are visible.
      await waitFor(() => {
        expect(screen.getByText(/Used by 2 agents/i)).toBeInTheDocument()
      })
      await user.type(screen.getByPlaceholderText('Delete'), 'Delete')
      await user.click(screen.getByRole('button', { name: /Delete MCP Server/i }))

      await waitFor(() => expect(deleteUrl).not.toBeNull())
      expect(deleteUrl).toContain('tool-1')
      expect(deleteUrl).toContain('force=true')
    })

    it('does not render a Delete button for legacy (code-backed) tools', async () => {
      // Legacy tools are re-seeded by the worker on startup — hard-delete is the
      // wrong lever, so the Manage view hides the Delete affordance entirely.
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ tool_source: 'legacy' })],
          }),
        ),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getByText('Draft')).toBeInTheDocument()
      })
      expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
    })

    it('unpublish surfaces an info toast with the usage count', async () => {
      const { toast } = await import('sonner')
      // Default mock tool has is_published undefined (renders as Draft) — flip
      // it to Published so the toggle button is "Unpublish".
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [createMockPlatformTool({ is_published: true })],
          }),
        ),
        http.post(`${API_BASE_URL}/api/v1/tools/platform/:toolId/unpublish`, () =>
          HttpResponse.json({ id: 'tool-1', is_published: false }),
        ),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /unpublish/i })).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /unpublish/i }))

      // The default usage mock returns count=2 (Alex + Sam).
      await waitFor(() => {
        expect(toast.info).toHaveBeenCalledWith(
          expect.stringMatching(/2 agents currently use this tool/i),
        )
      })
    })

    it('resets the type-to-confirm input between consecutive deletes', async () => {
      // Regression: the McpToolDeleteDialog wrapper must mount a FRESH
      // DeleteConfirmationDialog per delete (conditional render). An always-
      // mounted dialog would leak the typed "Delete" into the next dialog,
      // enabling the confirm button without re-typing — defeating the
      // type-to-confirm gate the user explicitly asked for.
      // Track deletions so the GET list reflects them (the real backend would).
      const deleted = new Set<string>()
      server.use(
        http.get(`${API_BASE_URL}/api/v1/tools/platform`, () =>
          HttpResponse.json({
            success: true,
            data: [
              createMockPlatformTool({ id: 'mcp-a', name: 'alpha', tool_source: 'mcp' }),
              createMockPlatformTool({ id: 'mcp-b', name: 'beta', tool_source: 'mcp' }),
            ].filter((t) => !deleted.has(t.id)),
          }),
        ),
        // Unused for both — no usage warnings.
        http.get(`${API_BASE_URL}/api/v1/tools/platform/:toolId/usage`, () =>
          HttpResponse.json({ count: 0, agents: [] }),
        ),
        http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, ({ params }) => {
          deleted.add(params.toolId as string)
          return HttpResponse.json({ deleted: true })
        }),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<PlatformToolsManager {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /delete/i })).toHaveLength(2)
      })

      // Delete the first MCP tool: type "Delete" + confirm.
      await user.click(screen.getAllByRole('button', { name: /delete/i })[0])
      await waitFor(() =>
        expect(screen.getByPlaceholderText('Delete')).toBeInTheDocument(),
      )
      await user.type(screen.getByPlaceholderText('Delete'), 'Delete')
      await user.click(screen.getByRole('button', { name: /Delete MCP Server/i }))

      // The dialog closes after the delete; only one delete button remains.
      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /delete/i })).toHaveLength(1)
      })

      // Open the delete dialog for the SECOND tool.
      await user.click(screen.getAllByRole('button', { name: /delete/i })[0])
      await waitFor(() =>
        expect(screen.getByPlaceholderText('Delete')).toBeInTheDocument(),
      )

      // The confirm input must be EMPTY (not pre-filled with the previous
      // "Delete"), and the confirm button must be disabled until re-typed.
      expect((screen.getByPlaceholderText('Delete') as HTMLInputElement).value).toBe('')
      expect(screen.getByRole('button', { name: /Delete MCP Server/i })).toBeDisabled()

      // Clicking the empty confirm input's button does nothing — type "Delete" first.
      await user.type(screen.getByPlaceholderText('Delete'), 'Delete')
      expect(screen.getByRole('button', { name: /Delete MCP Server/i })).toBeEnabled()
    })
  })

  it('has no catalog tab or "From catalog" button', () => {
    render(<PlatformToolsManager {...baseProps()} />)
    expect(screen.queryByRole('button', { name: /from catalog/i })).not.toBeInTheDocument()
  })

  describe('platform-admin messaging', () => {
    // The panel manages ALL platform tools (native + MCP), not just MCP
    // servers, so the tab labels reflect the broader scope. (The "Platform
    // Tools" H1 lives on the /platform/tools PAGE, not the component.)
    //   - author tab: "Configure MCP server" (was "Author server")
    //   - manage tab: "Manage existing tools (N)" (was "Manage (N)")
    it('renders the two reworded view tabs', () => {
      render(<PlatformToolsManager {...baseProps()} />)
      expect(
        screen.getByRole('button', { name: /Configure MCP server/i }),
      ).toBeInTheDocument()
      // The manage tab carries the live platform-tools count.
      expect(
        screen.getByRole('button', { name: /Manage existing tools/i }),
      ).toBeInTheDocument()
    })
  })

  it('resets the form after a successful save so the admin can author another', async () => {
    // The inline panel has no dialog to close on save; it clears every author
    // field (incl. the pasted-config box) so the next server starts fresh.
    const { userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    const getBody = captureCreateBody()
    render(<PlatformToolsManager {...authorProps()} />)
    const pasteBox = screen.getByPlaceholderText(/mcpServers/i) as HTMLTextAreaElement
    fireEvent.change(pasteBox, { target: { value: '{ "x": 1 }' } })
    await user.type(screen.getByLabelText(/^name/i), 'my-mcp')
    await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
    await user.click(screen.getByRole('button', { name: /^save draft/i }))

    await waitFor(() => expect(getBody()).not.toBeNull())
    // Every author field resets — name, url, and the pasted-config box.
    expect((screen.getByLabelText(/^name/i) as HTMLInputElement).value).toBe('')
    expect((screen.getByPlaceholderText(/mcpServers/i) as HTMLTextAreaElement).value).toBe('')
  })
})