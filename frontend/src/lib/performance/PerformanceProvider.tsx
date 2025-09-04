"use client";

import React, { createContext, useContext, useCallback, useMemo, useState, useRef } from 'react';
import { debounce, throttle } from 'lodash-es';

/**
 * Performance Optimization Architecture
 * 
 * This provider implements comprehensive performance optimization patterns:
 * 
 * Patterns Applied:
 * - Context Pattern: Centralized performance utilities
 * - Observer Pattern: Performance monitoring and metrics
 * - Strategy Pattern: Different optimization strategies per component type
 * - Memoization: Intelligent caching of expensive computations
 * - Throttling/Debouncing: Rate limiting for frequent operations
 * - Lazy Loading: On-demand resource loading
 * - Virtual Scrolling: Efficient rendering of large lists
 */

export interface PerformanceMetrics {
  renderCount: number;
  lastRenderTime: number;
  averageRenderTime: number;
  memoryUsage: number;
  componentTree: Map<string, ComponentMetrics>;
}

export interface ComponentMetrics {
  id: string;
  name: string;
  renderCount: number;
  totalRenderTime: number;
  averageRenderTime: number;
  lastProps: any;
  propsChanged: boolean;
  memorySize: number;
}

export interface PerformanceConfig {
  enableMetrics: boolean;
  enableMemoization: boolean;
  debounceDelay: number;
  throttleDelay: number;
  maxCacheSize: number;
  enableVirtualScrolling: boolean;
  chunkSize: number;
}

export interface PerformanceContextValue {
  // Configuration
  config: PerformanceConfig;
  updateConfig: (updates: Partial<PerformanceConfig>) => void;
  
  // Metrics
  metrics: PerformanceMetrics;
  getComponentMetrics: (componentId: string) => ComponentMetrics | undefined;
  recordRender: (componentId: string, renderTime: number, props?: any) => void;
  
  // Optimization Utilities
  memoize: <T extends (...args: any[]) => any>(fn: T, keyFn?: (...args: Parameters<T>) => string) => T;
  debounceCallback: <T extends (...args: any[]) => any>(fn: T, delay?: number) => T;
  throttleCallback: <T extends (...args: any[]) => any>(fn: T, delay?: number) => T;
  
  // Virtual Scrolling
  createVirtualList: (items: any[], itemHeight: number, containerHeight: number) => {
    visibleItems: any[];
    startIndex: number;
    endIndex: number;
    totalHeight: number;
    offsetY: number;
  };
  
  // Lazy Loading
  createLazyLoader: (threshold?: number) => {
    observe: (element: Element, callback: () => void) => void;
    unobserve: (element: Element) => void;
  };
  
  // Performance Monitoring
  startPerformanceMonitoring: (componentId: string) => () => void;
  getPerformanceReport: () => PerformanceReport;
}

export interface PerformanceReport {
  timestamp: number;
  summary: {
    totalComponents: number;
    slowestComponent: string;
    averageRenderTime: number;
    totalRenderCount: number;
    memoryFootprint: number;
  };
  recommendations: string[];
  componentDetails: ComponentMetrics[];
}

const defaultConfig: PerformanceConfig = {
  enableMetrics: process.env.NODE_ENV === 'development',
  enableMemoization: true,
  debounceDelay: 300,
  throttleDelay: 16, // ~60fps
  maxCacheSize: 100,
  enableVirtualScrolling: true,
  chunkSize: 50
};

const PerformanceContext = createContext<PerformanceContextValue | null>(null);

export function usePerformance() {
  const context = useContext(PerformanceContext);
  if (!context) {
    throw new Error('usePerformance must be used within a PerformanceProvider');
  }
  return context;
}

export function PerformanceProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<PerformanceConfig>(defaultConfig);
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    renderCount: 0,
    lastRenderTime: 0,
    averageRenderTime: 0,
    memoryUsage: 0,
    componentTree: new Map()
  });

  // Performance monitoring refs
  const memoCache = useRef(new Map<string, { value: any; timestamp: number; hits: number }>());
  const observerRef = useRef<IntersectionObserver>();
  const performanceObserverRef = useRef<PerformanceObserver>();

  // Initialize performance monitoring
  React.useEffect(() => {
    if (!config.enableMetrics) return;

    // Initialize Performance Observer for more detailed metrics
    if (typeof window !== 'undefined' && 'PerformanceObserver' in window) {
      performanceObserverRef.current = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          if (entry.entryType === 'measure' && entry.name.startsWith('react-')) {
            // React DevTools integration
            setMetrics(prev => ({
              ...prev,
              lastRenderTime: entry.duration,
              averageRenderTime: (prev.averageRenderTime + entry.duration) / 2
            }));
          }
        });
      });
      
      performanceObserverRef.current.observe({ entryTypes: ['measure', 'navigation'] });
    }

    return () => {
      performanceObserverRef.current?.disconnect();
    };
  }, [config.enableMetrics]);

  // Configuration management
  const updateConfig = useCallback((updates: Partial<PerformanceConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

  // Component metrics tracking
  const recordRender = useCallback((componentId: string, renderTime: number, props?: any) => {
    if (!config.enableMetrics) return;

    setMetrics(prev => {
      const existing = prev.componentTree.get(componentId);
      const newMetrics: ComponentMetrics = {
        id: componentId,
        name: componentId,
        renderCount: (existing?.renderCount || 0) + 1,
        totalRenderTime: (existing?.totalRenderTime || 0) + renderTime,
        averageRenderTime: existing 
          ? (existing.totalRenderTime + renderTime) / (existing.renderCount + 1)
          : renderTime,
        lastProps: props,
        propsChanged: existing ? JSON.stringify(existing.lastProps) !== JSON.stringify(props) : true,
        memorySize: JSON.stringify(props || {}).length // Rough estimate
      };

      const updatedTree = new Map(prev.componentTree);
      updatedTree.set(componentId, newMetrics);

      return {
        ...prev,
        renderCount: prev.renderCount + 1,
        lastRenderTime: renderTime,
        componentTree: updatedTree
      };
    });
  }, [config.enableMetrics]);

  const getComponentMetrics = useCallback((componentId: string) => {
    return metrics.componentTree.get(componentId);
  }, [metrics.componentTree]);

  // Memoization with intelligent cache management
  const memoize = useCallback(<T extends (...args: any[]) => any>(
    fn: T, 
    keyFn?: (...args: Parameters<T>) => string
  ): T => {
    if (!config.enableMemoization) return fn;

    return ((...args: Parameters<T>): ReturnType<T> => {
      const key = keyFn ? keyFn(...args) : JSON.stringify(args);
      const cached = memoCache.current.get(key);
      const now = Date.now();

      // Check if cached result exists and is still valid (5 minute TTL)
      if (cached && now - cached.timestamp < 300000) {
        cached.hits++;
        return cached.value;
      }

      // Clean cache if it's getting too large
      if (memoCache.current.size > config.maxCacheSize) {
        // Remove oldest entries
        const entries = Array.from(memoCache.current.entries());
        entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
        entries.slice(0, config.maxCacheSize / 2).forEach(([key]) => {
          memoCache.current.delete(key);
        });
      }

      const result = fn(...args);
      memoCache.current.set(key, { value: result, timestamp: now, hits: 0 });
      return result;
    }) as T;
  }, [config.enableMemoization, config.maxCacheSize]);

  // Optimized debounce and throttle
  const debounceCallback = useCallback(<T extends (...args: any[]) => any>(
    fn: T, 
    delay: number = config.debounceDelay
  ): T => {
    return debounce(fn, delay) as T;
  }, [config.debounceDelay]);

  const throttleCallback = useCallback(<T extends (...args: any[]) => any>(
    fn: T, 
    delay: number = config.throttleDelay
  ): T => {
    return throttle(fn, delay) as T;
  }, [config.throttleDelay]);

  // Virtual scrolling implementation
  const createVirtualList = useCallback((
    items: any[], 
    itemHeight: number, 
    containerHeight: number
  ) => {
    if (!config.enableVirtualScrolling) {
      return {
        visibleItems: items,
        startIndex: 0,
        endIndex: items.length - 1,
        totalHeight: items.length * itemHeight,
        offsetY: 0
      };
    }

    const [scrollTop, setScrollTop] = useState(0);
    
    return useMemo(() => {
      const startIndex = Math.floor(scrollTop / itemHeight);
      const endIndex = Math.min(
        startIndex + Math.ceil(containerHeight / itemHeight) + 1,
        items.length - 1
      );
      
      const visibleItems = items.slice(startIndex, endIndex + 1);
      const totalHeight = items.length * itemHeight;
      const offsetY = startIndex * itemHeight;

      return {
        visibleItems,
        startIndex,
        endIndex,
        totalHeight,
        offsetY,
        onScroll: (event: React.UIEvent<HTMLDivElement>) => {
          setScrollTop(event.currentTarget.scrollTop);
        }
      };
    }, [items, itemHeight, containerHeight, scrollTop]);
  }, [config.enableVirtualScrolling]);

  // Lazy loading implementation
  const createLazyLoader = useCallback((threshold: number = 0.1) => {
    if (!observerRef.current && typeof window !== 'undefined') {
      observerRef.current = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const callback = (entry.target as any).__lazyCallback;
              if (callback) {
                callback();
                observerRef.current?.unobserve(entry.target);
                delete (entry.target as any).__lazyCallback;
              }
            }
          });
        },
        { threshold }
      );
    }

    return {
      observe: (element: Element, callback: () => void) => {
        (element as any).__lazyCallback = callback;
        observerRef.current?.observe(element);
      },
      unobserve: (element: Element) => {
        delete (element as any).__lazyCallback;
        observerRef.current?.unobserve(element);
      }
    };
  }, []);

  // Performance monitoring utilities
  const startPerformanceMonitoring = useCallback((componentId: string) => {
    const startTime = performance.now();
    
    return () => {
      const endTime = performance.now();
      const renderTime = endTime - startTime;
      recordRender(componentId, renderTime);
    };
  }, [recordRender]);

  const getPerformanceReport = useCallback((): PerformanceReport => {
    const components = Array.from(metrics.componentTree.values());
    const slowestComponent = components.reduce((prev, current) => 
      current.averageRenderTime > prev.averageRenderTime ? current : prev,
      components[0] || { id: 'none', averageRenderTime: 0 } as ComponentMetrics
    );

    const recommendations: string[] = [];

    // Generate recommendations based on metrics
    components.forEach(comp => {
      if (comp.averageRenderTime > 16) {
        recommendations.push(`${comp.name}: Consider optimizing render performance (${comp.averageRenderTime.toFixed(2)}ms avg)`);
      }
      if (comp.renderCount > 100 && !comp.propsChanged) {
        recommendations.push(`${comp.name}: Consider using React.memo() or useMemo() to prevent unnecessary re-renders`);
      }
      if (comp.memorySize > 10000) {
        recommendations.push(`${comp.name}: Large props object detected, consider prop optimization`);
      }
    });

    if (memoCache.current.size > config.maxCacheSize * 0.8) {
      recommendations.push('Memoization cache is nearly full. Consider increasing maxCacheSize or cache cleanup frequency.');
    }

    return {
      timestamp: Date.now(),
      summary: {
        totalComponents: components.length,
        slowestComponent: slowestComponent.name,
        averageRenderTime: components.reduce((sum, c) => sum + c.averageRenderTime, 0) / Math.max(components.length, 1),
        totalRenderCount: metrics.renderCount,
        memoryFootprint: components.reduce((sum, c) => sum + c.memorySize, 0)
      },
      recommendations,
      componentDetails: components.sort((a, b) => b.averageRenderTime - a.averageRenderTime)
    };
  }, [metrics, config.maxCacheSize]);

  // Cleanup
  React.useEffect(() => {
    return () => {
      observerRef.current?.disconnect();
      performanceObserverRef.current?.disconnect();
    };
  }, []);

  const contextValue: PerformanceContextValue = useMemo(() => ({
    config,
    updateConfig,
    metrics,
    getComponentMetrics,
    recordRender,
    memoize,
    debounceCallback,
    throttleCallback,
    createVirtualList,
    createLazyLoader,
    startPerformanceMonitoring,
    getPerformanceReport
  }), [
    config,
    updateConfig,
    metrics,
    getComponentMetrics,
    recordRender,
    memoize,
    debounceCallback,
    throttleCallback,
    createVirtualList,
    createLazyLoader,
    startPerformanceMonitoring,
    getPerformanceReport
  ]);

  return (
    <PerformanceContext.Provider value={contextValue}>
      {children}
    </PerformanceContext.Provider>
  );
}