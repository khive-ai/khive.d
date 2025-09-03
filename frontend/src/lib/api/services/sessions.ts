/**
 * Session API Services and Hooks
 * Handles all session-related API calls and React Query integration
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, type ApiResponse } from "../client";
import { invalidateQueries, queryKeys } from "../query-client";
import { Session } from "@/types";

// API Service Functions
export const sessionApi = {
  // Get all sessions
  getSessions: async (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ApiResponse<Session[]>> => {
    return apiClient.get("/sessions", params);
  },

  // Get single session
  getSession: async (id: string): Promise<ApiResponse<Session>> => {
    return apiClient.get(`/sessions/${id}`);
  },

  // Create new session
  createSession: async (data: {
    objective: string;
    context?: string;
    coordinationId?: string;
  }): Promise<ApiResponse<Session>> => {
    return apiClient.post("/sessions", data);
  },

  // Update session
  updateSession: async (
    id: string,
    data: Partial<Omit<Session, "id" | "createdAt">>,
  ): Promise<ApiResponse<Session>> => {
    return apiClient.patch(`/sessions/${id}`, data);
  },

  // Delete session
  deleteSession: async (id: string): Promise<ApiResponse<void>> => {
    return apiClient.delete(`/sessions/${id}`);
  },

  // Control session
  controlSession: async (
    id: string,
    action: "pause" | "resume" | "stop" | "restart",
  ): Promise<ApiResponse<Session>> => {
    return apiClient.post(`/sessions/${id}/${action}`);
  },
};

// React Query Hooks
export const useSessionsQuery = (params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) => {
  return useQuery({
    queryKey: [...queryKeys.sessions, params],
    queryFn: () => sessionApi.getSessions(params),
    select: (response) => response.data,
  });
};

export const useSessionQuery = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: queryKeys.session(id),
    queryFn: () => sessionApi.getSession(id),
    select: (response) => response.data,
    enabled: enabled && !!id,
  });
};

export const useCreateSessionMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: sessionApi.createSession,
    onSuccess: (response) => {
      // Add the new session to the cache
      queryClient.setQueryData(
        queryKeys.session(response.data.id),
        response,
      );

      // Invalidate sessions list to refresh
      invalidateQueries.sessions();
    },
  });
};

export const useUpdateSessionMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: {
      id: string;
      data: Partial<Omit<Session, "id" | "createdAt">>;
    }) => sessionApi.updateSession(id, data),
    onMutate: async ({ id, data }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.session(id) });

      // Snapshot the previous value
      const previousSession = queryClient.getQueryData(queryKeys.session(id));

      // Optimistically update to the new value
      queryClient.setQueryData(queryKeys.session(id), (old: any) => ({
        ...old,
        data: { ...old?.data, ...data, updatedAt: new Date().toISOString() },
      }));

      // Return a context object with the snapshotted value
      return { previousSession };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousSession) {
        queryClient.setQueryData(
          queryKeys.session(variables.id),
          context.previousSession,
        );
      }
    },
    onSettled: (data, error, variables) => {
      // Always refetch after error or success
      queryClient.invalidateQueries({
        queryKey: queryKeys.session(variables.id),
      });
      invalidateQueries.sessions();
    },
  });
};

export const useDeleteSessionMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: sessionApi.deleteSession,
    onSuccess: (_, sessionId) => {
      // Remove the session from cache
      queryClient.removeQueries({ queryKey: queryKeys.session(sessionId) });

      // Invalidate sessions list
      invalidateQueries.sessions();
    },
  });
};

export const useControlSessionMutation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, action }: {
      id: string;
      action: "pause" | "resume" | "stop" | "restart";
    }) => sessionApi.controlSession(id, action),
    onMutate: async ({ id, action }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.session(id) });

      // Optimistically update status based on action
      const statusMap = {
        pause: "pending",
        resume: "running",
        stop: "failed",
        restart: "running",
      } as const;

      queryClient.setQueryData(queryKeys.session(id), (old: any) => ({
        ...old,
        data: {
          ...old?.data,
          status: statusMap[action],
          updatedAt: new Date().toISOString(),
        },
      }));
    },
    onSettled: (data, error, variables) => {
      // Refetch to get the actual state
      queryClient.invalidateQueries({
        queryKey: queryKeys.session(variables.id),
      });
      invalidateQueries.sessions();
    },
  });
};
