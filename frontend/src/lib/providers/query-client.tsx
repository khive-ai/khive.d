/**
 * React Query Provider with optimized configuration for async operations
 * Implements async-programming domain patterns for excellent UX
 */

"use client";

import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { ReactNode, useState } from "react";
import { KhiveApiError } from "../api/client";

interface Props {
  children: ReactNode;
}

// Global error handler for queries
const handleQueryError = (error: unknown) => {
  if (error instanceof KhiveApiError) {
    console.error("Query Error:", {
      message: error.message,
      status: error.status,
      code: error.code,
      details: error.details,
    });

    // You could integrate with a toast notification system here
    // toast.error(error.message);
  } else {
    console.error("Unknown Query Error:", error);
  }
};

// Global error handler for mutations
const handleMutationError = (error: unknown) => {
  if (error instanceof KhiveApiError) {
    console.error("Mutation Error:", {
      message: error.message,
      status: error.status,
      code: error.code,
      details: error.details,
    });

    // You could integrate with a toast notification system here
    // toast.error(error.message);
  } else {
    console.error("Unknown Mutation Error:", error);
  }
};

function makeQueryClient() {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: handleQueryError,
    }),
    mutationCache: new MutationCache({
      onError: handleMutationError,
    }),
    defaultOptions: {
      queries: {
        // Global query configuration following async-programming patterns
        staleTime: 1000 * 60 * 5, // 5 minutes
        gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
        retry: (failureCount, error) => {
          if (
            error instanceof KhiveApiError &&
            error.status >= 400 &&
            error.status < 500
          ) {
            return false; // Don't retry client errors
          }
          return failureCount < 3;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        refetchOnWindowFocus: false,
        refetchOnReconnect: true,
      },
      mutations: {
        // Global mutation configuration
        retry: (failureCount, error) => {
          if (
            error instanceof KhiveApiError &&
            error.status >= 400 &&
            error.status < 500
          ) {
            return false; // Don't retry client errors
          }
          return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined = undefined;

function getQueryClient() {
  if (typeof window === "undefined") {
    // Server: always make a new query client
    return makeQueryClient();
  } else {
    // Browser: make a new query client if we don't already have one
    if (!browserQueryClient) browserQueryClient = makeQueryClient();
    return browserQueryClient;
  }
}

export function QueryProvider({ children }: Props) {
  // NOTE: Avoid useState when initializing the query client if you don't
  // have a suspense boundary between this and the code that may
  // suspend because React will throw away the client on the initial
  // render if it suspends and there is no boundary
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools
        initialIsOpen={false}
        buttonPosition="bottom-right"
        position="bottom"
      />
    </QueryClientProvider>
  );
}

export default QueryProvider;
