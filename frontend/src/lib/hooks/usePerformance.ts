import { useEffect, useRef, useState } from "react";

import {
  analyzeResourcePerformance,
  getMemoryUsage,
  measureWebVitals,
} from "@/utils/performance";

interface PerformanceData {
  webVitals: {
    fcp?: number;
    lcp?: number;
    fid?: number;
    cls?: number;
    ttfb?: number;
  };
  resourceTiming: Array<{
    name: string;
    duration: number;
    transferSize: number;
    decodedSize: number;
  }>;
  memoryUsage: {
    usedJSHeapSize: number;
    totalJSHeapSize: number;
    jsHeapSizeLimit: number;
    utilization: number;
  } | null;
  renderTime: number;
}

/**
 * Performance monitoring hook
 * Tracks Core Web Vitals, resource loading, and memory usage
 * Inspired by rust-performance principles: zero-cost abstractions in production
 */
export function usePerformance(
  componentName?: string,
  enableDetailedMonitoring = process.env.NODE_ENV === "development",
): PerformanceData {
  const [performanceData, setPerformanceData] = useState<PerformanceData>({
    webVitals: {},
    resourceTiming: [],
    memoryUsage: null,
    renderTime: 0,
  });

  const renderStartTime = useRef<number>(performance.now());

  useEffect(() => {
    // Measure component render time
    const renderEndTime = performance.now();
    const renderTime = renderEndTime - renderStartTime.current;

    if (enableDetailedMonitoring && componentName) {
      console.log(
        `🎯 ${componentName} render time: ${renderTime.toFixed(2)}ms`,
      );
    }

    // Initialize performance monitoring
    measureWebVitals((metrics) => {
      setPerformanceData((prev) => ({
        ...prev,
        webVitals: metrics,
      }));

      // Log performance issues in development
      if (enableDetailedMonitoring) {
        const issues: string[] = [];

        if (metrics.fcp > 2000) issues.push(`High FCP: ${metrics.fcp}ms`);
        if (metrics.lcp > 2500) issues.push(`High LCP: ${metrics.lcp}ms`);
        if (metrics.cls > 0.1) issues.push(`High CLS: ${metrics.cls}`);
        if (metrics.fid > 100) issues.push(`High FID: ${metrics.fid}ms`);

        if (issues.length > 0) {
          console.warn("⚠️ Performance Issues:", issues);
        }
      }
    });

    // Analyze resource performance
    const resourceTiming = analyzeResourcePerformance();

    // Get memory usage
    const memoryUsage = getMemoryUsage();

    setPerformanceData((prev) => ({
      ...prev,
      resourceTiming,
      memoryUsage,
      renderTime,
    }));

    // Memory usage alerts (rust-inspired memory safety)
    if (memoryUsage && memoryUsage.utilization > 80) {
      console.warn(
        `🧠 High memory usage: ${memoryUsage.utilization.toFixed(1)}%`,
      );
    }
  }, [componentName, enableDetailedMonitoring]);

  return performanceData;
}

/**
 * Hook for tracking component-specific performance metrics
 * Useful for identifying performance bottlenecks in specific components
 */
export function useComponentPerformance(
  componentName: string,
  deps: React.DependencyList = [],
) {
  const startTime = useRef<number>(0);
  const [metrics, setMetrics] = useState({
    renderCount: 0,
    averageRenderTime: 0,
    lastRenderTime: 0,
  });

  useEffect(() => {
    startTime.current = performance.now();
  });

  useEffect(() => {
    const endTime = performance.now();
    const renderTime = endTime - startTime.current;

    setMetrics((prev) => {
      const newRenderCount = prev.renderCount + 1;
      const newAverageRenderTime =
        (prev.averageRenderTime * prev.renderCount + renderTime) /
        newRenderCount;

      return {
        renderCount: newRenderCount,
        averageRenderTime: newAverageRenderTime,
        lastRenderTime: renderTime,
      };
    });

    if (process.env.NODE_ENV === "development") {
      console.log(
        `🎯 ${componentName}: ${renderTime.toFixed(2)}ms (avg: ${
          metrics.averageRenderTime.toFixed(2)
        }ms)`,
      );
    }
  }, deps);

  return metrics;
}

/**
 * Hook for lazy loading components with performance monitoring
 * Implements intersection observer with performance tracking
 */
export function useLazyLoad<T extends HTMLElement>(
  threshold = 0.1,
  rootMargin = "50px",
) {
  const [isVisible, setIsVisible] = useState(false);
  const [loadTime, setLoadTime] = useState<number | null>(null);
  const elementRef = useRef<T>(null);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isVisible) {
          const startTime = performance.now();
          setIsVisible(true);

          // Measure load time
          requestAnimationFrame(() => {
            const endTime = performance.now();
            setLoadTime(endTime - startTime);
          });
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [threshold, rootMargin, isVisible]);

  return { elementRef, isVisible, loadTime };
}

/**
 * Hook for monitoring API call performance
 * Tracks request/response times and error rates
 */
export function useAPIPerformance() {
  const [apiMetrics, setApiMetrics] = useState({
    totalRequests: 0,
    failedRequests: 0,
    averageResponseTime: 0,
    slowRequests: 0, // Requests > 1000ms
  });

  const trackAPICall = async <T>(
    apiCall: () => Promise<T>,
    endpoint?: string,
  ): Promise<T> => {
    const startTime = performance.now();

    try {
      const result = await apiCall();
      const endTime = performance.now();
      const responseTime = endTime - startTime;

      setApiMetrics((prev) => {
        const newTotalRequests = prev.totalRequests + 1;
        const newAverageResponseTime =
          (prev.averageResponseTime * prev.totalRequests + responseTime) /
          newTotalRequests;

        return {
          ...prev,
          totalRequests: newTotalRequests,
          averageResponseTime: newAverageResponseTime,
          slowRequests: responseTime > 1000
            ? prev.slowRequests + 1
            : prev.slowRequests,
        };
      });

      if (process.env.NODE_ENV === "development") {
        const status = responseTime > 1000
          ? "🐌"
          : responseTime > 500
          ? "⚡"
          : "🚀";
        console.log(
          `${status} API ${endpoint || "call"}: ${responseTime.toFixed(2)}ms`,
        );
      }

      return result;
    } catch (error) {
      setApiMetrics((prev) => ({
        ...prev,
        totalRequests: prev.totalRequests + 1,
        failedRequests: prev.failedRequests + 1,
      }));
      throw error;
    }
  };

  return { apiMetrics, trackAPICall };
}
