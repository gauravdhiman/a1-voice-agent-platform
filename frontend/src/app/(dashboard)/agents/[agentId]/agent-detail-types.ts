/** Editable fields shared by the agent-detail tabs. */
export interface AgentDetailFormState {
  name: string;
  persona: string;
  tone: string;
  is_active: boolean;
  is_published_on_public_page: boolean;
  call_recording_enabled: boolean;
  use_platform_credits: boolean;
  instructions_markdown: string;
  preset_id: string | null;
  is_demo: boolean;
  demo_slug: string;
  public_description: string;
  demo_public_result_url: string;
  demo_calls_remaining: number;
  demo_max_call_duration_minutes: number;
}
