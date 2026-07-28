/**
 * Tests for AddMcpServerDialog — platform-admin authoring + publish lifecycle
 * (RFC §6.6).
 *
 * Covers:
 *  - Author: paste `mcpServers` JSON → parse autofills the structured fields;
 *    stdio entries surface an inline per-entry error; "Test & discover" calls
 *    discoverMcpTools and renders the tool list; "Save draft" / "Publish" call
 *    createPlatformTool with the right payload (is_published, secret-header
 *    template, requires_auth/auth_type for the api-key mode) — no
 *    organization_id (global row), no per-agent attach hand-off.
 *  - Auth/key model: api-key mode shows the `{{KEY}}` secret-header template +
 *    transient Test API key; discover substitutes the test key into `{{KEY}}`;
 *    save persists the template + requires_auth=true + auth_type=api_key.
 *  - Manage: lists drafts + published with Draft/Published badges and
 *    publish/unpublish + delete actions.
 *  - No catalog tab (retired) and no "From catalog" button.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  renderWithProviders as render,
  screen,
  waitFor,
  fireEvent,
} from '../utils/test-utils'
import { AddMcpServerDialog } from '@/components/tools/add-mcp-server-dialog'
import { server } from '../mocks/server'
import { http, HttpResponse } from 'msw'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const baseProps = (overrides: Partial<Parameters<typeof AddMcpServerDialog>[0]> = {}) => ({
  open: true,
  onOpenChange: vi.fn(),
  ...overrides,
})

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

describe('AddMcpServerDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Author flow', () => {
    it('parses mcpServers JSON and autofills name + url + public headers', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<AddMcpServerDialog {...baseProps()} />)

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
      render(<AddMcpServerDialog {...baseProps()} />)

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
      render(<AddMcpServerDialog {...baseProps()} />)

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
      render(<AddMcpServerDialog {...baseProps()} />)

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

    it('Save draft posts is_published=false with no organization_id', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const onOpenChange = vi.fn()
      const getBody = captureCreateBody()
      render(<AddMcpServerDialog {...baseProps({ onOpenChange })} />)

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
      expect(onOpenChange).toHaveBeenCalledWith(false)
    })

    it('Publish posts is_published=true', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<AddMcpServerDialog {...baseProps()} />)

      await user.type(screen.getByLabelText(/^name/i), 'my-mcp')
      await user.type(screen.getByLabelText(/server url/i), 'https://example.com/mcp')
      await user.click(screen.getByRole('button', { name: /^publish$/i }))

      await waitFor(() => expect(getBody()).not.toBeNull())
      expect(getBody()!.is_published).toBe(true)
    })

    it('api-key mode: save persists the {{KEY}} template + requires_auth + auth_type=api_key', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      const getBody = captureCreateBody()
      render(<AddMcpServerDialog {...baseProps()} />)

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
      render(<AddMcpServerDialog {...baseProps()} />)

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
      render(<AddMcpServerDialog {...baseProps()} />)
      expect(screen.getByRole('button', { name: /^save draft/i })).toBeDisabled()
      expect(screen.getByRole('button', { name: /^publish$/i })).toBeDisabled()
    })
  })

  describe('Manage flow', () => {
    it('lists platform tools with a Draft badge + Publish + delete actions', async () => {
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<AddMcpServerDialog {...baseProps()} />)

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
      render(<AddMcpServerDialog {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /publish/i }))

      await waitFor(() => expect(publishedCalled).toBe(true))
    })

    it('delete button calls the delete endpoint', async () => {
      let deletedId: string | null = null
      server.use(
        http.delete(`${API_BASE_URL}/api/v1/tools/platform/:toolId`, ({ params }) => {
          deletedId = params.toolId as string
          return HttpResponse.json({ deleted: true })
        }),
      )
      const { userEvent } = await import('@testing-library/user-event')
      const user = userEvent.setup()
      render(<AddMcpServerDialog {...baseProps()} />)

      await user.click(screen.getByRole('button', { name: /manage/i }))
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
      })
      await user.click(screen.getByRole('button', { name: /delete/i }))

      await waitFor(() => expect(deletedId).toBe('tool-1'))
    })
  })

  it('has no catalog tab or "From catalog" button', () => {
    render(<AddMcpServerDialog {...baseProps()} />)
    expect(screen.queryByRole('button', { name: /from catalog/i })).not.toBeInTheDocument()
  })

  it('resets form state when reopened', async () => {
    const { rerender } = render(<AddMcpServerDialog {...baseProps()} />)
    const jsonTextarea = screen.getByPlaceholderText(/mcpServers/i) as HTMLTextAreaElement
    fireEvent.change(jsonTextarea, { target: { value: '{ "x": 1 }' } })
    expect(jsonTextarea.value).toContain('"x"')

    // Close + reopen.
    rerender(<AddMcpServerDialog {...baseProps({ open: false })} />)
    rerender(<AddMcpServerDialog {...baseProps({ open: true })} />)
    const reopened = screen.getByPlaceholderText(/mcpServers/i) as HTMLTextAreaElement
    expect(reopened.value).toBe('')
  })
})