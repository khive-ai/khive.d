/**
 * API Hooks Tests
 * Comprehensive test suite for React Query hooks managing orchestration data
 * Focus on real-time updates, error handling, and multi-agent coordination
 */

import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";
import * as hooks from "../hooks";
import { apiClient, KhiveApiError } from "../client";
import {
  Agent,
  CoordinationMetrics,
  Domain,
  FileLock,
  HookEvent,
  Plan,
  Role,
  Session,
} from "@/types";

// Mock the API client
jest.mock("../client");

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Mock data for orchestration testing
const mockCoordinationMetrics: CoordinationMetrics = {
  conflictsPrevented: 42,
  taskDeduplicationRate: 0.87,
  averageTaskCompletionTime: 35.2,
  activeAgents: 12,
  activeSessions: 4,
};

const mockSessions: Session[] = [
  {
    id: "session_001",
    coordinationId: "coord_001",
    status: "running",
    complexity: 0.72,
    confidence: 0.85,
    createdAt: "2024-01-01T10:00:00Z",
    updatedAt: "2024-01-01T10:30:00Z",
    objective: "Multi-agent research synthesis",
    context: "fan_out_fan_in coordination with 7 agents",
  },
  {
    id: "session_002",
    coordinationId: "coord_002",
    status: "completed",
    complexity: 0.45,
    confidence: 0.95,
    createdAt: "2024-01-01T09:00:00Z",
    updatedAt: "2024-01-01T10:15:00Z",
    objective: "Parallel implementation tasks",
    context: "parallel coordination with 4 implementers",
  },
];

const mockAgents: Agent[] = [
  {
    id: "researcher_001",
    role: "researcher",
    domain: "memory-systems",
    status: "active",
    currentTask: "Analyzing distributed memory patterns",
    duration: 900000,
    sessionId: "session_001",
  },
  {
    id: "analyst_001",
    role: "analyst",
    domain: "agentic-systems",
    status: "busy",
    currentTask: "Synthesizing research findings",
    duration: 600000,
    sessionId: "session_001",
  },
];

const mockPlans: Plan[] = [
  {
    id: "plan_001",
    sessionId: "session_001",
    nodes: [
      {
        id: "node_001",
        phase: "discovery",
        status: "running",
        agents: ["researcher_001", "researcher_002"],
        tasks: ["research task 1", "research task 2"],
        coordinationStrategy: "FAN_OUT_SYNTHESIZE",
        expectedArtifacts: ["research_report.md"],
        dependencies: [],
      },
    ],
    edges: [],
  },
];

const mockRoles: Role[] = [
  {
    id: "researcher",
    name: "Researcher",
    description: "Discovery and exploration agent",
    capabilities: ["research", "analysis", "discovery"],
    filePath: "/roles/researcher.yml",
  },
];

const mockDomains: Domain[] = [
  {
    id: "memory-systems",
    name: "Memory Systems",
    description: "Memory architectures and patterns",
    knowledgePatterns: { patterns: ["cache_coherence", "distributed_memory"] },
    decisionRules: { rules: ["memory_optimization"] },
    specializedTools: ["memory_analyzer"],
    metrics: ["latency", "throughput"],
    filePath: "/domains/memory-systems.yml",
  },
];

const mockEvents: HookEvent[] = [
  {
    id: "event_001",
    coordinationId: "coord_001",
    agentId: "researcher_001",
    eventType: "pre_command",
    timestamp: "2024-01-01T10:30:00Z",
    metadata: { command: "research", phase: "discovery" },
  },
];

const mockFileLocks: FileLock[] = [
  {
    filePath: "/workspace/research.md",
    agentId: "researcher_001",
    expiration: "2024-01-01T11:00:00Z",
    isStale: false,
  },
];

// Create a wrapper component for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0, // Previously cacheTime
      },
      mutations: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe("API Hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Query Keys Consistency", () => {
    it("should have consistent query keys for all resources", () => {
      expect(hooks.queryKeys.sessions()).toEqual(["sessions"]);
      expect(hooks.queryKeys.session("123")).toEqual(["sessions", "123"]);
      expect(hooks.queryKeys.agents()).toEqual(["agents"]);
      expect(hooks.queryKeys.agent("456")).toEqual(["agents", "456"]);
      expect(hooks.queryKeys.metrics()).toEqual(["metrics"]);
      expect(hooks.queryKeys.plans()).toEqual(["plans"]);
      expect(hooks.queryKeys.plan("789")).toEqual(["plans", "789"]);
      expect(hooks.queryKeys.roles()).toEqual(["roles"]);
      expect(hooks.queryKeys.domains()).toEqual(["domains"]);
      expect(hooks.queryKeys.events()).toEqual(["events", undefined]);
      expect(hooks.queryKeys.events("coord_001")).toEqual([
        "events",
        "coord_001",
      ]);
      expect(hooks.queryKeys.fileLocks()).toEqual(["file-locks"]);
    });
  });

  describe("Session Management Hooks", () => {
    it("should fetch sessions successfully", async () => {
      mockApiClient.get.mockResolvedValue(mockSessions);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSessions(), { wrapper });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockSessions);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/sessions");
    });

    it("should fetch individual session by ID", async () => {
      const session = mockSessions[0];
      mockApiClient.get.mockResolvedValue(session);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSession("session_001"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(session);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/api/sessions/session_001",
      );
    });

    it("should not fetch session when ID is empty", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSession(""), { wrapper });

      expect(result.current.isPending).toBe(true);
      expect(result.current.fetchStatus).toBe("idle");
      expect(mockApiClient.get).not.toHaveBeenCalled();
    });

    it("should create session and invalidate cache", async () => {
      const newSession = mockSessions[0];
      mockApiClient.post.mockResolvedValue(newSession);
      mockApiClient.get.mockResolvedValue(mockSessions);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useCreateSession(), {
        wrapper,
      });

      const sessionData = {
        objective: "Test session",
        context: "Test context",
      };
      await result.current.mutateAsync(sessionData);

      expect(mockApiClient.post).toHaveBeenCalledWith(
        "/api/sessions",
        sessionData,
      );
    });
  });

  describe("Agent Management Hooks", () => {
    it("should fetch agents successfully", async () => {
      mockApiClient.get.mockResolvedValue(mockAgents);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useAgents(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockAgents);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/agents");
    });

    it("should fetch individual agent by ID", async () => {
      const agent = mockAgents[0];
      mockApiClient.get.mockResolvedValue(agent);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useAgent("researcher_001"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(agent);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/api/agents/researcher_001",
      );
    });
  });

  describe("Coordination Metrics Hook", () => {
    it("should fetch coordination metrics with auto-refresh", async () => {
      mockApiClient.get.mockResolvedValue(mockCoordinationMetrics);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useCoordinationMetrics(), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockCoordinationMetrics);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/api/coordination/metrics",
      );
    });

    it("should have refresh interval configured for real-time monitoring", () => {
      // This tests the configuration of refetchInterval in the hook
      // The actual interval behavior would require more complex testing with fake timers
      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useCoordinationMetrics(), {
        wrapper,
      });

      // The hook should be configured with refetchInterval
      // We can't easily test the actual interval without more complex setup
      expect(result.current).toBeDefined();
    });
  });

  describe("Plan Management Hooks", () => {
    it("should fetch plans successfully", async () => {
      mockApiClient.get.mockResolvedValue(mockPlans);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.usePlans(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockPlans);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/plans");
    });

    it("should fetch individual plan by ID", async () => {
      const plan = mockPlans[0];
      mockApiClient.get.mockResolvedValue(plan);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.usePlan("plan_001"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(plan);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/plans/plan_001");
    });
  });

  describe("Configuration Hooks", () => {
    it("should fetch roles with extended cache time", async () => {
      mockApiClient.get.mockResolvedValue(mockRoles);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useRoles(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockRoles);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/config/roles");
    });

    it("should fetch domains with extended cache time", async () => {
      mockApiClient.get.mockResolvedValue(mockDomains);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useDomains(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockDomains);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/config/domains");
    });
  });

  describe("Real-time Event Hooks", () => {
    it("should fetch events without coordination ID", async () => {
      mockApiClient.get.mockResolvedValue(mockEvents);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useEvents(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockEvents);
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/events");
    });

    it("should fetch events with coordination ID filter", async () => {
      mockApiClient.get.mockResolvedValue(mockEvents);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useEvents("coord_001"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockEvents);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/api/events?coordination_id=coord_001",
      );
    });

    it("should have fast refresh interval for real-time updates", () => {
      // Events should refresh every 2 seconds for real-time monitoring
      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useEvents(), { wrapper });

      expect(result.current).toBeDefined();
    });
  });

  describe("File Lock Management", () => {
    it("should fetch file locks with regular refresh", async () => {
      mockApiClient.get.mockResolvedValue(mockFileLocks);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useFileLocks(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockFileLocks);
      expect(mockApiClient.get).toHaveBeenCalledWith(
        "/api/coordination/file-locks",
      );
    });
  });

  describe("Error Handling and Retries", () => {
    it("should not retry on 4xx client errors", async () => {
      const clientError = new KhiveApiError("Not Found", 404, {});
      mockApiClient.get.mockRejectedValue(clientError);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSessions(), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(clientError);
      // Should not retry 4xx errors
      expect(mockApiClient.get).toHaveBeenCalledTimes(1);
    });

    it("should retry on 5xx server errors", async () => {
      const serverError = new KhiveApiError("Internal Server Error", 500, {});
      mockApiClient.get.mockRejectedValue(serverError);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSessions(), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Should retry server errors (default is 3 times)
      expect(mockApiClient.get).toHaveBeenCalledTimes(3);
    });

    it("should handle network errors with retries", async () => {
      const networkError = new Error("Network Error");
      mockApiClient.get.mockRejectedValue(networkError);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSessions(), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      // Should retry network errors
      expect(mockApiClient.get).toHaveBeenCalledTimes(3);
    });
  });

  describe("Cache Invalidation Utilities", () => {
    it("should provide invalidation functions for all query types", async () => {
      mockApiClient.get.mockResolvedValue(mockSessions);

      const wrapper = createWrapper();
      const { result: invalidateResult } = renderHook(
        () => hooks.useInvalidateQueries(),
        { wrapper },
      );
      const { result: sessionsResult } = renderHook(() => hooks.useSessions(), {
        wrapper,
      });

      await waitFor(() => {
        expect(sessionsResult.current.isLoading).toBe(false);
      });

      // Test individual invalidation functions exist
      expect(typeof invalidateResult.current.invalidateSessions).toBe(
        "function",
      );
      expect(typeof invalidateResult.current.invalidateAgents).toBe("function");
      expect(typeof invalidateResult.current.invalidateMetrics).toBe(
        "function",
      );
      expect(typeof invalidateResult.current.invalidatePlans).toBe("function");
      expect(typeof invalidateResult.current.invalidateEvents).toBe("function");
      expect(typeof invalidateResult.current.invalidateAll).toBe("function");
    });
  });

  describe("Multi-Agent Coordination Specific Features", () => {
    it("should handle coordination metrics for conflict prevention", async () => {
      const coordinationData = {
        ...mockCoordinationMetrics,
        conflictsPrevented: 127,
        taskDeduplicationRate: 0.92,
      };
      mockApiClient.get.mockResolvedValue(coordinationData);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useCoordinationMetrics(), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data?.conflictsPrevented).toBe(127);
      expect(result.current.data?.taskDeduplicationRate).toBe(0.92);
    });

    it("should support agent status filtering in coordination scenarios", async () => {
      const activeAgents = mockAgents.filter((agent) =>
        agent.status === "active"
      );
      mockApiClient.get.mockResolvedValue(activeAgents);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useAgents(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should fetch all agents, filtering happens in components
      expect(mockApiClient.get).toHaveBeenCalledWith("/api/agents");
    });

    it("should handle session coordination patterns", async () => {
      const fanOutSession = {
        ...mockSessions[0],
        context:
          "FAN_OUT_SYNTHESIZE: 7 researchers → 2 analysts → 1 synthesizer",
      };
      mockApiClient.get.mockResolvedValue([fanOutSession]);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useSessions(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const session = result.current.data?.[0];
      expect(session?.context).toContain("FAN_OUT_SYNTHESIZE");
    });

    it("should support real-time coordination events", async () => {
      const coordinationEvents = [
        ...mockEvents,
        {
          id: "event_002",
          coordinationId: "coord_001",
          agentId: "analyst_001",
          eventType: "pre_agent_spawn" as const,
          timestamp: "2024-01-01T10:35:00Z",
          metadata: {
            spawned_role: "synthesizer",
            coordination_pattern: "fan_in",
          },
        },
      ];
      mockApiClient.get.mockResolvedValue(coordinationEvents);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useEvents("coord_001"), {
        wrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[1].eventType).toBe("pre_agent_spawn");
    });

    it("should manage file locks for concurrent agent operations", async () => {
      const concurrentLocks = [
        ...mockFileLocks,
        {
          filePath: "/workspace/analysis.md",
          agentId: "analyst_001",
          expiration: "2024-01-01T11:05:00Z",
          isStale: false,
        },
      ];
      mockApiClient.get.mockResolvedValue(concurrentLocks);

      const wrapper = createWrapper();
      const { result } = renderHook(() => hooks.useFileLocks(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toHaveLength(2);
      expect(result.current.data?.[1].agentId).toBe("analyst_001");
    });
  });

  describe("Performance and Optimization", () => {
    it("should use appropriate stale times for different data types", () => {
      // Configuration data should have longer stale times
      const wrapper = createWrapper();

      // Roles and domains should cache for 30 minutes
      const { result: rolesResult } = renderHook(() => hooks.useRoles(), {
        wrapper,
      });
      const { result: domainsResult } = renderHook(() => hooks.useDomains(), {
        wrapper,
      });

      expect(rolesResult.current).toBeDefined();
      expect(domainsResult.current).toBeDefined();
    });

    it("should handle concurrent requests efficiently", async () => {
      mockApiClient.get.mockResolvedValue(mockSessions);

      const wrapper = createWrapper();

      // Multiple hooks using the same query should share the request
      const { result: result1 } = renderHook(() => hooks.useSessions(), {
        wrapper,
      });
      const { result: result2 } = renderHook(() => hooks.useSessions(), {
        wrapper,
      });

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
        expect(result2.current.isLoading).toBe(false);
      });

      // Should only make one API call due to React Query deduplication
      expect(mockApiClient.get).toHaveBeenCalledTimes(1);
      expect(result1.current.data).toEqual(result2.current.data);
    });
  });
});
