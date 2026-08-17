import { createMockAgentTool } from './data-factories'

describe('createMockAgentTool', () => {
  it('provides defaults for OAuth refresh metadata', () => {
    const agentTool = createMockAgentTool()

    expect(agentTool.last_refreshed_at).toBeNull()
    expect(agentTool.oauth_refresh_mode).toBeNull()
    expect(agentTool.oauth_refresh_interval_minutes).toBeNull()
    expect(agentTool.oauth_refresh_message).toBeNull()
  })
})
