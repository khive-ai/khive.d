// Virtual scrolling hook for high-performance rendering of large lists
import { useState, useEffect, useMemo, useCallback } from 'react';

export interface VirtualScrollConfig {
  itemHeight: number;
  containerHeight: number;
  overscan: number;
  estimatedItemHeight?: number;
  enableDynamicHeight?: boolean;
}

export interface VirtualScrollResult {
  startIndex: number;
  endIndex: number;
  visibleItems: number;
  totalHeight: number;
  offsetY: number;
  scrollToIndex: (index: number) => void;
  scrollToTop: () => void;
  scrollToBottom: () => void;
}

export function useVirtualScroll<T>(
  items: T[],
  config: VirtualScrollConfig,
  scrollElement: HTMLElement | null
): VirtualScrollResult {
  const [scrollTop, setScrollTop] = useState(0);
  const [measuredHeights, setMeasuredHeights] = useState<Map<number, number>>(new Map());

  const {
    itemHeight,
    containerHeight,
    overscan,
    enableDynamicHeight = false,
    estimatedItemHeight = itemHeight,
  } = config;

  // Calculate visible range
  const { startIndex, endIndex, totalHeight, offsetY } = useMemo(() => {
    if (items.length === 0) {
      return { startIndex: 0, endIndex: 0, totalHeight: 0, offsetY: 0 };
    }

    let start = 0;
    let end = items.length - 1;
    let offset = 0;
    let total = 0;

    if (enableDynamicHeight) {
      // Dynamic height calculation
      let currentY = 0;
      start = items.length; // Start with invalid index
      
      for (let i = 0; i < items.length; i++) {
        const height = measuredHeights.get(i) || estimatedItemHeight;
        
        if (currentY + height >= scrollTop && start === items.length) {
          start = Math.max(0, i - overscan);
          offset = currentY - (overscan * estimatedItemHeight);
        }
        
        if (currentY > scrollTop + containerHeight && end === items.length - 1) {
          end = Math.min(items.length - 1, i + overscan);
          break;
        }
        
        currentY += height;
      }
      
      // If we haven't found the end yet, we're at the bottom
      if (end === items.length - 1) {
        end = Math.min(items.length - 1, start + Math.ceil(containerHeight / estimatedItemHeight) + overscan * 2);
      }
      
      total = currentY;
    } else {
      // Fixed height calculation (much faster)
      start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
      end = Math.min(
        items.length - 1,
        Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
      );
      offset = start * itemHeight;
      total = items.length * itemHeight;
    }

    return {
      startIndex: start,
      endIndex: end,
      totalHeight: total,
      offsetY: Math.max(0, offset),
    };
  }, [
    items.length,
    scrollTop,
    containerHeight,
    itemHeight,
    overscan,
    enableDynamicHeight,
    estimatedItemHeight,
    measuredHeights,
  ]);

  // Handle scroll events
  useEffect(() => {
    if (!scrollElement) return;

    const handleScroll = () => {
      setScrollTop(scrollElement.scrollTop);
    };

    scrollElement.addEventListener('scroll', handleScroll, { passive: true });
    return () => scrollElement.removeEventListener('scroll', handleScroll);
  }, [scrollElement]);

  // Scroll utilities
  const scrollToIndex = useCallback((index: number) => {
    if (!scrollElement || index < 0 || index >= items.length) return;

    let targetScrollTop: number;
    
    if (enableDynamicHeight) {
      // Calculate scroll position for dynamic heights
      targetScrollTop = 0;
      for (let i = 0; i < index; i++) {
        targetScrollTop += measuredHeights.get(i) || estimatedItemHeight;
      }
    } else {
      targetScrollTop = index * itemHeight;
    }

    scrollElement.scrollTo({ top: targetScrollTop, behavior: 'smooth' });
  }, [scrollElement, items.length, itemHeight, enableDynamicHeight, estimatedItemHeight, measuredHeights]);

  const scrollToTop = useCallback(() => {
    if (!scrollElement) return;
    scrollElement.scrollTo({ top: 0, behavior: 'smooth' });
  }, [scrollElement]);

  const scrollToBottom = useCallback(() => {
    if (!scrollElement) return;
    scrollElement.scrollTo({ top: totalHeight, behavior: 'smooth' });
  }, [scrollElement, totalHeight]);

  // Measure item height (for dynamic heights)
  const measureItem = useCallback((index: number, height: number) => {
    if (!enableDynamicHeight) return;
    
    setMeasuredHeights(prev => {
      const newMap = new Map(prev);
      if (newMap.get(index) !== height) {
        newMap.set(index, height);
        return newMap;
      }
      return prev;
    });
  }, [enableDynamicHeight]);

  return {
    startIndex,
    endIndex,
    visibleItems: endIndex - startIndex + 1,
    totalHeight,
    offsetY,
    scrollToIndex,
    scrollToTop,
    scrollToBottom,
    measureItem,
  } as VirtualScrollResult & { measureItem?: (index: number, height: number) => void };
}

// Hook for measuring item heights dynamically
export function useItemMeasurement(
  ref: React.RefObject<HTMLElement>,
  index: number,
  measureItem?: (index: number, height: number) => void
): void {
  useEffect(() => {
    if (!ref.current || !measureItem) return;
    
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const height = entry.contentRect.height;
        measureItem(index, height);
      }
    });
    
    resizeObserver.observe(ref.current);
    
    return () => resizeObserver.disconnect();
  }, [ref, index, measureItem]);
}