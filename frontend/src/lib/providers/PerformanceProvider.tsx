"use client";

import React, {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

import {
  checkPerformanceBudget,
  measureWebVitals,
  type PerformanceBudget,
} from "@/utils/performance";

interface PerformanceContextType {
  isMonitoring: boolean;
  performanceData: {
    fcp?: number;
    lcp?: number;
    fid?: number;
    cls?: number;
    ttfb?: number;
  };
  performanceBudget: PerformanceBudget;
  budgetViolations: string[];
  toggleMonitoring: () => void;
  updateBudget: (budget: Partial<PerformanceBudget>) => void;
}

const defaultBudget: PerformanceBudget = {
  fcp: 1500, // 1.5s for First Contentful Paint
  lcp: 2500, // 2.5s for Largest Contentful Paint
  cls: 0.1, // 0.1 for Cumulative Layout Shift
  fid: 100, // 100ms for First Input Delay
};

const PerformanceContext = createContext<PerformanceContextType | undefined>(
  undefined,
);

interface PerformanceProviderProps {
  children: ReactNode;
  enableInProduction?: boolean;
  customBudget?: Partial<PerformanceBudget>;
}

/**
 * Performance Provider
 * Provides performance monitoring context throughout the app
 * Inspired by rust-performance: zero-cost in production unless explicitly enabled
 */
export function PerformanceProvider({
  children,
  enableInProduction = false,
  customBudget = {},
}: PerformanceProviderProps) {
  const [isMonitoring, setIsMonitoring] = useState(
    process.env.NODE_ENV === "development" || enableInProduction,
  );

  const [performanceData, setPerformanceData] = useState<{
    fcp?: number;
    lcp?: number;
    fid?: number;
    cls?: number;
    ttfb?: number;
  }>({});

  const [performanceBudget, setPerformanceBudget] = useState<PerformanceBudget>(
    {
      ...defaultBudget,
      ...customBudget,
    },
  );

  const [budgetViolations, setBudgetViolations] = useState<string[]>([]);

  useEffect(() => {
    if (!isMonitoring) return;

    measureWebVitals((metrics) => {
      setPerformanceData(metrics);

      // Check budget violations
      const budgetCheck = checkPerformanceBudget(metrics, performanceBudget);
      setBudgetViolations(budgetCheck.violations);

      // Log violations in development
      if (process.env.NODE_ENV === "development" && !budgetCheck.passed) {
        console.group("⚠️ Performance Budget Violations");
        budgetCheck.violations.forEach((violation) => console.warn(violation));
        console.groupEnd();
      }

      // Send to analytics in production (if configured)
      if (process.env.NODE_ENV === "production" && enableInProduction) {
        // Replace with your analytics service
        // analytics.track('performance_metrics', metrics);
      }
    });
  }, [isMonitoring, performanceBudget, enableInProduction]);

  const toggleMonitoring = () => {
    setIsMonitoring((prev) => !prev);
  };

  const updateBudget = (budget: Partial<PerformanceBudget>) => {
    setPerformanceBudget((prev) => ({ ...prev, ...budget }));
  };

  return (
    <PerformanceContext.Provider
      value={{
        isMonitoring,
        performanceData,
        performanceBudget,
        budgetViolations,
        toggleMonitoring,
        updateBudget,
      }}
    >
      {children}
      {process.env.NODE_ENV === "development" && <PerformanceMonitor />}
    </PerformanceContext.Provider>
  );
}

/**
 * Development-only performance monitor
 * Shows real-time performance data in development
 */
function PerformanceMonitor() {
  const context = useContext(PerformanceContext);
  if (!context?.isMonitoring) return null;

  const { performanceData, budgetViolations } = context;

  return (
    <div
      style={{
        position: "fixed",
        bottom: "20px",
        right: "20px",
        background: "rgba(0, 0, 0, 0.8)",
        color: "white",
        padding: "12px",
        borderRadius: "8px",
        fontSize: "12px",
        fontFamily: "monospace",
        zIndex: 9999,
        minWidth: "200px",
        maxWidth: "300px",
      }}
    >
      <div style={{ fontWeight: "bold", marginBottom: "8px" }}>
        🎯 Performance Monitor
      </div>

      {performanceData.fcp && (
        <div
          style={{ color: performanceData.fcp > 1500 ? "#ff6b6b" : "#51cf66" }}
        >
          FCP: {performanceData.fcp.toFixed(0)}ms
        </div>
      )}

      {performanceData.lcp && (
        <div
          style={{ color: performanceData.lcp > 2500 ? "#ff6b6b" : "#51cf66" }}
        >
          LCP: {performanceData.lcp.toFixed(0)}ms
        </div>
      )}

      {performanceData.cls !== undefined && (
        <div
          style={{ color: performanceData.cls > 0.1 ? "#ff6b6b" : "#51cf66" }}
        >
          CLS: {performanceData.cls.toFixed(3)}
        </div>
      )}

      {performanceData.fid && (
        <div
          style={{ color: performanceData.fid > 100 ? "#ff6b6b" : "#51cf66" }}
        >
          FID: {performanceData.fid.toFixed(0)}ms
        </div>
      )}

      {budgetViolations.length > 0 && (
        <div style={{ marginTop: "8px", color: "#ff6b6b", fontSize: "10px" }}>
          <div>⚠️ Budget Violations:</div>
          {budgetViolations.slice(0, 2).map((violation, index) => (
            <div key={index} style={{ marginTop: "2px" }}>
              {violation}
            </div>
          ))}
          {budgetViolations.length > 2 && (
            <div>... and {budgetViolations.length - 2} more</div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Hook to use performance context
 */
export function usePerformanceContext() {
  const context = useContext(PerformanceContext);
  if (context === undefined) {
    throw new Error(
      "usePerformanceContext must be used within a PerformanceProvider",
    );
  }
  return context;
}
