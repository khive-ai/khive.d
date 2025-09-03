/**
 * React Query hooks for async state management
 * Implements async-programming patterns for optimal UX
 */

import {
  useMutation,
  UseMutationOptions,
  useQuery,
  useQueryClient,
  UseQueryOptions,
} from "@tanstack/react-query";
import { apiClient, KhiveApiError } from "./client";
import {
  Agent,
  AgentAnalytics,
  CoordinationMetrics,
  Domain,
  FileLock,
  HookEvent,
  Plan,
  Role,
  Session,
  SystemPerformanceMetrics,
} from "../types";

// Query Keys for consistent caching
export const queryKeys = {
  sessions: () => ["sessions"] as const,
  session: (id: string) => ["sessions", id] as const,
  agents: () => ["agents"] as const,
  agent: (id: string) => ["agents", id] as const,
  metrics: () => ["metrics"] as const,
  systemPerformance: () => ["system-performance"] as const,
  agentAnalytics: () => ["agent-analytics"] as const,
  plans: () => ["plans"] as const,
  plan: (id: string) => ["plans", id] as const,
  roles: () => ["roles"] as const,
  domains: () => ["domains"] as const,
  events: (coordinationId?: string) => ["events", coordinationId] as const,
  fileLocks: () => ["file-locks"] as const,
} as const;

// Default query options with proper error handling
const defaultQueryOptions = {
  staleTime: 1000 * 60 * 5, // 5 minutes
  retry: (failureCount: number, error: any) => {
    if (
      error instanceof KhiveApiError &&
      error.status >= 400 &&
      error.status < 500
    ) {
      return false; // Don't retry client errors
    }
    return failureCount < 3;
  },
  retryDelay: (attemptIndex: number) =>
    Math.min(1000 * 2 ** attemptIndex, 30000),
};

// Session Management Hooks
export function useSessions(
  options?: UseQueryOptions<Session[], KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.sessions(),
    queryFn: () => apiClient.get<Session[]>("/api/sessions"),
    ...defaultQueryOptions,
    ...options,
  });
}

export function useSession(
  id: string,
  options?: UseQueryOptions<Session, KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.session(id),
    queryFn: () => apiClient.get<Session>(`/api/sessions/${id}`),
    enabled: !!id,
    ...defaultQueryOptions,
    ...options,
  });
}

export function useCreateSession(
  options?: UseMutationOptions<Session, KhiveApiError, Partial<Session>>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionData: Partial<Session>) =>
      apiClient.post<Session>("/api/sessions", sessionData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions() });
    },
    ...options,
  });
}

// Agent Spawning Hook
interface SpawnAgentRequest {
  role: string;
  domain: string;
  taskContext: string;
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  qualityGate: "basic" | "thorough" | "critical";
  expectedArtifacts: string[];
  agentCount?: number;
  timeout?: number;
  priority?: "low" | "normal" | "high" | "critical";
  isolateWorkspace?: boolean;
  coordinationId?: string;
}

interface SpawnAgentResponse {
  agents: Agent[];
  sessionId: string;
  coordinationId: string;
  status: "spawning" | "active" | "error";
  message: string;
}

export function useSpawnAgent(
  options?: UseMutationOptions<
    SpawnAgentResponse,
    KhiveApiError,
    SpawnAgentRequest
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (spawnRequest: SpawnAgentRequest) =>
      apiClient.post<SpawnAgentResponse>("/api/agents", spawnRequest),
    onSuccess: () => {
      // Invalidate related queries to refresh UI
      queryClient.invalidateQueries({ queryKey: queryKeys.agents() });
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions() });
      queryClient.invalidateQueries({ queryKey: queryKeys.metrics() });
    },
    ...options,
  });
}

// Agent Management Hooks
export function useAgents(options?: UseQueryOptions<Agent[], KhiveApiError>) {
  return useQuery({
    queryKey: queryKeys.agents(),
    queryFn: () => apiClient.get<Agent[]>("/api/agents"),
    ...defaultQueryOptions,
    ...options,
  });
}

export function useAgent(
  id: string,
  options?: UseQueryOptions<Agent, KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.agent(id),
    queryFn: () => apiClient.get<Agent>(`/api/agents/${id}`),
    enabled: !!id,
    ...defaultQueryOptions,
    ...options,
  });
}

// Coordination Metrics Hook
export function useCoordinationMetrics(
  options?: UseQueryOptions<CoordinationMetrics, KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.metrics(),
    queryFn: () =>
      apiClient.get<CoordinationMetrics>("/api/coordination/metrics"),
    refetchInterval: 10000, // Refresh every 10 seconds
    ...defaultQueryOptions,
    ...options,
  });
}

// Plan Management Hooks
export function usePlans(options?: UseQueryOptions<Plan[], KhiveApiError>) {
  return useQuery({
    queryKey: queryKeys.plans(),
    queryFn: () => apiClient.get<Plan[]>("/api/plans"),
    ...defaultQueryOptions,
    ...options,
  });
}

export function usePlan(
  id: string,
  options?: UseQueryOptions<Plan, KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.plan(id),
    queryFn: () => apiClient.get<Plan>(`/api/plans/${id}`),
    enabled: !!id,
    ...defaultQueryOptions,
    ...options,
  });
}

// Configuration Hooks
export function useRoles(options?: UseQueryOptions<Role[], KhiveApiError>) {
  return useQuery({
    queryKey: queryKeys.roles(),
    queryFn: () => apiClient.get<Role[]>("/api/config/roles"),
    staleTime: 1000 * 60 * 30, // Roles don't change often, cache for 30 minutes
    ...options,
  });
}

export function useDomains(options?: UseQueryOptions<Domain[], KhiveApiError>) {
  return useQuery({
    queryKey: queryKeys.domains(),
    queryFn: () => apiClient.get<Domain[]>("/api/config/domains"),
    staleTime: 1000 * 60 * 30, // Domains don't change often, cache for 30 minutes
    ...options,
  });
}

// Event Hooks with real-time capabilities
export function useEvents(
  coordinationId?: string,
  options?: UseQueryOptions<HookEvent[], KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.events(coordinationId),
    queryFn: () => {
      const url = coordinationId
        ? `/api/events?coordination_id=${coordinationId}`
        : "/api/events";
      return apiClient.get<HookEvent[]>(url);
    },
    refetchInterval: 2000, // Real-time updates every 2 seconds
    ...defaultQueryOptions,
    ...options,
  });
}

// File Lock Management
export function useFileLocks(
  options?: UseQueryOptions<FileLock[], KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.fileLocks(),
    queryFn: () => apiClient.get<FileLock[]>("/api/coordination/file-locks"),
    refetchInterval: 5000, // Check locks every 5 seconds
    ...defaultQueryOptions,
    ...options,
  });
}

// System Performance Hooks for Observability Console
export function useSystemPerformance(
  options?: UseQueryOptions<SystemPerformanceMetrics, KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.systemPerformance(),
    queryFn: () =>
      apiClient.get<SystemPerformanceMetrics>(
        "/api/observability/system-performance",
      ),
    refetchInterval: 5000, // Refresh every 5 seconds for real-time data
    ...defaultQueryOptions,
    ...options,
  });
}

// Agent Analytics Hooks for Success/Failure Tracking
export function useAgentAnalytics(
  options?: UseQueryOptions<AgentAnalytics, KhiveApiError>,
) {
  return useQuery({
    queryKey: queryKeys.agentAnalytics(),
    queryFn: () =>
      apiClient.get<AgentAnalytics>("/api/observability/agent-analytics"),
    refetchInterval: 30000, // Refresh every 30 seconds
    ...defaultQueryOptions,
    ...options,
  });
}

// Utility hook for invalidating queries
export function useInvalidateQueries() {
  const queryClient = useQueryClient();

  return {
    invalidateSessions: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.sessions() }),
    invalidateAgents: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.agents() }),
    invalidateMetrics: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.metrics() }),
    invalidateSystemPerformance: () =>
      queryClient.invalidateQueries({
        queryKey: queryKeys.systemPerformance(),
      }),
    invalidateAgentAnalytics: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.agentAnalytics() }),
    invalidatePlans: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.plans() }),
    invalidateEvents: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.events() }),
    invalidateAll: () => queryClient.invalidateQueries(),
  };
}
