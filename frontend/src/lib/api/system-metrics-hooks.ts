/**
 * System Performance Metrics API Hooks
 * MVP feature: Real-time CPU/memory monitoring and agent success/failure tracking
 */

import { useQuery, UseQueryOptions } from "@tanstack/react-query";
import { apiClient, KhiveApiError } from "./client";
import {
  AgentPerformanceMetrics,
  ObservabilityConfig,
  SystemHealthSummary,
  SystemMetrics,
  TimeSeriesData,
} from "../types/system-metrics";

// Query Keys for system metrics
export const systemMetricsQueryKeys = {
  systemMetrics: () => ["system-metrics"] as const,
  systemMetricsHistory: (timeRange: string) =>
    ["system-metrics-history", timeRange] as const,
  agentPerformance: () => ["agent-performance"] as const,
  agentPerformanceHistory: (agentId: string) =>
    ["agent-performance-history", agentId] as const,
  systemHealth: () => ["system-health"] as const,
  observabilityConfig: () => ["observability-config"] as const,
} as const;

// Default query options for real-time data
const realtimeQueryOptions = {
  staleTime: 1000 * 30, // 30 seconds
  retry: (failureCount: number, error: any) => {
    if (
      error instanceof KhiveApiError &&
      error.status >= 400 &&
      error.status < 500
    ) {
      return false;
    }
    return failureCount < 3;
  },
  retryDelay: (attemptIndex: number) =>
    Math.min(1000 * 2 ** attemptIndex, 10000),
};

/**
 * Hook for fetching current system metrics (CPU, memory, disk, network)
 * Refreshes every 5 seconds for real-time monitoring
 */
export function useSystemMetrics(
  options?: UseQueryOptions<SystemMetrics, KhiveApiError>,
) {
  return useQuery({
    queryKey: systemMetricsQueryKeys.systemMetrics(),
    queryFn: () => apiClient.get<SystemMetrics>("/api/system/metrics"),
    refetchInterval: 5000, // 5 seconds for CPU/memory updates
    ...realtimeQueryOptions,
    ...options,
  });
}

/**
 * Hook for fetching historical system metrics for charts
 * @param timeRange - Time range: '1h', '6h', '24h', '7d'
 */
export function useSystemMetricsHistory(
  timeRange: string = "1h",
  options?: UseQueryOptions<TimeSeriesData[], KhiveApiError>,
) {
  return useQuery({
    queryKey: systemMetricsQueryKeys.systemMetricsHistory(timeRange),
    queryFn: () =>
      apiClient.get<TimeSeriesData[]>(
        `/api/system/metrics/history?range=${timeRange}`,
      ),
    refetchInterval: timeRange === "1h" ? 30000 : 60000, // More frequent updates for short ranges
    ...realtimeQueryOptions,
    ...options,
  });
}

/**
 * Hook for fetching agent performance metrics and success/failure rates
 * Includes task completion rates, error rates, and duration statistics
 */
export function useAgentPerformanceMetrics(
  options?: UseQueryOptions<AgentPerformanceMetrics[], KhiveApiError>,
) {
  return useQuery({
    queryKey: systemMetricsQueryKeys.agentPerformance(),
    queryFn: () =>
      apiClient.get<AgentPerformanceMetrics[]>("/api/agents/performance"),
    refetchInterval: 10000, // 10 seconds for agent performance
    ...realtimeQueryOptions,
    ...options,
  });
}

/**
 * Hook for fetching performance history for a specific agent
 */
export function useAgentPerformanceHistory(
  agentId: string,
  options?: UseQueryOptions<TimeSeriesData[], KhiveApiError>,
) {
  return useQuery({
    queryKey: systemMetricsQueryKeys.agentPerformanceHistory(agentId),
    queryFn: () =>
      apiClient.get<TimeSeriesData[]>(
        `/api/agents/${agentId}/performance/history`,
      ),
    enabled: !!agentId,
    refetchInterval: 15000, // 15 seconds for individual agent history
    ...realtimeQueryOptions,
    ...options,
  });
}

/**
 * Hook for fetching overall system health summary
 * Combines system metrics, agent metrics, and alerts
 */
export function useSystemHealth(
  options?: UseQueryOptions<SystemHealthSummary, KhiveApiError>,
) {
  return useQuery({
    queryKey: systemMetricsQueryKeys.systemHealth(),
    queryFn: () => apiClient.get<SystemHealthSummary>("/api/system/health"),
    refetchInterval: 10000, // 10 seconds for health summary
    ...realtimeQueryOptions,
    ...options,
  });
}

/**
 * Hook for fetching observability console configuration
 * Used to configure thresholds, refresh rates, and chart settings
 */
export function useObservabilityConfig(
  options?: UseQueryOptions<ObservabilityConfig, KhiveApiError>,
) {
  return useQuery({
    queryKey: systemMetricsQueryKeys.observabilityConfig(),
    queryFn: () =>
      apiClient.get<ObservabilityConfig>("/api/system/observability/config"),
    staleTime: 1000 * 60 * 10, // Config doesn't change often, cache for 10 minutes
    ...options,
  });
}

/**
 * Helper hook for generating mock data during development
 * This will be used when the backend endpoints are not yet available
 * @param enabled - Whether to use mock data
 */
export function useMockSystemMetrics(enabled: boolean = false) {
  return useQuery({
    queryKey: ["mock-system-metrics"],
    queryFn: async (): Promise<SystemMetrics> => {
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 100));

      return {
        timestamp: new Date().toISOString(),
        cpu: {
          usage: Math.random() * 100,
          cores: 8,
          loadAverage: {
            load1: Math.random() * 2,
            load5: Math.random() * 2,
            load15: Math.random() * 2,
          },
          processes: Math.floor(Math.random() * 200) + 100,
        },
        memory: {
          total: 16 * 1024 * 1024 * 1024, // 16GB
          used: Math.random() * 12 * 1024 * 1024 * 1024, // Random usage up to 12GB
          free: 0, // Calculated
          usage: 0, // Calculated
        },
      };
    },
    enabled,
    refetchInterval: enabled ? 2000 : false,
  });
}

/**
 * Helper hook for generating mock agent performance data
 */
export function useMockAgentPerformance(enabled: boolean = false) {
  return useQuery({
    queryKey: ["mock-agent-performance"],
    queryFn: async (): Promise<AgentPerformanceMetrics[]> => {
      await new Promise((resolve) => setTimeout(resolve, 150));

      const agents = ["researcher_001", "architect_001", "implementer_001"];

      return agents.map((agentId) => ({
        agentId,
        role: agentId.split("_")[0],
        domain: "agentic-systems",
        totalTasks: Math.floor(Math.random() * 50) + 10,
        successfulTasks: Math.floor(Math.random() * 40) + 8,
        failedTasks: Math.floor(Math.random() * 10),
        successRate: Math.random() * 30 + 70, // 70-100%
        averageTaskDuration: Math.random() * 5000 + 1000,
        errorRate: Math.random() * 30, // 0-30%
        lastActivity: new Date(Date.now() - Math.random() * 3600000)
          .toISOString(),
        taskHistory: [],
      }));
    },
    enabled,
    refetchInterval: enabled ? 5000 : false,
  });
}
