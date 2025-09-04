/**
 * Comprehensive Performance Optimization Patterns & Error Boundaries
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Architecture Patterns:
 * - React Error Boundaries with recovery mechanisms
 * - Performance monitoring and profiling
 * - Memory leak detection and prevention
 * - Lazy loading and code splitting strategies
 * - Virtual scrolling and render optimization
 * - Network request optimization and caching
 * - Resource cleanup and lifecycle management
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { BehaviorSubject, Observable, fromEvent, timer, combineLatest } from 'rxjs';
import { 
  map, 
  debounceTime, 
  scan, 
  distinctUntilChanged, 
  shareReplay,
  filter
} from 'rxjs/operators';

// ============================================================================
// PERFORMANCE MONITORING SYSTEM
// ============================================================================

export interface PerformanceMetrics {
  timestamp: number;
  // React Performance
  renderTime: number;
  componentCount: number;
  updateCount: number;
  memorizedHitRatio: number;
  
  // JavaScript Performance
  heapUsed: number;
  heapTotal: number;
  heapLimit: number;
  
  // Network Performance
  requestCount: number;
  requestDuration: number;
  cacheHitRatio: number;
  
  // User Experience
  fcp: number; // First Contentful Paint
  lcp: number; // Largest Contentful Paint
  fid: number; // First Input Delay
  cls: number; // Cumulative Layout Shift
  
  // Custom Metrics
  agentResponseTime: number;
  coordinationEfficiency: number;
  memoryLeaks: number;
}

export interface PerformanceAlert {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  metric: keyof PerformanceMetrics;
  threshold: number;
  currentValue: number;
  message: string;
  suggestedActions: string[];
  timestamp: number;
}

export class PerformanceMonitor {
  private metricsSubject = new BehaviorSubject<PerformanceMetrics>(this.getInitialMetrics());
  private alertsSubject = new BehaviorSubject<PerformanceAlert[]>([]);
  private observer: PerformanceObserver | null = null;
  private memoryObserver: NodeJS.Timeout | null = null;
  private renderProfiler: Map<string, { start: number; renders: number }> = new Map();
  
  // Performance thresholds
  private thresholds = {
    renderTime: { warning: 16, critical: 33 }, // 60fps = 16ms, 30fps = 33ms
    heapUsage: { warning: 50 * 1024 * 1024, critical: 100 * 1024 * 1024 }, // 50MB, 100MB
    requestDuration: { warning: 1000, critical: 3000 }, // 1s, 3s
    cacheHitRatio: { warning: 0.7, critical: 0.5 }, // 70%, 50%
    fcp: { warning: 2000, critical: 4000 }, // 2s, 4s
    lcp: { warning: 2500, critical: 4000 }, // 2.5s, 4s
    fid: { warning: 100, critical: 300 }, // 100ms, 300ms
    cls: { warning: 0.1, critical: 0.25 } // Layout shift scores
  };

  constructor() {
    this.initializePerformanceObserver();
    this.initializeMemoryMonitoring();
    this.startMetricsCollection();
    
    console.log('[PERF-MONITOR] Performance monitoring initialized');
  }

  private getInitialMetrics(): PerformanceMetrics {
    return {
      timestamp: Date.now(),
      renderTime: 0,
      componentCount: 0,
      updateCount: 0,
      memorizedHitRatio: 0,
      heapUsed: 0,
      heapTotal: 0,
      heapLimit: 0,
      requestCount: 0,
      requestDuration: 0,
      cacheHitRatio: 0,
      fcp: 0,
      lcp: 0,
      fid: 0,
      cls: 0,
      agentResponseTime: 0,
      coordinationEfficiency: 0,
      memoryLeaks: 0
    };
  }

  private initializePerformanceObserver(): void {
    if (typeof window === 'undefined' || !window.PerformanceObserver) return;

    try {
      this.observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        this.processPerformanceEntries(entries);
      });

      // Observe various performance entry types
      this.observer.observe({ entryTypes: ['measure', 'navigation', 'paint', 'largest-contentful-paint'] });
      
      console.log('[PERF-MONITOR] PerformanceObserver initialized');
    } catch (error) {
      console.warn('[PERF-MONITOR] PerformanceObserver not supported:', error);
    }
  }

  private initializeMemoryMonitoring(): void {
    if (typeof window === 'undefined') return;

    // Monitor memory usage every 5 seconds
    this.memoryObserver = setInterval(() => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        this.updateMemoryMetrics(memory);
      }
      
      this.detectMemoryLeaks();
    }, 5000);
  }

  private startMetricsCollection(): void {
    // Collect metrics every second
    timer(0, 1000).subscribe(() => {
      const currentMetrics = this.collectCurrentMetrics();
      this.metricsSubject.next(currentMetrics);
      this.checkThresholds(currentMetrics);
    });
  }

  private processPerformanceEntries(entries: PerformanceEntry[]): void {
    entries.forEach(entry => {
      switch (entry.entryType) {
        case 'paint':
          if (entry.name === 'first-contentful-paint') {
            this.updateMetric('fcp', entry.startTime);
          }
          break;
        
        case 'largest-contentful-paint':
          this.updateMetric('lcp', entry.startTime);
          break;
        
        case 'measure':
          if (entry.name.startsWith('React')) {
            this.updateMetric('renderTime', entry.duration);
          }
          break;
      }
    });
  }

  private updateMemoryMetrics(memory: any): void {
    this.updateMetric('heapUsed', memory.usedJSHeapSize);
    this.updateMetric('heapTotal', memory.totalJSHeapSize);
    this.updateMetric('heapLimit', memory.jsHeapSizeLimit);
  }

  private collectCurrentMetrics(): PerformanceMetrics {
    const current = this.metricsSubject.getValue();
    
    return {
      ...current,
      timestamp: Date.now(),
      // Additional real-time calculations would go here
    };
  }

  private updateMetric<K extends keyof PerformanceMetrics>(
    metric: K, 
    value: PerformanceMetrics[K]
  ): void {
    const current = this.metricsSubject.getValue();
    this.metricsSubject.next({
      ...current,
      [metric]: value,
      timestamp: Date.now()
    });
  }

  private checkThresholds(metrics: PerformanceMetrics): void {
    const alerts: PerformanceAlert[] = [];

    Object.entries(this.thresholds).forEach(([metricName, thresholds]) => {
      const metric = metricName as keyof PerformanceMetrics;
      const value = metrics[metric] as number;
      
      if (value > thresholds.critical) {
        alerts.push(this.createAlert(metric, 'critical', value, thresholds.critical));
      } else if (value > thresholds.warning) {
        alerts.push(this.createAlert(metric, 'high', value, thresholds.warning));
      }
    });

    if (alerts.length > 0) {
      this.alertsSubject.next(alerts);
    }
  }

  private createAlert(
    metric: keyof PerformanceMetrics,
    severity: PerformanceAlert['severity'],
    currentValue: number,
    threshold: number
  ): PerformanceAlert {
    const messages = {
      renderTime: 'Render performance is degraded',
      heapUsed: 'Memory usage is high',
      requestDuration: 'Network requests are slow',
      cacheHitRatio: 'Cache hit ratio is low',
      fcp: 'First Contentful Paint is slow',
      lcp: 'Largest Contentful Paint is slow',
      fid: 'First Input Delay is high',
      cls: 'Cumulative Layout Shift is high'
    };

    const actions = {
      renderTime: ['Use React.memo', 'Optimize re-renders', 'Implement virtual scrolling'],
      heapUsed: ['Check for memory leaks', 'Optimize data structures', 'Clear unused references'],
      requestDuration: ['Implement request caching', 'Optimize API endpoints', 'Use request batching'],
      cacheHitRatio: ['Improve caching strategy', 'Increase cache size', 'Optimize cache keys'],
      fcp: ['Optimize bundle size', 'Use code splitting', 'Implement lazy loading'],
      lcp: ['Optimize images', 'Preload critical resources', 'Minimize layout shifts'],
      fid: ['Reduce JavaScript execution time', 'Use web workers', 'Optimize event handlers'],
      cls: ['Specify dimensions for media', 'Avoid dynamic content insertion', 'Use CSS containment']
    };

    return {
      id: `alert_${metric}_${Date.now()}`,
      severity,
      metric,
      threshold,
      currentValue,
      message: messages[metric] || `${metric} threshold exceeded`,
      suggestedActions: actions[metric] || ['Investigate performance issue'],
      timestamp: Date.now()
    };
  }

  private detectMemoryLeaks(): void {
    const current = this.metricsSubject.getValue();
    
    // Simple memory leak detection - would be more sophisticated in production
    if (current.heapUsed > 0) {
      const growthRate = current.heapUsed / (current.heapTotal || 1);
      if (growthRate > 0.9) {
        this.updateMetric('memoryLeaks', current.memoryLeaks + 1);
        console.warn('[PERF-MONITOR] Potential memory leak detected');
      }
    }
  }

  // Public API
  getMetricsStream(): Observable<PerformanceMetrics> {
    return this.metricsSubject.asObservable();
  }

  getAlertsStream(): Observable<PerformanceAlert[]> {
    return this.alertsSubject.asObservable();
  }

  startRenderProfiling(componentName: string): void {
    this.renderProfiler.set(componentName, {
      start: performance.now(),
      renders: (this.renderProfiler.get(componentName)?.renders || 0) + 1
    });
  }

  endRenderProfiling(componentName: string): number {
    const profile = this.renderProfiler.get(componentName);
    if (profile) {
      const duration = performance.now() - profile.start;
      console.log(`[PERF-MONITOR] ${componentName} render: ${duration.toFixed(2)}ms (render #${profile.renders})`);
      return duration;
    }
    return 0;
  }

  recordCustomMetric(metric: keyof PerformanceMetrics, value: number): void {
    this.updateMetric(metric, value as any);
  }

  dispose(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    
    if (this.memoryObserver) {
      clearInterval(this.memoryObserver);
      this.memoryObserver = null;
    }
    
    console.log('[PERF-MONITOR] Performance monitor disposed');
  }
}

// ============================================================================
// ERROR BOUNDARY SYSTEM
// ============================================================================

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string | null;
  retryCount: number;
  lastErrorTime: number;
}

export interface ErrorBoundaryConfig {
  maxRetries: number;
  resetTimeoutMs: number;
  fallbackComponent?: React.ComponentType<{ error: Error; retry: () => void }>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  enableRecovery: boolean;
  logErrors: boolean;
}

export class EnhancedErrorBoundary extends Component<
  { children: ReactNode; config?: Partial<ErrorBoundaryConfig> },
  ErrorBoundaryState
> {
  private config: ErrorBoundaryConfig;
  private resetTimer: NodeJS.Timeout | null = null;

  constructor(props: { children: ReactNode; config?: Partial<ErrorBoundaryConfig> }) {
    super(props);
    
    this.config = {
      maxRetries: 3,
      resetTimeoutMs: 5000,
      enableRecovery: true,
      logErrors: true,
      ...props.config
    };

    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      retryCount: 0,
      lastErrorTime: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
      errorId: `error_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      lastErrorTime: Date.now()
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const errorId = this.state.errorId || 'unknown';
    
    if (this.config.logErrors) {
      console.error(`[ERROR-BOUNDARY] ${errorId}:`, error);
      console.error('[ERROR-BOUNDARY] Component stack:', errorInfo.componentStack);
    }

    this.setState(prevState => ({
      errorInfo,
      retryCount: prevState.retryCount + 1
    }));

    // Report error to monitoring service
    this.reportError(error, errorInfo, errorId);

    // Call custom error handler
    if (this.config.onError) {
      this.config.onError(error, errorInfo);
    }

    // Set up auto-recovery if enabled
    if (this.config.enableRecovery && this.state.retryCount < this.config.maxRetries) {
      this.scheduleReset();
    }
  }

  private reportError(error: Error, errorInfo: ErrorInfo, errorId: string): void {
    // In production, would send to error tracking service
    const errorReport = {
      id: errorId,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: Date.now(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      retryCount: this.state.retryCount
    };

    console.log('[ERROR-BOUNDARY] Error report:', errorReport);
    
    // Example: Send to monitoring service
    // fetch('/api/errors', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(errorReport)
    // });
  }

  private scheduleReset(): void {
    if (this.resetTimer) {
      clearTimeout(this.resetTimer);
    }

    this.resetTimer = setTimeout(() => {
      console.log(`[ERROR-BOUNDARY] Auto-recovery attempt ${this.state.retryCount}`);
      this.handleRetry();
    }, this.config.resetTimeoutMs);
  }

  private handleRetry = (): void => {
    if (this.state.retryCount >= this.config.maxRetries) {
      console.error('[ERROR-BOUNDARY] Max retries exceeded, giving up');
      return;
    }

    console.log('[ERROR-BOUNDARY] Retrying after error...');
    
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
      // Don't reset retryCount to prevent infinite loops
    });
  };

  componentWillUnmount(): void {
    if (this.resetTimer) {
      clearTimeout(this.resetTimer);
      this.resetTimer = null;
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const { error, retryCount } = this.state;
      
      // Use custom fallback component if provided
      if (this.config.fallbackComponent) {
        const FallbackComponent = this.config.fallbackComponent;
        return <FallbackComponent error={error!} retry={this.handleRetry} />;
      }

      // Default error UI
      return (
        <div style={{ 
          padding: '20px', 
          border: '2px solid #ff6b6b', 
          borderRadius: '8px', 
          backgroundColor: '#fff5f5',
          margin: '20px 0'
        }}>
          <h2 style={{ color: '#c92a2a', margin: '0 0 10px 0' }}>
            Something went wrong
          </h2>
          <p style={{ margin: '0 0 15px 0', color: '#495057' }}>
            {error?.message || 'An unexpected error occurred'}
          </p>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              onClick={this.handleRetry}
              disabled={retryCount >= this.config.maxRetries}
              style={{
                padding: '8px 16px',
                backgroundColor: retryCount >= this.config.maxRetries ? '#ccc' : '#4dabf7',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: retryCount >= this.config.maxRetries ? 'not-allowed' : 'pointer'
              }}
            >
              {retryCount >= this.config.maxRetries ? 'Max retries exceeded' : `Retry (${retryCount}/${this.config.maxRetries})`}
            </button>
            <span style={{ fontSize: '12px', color: '#868e96' }}>
              Error ID: {this.state.errorId}
            </span>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// ============================================================================
// MEMORY MANAGEMENT UTILITIES
// ============================================================================

export class MemoryManager {
  private subscriptions = new Set<{ unsubscribe: () => void }>();
  private timers = new Set<NodeJS.Timeout>();
  private intervals = new Set<NodeJS.Timeout>();
  private observers = new Set<{ disconnect: () => void }>();
  private eventListeners = new Set<{
    element: EventTarget;
    event: string;
    handler: EventListener;
  }>();

  // Track subscription for cleanup
  trackSubscription(subscription: { unsubscribe: () => void }): void {
    this.subscriptions.add(subscription);
  }

  // Track timer for cleanup
  trackTimer(timer: NodeJS.Timeout): void {
    this.timers.add(timer);
  }

  // Track interval for cleanup
  trackInterval(interval: NodeJS.Timeout): void {
    this.intervals.add(interval);
  }

  // Track observer for cleanup
  trackObserver(observer: { disconnect: () => void }): void {
    this.observers.add(observer);
  }

  // Track event listener for cleanup
  trackEventListener(
    element: EventTarget,
    event: string,
    handler: EventListener
  ): void {
    this.eventListeners.add({ element, event, handler });
    element.addEventListener(event, handler);
  }

  // Clean up all tracked resources
  cleanup(): void {
    console.log(`[MEMORY-MANAGER] Cleaning up ${this.getResourceCount()} resources`);

    // Clean up subscriptions
    this.subscriptions.forEach(sub => {
      try {
        sub.unsubscribe();
      } catch (error) {
        console.warn('[MEMORY-MANAGER] Error unsubscribing:', error);
      }
    });
    this.subscriptions.clear();

    // Clean up timers
    this.timers.forEach(timer => clearTimeout(timer));
    this.timers.clear();

    // Clean up intervals
    this.intervals.forEach(interval => clearInterval(interval));
    this.intervals.clear();

    // Clean up observers
    this.observers.forEach(observer => {
      try {
        observer.disconnect();
      } catch (error) {
        console.warn('[MEMORY-MANAGER] Error disconnecting observer:', error);
      }
    });
    this.observers.clear();

    // Clean up event listeners
    this.eventListeners.forEach(({ element, event, handler }) => {
      try {
        element.removeEventListener(event, handler);
      } catch (error) {
        console.warn('[MEMORY-MANAGER] Error removing event listener:', error);
      }
    });
    this.eventListeners.clear();

    console.log('[MEMORY-MANAGER] Cleanup completed');
  }

  getResourceCount(): number {
    return (
      this.subscriptions.size +
      this.timers.size +
      this.intervals.size +
      this.observers.size +
      this.eventListeners.size
    );
  }

  getResourceSummary(): Record<string, number> {
    return {
      subscriptions: this.subscriptions.size,
      timers: this.timers.size,
      intervals: this.intervals.size,
      observers: this.observers.size,
      eventListeners: this.eventListeners.size
    };
  }
}

// ============================================================================
// LAZY LOADING UTILITIES
// ============================================================================

export interface LazyLoadConfig {
  threshold: number; // Intersection threshold (0-1)
  rootMargin: string; // CSS margin string
  triggerOnce: boolean; // Whether to trigger only once
}

export class LazyLoadManager {
  private observer: IntersectionObserver | null = null;
  private elements = new Map<Element, () => void>();

  constructor(config: LazyLoadConfig = {
    threshold: 0.1,
    rootMargin: '50px',
    triggerOnce: true
  }) {
    if (typeof window !== 'undefined' && 'IntersectionObserver' in window) {
      this.observer = new IntersectionObserver(
        this.handleIntersection.bind(this),
        {
          threshold: config.threshold,
          rootMargin: config.rootMargin
        }
      );
    }
  }

  observe(element: Element, callback: () => void): void {
    if (!this.observer) {
      // Fallback: trigger immediately if IntersectionObserver not available
      callback();
      return;
    }

    this.elements.set(element, callback);
    this.observer.observe(element);
  }

  unobserve(element: Element): void {
    if (this.observer) {
      this.observer.unobserve(element);
      this.elements.delete(element);
    }
  }

  private handleIntersection(entries: IntersectionObserverEntry[]): void {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const callback = this.elements.get(entry.target);
        if (callback) {
          callback();
          // Remove from observation after triggering
          this.unobserve(entry.target);
        }
      }
    });
  }

  disconnect(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
      this.elements.clear();
    }
  }
}

// ============================================================================
// VIRTUAL SCROLLING UTILITIES
// ============================================================================

export interface VirtualScrollConfig {
  itemHeight: number;
  containerHeight: number;
  overscan: number; // Number of extra items to render
}

export class VirtualScrollManager {
  private config: VirtualScrollConfig;
  private scrollTop = 0;
  private totalItems = 0;

  constructor(config: VirtualScrollConfig) {
    this.config = config;
  }

  calculateVisibleRange(scrollTop: number, totalItems: number): {
    startIndex: number;
    endIndex: number;
    offsetY: number;
    totalHeight: number;
  } {
    this.scrollTop = scrollTop;
    this.totalItems = totalItems;

    const { itemHeight, containerHeight, overscan } = this.config;
    
    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const endIndex = Math.min(totalItems - 1, startIndex + visibleCount + overscan * 2);
    
    const offsetY = startIndex * itemHeight;
    const totalHeight = totalItems * itemHeight;

    return {
      startIndex,
      endIndex,
      offsetY,
      totalHeight
    };
  }

  updateScrollPosition(scrollTop: number): void {
    this.scrollTop = scrollTop;
  }

  getScrollTop(): number {
    return this.scrollTop;
  }
}

// Export singleton instances
export const performanceMonitor = new PerformanceMonitor();
export const globalMemoryManager = new MemoryManager();
export const lazyLoadManager = new LazyLoadManager();