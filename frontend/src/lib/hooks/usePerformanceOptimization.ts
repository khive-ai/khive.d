/**
 * React Hooks for Performance Optimization & Error Handling
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Provides React integration with performance optimization system:
 * - Performance monitoring and profiling
 * - Memory management and leak prevention
 * - Error boundaries and recovery
 * - Lazy loading and virtualization
 * - Render optimization patterns
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Subscription } from 'rxjs';
import { 
  performanceMonitor,
  globalMemoryManager,
  lazyLoadManager,
  PerformanceMetrics,
  PerformanceAlert,
  MemoryManager,
  VirtualScrollManager,
  VirtualScrollConfig
} from '../architecture/PerformanceOptimization';

// ============================================================================
// PERFORMANCE MONITORING HOOKS
// ============================================================================

/**
 * Hook for real-time performance monitoring
 */
export function usePerformanceMonitor() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const subscriptionRef = useRef<Subscription | null>(null);
  const alertsSubscriptionRef = useRef<Subscription | null>(null);

  useEffect(() => {
    console.log('[USE-PERF-MONITOR] Starting performance monitoring');

    // Subscribe to metrics
    subscriptionRef.current = performanceMonitor
      .getMetricsStream()
      .subscribe(newMetrics => {
        setMetrics(newMetrics);
      });

    // Subscribe to alerts
    alertsSubscriptionRef.current = performanceMonitor
      .getAlertsStream()
      .subscribe(newAlerts => {
        setAlerts(newAlerts);
        newAlerts.forEach(alert => {
          console.warn(`[USE-PERF-MONITOR] Performance alert: ${alert.message}`, alert);
        });
      });

    return () => {
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
      if (alertsSubscriptionRef.current) {
        alertsSubscriptionRef.current.unsubscribe();
        alertsSubscriptionRef.current = null;
      }
    };
  }, []);

  const recordCustomMetric = useCallback((metric: keyof PerformanceMetrics, value: number) => {
    performanceMonitor.recordCustomMetric(metric, value);
  }, []);

  const criticalAlerts = useMemo(() => 
    alerts.filter(alert => alert.severity === 'critical')
  , [alerts]);

  const getMetricTrend = useCallback((metric: keyof PerformanceMetrics, periods: number = 10) => {
    // Would implement trend calculation based on historical data
    return { trend: 'stable' as const, change: 0 };
  }, []);

  return {
    metrics,
    alerts,
    criticalAlerts,
    recordCustomMetric,
    getMetricTrend,
    isMonitoring: metrics !== null
  };
}

/**
 * Hook for component-level render profiling
 */
export function useRenderProfiler(componentName: string) {
  const renderCountRef = useRef(0);
  const [renderMetrics, setRenderMetrics] = useState({
    renderCount: 0,
    lastRenderTime: 0,
    averageRenderTime: 0
  });

  const startProfiling = useCallback(() => {
    performanceMonitor.startRenderProfiling(componentName);
  }, [componentName]);

  const endProfiling = useCallback(() => {
    const duration = performanceMonitor.endRenderProfiling(componentName);
    renderCountRef.current += 1;
    
    setRenderMetrics(prev => ({
      renderCount: renderCountRef.current,
      lastRenderTime: duration,
      averageRenderTime: ((prev.averageRenderTime * (renderCountRef.current - 1)) + duration) / renderCountRef.current
    }));

    return duration;
  }, [componentName]);

  // Auto-profile on every render
  useEffect(() => {
    startProfiling();
    return () => {
      endProfiling();
    };
  });

  return {
    ...renderMetrics,
    startProfiling,
    endProfiling
  };
}

/**
 * Hook for monitoring memory usage and detecting leaks
 */
export function useMemoryMonitor() {
  const [memoryInfo, setMemoryInfo] = useState<{
    heapUsed: number;
    heapTotal: number;
    heapLimit: number;
    isLeaking: boolean;
  } | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !('memory' in performance)) {
      console.warn('[USE-MEMORY-MONITOR] Memory API not available');
      return;
    }

    const checkMemory = () => {
      const memory = (performance as any).memory;
      const usageRatio = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
      
      setMemoryInfo({
        heapUsed: memory.usedJSHeapSize,
        heapTotal: memory.totalJSHeapSize,
        heapLimit: memory.jsHeapSizeLimit,
        isLeaking: usageRatio > 0.9 // Consider potential leak if using >90% of limit
      });
    };

    // Check memory usage every 5 seconds
    const interval = setInterval(checkMemory, 5000);
    checkMemory(); // Initial check

    return () => clearInterval(interval);
  }, []);

  const formatBytes = useCallback((bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  return {
    memoryInfo,
    formatBytes,
    usagePercentage: memoryInfo ? (memoryInfo.heapUsed / memoryInfo.heapLimit) * 100 : 0
  };
}

// ============================================================================
// MEMORY MANAGEMENT HOOKS
// ============================================================================

/**
 * Hook for automatic resource cleanup
 */
export function useMemoryManager(): MemoryManager {
  const memoryManagerRef = useRef<MemoryManager | null>(null);

  // Initialize memory manager if not exists
  if (!memoryManagerRef.current) {
    memoryManagerRef.current = new MemoryManager();
  }

  // Auto-cleanup on unmount
  useEffect(() => {
    const manager = memoryManagerRef.current!;
    
    return () => {
      manager.cleanup();
    };
  }, []);

  return memoryManagerRef.current;
}

/**
 * Hook for tracking subscriptions with automatic cleanup
 */
export function useSubscriptionManager() {
  const memoryManager = useMemoryManager();
  
  const trackSubscription = useCallback((subscription: { unsubscribe: () => void }) => {
    memoryManager.trackSubscription(subscription);
    return subscription;
  }, [memoryManager]);

  const trackTimer = useCallback((callback: () => void, delay: number) => {
    const timer = setTimeout(callback, delay);
    memoryManager.trackTimer(timer);
    return timer;
  }, [memoryManager]);

  const trackInterval = useCallback((callback: () => void, delay: number) => {
    const interval = setInterval(callback, delay);
    memoryManager.trackInterval(interval);
    return interval;
  }, [memoryManager]);

  const getResourceSummary = useCallback(() => {
    return memoryManager.getResourceSummary();
  }, [memoryManager]);

  return {
    trackSubscription,
    trackTimer,
    trackInterval,
    getResourceSummary,
    resourceCount: memoryManager.getResourceCount()
  };
}

// ============================================================================
// LAZY LOADING HOOKS
// ============================================================================

/**
 * Hook for lazy loading components or data
 */
export function useLazyLoad<T>(
  loadFn: () => Promise<T>,
  threshold: number = 0.1
) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isTriggered, setIsTriggered] = useState(false);
  const elementRef = useRef<HTMLElement | null>(null);

  const triggerLoad = useCallback(async () => {
    if (isTriggered) return;
    
    setIsTriggered(true);
    setIsLoading(true);
    setError(null);

    try {
      console.log('[USE-LAZY-LOAD] Loading data...');
      const result = await loadFn();
      setData(result);
      console.log('[USE-LAZY-LOAD] Data loaded successfully');
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Load failed');
      setError(error);
      console.error('[USE-LAZY-LOAD] Failed to load data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [loadFn, isTriggered]);

  const setRef = useCallback((element: HTMLElement | null) => {
    if (elementRef.current) {
      lazyLoadManager.unobserve(elementRef.current);
    }

    elementRef.current = element;

    if (element) {
      lazyLoadManager.observe(element, triggerLoad);
    }
  }, [triggerLoad]);

  // Manual trigger function
  const manualTrigger = useCallback(() => {
    triggerLoad();
  }, [triggerLoad]);

  return {
    data,
    isLoading,
    error,
    isTriggered,
    setRef,
    trigger: manualTrigger
  };
}

/**
 * Hook for lazy loading images with placeholder support
 */
export function useLazyImage(src: string, placeholder?: string) {
  const [imageSrc, setImageSrc] = useState(placeholder || '');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const { setRef, isTriggered } = useLazyLoad(
    useCallback(async () => {
      setIsLoading(true);
      
      return new Promise<string>((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          setImageSrc(src);
          setIsLoaded(true);
          setIsLoading(false);
          resolve(src);
        };
        img.onerror = () => {
          const error = new Error(`Failed to load image: ${src}`);
          setError(error);
          setIsLoading(false);
          reject(error);
        };
        img.src = src;
      });
    }, [src])
  );

  return {
    src: imageSrc,
    isLoaded,
    isLoading,
    error,
    setRef
  };
}

// ============================================================================
// VIRTUAL SCROLLING HOOKS
// ============================================================================

/**
 * Hook for virtual scrolling optimization
 */
export function useVirtualScroll<T>(
  items: T[],
  config: VirtualScrollConfig
) {
  const [scrollTop, setScrollTop] = useState(0);
  const virtualScrollManager = useRef(new VirtualScrollManager(config));

  const visibleRange = useMemo(() => {
    return virtualScrollManager.current.calculateVisibleRange(scrollTop, items.length);
  }, [scrollTop, items.length]);

  const visibleItems = useMemo(() => {
    return items.slice(visibleRange.startIndex, visibleRange.endIndex + 1)
      .map((item, index) => ({
        item,
        index: visibleRange.startIndex + index
      }));
  }, [items, visibleRange]);

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = event.currentTarget.scrollTop;
    setScrollTop(newScrollTop);
    virtualScrollManager.current.updateScrollPosition(newScrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight: visibleRange.totalHeight,
    offsetY: visibleRange.offsetY,
    handleScroll,
    startIndex: visibleRange.startIndex,
    endIndex: visibleRange.endIndex
  };
}

// ============================================================================
// RENDER OPTIMIZATION HOOKS
// ============================================================================

/**
 * Hook for debounced state updates
 */
export function useDebouncedState<T>(
  initialValue: T,
  delay: number = 300
): [T, T, (value: T) => void] {
  const [immediateValue, setImmediateValue] = useState(initialValue);
  const [debouncedValue, setDebouncedValue] = useState(initialValue);
  const timerRef = useRef<NodeJS.Timeout>();

  const setValue = useCallback((value: T) => {
    setImmediateValue(value);
    
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    
    timerRef.current = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
  }, [delay]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  return [immediateValue, debouncedValue, setValue];
}

/**
 * Hook for throttled state updates
 */
export function useThrottledState<T>(
  initialValue: T,
  delay: number = 100
): [T, (value: T) => void] {
  const [value, setValue] = useState(initialValue);
  const lastUpdateRef = useRef<number>(0);
  const pendingUpdateRef = useRef<T | null>(null);

  const setThrottledValue = useCallback((newValue: T) => {
    const now = Date.now();
    
    if (now - lastUpdateRef.current >= delay) {
      setValue(newValue);
      lastUpdateRef.current = now;
    } else {
      pendingUpdateRef.current = newValue;
      
      setTimeout(() => {
        if (pendingUpdateRef.current !== null) {
          setValue(pendingUpdateRef.current);
          pendingUpdateRef.current = null;
          lastUpdateRef.current = Date.now();
        }
      }, delay - (now - lastUpdateRef.current));
    }
  }, [delay]);

  return [value, setThrottledValue];
}

/**
 * Hook for preventing unnecessary re-renders
 */
export function useStableCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T {
  const callbackRef = useRef<T>(callback);
  
  useEffect(() => {
    callbackRef.current = callback;
  });

  return useCallback((...args: Parameters<T>) => {
    return callbackRef.current(...args);
  }, deps) as T;
}

// ============================================================================
// PERFORMANCE ANALYTICS HOOKS
// ============================================================================

/**
 * Hook for tracking component performance analytics
 */
export function usePerformanceAnalytics(componentName: string) {
  const [analytics, setAnalytics] = useState({
    mountTime: 0,
    updateCount: 0,
    totalUpdateTime: 0,
    averageUpdateTime: 0,
    lastUpdateTime: 0
  });

  const mountTimeRef = useRef<number>(Date.now());
  const renderProfiler = useRenderProfiler(componentName);

  useEffect(() => {
    const mountDuration = Date.now() - mountTimeRef.current;
    setAnalytics(prev => ({ ...prev, mountTime: mountDuration }));
  }, []);

  useEffect(() => {
    setAnalytics(prev => ({
      ...prev,
      updateCount: renderProfiler.renderCount,
      totalUpdateTime: prev.totalUpdateTime + renderProfiler.lastRenderTime,
      averageUpdateTime: renderProfiler.averageRenderTime,
      lastUpdateTime: renderProfiler.lastRenderTime
    }));
  }, [renderProfiler.renderCount, renderProfiler.lastRenderTime, renderProfiler.averageRenderTime]);

  const getPerformanceScore = useCallback(() => {
    const { mountTime, averageUpdateTime, updateCount } = analytics;
    
    // Simple scoring algorithm (0-100)
    let score = 100;
    
    // Penalize slow mount time
    if (mountTime > 100) score -= Math.min(30, (mountTime - 100) / 10);
    
    // Penalize slow updates
    if (averageUpdateTime > 16) score -= Math.min(40, (averageUpdateTime - 16) * 2);
    
    // Penalize excessive updates
    if (updateCount > 50) score -= Math.min(20, (updateCount - 50) / 5);
    
    return Math.max(0, Math.round(score));
  }, [analytics]);

  const getRecommendations = useCallback(() => {
    const recommendations = [];
    const { mountTime, averageUpdateTime, updateCount } = analytics;
    
    if (mountTime > 100) {
      recommendations.push('Consider lazy loading or code splitting to reduce mount time');
    }
    
    if (averageUpdateTime > 16) {
      recommendations.push('Use React.memo or useMemo to optimize render performance');
    }
    
    if (updateCount > 100) {
      recommendations.push('Check for unnecessary re-renders and optimize dependencies');
    }
    
    return recommendations;
  }, [analytics]);

  return {
    analytics,
    performanceScore: getPerformanceScore(),
    recommendations: getRecommendations()
  };
}