/**
 * TanStack React Query Configuration
 * Centralized query client setup with caching and error handling
 */

import { QueryClient } from "@tanstack/react-query";
import { getErrorMessage } from "./client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Stale time - how long data is considered fresh
      staleTime: 5 * 60 * 1000, // 5 minutes

      // Cache time - how long unused data stays in cache
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)

      // Retry configuration
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors (client errors)
        if (error instanceof Error && error.message.includes('"status":')) {
          try {
            const errorData = JSON.parse(error.message);
            if (errorData.status >= 400 && errorData.status < 500) {
              return false;
            }
          } catch {
            // If we can't parse the error, continue with default retry logic
          }
        }

        // Retry up to 3 times for other errors
        return failureCount < 3;
      },

      // Retry delay with exponential backoff
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),

      // Refetch on window focus for real-time data
      refetchOnWindowFocus: true,

      // Refetch on reconnect
      refetchOnReconnect: "always",

      // Error handling
      throwOnError: false,
    },

    mutations: {
      // Retry mutations once
      retry: 1,

      // Retry delay
      retryDelay: 1000,

      // Error handling
      throwOnError: false,

      // Global mutation error handler
      onError: (error) => {
        const message = getErrorMessage(error);
        console.error("Mutation error:", message);

        // You could integrate with a toast system here
        // toast.error(message);
      },
    },
  },
});

// Query key factory for consistent key management
export const queryKeys = {
  // Sessions
  sessions: ["sessions"] as const,
  session: (id: string) => ["sessions", id] as const,

  // Agents
  agents: ["agents"] as const,
  agent: (id: string) => ["agents", id] as const,
  agentsBySession: (sessionId: string) =>
    ["agents", "session", sessionId] as const,

  // Coordination
  coordination: ["coordination"] as const,
  coordinationMetrics: ["coordination", "metrics"] as const,
  coordinationEvents: (coordinationId?: string) =>
    coordinationId
      ? ["coordination", "events", coordinationId] as const
      : ["coordination", "events"] as const,

  // Plans
  plans: ["plans"] as const,
  plan: (id: string) => ["plans", id] as const,
  plansBySession: (sessionId: string) =>
    ["plans", "session", sessionId] as const,

  // File locks
  fileLocks: ["file-locks"] as const,

  // Hook events
  hookEvents: (coordinationId?: string, agentId?: string) => {
    const base = ["hook-events"];
    if (coordinationId) base.push(coordinationId);
    if (agentId) base.push(agentId);
    return base as const;
  },

  // Roles and Domains
  roles: ["roles"] as const,
  domains: ["domains"] as const,
} as const;

// Cache invalidation helpers
export const invalidateQueries = {
  sessions: () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.sessions }),
  session: (id: string) =>
    queryClient.invalidateQueries({ queryKey: queryKeys.session(id) }),
  agents: () => queryClient.invalidateQueries({ queryKey: queryKeys.agents }),
  agent: (id: string) =>
    queryClient.invalidateQueries({ queryKey: queryKeys.agent(id) }),
  coordination: () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.coordination }),
  plans: () => queryClient.invalidateQueries({ queryKey: queryKeys.plans }),
  all: () => queryClient.invalidateQueries(),
};

// Cache prefetching helpers
export const prefetchQueries = {
  sessions: () =>
    queryClient.prefetchQuery({
      queryKey: queryKeys.sessions,
      staleTime: 30000, // 30 seconds
    }),

  agents: () =>
    queryClient.prefetchQuery({
      queryKey: queryKeys.agents,
      staleTime: 30000,
    }),
};

// Optimistic updates helpers
export const optimisticUpdates = {
  updateSession: (sessionId: string, updater: (old: any) => any) => {
    queryClient.setQueryData(queryKeys.session(sessionId), updater);
  },

  updateAgent: (agentId: string, updater: (old: any) => any) => {
    queryClient.setQueryData(queryKeys.agent(agentId), updater);
  },
};

export default queryClient;
