/**
 * API Integration Export
 * Centralized exports for all API-related functionality
 */

// Core API client
export { apiClient, getErrorMessage, isApiError } from "./client";
export type { ApiError, ApiResponse } from "./client";

// Query client and utilities
export {
  invalidateQueries,
  optimisticUpdates,
  prefetchQueries,
  queryClient,
  queryKeys,
} from "./query-client";

// Service hooks
export * from "./services/sessions";

// Future services exports
// export * from './services/agents';
// export * from './services/coordination';
// export * from './services/plans';
