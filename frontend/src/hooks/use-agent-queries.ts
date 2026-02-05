import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agentService } from "@/services/agent-service";
import type {
  VoiceAgent,
  VoiceAgentCreate,
  VoiceAgentUpdate,
  AgentTool,
  AgentToolCreate,
  AgentToolUpdate,
} from "@/types/agent";
import { toast } from "sonner";

// Query keys for cache management
export const agentQueryKeys = {
  all: ["agents"] as const,
  myAgents: () => [...agentQueryKeys.all, "my"] as const,
  organization: (orgId: string) =>
    [...agentQueryKeys.all, "organization", orgId] as const,
  detail: (id: string) => [...agentQueryKeys.all, id] as const,
  systemPrompt: (id: string) =>
    [...agentQueryKeys.all, id, "system-prompt"] as const,
  platformTools: () => ["tools", "platform"] as const,
  agentTools: (agentId: string) => ["tools", "agent", agentId] as const,
};

// Get all agents for the current user
export function useMyAgents() {
  return useQuery({
    queryKey: agentQueryKeys.myAgents(),
    queryFn: () => agentService.getMyAgents(),
    staleTime: 30 * 1000, // 30 seconds
  });
}

// Get agents for a specific organization
export function useOrgAgents(orgId: string) {
  return useQuery({
    queryKey: agentQueryKeys.organization(orgId),
    queryFn: () => agentService.getOrgAgents(orgId),
    staleTime: 30 * 1000,
    enabled: !!orgId,
  });
}

// Get a single agent by ID
export function useAgent(agentId: string) {
  return useQuery({
    queryKey: agentQueryKeys.detail(agentId),
    queryFn: () => agentService.getAgentById(agentId),
    staleTime: 30 * 1000,
    enabled: !!agentId,
  });
}

// Get the generated system prompt for an agent
export function useAgentSystemPrompt(agentId: string) {
  return useQuery({
    queryKey: agentQueryKeys.systemPrompt(agentId),
    queryFn: () => agentService.getAgentSystemPrompt(agentId),
    staleTime: 5 * 1000, // Short stale time since it depends on agent/org data
    enabled: !!agentId,
  });
}

// Get all platform tools
export function usePlatformTools(onlyActive = true) {
  return useQuery({
    queryKey: agentQueryKeys.platformTools(),
    queryFn: () => agentService.getPlatformTools(onlyActive),
    staleTime: 5 * 60 * 1000, // 5 minutes - tools don't change often
  });
}

// Get tools for a specific agent
export function useAgentTools(agentId: string) {
  return useQuery({
    queryKey: agentQueryKeys.agentTools(agentId),
    queryFn: () => agentService.getAgentTools(agentId),
    staleTime: 30 * 1000,
    enabled: !!agentId,
  });
}

// Mutation: Create agent
export function useCreateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: VoiceAgentCreate) => agentService.createAgent(data),
    onMutate: async (newAgent) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: agentQueryKeys.myAgents() });

      // Snapshot previous value
      const previousAgents = queryClient.getQueryData<VoiceAgent[]>(
        agentQueryKeys.myAgents(),
      );

      // Optimistically update to the new value
      queryClient.setQueryData<VoiceAgent[]>(
        agentQueryKeys.myAgents(),
        (old) => [
          ...(old || []),
          {
            ...newAgent,
            id: `temp-${Date.now()}`,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          } as VoiceAgent,
        ],
      );

      // Return context with previous value
      return { previousAgents };
    },
    onError: (error, _, context) => {
      // Rollback to previous value
      if (context?.previousAgents) {
        queryClient.setQueryData(
          agentQueryKeys.myAgents(),
          context.previousAgents,
        );
      }
      toast.error("Failed to create agent");
    },
    onSuccess: () => {
      toast.success("Agent created successfully");
      // Invalidate to get fresh data
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.myAgents() });
    },
  });
}

// Mutation: Update agent
export function useUpdateAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentId,
      data,
    }: {
      agentId: string;
      data: VoiceAgentUpdate;
    }) => agentService.updateAgent(agentId, data),
    onMutate: async ({ agentId, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: agentQueryKeys.detail(agentId),
      });
      await queryClient.cancelQueries({ queryKey: agentQueryKeys.myAgents() });

      // Snapshot previous values
      const previousAgent = queryClient.getQueryData<VoiceAgent>(
        agentQueryKeys.detail(agentId),
      );
      const previousAgents = queryClient.getQueryData<VoiceAgent[]>(
        agentQueryKeys.myAgents(),
      );

      // Optimistically update agent details
      queryClient.setQueryData<VoiceAgent>(
        agentQueryKeys.detail(agentId),
        (old) => (old ? { ...old, ...data } : undefined),
      );

      // Optimistically update agent in list
      queryClient.setQueryData<VoiceAgent[]>(
        agentQueryKeys.myAgents(),
        (old) =>
          old?.map((agent) =>
            agent.id === agentId ? { ...agent, ...data } : agent,
          ),
      );

      return { previousAgent, previousAgents };
    },
    onError: (error, { agentId }, context) => {
      // Rollback on error
      if (context?.previousAgent) {
        queryClient.setQueryData(
          agentQueryKeys.detail(agentId),
          context.previousAgent,
        );
      }
      if (context?.previousAgents) {
        queryClient.setQueryData(
          agentQueryKeys.myAgents(),
          context.previousAgents,
        );
      }
      toast.error("Failed to update agent");
    },
    onSuccess: () => {
      toast.success("Agent updated successfully");
    },
    onSettled: (_, __, { agentId }) => {
      // Always refetch after error or success to ensure consistency
      queryClient.invalidateQueries({
        queryKey: agentQueryKeys.detail(agentId),
      });
      queryClient.invalidateQueries({ queryKey: agentQueryKeys.myAgents() });
    },
  });
}

// Mutation: Delete agent
export function useDeleteAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentId: string) => agentService.deleteAgent(agentId),
    onMutate: async (agentId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: agentQueryKeys.myAgents() });

      // Snapshot previous value
      const previousAgents = queryClient.getQueryData<VoiceAgent[]>(
        agentQueryKeys.myAgents(),
      );

      // Optimistically remove from list
      queryClient.setQueryData<VoiceAgent[]>(
        agentQueryKeys.myAgents(),
        (old) => old?.filter((agent) => agent.id !== agentId),
      );

      return { previousAgents };
    },
    onError: (error, _, context) => {
      // Rollback on error
      if (context?.previousAgents) {
        queryClient.setQueryData(
          agentQueryKeys.myAgents(),
          context.previousAgents,
        );
      }
      toast.error("Failed to delete agent");
    },
    onSuccess: () => {
      toast.success("Agent deleted successfully");
    },
  });
}

// Mutation: Configure agent tool
export function useConfigureAgentTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AgentToolCreate) =>
      agentService.configureAgentTool(data),
    onSuccess: (_, variables) => {
      toast.success("Tool connected successfully");
      queryClient.invalidateQueries({
        queryKey: agentQueryKeys.agentTools(variables.agent_id),
      });
    },
    onError: () => {
      toast.error("Failed to connect tool");
    },
  });
}

// Mutation: Update agent tool
export function useUpdateAgentTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentToolId,
      data,
    }: {
      agentToolId: string;
      data: AgentToolUpdate;
    }) => agentService.updateAgentTool(agentToolId, data),
    onMutate: async ({ agentToolId, data }) => {
      // Find all agent tools queries
      const queries = queryClient.getQueryCache().findAll({
        predicate: (query) => {
          const key = query.queryKey;
          return Array.isArray(key) && key[0] === "tools" && key[1] === "agent";
        },
      });

      // Snapshot previous values
      const previousData = new Map<string, AgentTool[]>();
      queries.forEach((query) => {
        const data = query.state.data as AgentTool[];
        if (data) previousData.set(JSON.stringify(query.queryKey), [...data]);
      });

      // Optimistically update
      queries.forEach((query) => {
        queryClient.setQueryData<AgentTool[]>(
          query.queryKey,
          (old) =>
            old?.map((tool) =>
              tool.id === agentToolId ? { ...tool, ...data } : tool,
            ),
        );
      });

      return { previousData };
    },
    onError: (_, __, context) => {
      // Rollback on error
      if (context?.previousData) {
        context.previousData.forEach((data, key) => {
          queryClient.setQueryData(JSON.parse(key), data);
        });
      }
      toast.error("Failed to update tool");
    },
  });
}

// Mutation: Toggle tool function
export function useToggleFunction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      agentToolId,
      unselectedFunctions,
    }: {
      agentToolId: string;
      unselectedFunctions: string[];
    }) =>
      agentService.updateAgentTool(agentToolId, {
        unselected_functions: unselectedFunctions,
      }),
    onMutate: ({ agentToolId, unselectedFunctions }) => {
      // Find all agent tools queries
      const queries = queryClient.getQueryCache().findAll({
        predicate: (query) => {
          const key = query.queryKey;
          return Array.isArray(key) && key[0] === "tools" && key[1] === "agent";
        },
      });

      // Snapshot previous values
      const previousData = new Map<string, AgentTool[]>();
      queries.forEach((query) => {
        const data = query.state.data as AgentTool[];
        if (data) previousData.set(JSON.stringify(query.queryKey), [...data]);
      });

      // Optimistically update
      queries.forEach((query) => {
        queryClient.setQueryData<AgentTool[]>(
          query.queryKey,
          (old) =>
            old?.map((tool) =>
              tool.id === agentToolId
                ? { ...tool, unselected_functions: unselectedFunctions }
                : tool,
            ),
        );
      });

      return { previousData };
    },
    onSuccess: (_, { unselectedFunctions }) => {
      const isEnabling = unselectedFunctions.length === 0;
      toast.success(isEnabling ? "Function enabled" : "Function disabled");
    },
    onError: (_, __, context) => {
      // Rollback on error
      if (context?.previousData) {
        context.previousData.forEach((data, key) => {
          queryClient.setQueryData(JSON.parse(key), data);
        });
      }
      toast.error("Failed to update function");
    },
  });
}

// Mutation: Start OAuth
export function useStartOAuth() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      toolName,
      agentId,
    }: {
      toolName: string;
      agentId: string;
    }) => agentService.startOAuth(toolName, agentId),
    onSuccess: (response, { agentId }) => {
      window.open(response.auth_url, "_blank");
      toast.info("Opening authentication page...");

      // Refresh tools after 3 seconds
      setTimeout(() => {
        queryClient.invalidateQueries({
          queryKey: agentQueryKeys.agentTools(agentId),
        });
      }, 3000);
    },
    onError: () => {
      toast.error("Failed to start authentication");
    },
  });
}

// Mutation: Logout agent tool
export function useLogoutAgentTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentToolId: string) =>
      agentService.logoutAgentTool(agentToolId),
    onSuccess: () => {
      toast.success("Logged out successfully");

      // Find and invalidate agent tools query
      const queries = queryClient.getQueryCache().findAll({
        queryKey: agentQueryKeys.agentTools(""),
      });
      queries.forEach((query) => query.invalidate());
    },
    onError: () => {
      toast.error("Failed to log out");
    },
  });
}

// Mutation: Delete agent tool
export function useDeleteAgentTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agentToolId: string) =>
      agentService.deleteAgentTool(agentToolId),
    onSuccess: () => {
      toast.success("Tool disconnected successfully");

      // Find and invalidate agent tools query
      const queries = queryClient.getQueryCache().findAll({
        queryKey: agentQueryKeys.agentTools(""),
      });
      queries.forEach((query) => query.invalidate());
    },
    onError: () => {
      toast.error("Failed to disconnect tool");
    },
  });
}

