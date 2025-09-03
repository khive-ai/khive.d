/**
 * Main Providers Component - Application Architecture Foundation
 * Combines all providers with proper async patterns and error handling
 */

"use client";

import { ReactNode } from "react";
import { QueryProvider } from "./query-client";
import { CustomThemeProvider } from "./theme-provider";
import { ErrorBoundary } from "./error-boundary";

interface ProvidersProps {
  children: ReactNode;
}

/**
 * Main providers component that wraps the entire application
 * Implements proper provider hierarchy for optimal async performance
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <CustomThemeProvider>
          {children}
        </CustomThemeProvider>
      </QueryProvider>
    </ErrorBoundary>
  );
}

export default Providers;

// Re-export all provider components and hooks for convenience
export { QueryProvider } from "./query-client";
export { CustomThemeProvider, useTheme } from "./theme-provider";
export { ErrorBoundary } from "./error-boundary";
