/**
 * Voice Agent and Tool related type definitions
 */

export enum AuthStatus {
  NOT_AUTHENTICATED = "not_authenticated", // No tokens exist
  AUTHENTICATED = "authenticated", // Valid tokens exist
  EXPIRED = "expired", // Tokens exist but have expired
}

export enum ConnectionStatus {
  NOT_CONNECTED = "not_connected", // No agent_tools record
  CONNECTED_NO_AUTH = "connected_no_auth", // Connected, tool doesn't require auth
  CONNECTED_AUTH_VALID = "connected_auth_valid", // Connected, requires auth, valid tokens
  CONNECTED_AUTH_INVALID = "connected_auth_invalid", // Connected, requires auth, invalid/missing tokens
}

export interface VoiceAgent {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  phone_number: string | null;
  system_prompt: string | null;
  voice_settings: Record<string, unknown> | null;
  is_active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface VoiceAgentCreate {
  organization_id: string;
  name: string;
  phone_number?: string | null;
  system_prompt?: string | null;
  is_active?: boolean;
}

export interface VoiceAgentUpdate {
  name?: string;
  phone_number?: string | null;
  system_prompt?: string | null;
  is_active?: boolean;
}

export interface PlatformToolFunction {
  type: string;
  name: string;
  description: string;
  parameters?: {
    type: string;
    properties?: Record<
      string,
      {
        type: string;
        description?: string;
        default?: unknown;
      }
    >;
    required?: string[];
  };
}

export interface PlatformTool {
  id: string;
  name: string;
  description: string | null;
  config_schema: Record<string, unknown> | null;
  tool_functions_schema: {
    functions: PlatformToolFunction[];
  } | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  auth_type: string | null;
  requires_auth: boolean;
  auth_config: Record<string, unknown> | null;
}

export interface AgentTool {
  id: string;
  agent_id: string;
  tool_id: string;
  config: Record<string, unknown> | null;
  sensitive_config: Record<string, unknown> | null;
  unselected_functions: string[] | null;
  is_enabled: boolean;
  auth_status: AuthStatus;
  token_expires_at: number | null;
  connection_status: ConnectionStatus;
  created_at: string;
  updated_at: string;
  tool?: PlatformTool;
}

export interface AgentToolCreate {
  agent_id: string;
  tool_id: string;
  config?: Record<string, unknown> | null;
  sensitive_config?: Record<string, unknown> | null;
  unselected_functions?: string[] | null;
  is_enabled?: boolean;
}

export interface AgentToolUpdate {
  config?: Record<string, unknown> | null;
  sensitive_config?: Record<string, unknown> | null;
  unselected_functions?: string[] | null;
  is_enabled?: boolean;
}
