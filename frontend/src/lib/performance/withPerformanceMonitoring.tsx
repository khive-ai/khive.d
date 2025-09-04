"use client";

import React, { ComponentType, memo, useEffect, useRef, forwardRef } from 'react';
import { usePerformance } from './PerformanceProvider';

/**
 * Performance Monitoring Higher-Order Component
 * 
 * This HOC provides automatic performance monitoring for React components
 * following software architecture principles:
 * 
 * Principles Applied:
 * - Higher-Order Component Pattern: Composition over inheritance
 * - Decorator Pattern: Adds performance monitoring behavior
 * - Observer Pattern: Monitors and reports component performance
 * - Memoization Pattern: Automatic intelligent memoization
 * - Single Responsibility: Each HOC has one specific purpose
 */

export interface PerformanceMonitoringOptions {
  displayName?: string;
  enableMemoization?: boolean;
  memoizationKey?: (props: any) => string;
  trackProps?: boolean;
  slowRenderThreshold?: number; // milliseconds
  enableVirtualization?: boolean;
}

/**
 * HOC for automatic performance monitoring and optimization
 */
export function withPerformanceMonitoring<P extends object>(
  WrappedComponent: ComponentType<P>,
  options: PerformanceMonitoringOptions = {}
) {
  const {
    displayName = WrappedComponent.displayName || WrappedComponent.name || 'Component',
    enableMemoization = true,
    memoizationKey,
    trackProps = true,
    slowRenderThreshold = 16,
    enableVirtualization = false
  } = options;

  const PerformanceMonitoredComponent = forwardRef<any, P>((props, ref) => {
    const performance = usePerformance();
    const renderStartTime = useRef<number>();
    const componentId = useRef(`${displayName}_${Math.random().toString(36).substr(2, 9)}`);
    const previousProps = useRef<P>();

    // Track render start
    useEffect(() => {
      renderStartTime.current = performance?.config.enableMetrics ? Date.now() : undefined;
    });

    // Track render end and props changes
    useEffect(() => {
      if (!performance?.config.enableMetrics || !renderStartTime.current) return;

      const renderTime = Date.now() - renderStartTime.current;
      
      // Check for slow renders
      if (renderTime > slowRenderThreshold) {
        console.warn(
          `Slow render detected in ${displayName}: ${renderTime}ms`,
          { props, previousProps: previousProps.current }
        );
      }

      performance.recordRender(
        componentId.current,
        renderTime,
        trackProps ? props : undefined
      );

      previousProps.current = props;
    });

    // Performance monitoring lifecycle
    useEffect(() => {
      const stopMonitoring = performance?.startPerformanceMonitoring(componentId.current);
      return stopMonitoring;
    }, [performance]);

    return <WrappedComponent {...props} ref={ref} />;
  });

  // Apply memoization if enabled
  const FinalComponent = enableMemoization 
    ? memo(PerformanceMonitoredComponent, (prevProps, nextProps) => {
        if (memoizationKey) {
          return memoizationKey(prevProps) === memoizationKey(nextProps);
        }
        // Default shallow comparison
        return Object.keys(prevProps).every(key => 
          prevProps[key as keyof P] === nextProps[key as keyof P]
        ) && Object.keys(nextProps).every(key => 
          prevProps[key as keyof P] === nextProps[key as keyof P]
        );
      })
    : PerformanceMonitoredComponent;

  FinalComponent.displayName = `withPerformanceMonitoring(${displayName})`;

  return FinalComponent;
}

/**
 * HOC for automatic props optimization
 */
export function withPropsOptimization<P extends object>(
  WrappedComponent: ComponentType<P>,
  propsSelector?: (props: P) => Partial<P>
) {
  const PropsOptimizedComponent = memo<P>((props) => {
    const performance = usePerformance();
    
    // Use memoization for expensive prop computations
    const optimizedProps = performance.memoize(
      (props: P) => propsSelector ? { ...props, ...propsSelector(props) } : props,
      (props: P) => JSON.stringify(propsSelector ? propsSelector(props) : props)
    )(props);

    return <WrappedComponent {...optimizedProps} />;
  });

  PropsOptimizedComponent.displayName = `withPropsOptimization(${WrappedComponent.displayName || WrappedComponent.name})`;
  return PropsOptimizedComponent;
}

/**
 * HOC for lazy loading components
 */
export function withLazyLoading<P extends object>(
  WrappedComponent: ComponentType<P>,
  fallback: React.ReactNode = <div>Loading...</div>,
  threshold: number = 0.1
) {
  const LazyComponent = (props: P) => {
    const [isVisible, setIsVisible] = React.useState(false);
    const [hasLoaded, setHasLoaded] = React.useState(false);
    const elementRef = useRef<HTMLDivElement>(null);
    const performance = usePerformance();

    useEffect(() => {
      const lazyLoader = performance.createLazyLoader(threshold);
      
      if (elementRef.current) {
        lazyLoader.observe(elementRef.current, () => {
          setIsVisible(true);
          setHasLoaded(true);
        });
      }

      return () => {
        if (elementRef.current) {
          lazyLoader.unobserve(elementRef.current);
        }
      };
    }, [performance, threshold]);

    if (!isVisible && !hasLoaded) {
      return <div ref={elementRef}>{fallback}</div>;
    }

    return <WrappedComponent {...props} />;
  };

  LazyComponent.displayName = `withLazyLoading(${WrappedComponent.displayName || WrappedComponent.name})`;
  return LazyComponent;
}

/**
 * HOC for virtual scrolling optimization
 */
export function withVirtualScrolling<P extends { items: any[]; itemHeight: number }>(
  WrappedComponent: ComponentType<P>,
  containerHeight: number = 400
) {
  const VirtualizedComponent = (props: P) => {
    const { items, itemHeight, ...otherProps } = props;
    const performance = usePerformance();
    const containerRef = useRef<HTMLDivElement>(null);
    
    const virtualList = performance.createVirtualList(items, itemHeight, containerHeight);

    return (
      <div 
        ref={containerRef}
        style={{ height: containerHeight, overflow: 'auto' }}
        onScroll={virtualList.onScroll}
      >
        <div style={{ height: virtualList.totalHeight, position: 'relative' }}>
          <div style={{ transform: `translateY(${virtualList.offsetY}px)` }}>
            <WrappedComponent 
              {...otherProps as P}
              items={virtualList.visibleItems}
              itemHeight={itemHeight}
            />
          </div>
        </div>
      </div>
    );
  };

  VirtualizedComponent.displayName = `withVirtualScrolling(${WrappedComponent.displayName || WrappedComponent.name})`;
  return VirtualizedComponent;
}

/**
 * Hook for manual performance monitoring
 */
export function useComponentPerformance(componentName: string) {
  const performance = usePerformance();
  const renderCount = useRef(0);
  const startTime = useRef<number>();

  const startRender = React.useCallback(() => {
    if (performance.config.enableMetrics) {
      startTime.current = performance.startPerformanceMonitoring(componentName);
      renderCount.current++;
    }
  }, [performance, componentName]);

  const endRender = React.useCallback(() => {
    if (startTime.current) {
      startTime.current();
      startTime.current = undefined;
    }
  }, []);

  return {
    startRender,
    endRender,
    renderCount: renderCount.current,
    getMetrics: () => performance.getComponentMetrics(componentName)
  };
}

/**
 * Hook for optimized callbacks
 */
export function useOptimizedCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList,
  mode: 'debounce' | 'throttle' = 'debounce',
  delay?: number
): T {
  const performance = usePerformance();
  
  return React.useMemo(() => {
    if (mode === 'debounce') {
      return performance.debounceCallback(callback, delay);
    } else {
      return performance.throttleCallback(callback, delay);
    }
  }, [...deps, performance, mode, delay]);
}

/**
 * Hook for performance-optimized state updates
 */
export function useOptimizedState<T>(
  initialValue: T,
  updateMode: 'debounced' | 'throttled' | 'immediate' = 'immediate'
) {
  const [value, setValue] = React.useState<T>(initialValue);
  const performance = usePerformance();
  
  const optimizedSetValue = React.useMemo(() => {
    switch (updateMode) {
      case 'debounced':
        return performance.debounceCallback(setValue, 300);
      case 'throttled':
        return performance.throttleCallback(setValue, 16);
      default:
        return setValue;
    }
  }, [performance, updateMode]);

  return [value, optimizedSetValue] as const;
}

/**
 * Performance debugging utilities
 */
export function PerformanceDebugger() {
  const performance = usePerformance();
  const [report, setReport] = React.useState<any>(null);
  const [isVisible, setIsVisible] = React.useState(false);

  React.useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;

    const interval = setInterval(() => {
      setReport(performance.getPerformanceReport());
    }, 5000);

    return () => clearInterval(interval);
  }, [performance]);

  if (process.env.NODE_ENV !== 'development' || !isVisible) {
    return (
      <button 
        onClick={() => setIsVisible(true)}
        style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          zIndex: 9999,
          padding: '8px 12px',
          backgroundColor: '#007acc',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Performance
      </button>
    );
  }

  return (
    <div style={{
      position: 'fixed',
      top: 20,
      right: 20,
      width: 300,
      maxHeight: 400,
      backgroundColor: 'white',
      border: '1px solid #ccc',
      borderRadius: '4px',
      padding: 16,
      zIndex: 9999,
      overflow: 'auto',
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>Performance Monitor</h3>
        <button onClick={() => setIsVisible(false)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}>
          ×
        </button>
      </div>
      
      {report && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <strong>Components:</strong> {report.summary.totalComponents}
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong>Avg Render:</strong> {report.summary.averageRenderTime.toFixed(2)}ms
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong>Slowest:</strong> {report.summary.slowestComponent}
          </div>
          
          {report.recommendations.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <strong>Recommendations:</strong>
              <ul style={{ fontSize: '12px', margin: '8px 0', paddingLeft: 16 }}>
                {report.recommendations.slice(0, 3).map((rec: string, i: number) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}