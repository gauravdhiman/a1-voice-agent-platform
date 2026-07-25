/**
 * Type-level + runtime tests for the `PlatformTool` interface.
 *
 * Contract: the backend `PlatformTool` response model
 * (``shared/voice_agents/tool_models.py``) carries MCP-sourcing fields
 * (``tool_source`` / ``mcp_server_url`` / ``mcp_server_name`` /
 * ``mcp_server_headers``) that the frontend must surface so the UI can
 * distinguish legacy tools from MCP-sourced tools (e.g. render the real
 * Google Calendar MCP server URL, gate MCP-only affordances). These tests
 * pin the presence and shape of those fields on the TS interface.
 */
import { describe, it, expect, expectTypeOf } from "vitest";

import type { PlatformTool, ToolSource } from "@/types/agent";

describe("PlatformTool type", () => {
  it("exposes the MCP-sourcing fields with the right types", () => {
    // Type-level: the fields exist and have the expected TS types. This
    // fails to compile (red) until the fields are added to the interface.
    expectTypeOf<PlatformTool>().toHaveProperty("tool_source").toMatchTypeOf<
      ToolSource | undefined
    >();
    expectTypeOf<PlatformTool>()
      .toHaveProperty("mcp_server_url")
      .toMatchTypeOf<string | null | undefined>();
    expectTypeOf<PlatformTool>()
      .toHaveProperty("mcp_server_name")
      .toMatchTypeOf<string | null | undefined>();
    expectTypeOf<PlatformTool>()
      .toHaveProperty("mcp_server_headers")
      .toMatchTypeOf<Record<string, string> | null | undefined>();
  });

  it("a fully-formed MCP platform tool round-trips through the interface", () => {
    // Runtime: a real-shaped MCP platform_tools row (mirrors the seeded
    // ``Google_calendar_mcp`` row) satisfies the interface and the MCP
    // fields are readable. Proves the field is not just present on the
    // type but usable on a value.
    const tool: PlatformTool = {
      id: "c2764c2f-24c6-49c6-b36a-64422b89a93f",
      name: "Google_calendar_mcp",
      description: "Google Calendar via MCP",
      config_schema: null,
      tool_functions_schema: { functions: [] },
      is_active: true,
      created_at: "2026-07-16T00:00:00Z",
      updated_at: "2026-07-16T00:00:00Z",
      auth_type: "oauth2",
      requires_auth: true,
      auth_config: {
        provider: "google",
        auth_url: "https://accounts.google.com/o/oauth2/v2/auth",
        token_url: "https://oauth2.googleapis.com/token",
        scopes: [
          "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
          "https://www.googleapis.com/auth/calendar.events.freebusy",
          "https://www.googleapis.com/auth/calendar.events.readonly",
          "https://www.googleapis.com/auth/calendar.events",
        ],
        access_type: "offline",
        prompt: "consent",
      },
      tool_source: "mcp",
      mcp_server_url: "https://calendarmcp.googleapis.com/mcp/v1",
      mcp_server_name: "google-calendar",
      mcp_server_headers: null,
    };

    expect(tool.tool_source).toBe("mcp");
    expect(tool.mcp_server_url).toBe(
      "https://calendarmcp.googleapis.com/mcp/v1"
    );
    expect(tool.mcp_server_name).toBe("google-calendar");
    expect(tool.mcp_server_headers).toBeNull();
  });

  it("a legacy platform tool omits the MCP fields and still satisfies the interface", () => {
    // Back-compat: legacy rows need not carry the MCP fields. They MUST
    // remain optional so existing legacy tool payloads type-check.
    const tool: PlatformTool = {
      id: "96207764-76e4-480b-b728-1b402ba1f8d7",
      name: "Google_calendar",
      description: "Google Calendar (legacy)",
      config_schema: null,
      tool_functions_schema: { functions: [] },
      is_active: true,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      auth_type: "oauth2",
      requires_auth: true,
      auth_config: null,
    };

    expect(tool.tool_source).toBeUndefined();
    expect(tool.mcp_server_url).toBeUndefined();
  });
});