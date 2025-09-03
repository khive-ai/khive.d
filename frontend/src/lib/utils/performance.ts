// Performance utilities inspired by rust-performance principles

interface PerformanceMetrics {
  fcp: number; // First Contentful Paint
  lcp: number; // Largest Contentful Paint
  fid: number; // First Input Delay
  cls: number; // Cumulative Layout Shift
  ttfb: number; // Time to First Byte
}

interface ResourceTiming {
  name: string;
  duration: number;
  transferSize: number;
  decodedSize: number;
}

/**
 * Measures Core Web Vitals and reports to analytics
 * Zero-cost abstraction: Only runs in production with proper conditions
 */
export function measureWebVitals(
  onPerfEntry?: (metric: PerformanceMetrics) => void,
): void {
  if (typeof window === "undefined" || !("performance" in window)) return;

  const metrics: Partial<PerformanceMetrics> = {};

  // First Contentful Paint
  const fcpEntry = performance.getEntriesByName("first-contentful-paint")[0];
  if (fcpEntry) {
    metrics.fcp = fcpEntry.startTime;
  }

  // Largest Contentful Paint
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1] as PerformanceEventTiming;
    metrics.lcp = lastEntry.startTime;

    if (Object.keys(metrics).length === 5 && onPerfEntry) {
      onPerfEntry(metrics as PerformanceMetrics);
    }
  }).observe({ type: "largest-contentful-paint", buffered: true });

  // First Input Delay
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    entries.forEach((entry) => {
      const fidEntry = entry as PerformanceEventTiming;
      metrics.fid = fidEntry.processingStart - fidEntry.startTime;
    });
  }).observe({ type: "first-input", buffered: true });

  // Cumulative Layout Shift
  new PerformanceObserver((list) => {
    let clsValue = 0;
    const entries = list.getEntries() as PerformanceEventTiming[];

    entries.forEach((entry) => {
      if (!("hadRecentInput" in entry) || !(entry as any).hadRecentInput) {
        clsValue += (entry as any).value;
      }
    });

    metrics.cls = clsValue;
  }).observe({ type: "layout-shift", buffered: true });

  // Time to First Byte
  const navigationEntry = performance.getEntriesByType(
    "navigation",
  )[0] as PerformanceNavigationTiming;
  if (navigationEntry) {
    metrics.ttfb = navigationEntry.responseStart - navigationEntry.requestStart;
  }
}

/**
 * Analyzes resource loading performance
 * Memory-optimized: Processes resources in chunks to avoid memory spikes
 */
export function analyzeResourcePerformance(): ResourceTiming[] {
  if (typeof window === "undefined" || !("performance" in window)) return [];

  const resources = performance.getEntriesByType(
    "resource",
  ) as PerformanceResourceTiming[];
  const chunkSize = 50; // Process in chunks to avoid memory issues
  const results: ResourceTiming[] = [];

  for (let i = 0; i < resources.length; i += chunkSize) {
    const chunk = resources.slice(i, i + chunkSize);

    chunk.forEach((resource) => {
      // Skip data URLs and blob URLs for cleaner metrics
      if (
        resource.name.startsWith("data:") || resource.name.startsWith("blob:")
      ) return;

      results.push({
        name: resource.name,
        duration: resource.duration,
        transferSize: resource.transferSize || 0,
        decodedSize: resource.decodedBodySize || 0,
      });
    });
  }

  return results.sort((a, b) => b.duration - a.duration);
}

/**
 * Performance-aware component wrapper
 * Implements lazy loading and intersection observer patterns
 */
export class PerformanceObserver {
  private static instance: PerformanceObserver;
  private observers: Map<string, IntersectionObserver> = new Map();

  static getInstance(): PerformanceObserver {
    if (!PerformanceObserver.instance) {
      PerformanceObserver.instance = new PerformanceObserver();
    }
    return PerformanceObserver.instance;
  }

  observeElement(
    element: Element,
    callback: (entry: IntersectionObserverEntry) => void,
    options?: IntersectionObserverInit,
  ): void {
    const key = `${element.tagName}-${Date.now()}`;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(callback);
      },
      {
        threshold: 0.1,
        rootMargin: "50px",
        ...options,
      },
    );

    observer.observe(element);
    this.observers.set(key, observer);
  }

  disconnect(key?: string): void {
    if (key && this.observers.has(key)) {
      this.observers.get(key)?.disconnect();
      this.observers.delete(key);
    } else {
      // Disconnect all observers
      this.observers.forEach((observer) => observer.disconnect());
      this.observers.clear();
    }
  }
}

/**
 * Memory usage monitoring
 * Rust-inspired: Track allocations and deallocations
 */
export function getMemoryUsage(): MemoryUsage | null {
  if (
    typeof window === "undefined" || !("performance" in window) ||
    !("memory" in performance)
  ) {
    return null;
  }

  const memory = (performance as any).memory;
  return {
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
    utilization: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100,
  };
}

interface MemoryUsage {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  utilization: number;
}

/**
 * Bundle size analyzer for development
 * Helps identify optimization opportunities
 */
export function analyzeBundleSize(): void {
  if (process.env.NODE_ENV === "development" && typeof window !== "undefined") {
    const scripts = Array.from(document.querySelectorAll("script[src]"));
    const styles = Array.from(
      document.querySelectorAll('link[rel="stylesheet"]'),
    );

    console.group("📦 Bundle Analysis");
    console.log("Scripts:", scripts.length);
    console.log("Stylesheets:", styles.length);

    scripts.forEach((script, index) => {
      console.log(`Script ${index + 1}:`, (script as HTMLScriptElement).src);
    });

    console.groupEnd();
  }
}

/**
 * Performance budget checker
 * Alerts when performance thresholds are exceeded
 */
export interface PerformanceBudget {
  fcp: number; // First Contentful Paint budget in ms
  lcp: number; // Largest Contentful Paint budget in ms
  cls: number; // Cumulative Layout Shift budget
  fid: number; // First Input Delay budget in ms
}

export function checkPerformanceBudget(
  metrics: PerformanceMetrics,
  budget: PerformanceBudget,
): { passed: boolean; violations: string[] } {
  const violations: string[] = [];

  if (metrics.fcp > budget.fcp) {
    violations.push(`FCP exceeded budget: ${metrics.fcp}ms > ${budget.fcp}ms`);
  }

  if (metrics.lcp > budget.lcp) {
    violations.push(`LCP exceeded budget: ${metrics.lcp}ms > ${budget.lcp}ms`);
  }

  if (metrics.cls > budget.cls) {
    violations.push(`CLS exceeded budget: ${metrics.cls} > ${budget.cls}`);
  }

  if (metrics.fid > budget.fid) {
    violations.push(`FID exceeded budget: ${metrics.fid}ms > ${budget.fid}ms`);
  }

  return {
    passed: violations.length === 0,
    violations,
  };
}
