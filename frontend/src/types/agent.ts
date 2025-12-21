/**
 * Voice Agent and Tool related type definitions
 */

export interface VoiceAgent {
  id: string;
  organization_id: string;
  name: string;
  phone_number: string | null;
  system_prompt: string | null;
  is_active: boolean;
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

export interface PlatformTool {
  id: string;
  name: string;
  description: string | null;
  config_schema: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentTool {
  id: string;
  agent_id: string;
  tool_id: string;
  config: Record<string, unknown> | null;
  sensitive_config: Record<string, unknown> | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  tool?: PlatformTool;
}

export interface AgentToolCreate {
  agent_id: string;
  tool_id: string;
  config?: Record<string, unknown> | null;
  sensitive_config?: Record<string, unknown> | null;
  is_enabled?: boolean;
}

export interface AgentToolUpdate {
  config?: Record<string, unknown> | null;
  sensitive_config?: Record<string, unknown> | null;
  is_enabled?: boolean;
}
